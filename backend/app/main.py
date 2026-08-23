import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from pathlib import Path

from app.core.memory_engine import memory_engine
from app.core.permission_engine import permission_engine
from app.core.answer_generator import answer_generator
from app.tools.browser_tool import browser_tool
from app.tools.gmail_tool import gmail_tool
from app.tools.form_tool import form_tool
from app.tools.file_tool import file_tool
from app.tools.universal_web_tool import universal_web_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JARVIS Personal Computer Agent Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stream message queue for SSE broadcasts
stream_queue: asyncio.Queue = asyncio.Queue()

async def push_stream_event(step_type: str, message: str, details: Dict[str, Any] = None):
    """Pushes a live thinking/action log to the frontend SSE stream."""
    event = {
        "step_type": step_type,
        "message": message,
        "details": details or {}
    }
    await stream_queue.put(event)

class GoalRequest(BaseModel):
    goal: str
    target_url: Optional[str] = None

class ActionApprovalRequest(BaseModel):
    action_id: str
    payload: Optional[Dict[str, Any]] = None

class GenerateAnswerRequest(BaseModel):
    question: str
    context_hints: Optional[str] = ""
    max_words: Optional[int] = 150

from app.agent.executor import agent_executor, set_event_broadcaster

@app.on_event("startup")
async def startup_event():
    logger.info("Starting JARVIS Local Execution Engine with Agent Core...")
    set_event_broadcaster(push_stream_event)
    asyncio.create_task(browser_tool.initialize())

@app.on_event("shutdown")
async def shutdown_event():
    await browser_tool.close()

@app.get("/api/health")
async def health_check():
    return {
        "status": "ONLINE",
        "browser_connected": browser_tool.is_connected,
        "memory_loaded": bool(memory_engine.profile_data),
        "agent_core_active": True
    }

@app.get("/api/stream")
async def stream_logs(request: Request):
    """Server-Sent Events endpoint streaming live agent step updates to the React UI."""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(stream_queue.get(), timeout=1.0)
                yield {"data": json.dumps(event)}
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"step_type": "HEARTBEAT", "message": "ping"})}

    return EventSourceResponse(event_generator())

@app.get("/api/memory")
async def get_profile_memory():
    return memory_engine.profile_data

@app.post("/api/memory")
async def save_profile_memory(data: Dict[str, Any]):
    success = memory_engine.save_profile(data)
    if success:
        await push_stream_event("MEMORY_QUERY", "Updated candidate memory profile.")
        return {"status": "SUCCESS", "data": memory_engine.profile_data}
    raise HTTPException(status_code=500, detail="Failed to save profile memory")

@app.post("/api/memory/upload")
@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Uploads a local resume PDF/DOCX and ingests text into ChromaDB vector memory."""
    try:
        uploads_dir = Path(__file__).parent.parent / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        full_path = str((uploads_dir / file.filename).resolve())
        
        with open(full_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        text = memory_engine.add_document_context(full_path)
        await push_stream_event("MEMORY_QUERY", f"Ingested context from '{file.filename}' ({len(text)} chars) into vector memory.")
        return {"status": "SUCCESS", "filename": full_path, "extracted_chars": len(text), "data": memory_engine.profile_data}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.post("/api/generate-answer")
async def generate_custom_answer(req: GenerateAnswerRequest):
    """Dynamic LLM / semantic answer generator for open-ended application questions."""
    await push_stream_event("THINKING", f"Synthesizing personalized answer for: '{req.question[:60]}...'")
    res = answer_generator.generate_answer(req.question, req.context_hints, req.max_words)
    await push_stream_event("MEMORY_QUERY", f"Answer synthesized via {res.get('source')} for question: '{req.question[:40]}'")
    return res

@app.post("/api/execute")
async def execute_goal(req: GoalRequest):
    """Executes goal through the autonomous Agent Core with planning, verifiers, and telemetry."""
    return await agent_executor.execute_goal(req.goal)

@app.post("/api/approve")
async def approve_action(req: ActionApprovalRequest):
    await push_stream_event("THINKING", f"User approved action {req.action_id}. Proceeding to final execution...")
    
    if "email" in req.action_id or "pipeline" in req.action_id:
        res = await gmail_tool.send_draft(req.action_id, req.payload)
        if res.get("sent_on_chrome"):
            await push_stream_event("COMPLETED", f"✅ Email sent live on Gmail! {res.get('message', '')}")
        else:
            await push_stream_event("COMPLETED", f"⚠️ Email send issue: {res.get('message', 'Unknown error')}")
        return res
    elif "form" in req.action_id or "web" in req.action_id:
        res = await form_tool.submit_form(req.action_id, req.payload)
        if res.get("submitted_on_chrome"):
            verified = "✅ Verified!" if res.get("verified") else "(click verification pending)"
            await push_stream_event("COMPLETED", f"Form submitted on Chrome! {verified}")
        else:
            await push_stream_event("COMPLETED", f"⚠️ Form submit issue: {res.get('message', 'Submit button not found')}")
        return res
    
    return {"status": "UNKNOWN_ACTION"}

@app.post("/api/reject")
async def reject_action(req: ActionApprovalRequest):
    permission_engine.reject_action(req.action_id)
    await push_stream_event("COMPLETED", f"Action {req.action_id} was rejected by user. Execution halted.")
    return {"status": "REJECTED", "action_id": req.action_id}
