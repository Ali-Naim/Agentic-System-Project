# app/mcp_server.py
from fastapi import FastAPI, APIRouter, HTTPException
from typing import Dict, Any
from ai_agent import AcademicAIAgent
from models import QuizRequest, GradingRequest, AnnouncementRequest, ToolRequest

router = APIRouter()
ai_agent = AcademicAIAgent()

app = FastAPI(title="MCP Server for Academic Assistant")


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
def call_tool(req: ToolRequest):
    """Execute the tool dynamically based on AI agent's decision"""
    tool_name = req.tool_name
    params = req.params or {}

    try:
        if tool_name == "generate_quiz":
            qr = QuizRequest(**params)

            # Try to fetch course content from Moodle; fallback to empty string
            course_content = ""
            try:
                course_content = ai_agent.moodle.get_course_content(qr.course_id)
            except Exception:
                course_content = ""

            quiz = ai_agent.quiz_tools.generate_quiz(
                course_content=course_content,
                focus_area=qr.focus_area or qr.topic,
                difficulty=qr.difficulty,
                num_questions=qr.number_of_questions
            )

            # Attempt to post/create quiz in Moodle with available methods
            moodle_result = None
            try:
                if hasattr(ai_agent.moodle, "create_quiz_using_forum"):
                    moodle_result = ai_agent.moodle.create_quiz_using_forum(
                        qr.course_id,
                        {
                            "name": f"AI Quiz - {qr.focus_area}",
                            "description": f"Generated quiz on {qr.focus_area}",
                            "questions": quiz.get("questions", [])
                        }
                    )
                elif hasattr(ai_agent.moodle, "create_quiz"):
                    moodle_result = ai_agent.moodle.create_quiz(qr.course_id, quiz)
            except Exception as e:
                moodle_result = {"error": str(e)}

            return {"quiz_data": quiz, "moodle_result": moodle_result}

        elif tool_name == "grade_assignment":
            gr = GradingRequest(**params)

            # If only assignment_id provided, try to fetch assignment content from Moodle
            assignment_content = params.get("assignment_content", "")
            if not assignment_content and hasattr(ai_agent.moodle, "get_assignment_content"):
                try:
                    assignment_content = ai_agent.moodle.get_assignment_content(gr.assignment_id)
                except Exception:
                    assignment_content = ""

            result = ai_agent.grading_tools.grade_assignment(
                assignment_content=assignment_content,
                rubric=gr.rubric,
                student_answer=gr.student_answer
            )
            return {"grading_result": result}

        elif tool_name == "post_announcement":
            ar = AnnouncementRequest(**params)
            announcement = ai_agent.announcement_tools.create_announcement(ar.context, ar.urgency)
            
            print(ar)
            print(announcement)
            forum_result = None
            try:
                # prefer posting by forum id if provided, otherwise try course-level posting
                forum_id = params.get("forum_id")
                course_id = params.get("course_id")
                if forum_id and hasattr(ai_agent.moodle, "post_forum_discussion"):
                    forum_result = ai_agent.moodle.post_forum_discussion(
                        forum_id=forum_id,
                        message=announcement,
                        subject="AI Generated Announcement"
                    )
                elif hasattr(ai_agent.moodle, "post_forum_discussion"):
                    # try best-effort using course_id if forum_id not available
                    forum_result = ai_agent.moodle.post_forum_discussion(
                        forum_id=ar.course_id,
                        message=announcement,
                        subject="AI Generated Announcement"
                    )
            except Exception as e:
                forum_result = {"error": str(e)}

            return {"announcement": announcement, "forum_result": forum_result}

        elif tool_name == "analyze_performance":
            course_id = params.get("course_id")
            student_id = params.get("student_id")
            grades = {}
            try:
                grades = ai_agent.moodle.get_user_grades(course_id, student_id)
            except Exception:
                grades = params.get("student_data", {})

            analysis = ai_agent.performance_tools.analyze_performance(grades)
            return {"analysis": analysis}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

    except Exception as e:
        # return error payload for MCP clients (and log)
        return {"error": str(e)}


app.include_router(router, prefix="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)