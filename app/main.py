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
from models import UserRequest
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
            file_text = None

            # 1. Try to decode base64 (PDFs come base64 from the browser)
            try:
                decoded_bytes = base64.b64decode(request.file)
                
                # Heuristic: PDF files start with "%PDF"
                if decoded_bytes[:4] == b"%PDF":
                    file_text = extract_pdf_text(decoded_bytes)
                else:
                    # Not PDF → Treat as plain text
                    file_text = decoded_bytes.decode("utf-8", errors="ignore")
            except Exception:
                # fallback → assume text
                file_text = request.file

            try:
            
            # 2. Push file into Neo4j Graph Memory
                ai_agent.graph_memory.addGraphFile(
                    doc_text=file_text,
                    title=request.filename or "Uploaded Document",
                    metadata={"course_id":request.course_id,"chapter": request.filename}
                )
                return {"status": "success", "reply": "Document uploaded to graph memory successfully."}
            except Exception as e:
                print(f"❌ Error uploading document to graph memory: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to upload document to graph memory.")

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

async def stream_agent_response(user_prompt: str, context: dict) -> AsyncGenerator[str, None]:
    """Stream agent response with thoughts, actions, and final answer"""
    try:
        # Stream initial processing message
        yield "data: " + json.dumps({"type": "status", "content": "🤔 Processing your request..."}) + "\n\n"
        await asyncio.sleep(0.1)
        
        # Get the agent's response (you'll need to modify your agent to support streaming)
        result = ai_agent.handle_user_request(
            user_prompt=user_prompt,
            context=context
        )
        
        # Stream the agent's thought process if available
        if "thought_process" in result:
            yield "data: " + json.dumps({"type": "thought", "content": result["thought_process"]}) + "\n\n"
            await asyncio.sleep(0.1)
        
        # Stream the intent
        if "intent" in result:
            yield "data: " + json.dumps({"type": "action", "content": f"Executing: {result['intent']}"}) + "\n\n"
            await asyncio.sleep(0.1)
        
        # Stream the result in chunks to simulate token-by-token streaming
        if result.get("status") == "success":
            final_response = f"✅ I've executed: {result['intent']}\n\nResult: {result['result']}"
        elif result.get("status") == "incomplete":
            final_response = result["message"]
        elif result.get("status") == "error":
            final_response = f"❌ Sorry, I encountered an error: {result['error']}"
        else:
            final_response = "❓ Unknown response status"
        
        # Stream the final response token by token (simulated)
        words = final_response.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield "data: " + json.dumps({"type": "answer", "content": chunk}) + "\n\n"
            await asyncio.sleep(0.05)  # Adjust speed as needed
        
        # Stream completion signal
        yield "data: " + json.dumps({"type": "complete", "content": ""}) + "\n\n"
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        yield "data: " + json.dumps({"type": "error", "content": error_msg}) + "\n\n"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)