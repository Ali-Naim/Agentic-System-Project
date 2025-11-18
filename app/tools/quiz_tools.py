import json
from typing import Dict
from openai import OpenAI

class QuizTools:
    """Quiz generation and management tools"""
    
    def __init__(self, client: OpenAI):
        self.client = client

    def generate_quiz(self, course_content: str, focus_area: str, difficulty: str = "medium", num_questions: int = 10) -> Dict:
        """Generate a quiz based on course content"""
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
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_output": content}