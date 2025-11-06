"""Handler Service - HTTP API orchestrator."""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import requests
from bankassist.config import get_service_url
from bankassist.utils.intent import classify_intent

app = FastAPI(title="Handler Service")

# Service URLs
VOICE_URL = get_service_url("voice")
SMS_URL = get_service_url("sms")
CALL_URL = get_service_url("call")
LLM_URL = get_service_url("llm")
RAG_URL = get_service_url("rag")
READQUERY_URL = get_service_url("readquery")
WRITEOPS_URL = get_service_url("writeops")
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
    session = get_or_create_session(req.phone, req.account_id, req.verified)
    text = req.text
    intent = classify_intent(text)
    
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
    resp = requests.post(f"{CALL_URL}/end", json={"call_id": call_id, "transcript": transcript})
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["handler"])
