from openai import OpenAI

class AnnouncementTools:
    """Course announcements and reminders"""
    
    def __init__(self, client: OpenAI):
        self.client = client

    def create_announcement(self, context: str, urgency: str = "normal") -> str:
        """Create a course announcement"""
        prompt = f"""
        Create a {urgency} announcement for students based on:
        {context}

        Keep it professional, engaging, and concise.

        It is an annoucement for a university course.

        Don't exceed 150 words.

        Don't include greetings or sign-offs.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip()

    def generate_reminder(self, event_type: str, details: dict) -> str:
        """Generate a reminder message"""
        import json
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