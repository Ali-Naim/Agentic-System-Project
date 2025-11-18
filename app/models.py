# app/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    PROFESSOR = "professor"
    ADMIN = "admin"

class CourseContent(BaseModel):
    course_id: str
    title: str
    description: str
    materials: List[str]
    learning_outcomes: List[str]

class StudentPerformance(BaseModel):
    student_id: str
    course_id: str
    quiz_scores: Dict[str, float]
    assignment_scores: Dict[str, float]
    participation: float
    progress: float

class AIActionType(str, Enum):
    GENERATE_QUIZ = "generate_quiz"
    GRADE_ASSIGNMENT = "grade_assignment"
    POST_ANNOUNCEMENT = "post_announcement"
    SEND_REMINDER = "send_reminder"
    CREATE_STUDY_PLAN = "create_study_plan"
    ANSWER_QUESTION = "answer_question"
    GENERATE_LECTURE = "generate_lecture"
    ANALYZE_PERFORMANCE = "analyze_performance"
    RECOMMEND_RESOURCES = "recommend_resources"
    SCHEDULE_EVENTS = "schedule_events"


class QuizRequest(BaseModel):
    """Generate a Moodle quiz for a specific topic and difficulty."""
    course_id: int
    topic: str
    focus_area: str
    difficulty: str
    number_of_questions: int

class GradingRequest(BaseModel):
    """Grade a student's assignment based on rubric and content."""
    assignment_id: int
    student_answer: str
    rubric: Dict[str, Any]

class AnnouncementRequest(BaseModel):
    """Post an AI-generated announcement to the course forum."""
    course_id: int
    forum_id: int
    context: str
    urgency: str

class UserRequest(BaseModel):
    message: str
    course_id: Optional[int] = None
    action_type: Optional[str] = None
    file: Optional[str] = None

class ToolRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any]