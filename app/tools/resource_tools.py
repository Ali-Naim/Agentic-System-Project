import json
from typing import Dict
from openai import OpenAI

class ResourceTools:
    """Learning resources and scheduling tools"""
    
    def __init__(self, client: OpenAI):
        self.client = client

    def recommend_resources(self, student_profile: Dict, topic: str) -> Dict:
        """Recommend learning resources"""
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

    def schedule_sessions(self, student_availability: Dict, course_schedule: Dict) -> Dict:
        """Schedule study sessions"""
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