# app/moodle_integration.py
import requests
import json
from typing import Dict, List, Any
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import json
import PyPDF2
from io import BytesIO
import tempfile
import shutil
from typing import Tuple, List
import hashlib
# Load environment variables from .env (if present)
load_dotenv()


class MoodleIntegration:
    def __init__(self, neo4j_graph_memory=None):
        # Read base URL and token from environment variables. If not set, fall back to the previous defaults.
        # NOTE: Ensure your .env uses KEY=VALUE format (not KEY:VALUE) so python-dotenv can parse it.
        self.base_url = os.getenv('MOODLE_BASE_URL', 'https://teaching-assistant-agent.moodlecloud.com/webservice/rest/server.php')
        self.token = os.getenv('EXTERNAL_MOODLE_TOKEN', '4140e426c7adb15979c0c18ce57bd45d')
        self.neo4j_graph = neo4j_graph_memory

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
    
    def get_user_courses(self) -> List[Dict]:
        """Get all courses by the user"""
        courses = self.make_api_call('core_enrol_get_users_courses', {'userid': 2})
        return [{'id': course['id'], 'shortname': course['shortname']} for course in courses]

    def get_course_contents(self, course_id: int) -> List[Dict]:
        """Get course content"""
        response = self.make_api_call('core_course_get_contents', {'courseid': course_id})
        return [{'id': item['id'], 'name': item['name'], 'modules': item.get('modules', [])} for item in response]

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
        
    def get_course_context_id(self, course_id: int) -> int:
        """
        Resolve the correct Moodle context ID for a course.
        Needed for uploading files to the course.
        """
        result = self.make_api_call(
            "core_course_get_courses_by_field",
            {"field": "id", "value": course_id}
        )

        courses = result.get("courses", [])
        if not courses:
            raise Exception(f"Course ID {course_id} not found in Moodle.")

        return courses[0]["id"]  # This "id" is the *context ID* in MoodleCloud API

    # ---------------------------------------------------------
    # NEW: EXPORT QUIZ TO PDF
    # ---------------------------------------------------------
    def export_quiz_to_pdf(self, quiz_json: dict, output_path: str, include_answer_key: bool = True):
        """
        Export a quiz (already parsed into a dict) to a professional PDF format.
        """  
        print(quiz_json)
        print(output_path)
        # Ensure directory exists
        directory = os.path.dirname(output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        questions = quiz_json.get("questions", [])

        # PDF setup
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'QuizTitle', parent=styles['Title'], fontSize=24, spaceAfter=20, alignment=1
        )
        question_style = ParagraphStyle(
            'Question', parent=styles['Heading3'], fontSize=12, spaceAfter=6
        )
        option_style = ParagraphStyle(
            'Option', parent=styles['Normal'], leftIndent=20, fontSize=11, spaceAfter=4
        )
        answer_style = ParagraphStyle(
            'Answer', parent=styles['Normal'], textColor=colors.green,
            spaceAfter=10, leftIndent=20, fontSize=11
        )

        elements = []

        # Cover Page
        elements.append(Paragraph("🎯 AI-Generated Quiz", title_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"<b>Number of Questions:</b> {len(questions)}", styles["Normal"]))
        elements.append(Spacer(1, 40))

        # Questions
        for i, q in enumerate(questions, 1):
            elements.append(Paragraph(f"{i}. {q['question']}", question_style))
            for idx, option in enumerate(q.get("options", [])):
                letter = chr(65 + idx)
                elements.append(Paragraph(f"{letter}. {option}", option_style))
            elements.append(Spacer(1, 10))

        # Answer Key
        if include_answer_key:
            elements.append(PageBreak())
            elements.append(Paragraph("Answer Key", title_style))
            elements.append(Spacer(1, 20))
            for i, q in enumerate(questions, 1):
                elements.append(Paragraph(f"{i}. {q['answer']}", answer_style))

        doc.build(elements)
        print("PDF created at:", output_path)
        return output_path


    def upload_file(self, filepath: str, course_id: int, section_num: int = 0) -> dict:
        """
        Upload PDF to Moodle draft area using core_files_upload.
        """
        filename = os.path.basename(filepath)
        
        # Upload to draft area first
        with open(filepath, "rb") as f:
            file_content = f.read()
            
        # Encode file content as base64
        import base64
        file_content_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # Get user ID
        user_id = self.get_user_id()
        
        params = {
            "component": "user",
            "filearea": "draft",
            "itemid": 0,  # 0 will create a new draft area
            "filepath": "/",
            "filename": filename,
            "filecontent": file_content_base64,
            "contextlevel": "user",
            "instanceid": user_id
        }
        
        print(f"Uploading {filename} to draft area...")
        response = self.make_api_call("core_files_upload", params)
        
        # Check if response is a list with file info
        if response and isinstance(response, list) and len(response) > 0:
            file_info = response[0]
            draft_item_id = file_info.get('itemid')
            file_url = file_info.get('url', '')
            
            print(f"✓ File uploaded successfully!")
            print(f"  Draft itemid: {draft_item_id}")
            print(f"  URL: {file_url}")
            
            return {
                "success": True,
                "draft_itemid": draft_item_id,
                "filename": filename,
                "url": file_url,
                "file_info": file_info,
                "message": f"File uploaded to draft area with itemid: {draft_item_id}"
            }
        
        # If response is a dict (like in your output), it might be the file info directly
        elif response and isinstance(response, dict) and 'itemid' in response:
            draft_item_id = response.get('itemid')
            file_url = response.get('url', '')
            
            print(f"✓ File uploaded successfully!")
            print(f"  Draft itemid: {draft_item_id}")
            print(f"  URL: {file_url}")
            
            return {
                "success": True,
                "draft_itemid": draft_item_id,
                "filename": filename,
                "url": file_url,
                "file_info": response,
                "message": f"File uploaded to draft area with itemid: {draft_item_id}"
            }
        
        return {
            "success": False, 
            "message": "Upload failed - unexpected response format",
            "response": response
        }


    def get_user_id(self) -> int:
        """Get current user's ID."""
        response = self.make_api_call("core_webservice_get_site_info", {})
        return response.get('userid')


    def post_pdf_to_forum_with_attachment(self, forum_id: int, subject: str, message: str, draft_itemid: int) -> dict:
        """
        Post a discussion to forum WITH the PDF attached (not just a link).
        
        Args:
            forum_id: The forum instance ID
            subject: Post subject
            message: Post message
            draft_itemid: The draft itemid from the file upload for attachment
        """
        
        # Remove any URL from message - we're attaching the file instead
        clean_message = message
        
        # Use attachmentsdraftitemid parameter to attach the file
        params = {
            "forumid": forum_id,
            "subject": subject,
            "message": clean_message,
            "attachmentsdraftitemid": draft_itemid
        }
        
        print(f"\nPosting to forum {forum_id} with attachment (draft itemid: {draft_itemid}):")
        print(f"  Subject: {subject}")
        
        try:
            response = self.make_api_call("mod_forum_add_discussion", params)
            
            if response and isinstance(response, dict) and 'discussionid' in response:
                discussion_id = response['discussionid']
                print(f"  ✓ Successfully posted with attachment! Discussion ID: {discussion_id}")
                return {
                    "success": True,
                    "discussion_id": discussion_id,
                    "message": "Forum post with PDF attachment created successfully"
                }
            
            return {"success": False, "message": "Unexpected response", "response": response}
            
        except Exception as e:
            print(f"Forum post error: {str(e)}")
            return {"success": False, "message": f"Failed to post: {str(e)}"}


    def attach_draft_file_to_course(self, course_id: int, draft_item_id: int, filename: str, resource_name: str = None, intro: str = "") -> dict:
        """
        Alternative method: Attach a draft file to a Moodle course as a File resource.
        This creates a proper file resource in the course that's accessible to everyone.
        """
        if resource_name is None:
            resource_name = filename.replace('.pdf', '').replace('_', ' ')

        # Prepare the payload for the API
        params = {
            'courseid': course_id,
            'name': resource_name,
            'intro': intro,
            'introformat': 1,  # 1 = HTML
            'section': 0,  # Add to main section
            'visible': 1,  # Make it visible
            'groupmode': 0,  # No groups
            'groupingid': 0,
            'files': {
                'itemid': draft_item_id,
                'filename': filename
            }
        }

        try:
            response = self.make_api_call("mod_resource_add_resource", params)
            return {
                "success": True,
                "resource_id": response.get('id'),
                "response": response
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create resource: {str(e)}",
                "response": None
            }


    def create_and_upload_quiz_pdf(self, quiz_json: dict, forum_id: int = 6):
       result = self.create_google_forms_quiz_via_apps_script(quiz_json, forum_id)
       if result.get('success'):
            return result
       return {
            "success": False,
            "message": "Failed to post to forum and create resource"
        }


    # Alternative method if the above still doesn't work
    def create_quiz_as_resource_only(self, quiz_json: dict, filename: str, course_id: int, section_num: int = 0):
        """
        Alternative workflow: Create PDF and add it as a course resource only.
        This is more reliable than forum attachments.
        """
        
        # Step 1: Create PDF
        local_path = f"/tmp/{filename}"
        self.export_quiz_to_pdf(quiz_json, local_path)
        print(f"✓ PDF created: {filename}")
        
        # Step 2: Upload to Moodle draft area
        upload_result = self.upload_file(local_path, course_id)
        
        if not upload_result.get('success'):
            return {"success": False, "message": "Failed to upload PDF"}
        
        draft_itemid = upload_result.get('draft_itemid')
        
        # Step 3: Create as course resource (more reliable than forum attachment)
        resource_name = filename.replace('.pdf', '').replace('_', ' ')
        intro_text = f"<p>AI-generated quiz on {resource_name}. Download the attached PDF file.</p>"
        
        resource_result = self.attach_draft_file_to_course(
            course_id=course_id,
            draft_item_id=draft_itemid,
            filename=filename,
            resource_name=resource_name,
            intro=intro_text
        )
        
        if resource_result.get('success'):
            print(f"✓ Quiz PDF added as course resource!")
            return {
                "success": True,
                "filename": filename,
                "resource_id": resource_result.get('resource_id'),
                "message": f"Quiz PDF '{resource_name}' successfully created and added to course as resource!"
            }
        
        return {
            "success": False,
            "message": "Failed to create course resource",
            "upload_result": upload_result,
            "resource_result": resource_result
        }
    

    def create_google_forms_quiz_via_apps_script(self, quiz_data: Dict, forum_id: int) -> Dict:
        """
        Create a Google Forms quiz using Apps Script web app.
        Enhanced with better error handling and data formatting.
        """
        try:
            script_url = os.getenv('APPS_SCRIPT_WEB_APP_URL', "https://script.google.com/macros/s/AKfycbxQlmRO42rpDCytcXzIIAVXmXoUnQ9SLoZDbw3k9Eu5RWMFZJV1bB7GICM5K7DgQfKz/exec")
            if not script_url:
                return {
                    "success": False, 
                    "error": "APPS_SCRIPT_WEB_APP_URL not set in environment variables"
                }

            # Format quiz data for Apps Script
            formatted_quiz = self._format_quiz_for_google_forms(quiz_data)
            
            print(f"📤 Sending quiz data to Google Apps Script...")
            print(f"📝 Quiz: {formatted_quiz['quiz_title']}")
            print(f"❓ Questions: {len(formatted_quiz.get('questions', []))}")

            # Send request to Apps Script
            response = requests.post(
                script_url,
                json=formatted_quiz,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    form_url = result['form_url']
                    form_id = result['form_id']
                    
                    print(f"✅ Google Forms quiz created successfully!")
                    print(f"🔗 Form URL: {form_url}")
                    print(f"🆔 Form ID: {form_id}")

                    # Post to Moodle forum
                    forum_result = self._post_quiz_to_moodle_forum(
                        forum_id, quiz_data, form_url
                    )

                    return {
                        "success": True,
                        "form_url": form_url,
                        "form_id": form_id,
                        "edit_url": result.get('edit_url'),
                        "forum_discussion_id": forum_result.get('discussionid'),
                        "message": "Google Forms quiz created and posted to Moodle"
                    }
                else:
                    return {
                        "success": False, 
                        "error": f"Apps Script error: {result.get('error', 'Unknown error')}"
                    }
            else:
                return {
                    "success": False, 
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout - Apps Script took too long to respond"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def _format_quiz_for_google_forms(self, quiz_data: Dict) -> Dict:
        """Format quiz data for Google Forms API"""
        questions = []
        
        for i, q in enumerate(quiz_data.get('questions', [])):
            question = {
                'question': q.get('question', f'Question {i+1}'),
                'options': q.get('options', []),
                'answer': q.get('answer', 0),  # Index of correct answer
                'feedback': q.get('explanation', '')  # Feedback for correct answer
            }
            questions.append(question)
        
        return {
            'quiz_title': quiz_data.get('name', 'AI Generated Quiz'),
            'quiz_description': quiz_data.get('description', ''),
            'questions': questions
        }

    def _post_quiz_to_moodle_forum(self, forum_id: int, quiz_data: Dict, form_url: str) -> Dict:
        """Post the Google Forms quiz link to Moodle forum"""
        
        message = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2c3e50; margin: 0 0 20px 0;">🎯 {quiz_data.get('name', 'AI Generated Quiz')}</h2>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0;"><strong>Description:</strong> {quiz_data.get('description', '')}</p>
            </div>
            
            <div style="background: #e8f5e8; padding: 20px; border-radius: 8px;">
                <h3 style="color: #27ae60; margin: 0 0 15px 0;">📝 Take the Quiz</h3>
                <p style="margin: 0 0 15px 0;">This quiz was automatically generated and is hosted on Google Forms.</p>
                <a href="{form_url}" 
                target="_blank" 
                style="display: inline-block; background: #4285f4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; margin-bottom: 10px;">
                    🚀 Start Quiz on Google Forms
                </a>
                <p style="margin: 10px 0 0 0; font-size: 14px; color: #666;">
                    <em>Note: You'll need a Google account to submit the form</em>
                </p>
            </div>
        </div>
        """

        return self.post_forum_discussion(
            forum_id=forum_id,  # Default forum ID for quizzes
            subject=f"Google Forms Quiz: {quiz_data.get('name', 'AI Generated Quiz')}",
            message=message
        )
