# app/ai_agent.py
from openai import OpenAI
import instructor
from typing import List, Dict, Any
import json
import requests  # ✅ missing import
from moodle_integration import MoodleIntegration
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

class AcademicAIAgent:
    def __init__(self):
        # ✅ no need to use instructor.patch unless you’re using structured outputs from Instructor library
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.moodle = MoodleIntegration()
        self.mcp_base_url = "http://localhost:8000/mcp"

    def analyze_intent(self, user_prompt: str) -> Dict:
        """Analyze user intent and determine which tool to use"""
        prompt = f"""
        Analyze this user request and determine the appropriate action.
        
        User Request: {user_prompt}
        
        Available Actions:
        - generate_quiz: When user wants to create a quiz/test
        - grade_assignment: When user wants to grade student work
        - post_announcement: When user wants to post announcements
        - analyze_performance: When user wants student performance analysis
        - answer_question: When user asks general questions
        - create_study_plan: When user wants study plans
        - send_reminders: When user wants to send reminders
        
        Return JSON:
        {{
            "intent": "tool_name",
            "parameters": {{"param1": "value1", ...}},
            "confidence": 0.95
        }}
        """
        print(prompt)

        try:
            response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
            )

        except Exception as e:
            print(f"❌ Error in analyze_intent: {str(e)}")
            return {"intent": "error", "parameters": {}, "confidence": 0.0}
        
        return json.loads(response.choices[0].message.content)
    
    def handle_user_request(self, user_prompt: str, context: Dict = None) -> Dict:
        """Main entry point - analyzes intent and routes to appropriate tool"""
        # Step 1: Analyze intent
        intent_analysis = self.analyze_intent(user_prompt)

        print(f"Intent Analysis: {intent_analysis}")

        # Step 2: Call appropriate tool via MCP
        try:
            result = self.call_tool(
                intent_analysis["intent"], 
                intent_analysis["parameters"]
            )
            return {
                "status": "success",
                "intent": intent_analysis["intent"],
                "result": result,
                "confidence": intent_analysis["confidence"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "intent": intent_analysis["intent"]
            }





    # ---------------------------------------------------------
    # 📘 QUIZ GENERATION
    # ---------------------------------------------------------
    def generate_quiz(self, course_content: str, focus_area: str, difficulty: str = "medium", num_questions: int = 10) -> Dict:
        prompt = f"""
        Generate a {difficulty} level quiz with {num_questions} questions based on the following course content:
        {course_content}
        
        Focus Area: {focus_area}

        Include multiple choice questions with 4 options each.
        Return as valid JSON in the following format:
        {{
            "questions": [
                {{
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "answer": "B"
                }}
            ]
        }}
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # ✅ use faster model for structured tasks
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # fallback if model outputs text
            return {"raw_output": content}

    # ---------------------------------------------------------
    # 📗 GRADE ASSIGNMENT
    # ---------------------------------------------------------
    def grade_assignment(self, assignment_content: str, rubric: Dict, student_answer: str) -> Dict:
        prompt = f"""
        Grade the following assignment based on this rubric.
        Provide detailed feedback and a score (0-100).

        Assignment: {assignment_content}
        Rubric: {json.dumps(rubric, indent=2)}
        Student Answer: {student_answer}

        Return JSON:
        {{
            "score": <number>,
            "feedback": "<text>"
        }}
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"feedback": content}

    # ---------------------------------------------------------
    # 📙 STUDY PLAN
    # ---------------------------------------------------------
    def generate_personalized_study_plan(self, student_performance: Dict, course_content: Dict) -> Dict:
        prompt = f"""
        Create a personalized study plan based on:
        Student Performance: {json.dumps(student_performance, indent=2)}
        Course Content: {json.dumps(course_content, indent=2)}

        Focus on weak areas, suggest time allocations, and include motivational tips.
        Return JSON format.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"plan_text": content}

    # ---------------------------------------------------------
    # 📕 ANSWER QUESTIONS
    # ---------------------------------------------------------
    def answer_student_question(self, question: str, course_context: str) -> str:
        prompt = f"""
        Based on this course content, answer the student's question clearly and accurately.

        Course Context: {course_context}
        Student Question: {question}

        Respond in an educational, supportive tone.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip()

    # ---------------------------------------------------------
    # 📊 PERFORMANCE ANALYSIS
    # ---------------------------------------------------------
    def analyze_student_performance(self, student_data: Dict) -> Dict:
        prompt = f"""
        Analyze this student's performance data:
        {json.dumps(student_data, indent=2)}

        Identify strengths, weaknesses, and give 3 actionable recommendations.
        Return JSON format:
        {{
            "strengths": [...],
            "weaknesses": [...],
            "recommendations": [...]
        }}
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"analysis_text": content}

    # ---------------------------------------------------------
    # 📢 ANNOUNCEMENT / REMINDER
    # ---------------------------------------------------------
    def create_course_announcement(self, context: str, urgency: str = "normal") -> str:
        prompt = f"""
        Create a {urgency} announcement for students based on:
        {context}

        Keep it professional, engaging, and concise.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip()

    def generate_reminder_message(self, event_type: str, details: Dict) -> str:
        prompt = f"""
        Write a friendly reminder for students about:
        Event Type: {event_type}
        Details: {json.dumps(details, indent=2)}
        Keep it polite and short.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip()

    # ---------------------------------------------------------
    # 📘 RESOURCE & SCHEDULING
    # ---------------------------------------------------------
    def recommend_learning_resources(self, student_profile: Dict, topic: str) -> Dict:
        prompt = f"""
        Recommend learning resources for:
        Student Profile: {json.dumps(student_profile, indent=2)}
        Topic: {topic}

        Include books, videos, and articles. Return as JSON:
        {{
            "books": [...],
            "videos": [...],
            "articles": [...]
        }}
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"resources_text": content}

    def schedule_study_sessions(self, student_availability: Dict, course_schedule: Dict) -> Dict:
        prompt = f"""
        Create an optimal study schedule based on:
        Student Availability: {json.dumps(student_availability, indent=2)}
        Course Schedule: {json.dumps(course_schedule, indent=2)}

        Return JSON format with session times and durations.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"schedule_text": content}

    # ---------------------------------------------------------
    # 🧩 MCP Integration
    # ---------------------------------------------------------
    def call_tool(self, tool_name: str, params: dict):
        print(f"🔧 Calling tool: {tool_name}")
        print(f"📍 URL: {self.mcp_base_url}/call")
        print(f"📦 Params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.mcp_base_url}/call",
                json={
                    "tool_name": tool_name,
                    "params": params
                },
                timeout=10  # Add timeout to avoid hanging
            )
            print(f"📡 Response status: {response.status_code}")
            print(f"📄 Response content: {response.text[:500]}")  # Print first 500 chars of response
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection Error: Could not connect to {self.mcp_base_url}")
            print(f"Error details: {str(e)}")
            raise
        except requests.exceptions.Timeout as e:
            print("❌ Request timed out after 10 seconds")
            raise
        except Exception as e:
            print(f"❌ Unexpected error in call_tool: {str(e)}")
            raise

    def list_tools(self):
        response = requests.get(f"{self.mcp_base_url}/tools")
        response.raise_for_status()
        return response.json()
