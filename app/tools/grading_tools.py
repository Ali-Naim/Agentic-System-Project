import json
from typing import Dict, Any
from openai import OpenAI

class GradingTools:
    """Assignment grading and feedback tools"""
    
    def __init__(self, client: OpenAI):
        self.client = client

    def grade_assignment(self, assignment_content: str, rubric: Dict[str, Any], student_answer: str) -> Dict:
        """Grade a student's assignment"""
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