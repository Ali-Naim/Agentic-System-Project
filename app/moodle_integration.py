# app/moodle_integration.py
import requests
import json
from typing import Dict, List, Any
import os
from dotenv import load_dotenv

# Load environment variables from .env (if present)
load_dotenv()


class MoodleIntegration:
    def __init__(self):
        # Read base URL and token from environment variables. If not set, fall back to the previous defaults.
        # NOTE: Ensure your .env uses KEY=VALUE format (not KEY:VALUE) so python-dotenv can parse it.
        self.base_url = os.getenv('MOODLE_BASE_URL', 'https://teaching-assistant-agent.moodlecloud.com/webservice/rest/server.php')
        self.token = os.getenv('MOODLE_TOKEN', '6d65cb59e0bdb54835777843a7ea53f0')

    def make_api_call(self, function: str, data: Dict = None) -> Dict:
        """Make API call to Moodle"""
        # The .env value can include the full REST endpoint (server.php). Use it as provided.
        url = self.base_url
        params = {
            'wstoken': self.token,
            'moodlewsrestformat': 'json',
            'wsfunction': function
        }
        if data:
            params.update(data)

        response = requests.post(url, data=params)
        response.raise_for_status()
        return response.json()

    def get_courses(self) -> List[Dict]:
        """Get all courses"""
        return self.make_api_call('core_course_get_courses')

    def get_course_contents(self, course_id: int) -> List[Dict]:
        """Get course content"""
        response = self.make_api_call('core_course_get_contents', {'courseid': course_id})
        return response

    def create_quiz(self, course_id: int, quiz_data: Dict) -> Dict:
        """Create a new quiz"""
        return self.make_api_call('mod_quiz_add_quiz', {
            'courseid': course_id,
            'name': quiz_data['name'],
            'intro': quiz_data['description'],
            'timeopen': quiz_data.get('timeopen', 0),
            'timeclose': quiz_data.get('timeclose', 0)
        })

    def post_forum_discussion(self, forum_id: int, message: str, subject: str) -> Dict:
        """Post announcement to forum"""
        return self.make_api_call('mod_forum_add_discussion', {
            'forumid': forum_id,
            'subject': subject,
            'message': message
        })

    def get_user_grades(self, course_id: int, user_id: int = None) -> List[Dict]:
        """Get user grades"""
        params = {'courseid': course_id}
        if user_id:
            params['userid'] = user_id
        return self.make_api_call('gradereport_user_get_grade_items', params)

    def send_message(self, user_id: int, message: str) -> Dict:
        """Send message to user"""
        messages = [{
            'touserid': user_id,
            'text': message,
            'textformat': 1
        }]
        return self.make_api_call('core_message_send_instant_messages', {
            'messages': messages
        })

    def get_enrolled_students(self, course_id: int) -> List[Dict]:
        """Get all students enrolled in a specific course"""
        return self.make_api_call('core_enrol_get_enrolled_users', {'courseid': course_id})
    
    def create_quiz_using_forum(self, course_id: int, quiz_data: Dict) -> Dict:
        """Create quiz content as a forum discussion (workaround)"""
        try:
            # First, get available forums in the course
            forums = self.make_api_call('mod_forum_get_forums_by_courses', {
                'courseids[0]': course_id
            })
            
            
            if not forums or 'warnings' in forums:
                return {"error": "No forums available in this course"}
            
            # Use the first forum found
            forum_id = forums[0]['id']
            
            # Create a forum discussion with the quiz content
            result = self.make_api_call('mod_forum_add_discussion', {
                'forumid': forum_id,
                'subject': f"AI Generated Quiz - {quiz_data['name']}",
                'message': f"<h3>AI Generated Quiz</h3><p>{quiz_data['description']}</p>" +
                        f"<pre>{json.dumps(quiz_data.get('questions', []), indent=2)}</pre>",
                'options[0][name]': 'discussionpinned',
                'options[0][value]': 1  # Pin the discussion
            })
            
            return {"forum_discussion_id": result.get('discussionid'), "type": "forum_post"}
            
        except Exception as e:
            return {"error": f"Forum creation failed: {str(e)}"}

    def create_quiz_as_page(self, course_id: int, quiz_data: Dict) -> Dict:
        """Create quiz as a page resource (alternative workaround)"""
        try:
            # Create a page with quiz content
            result = self.make_api_call('mod_forum_add_discussion', {
                'forumid': self._get_announcements_forum(course_id),
                'subject': f"Quiz: {quiz_data['name']}",
                'message': self._format_quiz_as_html(quiz_data),
                'options[0][name]': 'discussionpinned',
                'options[0][value]': 1
            })
            
            return {"content_id": result.get('discussionid'), "type": "quiz_page"}
            
        except Exception as e:
            return {"error": f"Page creation failed: {str(e)}"}

    def _format_quiz_as_html(self, quiz_data: Dict) -> str:
        """Format quiz data as HTML for display"""
        html = f"""
        <div class='ai-quiz'>
            <h2>🎯 {quiz_data['name']}</h2>
            <p><strong>Description:</strong> {quiz_data['description']}</p>
            <hr>
            <h3>Questions:</h3>
        """
        
        for i, question in enumerate(quiz_data.get('questions', []), 1):
            html += f"""
            <div class='question'>
                <h4>Question {i}: {question.get('questionText', '')}</h4>
                <ul>
            """
            
            for option in question.get('options', []):
                html += f"<li>{option.get('optionText', '')}</li>"
                
            html += f"""
                </ul>
                <p><strong>Answer:</strong> Option {question.get('answerId', '')}</p>
            </div>
            <hr>
            """
        
        html += "</div>"
        return html

    def _get_announcements_forum(self, course_id: int) -> int:
        """Get the announcements forum ID for a course"""
        try:
            forums = self.make_api_call('mod_forum_get_forums_by_courses', {
                'courseids[0]': course_id
            })
            
            for forum in forums:
                if forum.get('type') == 'news':  # Announcements forum
                    return forum['id']
            
            # Return first forum if no announcements forum found
            return forums[0]['id'] if forums else 1
            
        except:
            return 1  # Fallback forum ID