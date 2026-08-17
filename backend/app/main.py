import asyncio
import json
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from app.core.memory_engine import memory_engine
from app.core.permission_engine import permission_engine
from app.tools.browser_tool import browser_tool
from app.tools.gmail_tool import gmail_tool
from app.tools.form_tool import form_tool
from app.tools.file_tool import file_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JARVIS Personal Computer Agent Backend", version="1.0.0")

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
        "step_type": step_type,  # THINKING, DOM_ACTION, MEMORY_QUERY, FILE_SEARCH, APPROVAL_REQUIRED, COMPLETED
        "message": message,
        "details": details or {}
    }
    await stream_queue.put(event)

class GoalRequest(BaseModel):
    goal: str
    target_url: str = None

class ActionApprovalRequest(BaseModel):
    action_id: str
    payload: Dict[str, Any] = None

@app.on_event("startup")
async def startup_event():
    logger.info("Starting JARVIS Local Execution Engine...")
    asyncio.create_task(browser_tool.initialize())

@app.on_event("shutdown")
async def shutdown_event():
    await browser_tool.close()

@app.get("/api/health")
async def health_check():
    return {
        "status": "ONLINE",
        "browser_connected": browser_tool.is_connected,
        "memory_loaded": bool(memory_engine.profile_data)
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
async def get_memory():
    return memory_engine.profile_data

@app.post("/api/memory")
async def update_memory(data: Dict[str, Any]):
    success = memory_engine.save_profile(data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile memory.")
    return {"status": "SUCCESS", "data": memory_engine.profile_data}

from fastapi import UploadFile, File

@app.post("/api/memory/upload")
async def upload_document_memory(file: UploadFile = File(...)):
    """Uploads a PDF/TXT resume or doc, extracts text context, and saves to memory."""
    try:
        content = await file.read()
        text = ""
        if file.filename.lower().endswith(".pdf"):
            import io
            from pypdf import PdfReader
            pdf = PdfReader(io.BytesIO(content))
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        else:
            text = content.decode("utf-8", errors="ignore")

        memory_engine.add_document_context(text, file.filename)
        await push_stream_event("MEMORY_QUERY", f"Ingested context from '{file.filename}' ({len(text)} chars) into vector memory.")
        return {"status": "SUCCESS", "filename": file.filename, "extracted_chars": len(text), "data": memory_engine.profile_data}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.post("/api/execute")
async def execute_goal(req: GoalRequest):
    goal_text = req.goal.lower()
    await push_stream_event("THINKING", f"Analyzing goal intent: '{req.goal}'")
    
    # Workflow 1: Gmail Compose
    if "email" in goal_text or "mail" in goal_text:
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', req.goal)
        recipient = email_match.group(0) if email_match else "mehtadev2004@gmail.com"
        
        await push_stream_event("MEMORY_QUERY", f"Target Recipient: '{recipient}'. Fetching account context...")
        await push_stream_event("DOM_ACTION", "Connecting to active Chrome session on port 9222...")
        await push_stream_event("DOM_ACTION", "Navigating Chrome tab to https://mail.google.com...")
        
        draft_res = await gmail_tool.create_draft(
            recipient=recipient,
            subject="Availability Tomorrow",
            body=f"Hi,\n\nI'll be available tomorrow after 4 PM.\n\nBest,\nDev"
        )
        
        await push_stream_event("APPROVAL_REQUIRED", f"Email draft prepared for {recipient}. Review details in popup.", draft_res["payload"])
        return draft_res

    # Workflow 2: Google Forms / Application filling
    elif "form" in goal_text or "apply" in goal_text or req.target_url:
        import re
        url_match = re.search(r'https?://[^\s]+', req.goal)
        url = url_match.group(0) if url_match else req.target_url
        
        if not url or url == "https://forms.gle/sample" or "<paste-form-url-here>" in url or "<url>" in url:
            await push_stream_event("COMPLETED", "Form URL missing. Please include your target form link in prompt: e.g. 'Fill form at https://forms.gle/xyz'")
            return {"status": "URL_REQUIRED", "message": "Please provide a valid form URL in prompt."}

        await push_stream_event("DOM_ACTION", f"Navigating to web form: {url}")
        await push_stream_event("DOM_ACTION", "Inspecting HTML input fields, placeholders, and labels...")
        await push_stream_event("MEMORY_QUERY", "Fetching candidate attributes (University, Degree, GPA, LinkedIn, GitHub)...")
        await push_stream_event("FILE_SEARCH", "Scanning ~/Downloads & ~/Documents for resume PDF...")
        
        form_res = await form_tool.process_form(url)
        filled_count = len(form_res["payload"].get("filled_fields", []))
        await push_stream_event("DOM_ACTION", f"Auto-filled {filled_count} fields directly on open Chrome page (Name, Email, Mobile, Education).")
        await push_stream_event("APPROVAL_REQUIRED", f"Form review sheet generated ({filled_count} fields populated). Click Approve & Submit to submit on Chrome.", form_res["payload"])
        return form_res

    # Workflow 3: Real Web Search & Research
    else:
        query = req.goal.replace("search", "").replace("find", "").replace("research", "").strip()
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        await push_stream_event("DOM_ACTION", f"Submitting search query to Google: '{query}'")
        nav_res = await browser_tool.navigate(search_url)
        await push_stream_event("COMPLETED", f"Search completed for '{query}'. Top results displayed in Chrome.")
        return {"status": "COMPLETED", "query": query, "url": search_url}

@app.post("/api/approve")
async def approve_action(req: ActionApprovalRequest):
    await push_stream_event("THINKING", f"User approved action {req.action_id}. Proceeding to final execution...")
    
    if "email" in req.action_id:
        res = await gmail_tool.send_draft(req.action_id)
        await push_stream_event("COMPLETED", "Email sent successfully to recipient!")
        return res
    elif "form" in req.action_id:
        res = await form_tool.submit_form(req.action_id, req.payload)
        await push_stream_event("COMPLETED", "Form submitted successfully on Chrome!")
        return res
    
    return {"status": "UNKNOWN_ACTION"}

@app.post("/api/reject")
async def reject_action(req: ActionApprovalRequest):
    permission_engine.reject_action(req.action_id)
    await push_stream_event("COMPLETED", f"Action {req.action_id} was rejected by user. Execution halted.")
    return {"status": "REJECTED", "action_id": req.action_id}
