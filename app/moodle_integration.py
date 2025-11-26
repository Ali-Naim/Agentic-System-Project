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
# Load environment variables from .env (if present)
load_dotenv()


class MoodleIntegration:
    def __init__(self):
        # Read base URL and token from environment variables. If not set, fall back to the previous defaults.
        # NOTE: Ensure your .env uses KEY=VALUE format (not KEY:VALUE) so python-dotenv can parse it.
        self.base_url = os.getenv('MOODLE_BASE_URL', 'https://teaching-assistant-agent.moodlecloud.com/webservice/rest/server.php')
        self.token = os.getenv('EXTERNAL_MOODLE_TOKEN', '4140e426c7adb15979c0c18ce57bd45d')

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


    def create_and_upload_quiz_pdf(self, quiz_json: dict, filename: str, course_id: int, forum_id: int = 6):
        """
        Complete workflow with proper file attachment to forum.
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
        print(f"✓ PDF uploaded to draft area (itemid: {draft_itemid})")
        
        # Step 3: Post to forum WITH FILE ATTACHMENT (not URL)
        subject = f"New Quiz: {filename.replace('.pdf', '').replace('_', ' ')}"
        message = f"""
        <p>A new quiz has been generated and is attached to this post!</p>
        <p><strong>Quiz Topic:</strong> {filename.replace('.pdf', '').replace('_', ' ')}</p>
        <p><strong>The PDF file is attached to this post - download it from the attachments below.</strong></p>
        """
        
        forum_result = self.post_pdf_to_forum_with_attachment(
            forum_id=forum_id,
            subject=subject,
            message=message,
            draft_itemid=draft_itemid  # This will attach the file to the forum post
        )
        
        if forum_result.get('success'):
            print(f"✓ Posted to forum with PDF attachment!")
            
            # Optional: Also create a resource in the course
            resource_result = self.attach_draft_file_to_course(
                course_id=course_id,
                draft_item_id=draft_itemid,
                filename=filename
            )
            
            if resource_result.get('success'):
                print(f"✓ Also created course resource with PDF!")
            
            return {
                "success": True,
                "filename": filename,
                "discussion_id": forum_result.get('discussion_id'),
                "resource_result": resource_result,
                "message": "Quiz PDF created, uploaded, and posted to forum as attachment!"
            }
        
        # If forum posting fails, try alternative: create course resource only
        print("Forum posting failed, trying to create course resource instead...")
        resource_result = self.attach_draft_file_to_course(
            course_id=course_id,
            draft_item_id=draft_itemid,
            filename=filename
        )
        
        if resource_result.get('success'):
            return {
                "success": True,
                "filename": filename,
                "resource_id": resource_result.get('resource_id'),
                "message": "Quiz PDF created and added as course resource (forum post failed)"
            }
        
        return {
            "success": False,
            "message": "Failed to post to forum and create resource",
            "upload_result": upload_result,
            "forum_result": forum_result,
            "resource_result": resource_result
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