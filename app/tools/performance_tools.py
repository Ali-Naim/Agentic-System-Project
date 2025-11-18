import json
from typing import Dict
from openai import OpenAI

class PerformanceTools:
    """Student performance analysis tools"""
    
    def __init__(self, client: OpenAI):
        self.client = client

    def analyze_performance(self, student_data: Dict) -> Dict:
        """Analyze student performance data"""
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