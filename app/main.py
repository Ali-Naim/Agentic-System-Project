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

async def get_user_request(
    message: Optional[str] = Form(None),
    course_id: Optional[int] = Form(None),
    action_type: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    body: Optional[str] = None
):
    """Dependency to handle both form data and JSON"""
    if body:
        # JSON request
        data = json.loads(body)
        return UserRequest(**data)
    else:
        # Form data request
        file_content = None
        if file:
            content = await file.read()
            file_content = content.decode('utf-8')
        
        return UserRequest(
            message=message,
            course_id=course_id,
            action_type=action_type,
            file=file_content
        )



@app.get("/")
async def root():
    return {"message": "Welcome to the Smart Academic Assistant API"}


@app.post("/chat")
async def chat(request: UserRequest):
    """Main chat endpoint - uses AI agent for intent analysis and execution"""
    try:

        print(request)
        # Use AI agent to handle the entire request
        result = ai_agent.handle_user_request(
            user_prompt=request.message,
            context={"course_id": request.course_id}
        )

        print(result)
        
        if result["status"] == "success":
            return {
                "reply": f"✅ I've executed: {result['intent']}\n\nResult: {result['result']}",
                "details": result
            }
        else:
            return {
                "reply": f"❌ Sorry, I encountered an error: {result['error']}",
                "details": result
            }
        
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": str(e)}
        )

# Keep direct endpoints for specific use cases
@app.post("/direct-action")
async def direct_action(action: str, params: Dict):
    """Direct action endpoint for precise tool execution"""
    try:
        result = ai_agent.call_tool(action, params)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.include_router(mcp_router, prefix="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
