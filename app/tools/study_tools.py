import json
from typing import Dict
from openai import OpenAI

class StudyTools:
    """Study planning and learning tools"""
    
    def __init__(self, client: OpenAI):
        self.client = client

    def generate_study_plan(self, student_performance: Dict, course_content: Dict) -> Dict:
        """Create personalized study plan"""
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

    def answer_question(self, question: str, course_context: str) -> str:
        """Answer student questions"""
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