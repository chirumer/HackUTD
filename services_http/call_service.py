"""Call Service - HTTP API for managing phone calls."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from bankassist.services.call import CallService, Call

app = FastAPI(title="Call Service")
call_svc = CallService()


class InitiateCallRequest(BaseModel):
    phone: str


class ReceiveCallRequest(BaseModel):
    phone: str


class AnswerCallRequest(BaseModel):
    call_id: str


class EndCallRequest(BaseModel):
    call_id: str
    transcript: Optional[str] = None


class CallResponse(BaseModel):
    call_id: str
    phone: str
    direction: str
    status: str
    started_at: float
    ended_at: Optional[float]
    duration: Optional[int]
    transcript: Optional[str]


@app.post("/initiate", response_model=CallResponse)
def initiate_call(req: InitiateCallRequest):
    """Initiate an outbound call."""
    call = call_svc.initiate_call(req.phone)
    return CallResponse(
        call_id=call.call_id,
        phone=call.phone,
        direction=call.direction,
        status=call.status,
        started_at=call.started_at,
        ended_at=call.ended_at,
        duration=call.duration,
        transcript=call.transcript
    )


@app.post("/receive", response_model=CallResponse)
def receive_call(req: ReceiveCallRequest):
    """Receive an inbound call."""
    call = call_svc.receive_call(req.phone)
    return CallResponse(
        call_id=call.call_id,
        phone=call.phone,
        direction=call.direction,
        status=call.status,
        started_at=call.started_at,
        ended_at=call.ended_at,
        duration=call.duration,
        transcript=call.transcript
    )


@app.post("/answer")
def answer_call(req: AnswerCallRequest):
    """Answer a ringing call."""
    success = call_svc.answer_call(req.call_id)
    if not success:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"status": "answered", "call_id": req.call_id}


@app.post("/end")
def end_call(req: EndCallRequest):
    """End an active call."""
    success = call_svc.end_call(req.call_id, req.transcript)
    if not success:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"status": "ended", "call_id": req.call_id}


@app.get("/call/{call_id}", response_model=CallResponse)
def get_call(call_id: str):
    """Get call details."""
    call = call_svc.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return CallResponse(
        call_id=call.call_id,
        phone=call.phone,
        direction=call.direction,
        status=call.status,
        started_at=call.started_at,
        ended_at=call.ended_at,
        duration=call.duration,
        transcript=call.transcript
    )


@app.get("/active", response_model=List[CallResponse])
def get_active_calls():
    """Get all active calls."""
    calls = call_svc.get_active_calls()
    return [CallResponse(
        call_id=c.call_id,
        phone=c.phone,
        direction=c.direction,
        status=c.status,
        started_at=c.started_at,
        ended_at=c.ended_at,
        duration=c.duration,
        transcript=c.transcript
    ) for c in calls]


@app.get("/history", response_model=List[CallResponse])
def get_call_history(phone: Optional[str] = None, limit: int = 10):
    """Get call history."""
    calls = call_svc.get_call_history(phone, limit)
    return [CallResponse(
        call_id=c.call_id,
        phone=c.phone,
        direction=c.direction,
        status=c.status,
        started_at=c.started_at,
        ended_at=c.ended_at,
        duration=c.duration,
        transcript=c.transcript
    ) for c in calls]


@app.get("/stats")
def stats():
    """Get call statistics."""
    return call_svc.stats()


@app.get("/health")
def health():
    return {"status": "ok", "service": "call"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["call"])
