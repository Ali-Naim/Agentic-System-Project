# app/main.py
from fastapi import FastAPI, HTTPException, UploadFile, Form, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional, Union
from ai_agent import AcademicAIAgent 
from mcp_server import router as mcp_router
import json
from models import UserRequest

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
        print(request)
        result = ai_agent.handle_user_request(
            user_prompt=request.message,
            context={"course_id": request.course_id}
        )
        
        print(f"Chat Result: {result}")
        print(f"Status: {result.get('status')}")
        
        # Handle incomplete requests
        if result.get("status") == "incomplete":
            return {
                "reply": result["message"],
                "missing_parameters": result["missing_parameters"],
                "memory": len(ai_agent.memory.get_history()),
                "details": result
            }
        
        elif result.get("status") == "success":
            return {
                "reply": f"✅ I've executed: {result['intent']}\n\nResult: {result['result']}",
                "memory": len(ai_agent.memory.get_history()),
                "details": result
            }
        
        elif result.get("status") == "error":
            return {
                "reply": f"❌ Sorry, I encountered an error: {result['error']}",
                "memory": len(ai_agent.memory.get_history()),
                "details": result
            }
        
        else:
            return {
                "reply": "❓ Unknown response status",
                "details": result
            }
        
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
async def list_courses():
    """List available courses (example endpoint)"""
    try:
        contents = ai_agent.moodle.get_course_contents()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)