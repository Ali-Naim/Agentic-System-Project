from openai import OpenAI
from typing import Dict, Any
import json
import os
from dotenv import load_dotenv

from moodle_integration import MoodleIntegration
from memory import ConversationMemory
from mcp_integration import MCPClient
from tools import (
    QuizTools, GradingTools, AnnouncementTools,
    PerformanceTools, StudyTools, ResourceTools
)
from models import QuizRequest, GradingRequest, AnnouncementRequest

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

class AcademicAIAgent:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.moodle = MoodleIntegration()
        self.mcp_client = MCPClient()
        self.memory = ConversationMemory(max_turns=5)
        self.tool_schemas = self._build_tool_schemas()
        self.quiz_tools = QuizTools(self.client)
        self.grading_tools = GradingTools(self.client)
        self.announcement_tools = AnnouncementTools(self.client)
        self.performance_tools = PerformanceTools(self.client)
        self.study_tools = StudyTools(self.client)
        self.resource_tools = ResourceTools(self.client)

    def _build_tool_schemas(self) -> Dict[str, Dict]:
        """Extract schemas from Pydantic models"""
        return {
            "generate_quiz": QuizRequest.model_json_schema(),
            "grade_assignment": GradingRequest.model_json_schema(),
            "post_announcement": AnnouncementRequest.model_json_schema(),
        }

    def _format_tools_for_prompt(self) -> str:
        """Format tool schemas for prompts"""
        formatted = ""
        for tool_name, schema in self.tool_schemas.items():
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            formatted += f"\n- {tool_name}:\n"
            formatted += f"  Description: {schema.get('description', 'No description')}\n"
            formatted += f"  Required: {', '.join(required)}\n"
            formatted += f"  Parameters: {', '.join(properties.keys())}\n"
        
        return formatted

    def analyze_intent(self, user_prompt: str) -> Dict:
        """Analyze user intent and determine which tool to use"""
        
        tools_description = self._format_tools_for_prompt()
        memory_context = self.memory.get_context()
        
        prompt = f"""
        Analyze this user request and determine the appropriate action.
        
        {memory_context}
        
        Current User Request: {user_prompt}
        
        Available Actions and their required parameters:
        {tools_description}
        
        IMPORTANT RULES:
        1. If a required parameter is NOT mentioned in the user request or recent history, add it to "missing_parameters"
        2. ONLY include parameters in "parameters" if the user explicitly provided them
        3. Do NOT make up values like "value", "default", "example", etc.
        4. For missing parameters, leave them OUT of the parameters dict
        5. Use context from previous messages to infer parameters when appropriate
        
        Return ONLY valid JSON (no markdown, no extra text):
        {{
            "intent": "tool_name",
            "parameters": {{"param1": "actual_value"}},
            "missing_parameters": ["param_name1", "param_name2"],
            "clarification_question": "What course would you like the quiz for?",
            "confidence": 0.95
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"❌ Error in analyze_intent: {str(e)}")
            return {"intent": "error", "parameters": {}, "confidence": 0.0}

    def handle_user_request(self, user_prompt: str, context: Dict = None) -> Dict:
        """Main entry point - analyzes intent and routes to appropriate tool"""
        intent_analysis = self.analyze_intent(user_prompt)
        
        print(f"Intent Analysis: {intent_analysis}")
        
        if intent_analysis.get("missing_parameters"):
            response = {
                "status": "incomplete",
                "intent": intent_analysis["intent"],
                "missing_parameters": intent_analysis["missing_parameters"],
                "clarification_question": intent_analysis.get("clarification_question"),
                "message": f"I need more information to proceed. {intent_analysis.get('clarification_question', 'Please provide the missing parameters.')}"
            }
            
            self.memory.add(user_prompt, response["message"])
            return response
        
        try:
            result = self.call_tool(
                intent_analysis["intent"], 
                intent_analysis["parameters"]
            )
            
            success_message = f"✅ Successfully executed {intent_analysis['intent']}"
            self.memory.add(user_prompt, success_message)
            
            return {
                "status": "success",
                "intent": intent_analysis["intent"],
                "result": result,
                "confidence": intent_analysis["confidence"]
            }
        except Exception as e:
            error_message = f"❌ Error: {str(e)}"
            self.memory.add(user_prompt, error_message)
            
            return {
                "status": "error",
                "error": str(e),
                "intent": intent_analysis["intent"]
            }

    def call_tool(self, tool_name: str, params: dict):
        """Call a tool through MCP"""
        return self.mcp_client.call_tool(tool_name, params)

    def list_tools(self):
        """List available tools"""
        return self.mcp_client.list_tools()

    # Expose memory methods
    def clear_memory(self):
        self.memory.clear()

    def get_memory(self):
        return self.memory.get_history()

    def get_conversation_history(self):
        return self.memory.conversation_history