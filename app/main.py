# app/main.py
from fastapi import FastAPI, HTTPException, UploadFile, Form, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import asyncio
from pydantic import BaseModel
from typing import AsyncGenerator, Dict, Optional, Union
from ai_agent import AcademicAIAgent 
from mcp_server import router as mcp_router
import json
from models import UserRequest,ConfirmationRequest
import base64
from utils import extract_pdf_text


app = FastAPI(title="Smart Academic Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_agent = AcademicAIAgent()

@app.get("/")
async def root():
    return {"message": "Welcome to the Smart Academic Assistant API"}
@app.post("/chat")
async def chat(request: UserRequest):
    """Main chat endpoint - uses AI agent for intent analysis and execution"""
    try:
        if request.file:
           return StreamingResponse(
                feed_graph(file=request.file, 
                          filename=request.filename, 
                          course_id=request.course_id), 
                media_type="text/event-stream")

        else:
            return StreamingResponse(
                stream_agent_response(
                    user_prompt=request.message,
                    context={"course_id": request.course_id, "forum_id": request.forum_id}
                ),
                media_type="text/event-stream"
            )
            
    except Exception as e:
        print(f"Exception in /chat: {str(e)}")
        return JSONResponse(
            status_code=500, 
            content={"error": str(e), "message": "An unexpected error occurred"}
        )

@app.post("/clear-memory")
async def clear_memory():
    """Clear conversation history"""
    ai_agent.clear_memory()
    return {"status": "success", "message": "Conversation history cleared"}

@app.get("/memory")
async def get_memory():
    """Get current conversation history"""
    return {
        "history": ai_agent.get_memory(),
        "size": len(ai_agent.get_memory())
    }

@app.get("/tools")
async def list_tools():
    """Get list of available tools"""
    try:
        return ai_agent.list_tools()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/courses")
async def list_courses():
    """List available courses (example endpoint)"""
    try:
        courses = ai_agent.moodle.get_user_courses()
        return {"courses": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/course-contents/{course_id}")
async def list_courses(course_id: int):
    """List available courses (example endpoint)"""
    try:
        contents = ai_agent.moodle.get_course_contents(course_id=course_id)
        return {"contents": contents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Keep direct endpoints for specific use cases
@app.post("/direct-action")
async def direct_action(action: str, params: Dict):
    """Direct action endpoint for precise tool execution"""
    try:
        result = ai_agent.call_tool(action, params)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("materials/{course_id}")
async def get_materials(course_id: int):
    """Fetch course materials for a given course ID"""
    try:
        materials = ai_agent.moodle.get_course_materials(course_id)
        return {"course_id": course_id, "materials": materials}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/save-as-graph/{course_id}")
async def upload_document(course_id: int ):
    """Upload a document to be processed and added to memory"""
    try:
        print("Uploading course materials to graph database...", course_id)
        # ai_agent.moodle.debug_course_structure(9)
        result = ai_agent.moodle.save_as_graph(course_id, chunk_overlap=200, chunk_size=1000)
        return {"status": "success", "message": "Documents Uploaded Successfuly", "result":result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/confirm-action")
async def confirm_action(request: ConfirmationRequest):
    """Handle user confirmation for actions"""
    try:
        if request.confirmed:
            # If confirmed, execute the original request
            return StreamingResponse(
                stream_agent_response(
                    user_prompt=request.original_request.get("message", ""),
                    context={
                        "course_id": request.original_request.get("course_id"),
                        "forum_id": request.original_request.get("forum_id"),
                        "confirmed": True  # Add flag to indicate confirmation
                    }
                ),
                media_type="text/event-stream"
            )
        else:
            # If not confirmed, return a refinement message
            return JSONResponse(
                content={
                    "status": "refinement_required",
                    "message": "Please refine your request. What would you like to change?"
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
async def stream_agent_response(user_prompt: str, context: dict) -> AsyncGenerator[str, None]:
    """Stream agent response with thoughts, actions, and final answer"""
    try:
        # Stream initial processing message
        yield "data: " + json.dumps({"type": "status", "content": "🤔 Processing your request..."}) + "\n\n"
        await asyncio.sleep(0.1)
        
        # Get the agent's response
        result = ai_agent.handle_user_request(
            user_prompt=user_prompt,
            context=context
        )
        
        # Check if this is a Moodle action that requires confirmation
        moodle_actions = ["generate_quiz", "post_announcement"]
        
        if (result.get("status") == "success" and 
            result.get("intent") in moodle_actions and
            not context.get("confirmed")):
            
            # First, stream the generated content to show the user
            generated_content = result.get("generated_content", "")
            
            if generated_content:
                # Format the content nicely for display
                if result["intent"] == "generate_quiz":
                    content_display = format_quiz_for_display(generated_content)
                else:  # announcement
                    content_display = generated_content
                
                # Stream the generated content
                yield "data: " + json.dumps({"type": "answer", "content": content_display}) + "\n\n"
                await asyncio.sleep(0.1)
            
            # Then ask for confirmation
            yield "data: " + json.dumps({
                "type": "confirmation_required",
                "content": f"✅ I've generated the {result['intent'].replace('_', ' ')}. Would you like to proceed and post it to Moodle?",
                "intent": result["intent"],
                "generated_content": generated_content,
                "original_request": {
                    "message": user_prompt,
                    "course_id": context.get("course_id"),
                    "forum_id": context.get("forum_id")
                }
            }) + "\n\n"
            return
        
        # For non-Moodle actions or confirmed actions, proceed normally
        if "thought_process" in result:
            yield "data: " + json.dumps({"type": "thought", "content": result["thought_process"]}) + "\n\n"
            await asyncio.sleep(0.1)
        
        if "intent" in result:
            yield "data: " + json.dumps({"type": "action", "content": f"Executing: {result['intent']}"}) + "\n\n"
            await asyncio.sleep(0.1)
        
        # Stream the final result
        if result.get("status") == "success":
            final_response = result["message"]
        elif result.get("status") == "incomplete":
            final_response = result["message"]
        elif result.get("status") == "error":
            final_response = f"❌ Sorry, I encountered an error: {result['error']}"
        else:
            final_response = "❓ Unknown response status"
        
        # Stream the final response
        words = final_response.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield "data: " + json.dumps({"type": "answer", "content": chunk}) + "\n\n"
            await asyncio.sleep(0.05)
        
        # Stream completion signal
        yield "data: " + json.dumps({"type": "complete", "content": ""}) + "\n\n"
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        yield "data: " + json.dumps({"type": "error", "content": error_msg}) + "\n\n"

def format_quiz_for_display(quiz_data):
    """Format quiz data for nice display"""
    if isinstance(quiz_data, str):
        return quiz_data
    
    if isinstance(quiz_data, dict):
        # Handle different quiz formats
        if 'raw_output' in quiz_data:
            questions = quiz_data['raw_output']
        elif 'questions' in quiz_data:
            questions = quiz_data['questions']
        else:
            questions = []
        
        formatted = "📝 **Generated Quiz**\n\n"
        for i, question in enumerate(questions, 1):
            formatted += f"**Q{i}: {question.get('question', 'No question text')}**\n"
            
            # Add options if available
            options = question.get('options', [])
            for j, option in enumerate(options):
                formatted += f"   {chr(65+j)}. {option}\n"
            
            # Add answer if available
            if 'answer' in question:
                formatted += f"   **Answer: {question['answer']}**\n"
            
            formatted += "\n"
        
        return formatted
    
    return str(quiz_data)

# Add this new endpoint for confirmed actions
@app.post("/execute-confirmed-action")
async def execute_confirmed_action(request: ConfirmationRequest):
    """Execute the action after user confirmation"""
    try:
        # Add confirmed flag to context
        context = {
            "course_id": request.original_request.get("course_id"),
            "forum_id": request.original_request.get("forum_id"),
            "confirmed": True,
            "generated_content": request.original_request.get("generated_content")
        }
        
        # Execute the confirmed action
        return StreamingResponse(
            stream_confirmed_action(
                user_prompt=request.original_request.get("message", ""),
                context=context,
                intent=request.original_request.get("intent")
            ),
            media_type="text/event-stream"
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

async def stream_confirmed_action(user_prompt: str, context: dict, intent: str) -> AsyncGenerator[str, None]:
    """Stream the execution of a confirmed action"""
    try:
        yield "data: " + json.dumps({"type": "status", "content": "🚀 Executing confirmed action..."}) + "\n\n"
        await asyncio.sleep(0.1)
        
        # Execute the action with confirmation
        result = ai_agent.handle_user_request(
            user_prompt=user_prompt,
            context=context
        )
        
        # Stream the execution process
        if "thought_process" in result:
            yield "data: " + json.dumps({"type": "thought", "content": result["thought_process"]}) + "\n\n"
            await asyncio.sleep(0.1)
        
        yield "data: " + json.dumps({"type": "action", "content": f"Posting to Moodle: {intent.replace('_', ' ')}"}) + "\n\n"
        await asyncio.sleep(0.1)
        
        # Stream the result
        if result.get("status") == "success":
            final_response = result["message"]
        else:
            final_response = f"❌ Action failed: {result.get('error', 'Unknown error')}"
        
        words = final_response.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield "data: " + json.dumps({"type": "answer", "content": chunk}) + "\n\n"
            await asyncio.sleep(0.05)
        
        yield "data: " + json.dumps({"type": "complete", "content": ""}) + "\n\n"
        
    except Exception as e:
        error_msg = f"❌ Error executing action: {str(e)}"
        yield "data: " + json.dumps({"type": "error", "content": error_msg}) + "\n\n"



async def feed_graph(file: str, filename: str = None, course_id: int = None ):
    file_text = None
    try:
        decoded_bytes = base64.b64decode(file)
        
        # Heuristic: PDF files start with "%PDF"
        if decoded_bytes[:4] == b"%PDF":
            file_text = extract_pdf_text(decoded_bytes)
        else:
            # Not PDF → Treat as plain text
            file_text = decoded_bytes.decode("utf-8", errors="ignore")
    except Exception:
        # fallback → assume text
        file_text = file

    try:
    
    # 2. Push file into Neo4j Graph Memory
        ai_agent.graph_memory.addGraphFile(
            doc_text=file_text,
            title=filename or "Uploaded Document",
            metadata={"course_id": course_id,"chapter": filename}
        )

        response = "Document uploaded and processed successfully."
                # Stream the final response
        words = response.split()

        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield "data: " + json.dumps({"type": "answer", "content": chunk}) + "\n\n"
            await asyncio.sleep(0.05)
        
        # Stream completion signal
        yield "data: " + json.dumps({"type": "complete", "content": ""}) + "\n\n"

    except Exception as e:
        print(f"❌ Error uploading document to graph memory: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload document to graph memory.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)