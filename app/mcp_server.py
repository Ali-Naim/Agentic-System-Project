# app/mcp_server.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from ai_agent import AcademicAIAgent
from models import QuizRequest, GradingRequest, AnnouncementRequest

router = APIRouter()
ai_agent = AcademicAIAgent()

@router.get("/tools")
def list_tools():
    """List available MCP tools."""
    return {
        "tools": [
            {
                "name": "generate_quiz",
                "description": "Generate a Moodle quiz for a specific topic and difficulty.",
                "parameters": list(QuizRequest.model_json_schema().get("properties", {}).keys())
            },
            {
                "name": "grade_assignment",
                "description": "Grade a student's assignment based on rubric and content.",
                "parameters": list(GradingRequest.model_json_schema().get("properties", {}).keys())
            },
            {
                "name": "post_announcement",
                "description": "Post an AI-generated announcement to the course forum.",
                "parameters": list(AnnouncementRequest.model_json_schema().get("properties", {}).keys())
            }
        ]
    }

@router.post("/call")
def call_tool(tool_name: str, params: Dict[str, Any]):
    """Execute the tool dynamically based on AI agent's decision"""
    try:
        print(tool_name, params)
        if tool_name == "generate_quiz":
            req = QuizRequest(**params)
            quiz = ai_agent.generate_quiz(
                course_content="",  # Will be fetched from Moodle
                focus_area=req.focus_area,
                difficulty=req.difficulty,
                num_questions=req.num_questions
            )

            print(quiz)
            # Post to Moodle
            moodle_result = ai_agent.moodle.create_quiz_using_forum(
                req.course_id, 
                {
                    'name': f"AI Quiz - {req.focus_area}",
                    'description': f"Generated quiz on {req.focus_area}",
                    'questions': quiz.get('questions', [])
                }
            )
            print(moodle_result)
            return {"quiz_data": quiz, "moodle_result": moodle_result}

        elif tool_name == "grade_assignment":
            req = GradingRequest(**params)
            result = ai_agent.grade_assignment(
                assignment_content=req.assignment_content,
                rubric=req.rubric,
                student_answer=req.student_answer
            )
            return {"grading_result": result}

        elif tool_name == "post_announcement":
            req = AnnouncementRequest(**params)
            announcement = ai_agent.create_course_announcement(
                req.context, 
                req.urgency
            )
            # Post to Moodle forum
            forum_result = ai_agent.moodle.post_forum_discussion(
                forum_id=req.forum_id,
                message=announcement,
                subject="AI Generated Announcement"
            )
            return {"announcement": announcement, "forum_result": forum_result}
            
        elif tool_name == "analyze_performance":
            # Analyze student performance
            grades = ai_agent.moodle.get_user_grades(
                params['course_id'], 
                params.get('student_id')
            )
            analysis = ai_agent.analyze_student_performance(grades)
            return {"analysis": analysis}
            
        else:
            return {"error": f"Unknown tool: {tool_name}"}
            
    except Exception as e:
        return {"error": str(e)}