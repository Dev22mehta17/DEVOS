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

@app.post("/api/memory/upload")
async def upload_document_memory(file: UploadFile = File(...)):
    """Uploads a PDF/TXT resume or doc, extracts text, saves file to disk, and ingests into vector memory."""
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

        upload_dir = Path(__file__).parent.parent / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_file = upload_dir / file.filename
        with open(saved_file, "wb") as f:
            f.write(content)

        full_path = str(saved_file.resolve())
        memory_engine.add_document_context(text, full_path)
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
    goal_text = req.goal.lower()
    await push_stream_event("THINKING", f"Analyzing goal intent: '{req.goal}'")
    
    # ─── Priority 1: Direct Web URL / Form Application Workflow ───
    # If the user provides ANY http/https URL, it is ALWAYS a web task / form fill (unless explicitly 'search google')
    url_match = re.search(r'https?://[^\s\'"<>]+', req.goal)
    target_url = url_match.group(0) if url_match else req.target_url

    if target_url and not any(k in goal_text for k in ["search google for", "google search"]):
        url = target_url.strip(".,'\"")
        await push_stream_event("DOM_ACTION", f"Navigating to target portal: {url}")
        await push_stream_event("DOM_ACTION", "Inspecting form controls, candidate fields, and file uploaders...")
        await push_stream_event("MEMORY_QUERY", "Retrieving profile attributes, resume files, and custom notes...")

        # If Google Form, use specialized Google Form tool
        if "docs.google.com/forms" in url or "forms.gle" in url:
            form_res = await form_tool.process_form(url)
        else:
            # Universal Web Workflow (Taleo, Greenhouse, Lever, Workday, Portals)
            form_res = await universal_web_tool.execute_web_task(url, req.goal)

        filled_count = len(form_res["payload"].get("filled_fields", []))
        await push_stream_event("DOM_ACTION", f"Detected and populated {filled_count} fields directly on open Chrome page.")
        await push_stream_event("APPROVAL_REQUIRED", f"Review sheet generated ({filled_count} fields). Review in modal and click Approve to submit.", form_res["payload"])
        return form_res

    # ─── Priority 2: Gmail Agent Workflows ───
    if any(k in goal_text for k in ["email", "mail", "gmail", "inbox", "recruiter", "hr"]):
        
        # 2A. Reply Intent
        if any(k in goal_text for k in ["reply", "respond", "answer to"]):
            search_query = "recruiter"
            if "from" in goal_text:
                search_query = req.goal.split("from")[-1].split("and")[0].strip()
            elif "about" in goal_text:
                search_query = req.goal.split("about")[-1].strip()

            await push_stream_event("DOM_ACTION", f"Searching Gmail threads for: '{search_query}'...")
            attach_res = "resume" in goal_text or "cv" in goal_text
            reply_res = await gmail_tool.create_reply_draft(search_query, reply_intent=req.goal, attach_resume=attach_res)
            
            await push_stream_event("APPROVAL_REQUIRED", f"Reply draft staged for {reply_res['payload']['recipient']}. Review in modal.", reply_res["payload"])
            return reply_res

        # 2B. Forward Intent
        elif any(k in goal_text for k in ["forward", "fwd"]):
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', req.goal)
            fwd_to = email_match.group(0) if email_match else "rahul@example.com"
            search_query = "interview"
            if "about" in goal_text:
                search_query = req.goal.split("about")[-1].split("to")[0].strip()
            
            await push_stream_event("DOM_ACTION", f"Locating email to forward matching: '{search_query}'...")
            fwd_res = await gmail_tool.create_forward_draft(search_query, forward_to=fwd_to, explanation=req.goal)
            await push_stream_event("APPROVAL_REQUIRED", f"Forward draft staged to {fwd_to}. Review in modal.", fwd_res["payload"])
            return fwd_res

        # 2C. Standard Compose / Send Intent
        else:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', req.goal)
            recipient = email_match.group(0) if email_match else "mehtadev2004@gmail.com"
            attach_resume = any(k in goal_text for k in ["resume", "cv", "pdf", "attach"])
            
            await push_stream_event("MEMORY_QUERY", f"Preparing email to: '{recipient}' (Attach Resume: {attach_resume})...")
            
            draft_res = await gmail_tool.create_draft(
                recipient=recipient,
                subject="Application / Availability Follow-up",
                body=f"Hi,\n\nI am writing to express my interest and confirm my availability. Looking forward to connecting with your team!",
                attach_resume=attach_resume
            )
            
            await push_stream_event("APPROVAL_REQUIRED", f"Email draft prepared for {recipient}. Review details in popup.", draft_res["payload"])
            return draft_res

    # ─── Priority 3: Form / Apply / Register without direct URL in prompt ───
    elif any(k in goal_text for k in ["form", "from", "apply", "register", "signup", "sign up", "book", "application"]):
        await push_stream_event("COMPLETED", "Please include the target website or form link: e.g. 'Fill form at https://...'")
        return {"status": "URL_REQUIRED", "message": "Please provide a valid URL in prompt."}

    # ─── Priority 4: Real Web Search & Research ───
    else:
        query = req.goal.replace("search", "").replace("find", "").replace("research", "").strip()
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        await push_stream_event("DOM_ACTION", f"Submitting search query to Google: '{query}'")
        await browser_tool.navigate(search_url)
        await push_stream_event("COMPLETED", f"Search completed for '{query}'. Top results displayed in Chrome.")
        return {"status": "COMPLETED", "query": query, "url": search_url}

@app.post("/api/approve")
async def approve_action(req: ActionApprovalRequest):
    await push_stream_event("THINKING", f"User approved action {req.action_id}. Proceeding to final execution...")
    
    if "email" in req.action_id:
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
