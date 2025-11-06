"""Handler Service - HTTP API orchestrator."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
import requests
import time
import asyncio
import json
from shared.config import get_service_url
from shared.utils.intent import classify_intent
from shared.utils.logger import ServiceLogger
from shared.utils.metrics import MetricsCollector

from services.handler import config

app = FastAPI(title="Handler Service")

# Initialize logger and metrics
logger = ServiceLogger("handler")
metrics = MetricsCollector("handler")

logger.info("Handler service starting up")

# Service URLs
VOICE_URL = get_service_url("voice")
SMS_URL = get_service_url("sms")
CALL_URL = get_service_url("call")
LLM_URL = get_service_url("llm")
RAG_URL = get_service_url("rag")
READQUERY_URL = get_service_url("readquery")
WRITEOPS_URL = get_service_url("write_ops")
COMPLAINT_URL = get_service_url("complaint")
QR_URL = get_service_url("qr")

# In-memory session store (in production, use Redis or a database)
sessions = {}


class HandleRequest(BaseModel):
    phone: str
    account_id: str
    text: str
    verified: bool = False


class HandleResponse(BaseModel):
    reply: str
    session_verified: bool


def get_or_create_session(phone: str, account_id: str, verified: bool):
    if phone not in sessions:
        sessions[phone] = {
            "phone": phone,
            "account_id": account_id,
            "verified": verified,
            "pending_verification_type": None
        }
    return sessions[phone]


@app.post("/handle", response_model=HandleResponse)
def handle_text(req: HandleRequest):
    start_time = time.time()
    logger.info(f"Handling request from {req.phone}", phone=req.phone, account=req.account_id)
    metrics.increment("requests_total")
    
    session = get_or_create_session(req.phone, req.account_id, req.verified)
    text = req.text
    intent = classify_intent(text)
    
    logger.info(f"Classified intent: {intent}", intent=intent, text=text[:50])
    metrics.increment(f"intent_{intent}")
    
    if intent == "general":
        # Call LLM service
        resp = requests.post(f"{LLM_URL}/answer", json={"question": text})
        resp.raise_for_status()
        answer = resp.json()["answer"]
        return HandleResponse(reply=answer, session_verified=session["verified"])
    
    if intent == "offers":
        # Call RAG service
        resp = requests.post(f"{RAG_URL}/query", json={"question": text})
        resp.raise_for_status()
        answer = resp.json()["answer"]
        return HandleResponse(reply=answer, session_verified=session["verified"])
    
    if intent == "read":
        try:
            # Call ReadQuery service
            resp = requests.post(f"{READQUERY_URL}/query", json={
                "user_text": text,
                "account_id": session["account_id"],
                "verified": session["verified"]
            })
            resp.raise_for_status()
            result = resp.json()
            
            if result["type"] == "transactions":
                n = len(result.get("items", []))
                return HandleResponse(
                    reply=f"Your last {n} transactions have been sent to your phone via SMS.",
                    session_verified=session["verified"]
                )
            if result["type"] == "balance":
                amt = result["amount"]
                return HandleResponse(
                    reply=f"Your current balance is ${amt:.2f}.",
                    session_verified=session["verified"]
                )
            return HandleResponse(
                reply="I couldn't find that information.",
                session_verified=session["verified"]
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # Verification required
                session["pending_verification_type"] = "read"
                code = "123456"
                # Send OTP via SMS service
                requests.post(f"{SMS_URL}/expect", json={"phone": session["phone"], "purpose": "otp"})
                requests.post(f"{SMS_URL}/send", json={"to": session["phone"], "body": f"Enter OTP to proceed: {code}"})
                # Simulate receive
                requests.post(f"{SMS_URL}/receive", json={"from_number": session["phone"], "body": code})
                session["verified"] = True
                return HandleResponse(
                    reply="For your security, we sent you a verification code (OTP). Please reply with the code to continue.",
                    session_verified=session["verified"]
                )
            raise
    
    if intent == "write":
        try:
            # Parse simple pattern: "transfer 50 to bob"
            amt = 0.0
            to = "merchant"
            tokens = text.lower().split()
            if "transfer" in tokens:
                i = tokens.index("transfer")
                if i + 1 < len(tokens):
                    try:
                        amt = float(tokens[i + 1])
                    except:
                        amt = 10.0
            if "to" in tokens:
                j = tokens.index("to")
                if j + 1 < len(tokens):
                    to = tokens[j + 1]
            
            # Call WriteOps service
            resp = requests.post(f"{WRITEOPS_URL}/transfer", json={
                "from_acct": session["account_id"],
                "to_acct": to,
                "amount": amt,
                "verified": session["verified"],
                "context": {}
            })
            resp.raise_for_status()
            result = resp.json()
            
            if result["status"] == "ok":
                tx = result["transaction"]
                return HandleResponse(
                    reply=f"Transferred ${tx['amount']:.2f} to {tx['counterparty']}.",
                    session_verified=session["verified"]
                )
            return HandleResponse(
                reply=f"Sorry, this transfer was blocked: {result.get('reason', 'unknown')}",
                session_verified=session["verified"]
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # Verification required
                session["pending_verification_type"] = "write"
                code = "654321"
                requests.post(f"{SMS_URL}/expect", json={"phone": session["phone"], "purpose": "otp"})
                requests.post(f"{SMS_URL}/send", json={"to": session["phone"], "body": f"Enter OTP to confirm transfer: {code}"})
                requests.post(f"{SMS_URL}/receive", json={"from_number": session["phone"], "body": code})
                session["verified"] = True
                return HandleResponse(
                    reply="We sent a verification code by SMS. Please reply to continue.",
                    session_verified=session["verified"]
                )
            raise
    
    if intent == "complaint":
        # Send link via SMS service
        link = "https://example.com/upload"
        requests.post(f"{SMS_URL}/send", json={"to": session["phone"], "body": f"Please upload a photo here: {link}"})
        
        # Simulate user replies with image URL
        image_url = "https://example.com/uploads/photo.jpg"
        
        # Lodge complaint
        resp = requests.post(f"{COMPLAINT_URL}/lodge", json={
            "phone": session["phone"],
            "text": text,
            "image_url": image_url
        })
        resp.raise_for_status()
        complaint = resp.json()
        
        return HandleResponse(
            reply=f"Your complaint #{complaint['id']} has been filed. We'll be in touch.",
            session_verified=session["verified"]
        )
    
    if intent == "qr":
        # Parse amount
        amt = 0.0
        tokens = text.lower().split()
        for tok in tokens:
            if tok.replace('.', '', 1).isdigit():
                amt = float(tok)
                break
        
        # Call QR service
        resp = requests.post(f"{QR_URL}/create", json={
            "account_id": session["account_id"],
            "amount": amt,
            "verified": session["verified"],
            "context": {}
        })
        resp.raise_for_status()
        result = resp.json()
        
        if result["status"] == "ok":
            qr = result["qr_code"]
            # Send QR via SMS
            requests.post(f"{SMS_URL}/send", json={
                "to": session["phone"],
                "body": "Here is your QR code",
                "media_url": f"data:qr;base64,{qr}"
            })
            return HandleResponse(
                reply=f"A QR code for ${amt:.2f} was sent via SMS.",
                session_verified=session["verified"]
            )
        return HandleResponse(
            reply=f"Cannot create QR code: {result.get('reason', 'unknown')}",
            session_verified=session["verified"]
        )
    
    return HandleResponse(
        reply="I'm not sure I understood. Could you rephrase?",
        session_verified=session["verified"]
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "handler"}


@app.websocket("/call/stream")
async def call_stream_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for handling call audio streams.
    Receives audio from call service, forwards to voice service for transcription, and logs results.
    """
    await websocket.accept()
    logger.info("Call service connected for audio streaming")
    
    voice_ws = None
    call_sid = None
    phone = None
    
    try:
        # Import websockets library
        import websockets
        
        # Connect to voice service
        voice_ws_url = VOICE_URL.replace('http', 'ws') + '/live-transcribe'
        logger.info(f"Connecting to voice service: {voice_ws_url}")
        
        voice_ws = await websockets.connect(voice_ws_url)
        logger.info("Connected to voice service for transcription")
        
        async def forward_from_call_to_voice():
            """Forward audio from call service to voice service"""
            try:
                while True:
                    data = await websocket.receive()
                    
                    if 'bytes' in data:
                        # Audio data - forward to voice service
                        await voice_ws.send(data['bytes'])
                    elif 'text' in data:
                        # Control message
                        msg = json.loads(data['text'])
                        if msg.get('type') == 'start':
                            nonlocal call_sid, phone
                            call_sid = msg.get('call_sid')
                            phone = msg.get('phone')
                            logger.info(f"Transcription started for call {call_sid}", call_sid=call_sid, phone=phone)
                        elif msg.get('type') == 'stop':
                            logger.info(f"Transcription stopped for call {call_sid}", call_sid=call_sid)
                            await voice_ws.send(json.dumps({'type': 'stop'}))
                            break
            except WebSocketDisconnect:
                logger.info("Call service disconnected")
            except Exception as e:
                logger.error(f"Error forwarding to voice: {e}")
        
        async def forward_from_voice_to_call():
            """Forward transcription results from voice service to call service"""
            try:
                async for message in voice_ws:
                    data = json.loads(message)
                    
                    if data.get('type') == 'partial':
                        # Log partial transcription
                        logger.info(f"[PARTIAL] \"{data.get('text')}\"", call_sid=call_sid, phone=phone)
                        # Forward to call service
                        await websocket.send_json(data)
                    
                    elif data.get('type') == 'final':
                        # Log final transcription
                        logger.info(f"[FINAL SENTENCE] \"{data.get('text')}\"", call_sid=call_sid, phone=phone)
                        metrics.increment("transcriptions_completed")
                        # Forward to call service
                        await websocket.send_json(data)
                    
                    elif data.get('type') == 'error':
                        logger.error(f"Transcription error: {data.get('error')}", call_sid=call_sid)
                        await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error forwarding from voice: {e}")
        
        # Run both forwarding tasks concurrently
        await asyncio.gather(
            forward_from_call_to_voice(),
            forward_from_voice_to_call()
        )
        
    except Exception as e:
        logger.error(f"Live transcription error: {e}")
    finally:
        if voice_ws:
            await voice_ws.close()
        logger.info("Live transcription session ended", call_sid=call_sid)


