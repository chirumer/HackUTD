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

# In-memory conversation history store (in production, use a database)
# Structure: { call_sid: { phone: str, messages: [...], started_at: timestamp, ended_at: timestamp } }
conversation_history = {}
completed_conversations = []  # List of completed conversations


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
    Receives audio from call service, forwards to voice service for transcription,
    processes responses with LLM, and streams TTS audio back to caller.
    """
    await websocket.accept()
    logger.info("Call service connected for audio streaming")
    
    voice_ws = None
    call_sid = None
    phone = None
    conversation_active = True
    pending_llm_tasks = []  # Track pending LLM responses
    
    try:
        # Import websockets library
        import websockets
        
        # Connect to voice service
        voice_ws_url = VOICE_URL.replace('http', 'ws') + '/live-transcribe'
        logger.info(f"Connecting to voice service: {voice_ws_url}")
        
        # Connect with ping_interval to keep connection alive
        voice_ws = await websockets.connect(
            voice_ws_url,
            ping_interval=20,  # Send ping every 20 seconds
            ping_timeout=10,   # Wait 10 seconds for pong
            close_timeout=10   # Wait 10 seconds when closing
        )
        logger.info("Connected to voice service for transcription")
        
        async def forward_from_call_to_voice():
            """Forward audio from call service to voice service"""
            nonlocal conversation_active, call_sid, phone
            try:
                logger.info("Starting audio forwarding loop", call_sid=call_sid)
                while conversation_active:
                    data = await websocket.receive()
                    
                    if 'bytes' in data:
                        # Audio data - forward to voice service
                        await voice_ws.send(data['bytes'])
                    elif 'text' in data:
                        # Control message
                        msg = json.loads(data['text'])
                        if msg.get('type') == 'start':
                            call_sid = msg.get('call_sid')
                            phone = msg.get('phone')
                            logger.info(f"Call stream started for {call_sid}", call_sid=call_sid, phone=phone)
                            
                            # Initialize conversation history for this call
                            conversation_history[call_sid] = {
                                'call_sid': call_sid,
                                'phone': phone,
                                'messages': [],
                                'started_at': time.time(),
                                'ended_at': None
                            }
                            
                            # Send welcome message
                            welcome_text = "Hello! I'm your AI banking assistant. How can I help you today?"
                            await send_tts_to_caller(welcome_text)
                            
                        elif msg.get('type') == 'stop':
                            logger.info(f"Call stream stopped for {call_sid}", call_sid=call_sid)
                            conversation_active = False
                            await voice_ws.send(json.dumps({'type': 'stop'}))
                            break
                
                logger.info("Audio forwarding loop ended", call_sid=call_sid)
            except WebSocketDisconnect:
                logger.info("Call service disconnected (user hung up)", call_sid=call_sid)
                conversation_active = False
                # Break out to trigger cleanup
            except Exception as e:
                logger.error(f"Error forwarding to voice: {e}", call_sid=call_sid)
                conversation_active = False
        
        async def send_tts_to_caller(text: str):
            """Generate TTS and instruct call service to play audio to caller"""
            try:
                logger.info(f"[ASSISTANT RESPONSE] \"{text}\"", call_sid=call_sid, phone=phone)
                
                # Store assistant message in conversation history
                if call_sid in conversation_history:
                    conversation_history[call_sid]['messages'].append({
                        'role': 'assistant',
                        'text': text,
                        'timestamp': time.time()
                    })
                
                # Generate TTS using voice service
                tts_response = requests.post(
                    f"{VOICE_URL}/synthesize",
                    json={"text": text},
                    timeout=10
                )
                tts_response.raise_for_status()
                tts_data = tts_response.json()
                
                if 'audio_bytes' in tts_data:
                    audio_base64 = tts_data['audio_bytes']
                    
                    logger.info(f"TTS generated, instructing call service to play audio", call_sid=call_sid)
                    
                    # Instruct call service to play this audio (with text for reference)
                    await websocket.send_json({
                        'type': 'play_audio',
                        'audio': audio_base64,
                        'text': text,  # Include text for logging/debugging
                        'format': 'wav'
                    })
                    
                    metrics.increment("tts_responses_sent")
                else:
                    logger.error("TTS response missing audio_bytes", call_sid=call_sid)
                    
            except Exception as e:
                logger.error(f"Error generating TTS: {e}", call_sid=call_sid)
        
        async def process_with_llm(user_text: str):
            """Process user input with LLM and respond"""
            try:
                logger.info(f"Processing with LLM: \"{user_text}\"", call_sid=call_sid)
                metrics.increment("llm_queries")
                
                # Build conversation context from history
                conversation_context = []
                if call_sid in conversation_history:
                    for msg in conversation_history[call_sid]['messages']:
                        conversation_context.append({
                            'role': msg['role'],
                            'content': msg['text']
                        })
                
                # Add current user message to context
                conversation_context.append({
                    'role': 'user',
                    'content': user_text
                })
                
                # Get response from LLM service with full context
                llm_response = requests.post(
                    f"{LLM_URL}/answer",
                    json={"question": user_text, "conversation_history": conversation_context},
                    timeout=15
                )
                llm_response.raise_for_status()
                llm_data = llm_response.json()
                
                answer = llm_data.get('answer', "I'm sorry, I didn't understand that.")
                
                # Instruct call service to play TTS response
                await send_tts_to_caller(answer)
                
            except Exception as e:
                logger.error(f"Error processing with LLM: {e}", call_sid=call_sid)
                # Send error response
                await send_tts_to_caller("I'm sorry, I'm having trouble processing that. Could you please try again?")
            finally:
                # Remove this task from pending list
                current_task = asyncio.current_task()
                if current_task in pending_llm_tasks:
                    pending_llm_tasks.remove(current_task)
                    logger.info(f"LLM task completed, {len(pending_llm_tasks)} tasks remaining", call_sid=call_sid)
        
        async def forward_from_voice_to_call():
            """Forward transcription results from voice service and process with LLM"""
            nonlocal conversation_active
            try:
                logger.info("Starting transcription loop", call_sid=call_sid)
                async for message in voice_ws:
                    if not conversation_active:
                        logger.info("Conversation marked inactive, exiting transcription loop", call_sid=call_sid)
                        break
                        
                    data = json.loads(message)
                    
                    if data.get('type') == 'partial':
                        # Log partial transcription (handler only - call service doesn't need to know)
                        logger.info(f"[PARTIAL] \"{data.get('text')}\"", call_sid=call_sid, phone=phone)
                    
                    elif data.get('type') == 'final':
                        # Complete sentence detected
                        user_text = data.get('text', '').strip()
                        logger.info(f"[USER SAID] \"{user_text}\"", call_sid=call_sid, phone=phone)
                        metrics.increment("transcriptions_completed")
                        
                        # Store user message in conversation history
                        if call_sid in conversation_history:
                            conversation_history[call_sid]['messages'].append({
                                'role': 'user',
                                'text': user_text,
                                'timestamp': time.time()
                            })
                        
                        if user_text:
                            # Check if user wants to end call
                            end_phrases = ['goodbye', 'bye', 'thank you goodbye', 'that\'s all', 'hang up', 'end call']
                            if any(phrase in user_text.lower() for phrase in end_phrases):
                                logger.info("User requested call end", call_sid=call_sid)
                                
                                # Wait for all pending LLM responses to complete
                                if pending_llm_tasks:
                                    logger.info(f"Waiting for {len(pending_llm_tasks)} pending LLM responses before ending call", call_sid=call_sid)
                                    await asyncio.gather(*pending_llm_tasks, return_exceptions=True)
                                    logger.info("All pending LLM responses completed", call_sid=call_sid)
                                
                                await send_tts_to_caller("Thank you for calling. Goodbye!")
                                
                                # Wait for audio to play
                                await asyncio.sleep(5)
                                
                                # Instruct call service to end the call
                                await websocket.send_json({
                                    'type': 'end_call', 
                                    'reason': 'user_completed'
                                })
                                conversation_active = False
                                break
                            
                            # Process with LLM (async - continue transcribing)
                            logger.info("Spawning LLM task, continuing to listen for more speech", call_sid=call_sid)
                            task = asyncio.create_task(process_with_llm(user_text))
                            pending_llm_tasks.append(task)  # Track this task
                            # Loop continues - keep listening for more speech
                    
                    elif data.get('type') == 'error':
                        logger.error(f"Transcription error: {data.get('error')}", call_sid=call_sid)
                
                # If we reach here, the voice_ws loop has ended
                logger.info("Voice WebSocket stream ended (voice service closed connection or no more messages)", call_sid=call_sid)
                        
            except Exception as e:
                logger.error(f"Error in transcription loop: {e}", call_sid=call_sid)
                conversation_active = False
        
        # Run both forwarding tasks concurrently
        # Use return_exceptions=True to prevent one task's error from canceling the other
        logger.info("Starting concurrent audio and transcription tasks", call_sid=call_sid)
        results = await asyncio.gather(
            forward_from_call_to_voice(),
            forward_from_voice_to_call(),
            return_exceptions=True
        )
        
        # Log task completion
        for i, result in enumerate(results):
            task_name = ['forward_from_call_to_voice', 'forward_from_voice_to_call'][i]
            if isinstance(result, Exception):
                logger.error(f"Task {task_name} ended with exception: {result}", call_sid=call_sid)
            else:
                logger.info(f"Task {task_name} completed normally", call_sid=call_sid)
        
    except Exception as e:
        logger.error(f"Call stream error: {e}", call_sid=call_sid)
    finally:
        # Ensure conversation cleanup happens even if tasks fail
        logger.info(f"Cleaning up call stream for {call_sid}", call_sid=call_sid)
        
        # Mark conversation as ended and save to completed conversations
        if call_sid and call_sid in conversation_history:
            conversation_history[call_sid]['ended_at'] = time.time()
            duration = conversation_history[call_sid]['ended_at'] - conversation_history[call_sid]['started_at']
            
            # Log full conversation
            logger.info("="*80)
            logger.info(f"CALL ENDED - Full Conversation Log")
            logger.info(f"Call SID: {call_sid}")
            logger.info(f"Phone: {phone}")
            logger.info(f"Duration: {duration:.2f}s")
            logger.info(f"End Reason: {'User hung up' if not conversation_active else 'Normal completion'}")
            logger.info("="*80)
            for i, msg in enumerate(conversation_history[call_sid]['messages'], 1):
                role_label = "👤 USER" if msg['role'] == 'user' else "🤖 ASSISTANT"
                timestamp_offset = msg['timestamp'] - conversation_history[call_sid]['started_at']
                logger.info(f"[{timestamp_offset:6.1f}s] {role_label}: {msg['text']}")
            logger.info("="*80)
            
            # Save to completed conversations (keep last 50)
            completed_conversations.insert(0, conversation_history[call_sid].copy())
            if len(completed_conversations) > 50:
                completed_conversations.pop()
            
            # Remove from active conversations
            del conversation_history[call_sid]
            logger.info(f"Conversation moved to completed list", call_sid=call_sid)
        else:
            logger.warning(f"No conversation history found for cleanup", call_sid=call_sid)
        
        # Close voice WebSocket
        if voice_ws:
            try:
                await voice_ws.close()
                logger.info("Voice WebSocket closed", call_sid=call_sid)
            except:
                pass
        
        logger.info("Call stream session ended", call_sid=call_sid)


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
    """End a call and store transcript. Called by call service when call ends."""
    logger.info(f"Received call end notification for {call_id}", call_id=call_id)
    metrics.increment("calls_ended")
    
    # If conversation is still in active state, move it to completed
    if call_id in conversation_history:
        logger.info(f"Moving conversation {call_id} from active to completed", call_id=call_id)
        conversation_history[call_id]['ended_at'] = time.time()
        duration = conversation_history[call_id]['ended_at'] - conversation_history[call_id]['started_at']
        
        # Log full conversation
        logger.info("="*80)
        logger.info(f"CALL ENDED - Full Conversation Log (via /call/end)")
        logger.info(f"Call SID: {call_id}")
        logger.info(f"Phone: {conversation_history[call_id]['phone']}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("="*80)
        for i, msg in enumerate(conversation_history[call_id]['messages'], 1):
            role_label = "👤 USER" if msg['role'] == 'user' else "🤖 ASSISTANT"
            timestamp_offset = msg['timestamp'] - conversation_history[call_id]['started_at']
            logger.info(f"[{timestamp_offset:6.1f}s] {role_label}: {msg['text']}")
        logger.info("="*80)
        
        # Save to completed conversations
        completed_conversations.insert(0, conversation_history[call_id].copy())
        if len(completed_conversations) > 50:
            completed_conversations.pop()
        
        # Remove from active
        del conversation_history[call_id]
        logger.info(f"Conversation cleanup completed", call_id=call_id)
    else:
        logger.info(f"Conversation {call_id} already cleaned up or not found", call_id=call_id)
    
    # Forward to call service if needed
    try:
        resp = requests.post(f"{CALL_URL}/end", json={"call_id": call_id, "transcript": transcript}, timeout=2)
        return resp.json() if resp.status_code == 200 else {"status": "ok"}
    except:
        return {"status": "ok", "message": "Call ended, conversation saved"}


@app.get("/logs")
def get_logs(limit: int = 100):
    """Get recent logs from this service."""
    return logger.get_recent_logs(limit=limit)


@app.get("/metrics")
def get_metrics(period: Optional[int] = None):
    """Get metrics from this service."""
    return metrics.get_all_metrics(time_period_minutes=period)


@app.get("/conversations/active")
def get_active_conversations():
    """Get all active conversation histories."""
    return {
        "active_conversations": list(conversation_history.values()),
        "count": len(conversation_history)
    }


@app.get("/conversations/completed")
def get_completed_conversations(limit: int = 50):
    """Get completed conversation histories."""
    return {
        "completed_conversations": completed_conversations[:limit],
        "count": len(completed_conversations),
        "total_completed": len(completed_conversations)
    }


@app.get("/conversations/{call_sid}")
def get_conversation(call_sid: str):
    """Get conversation history for a specific call."""
    # Check active conversations first
    if call_sid in conversation_history:
        return {
            "status": "active",
            "conversation": conversation_history[call_sid]
        }
    
    # Check completed conversations
    for conv in completed_conversations:
        if conv['call_sid'] == call_sid:
            return {
                "status": "completed",
                "conversation": conv
            }
    
    return {"error": "Conversation not found"}, 404


@app.post("/conversations/cleanup")
@app.get("/conversations/cleanup")
def cleanup_stuck_conversations(max_age_seconds: int = 300):
    """
    Manually cleanup conversations that are stuck in active state.
    Moves conversations older than max_age_seconds to completed.
    Can be called via POST /conversations/cleanup or GET /conversations/cleanup?max_age_seconds=300
    """
    current_time = time.time()
    cleaned_up = []
    
    # Find stuck conversations (older than max_age_seconds)
    stuck_calls = []
    for call_sid, conv in conversation_history.items():
        age = current_time - conv['started_at']
        if age > max_age_seconds:
            stuck_calls.append(call_sid)
    
    # Move them to completed
    for call_sid in stuck_calls:
        conv = conversation_history[call_sid]
        conv['ended_at'] = current_time
        duration = conv['ended_at'] - conv['started_at']
        
        logger.info(f"Cleaning up stuck conversation: {call_sid} (duration: {duration:.1f}s)", call_sid=call_sid)
        
        # Save to completed
        completed_conversations.insert(0, conv.copy())
        if len(completed_conversations) > 50:
            completed_conversations.pop()
        
        # Remove from active
        del conversation_history[call_sid]
        cleaned_up.append({
            "call_sid": call_sid,
            "phone": conv['phone'],
            "duration": duration,
            "message_count": len(conv['messages'])
        })
    
    return {
        "status": "ok",
        "cleaned_up_count": len(cleaned_up),
        "conversations": cleaned_up
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