@app.post("/call/initiate")
def initiate_call(phone: str):
    """Initiate an outbound call to a customer."""
    resp = requests.post(f"{CALL_URL}/initiate", json={"phone": phone})
    resp.raise_for_status()
    return resp.json()


@app.post("/call/receive")
def receive_call(phone: str):
    """Receive an inbound call from a customer."""
    resp = requests.post(f"{CALL_URL}/receive", json={"phone": phone})
    resp.raise_for_status()
    call = resp.json()
    # Auto-answer the call
    requests.post(f"{CALL_URL}/answer", json={"call_id": call["call_id"]})
    return call


@app.post("/call/end")
def end_call(call_id: str, transcript: str = ""):
    """End a call and store transcript."""
    logger.info(f"Ending call {call_id}", call_id=call_id)
    metrics.increment("calls_ended")
    resp = requests.post(f"{CALL_URL}/end", json={"call_id": call_id, "transcript": transcript})
    resp.raise_for_status()
    return resp.json()


@app.get("/logs")
def get_logs(limit: int = 100):
    """Get recent logs from this service."""
    return logger.get_recent_logs(limit=limit)


@app.get("/metrics")
def get_metrics(period: Optional[int] = None):
    """Get metrics from this service."""
    return metrics.get_all_metrics(time_period_minutes=period)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
