"""SMS Service - HTTP API."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from bankassist.services.sms import SMSService, SMS

from services.sms import config

app = FastAPI(title="SMS Service")
sms_svc = SMSService()


class SendSMSRequest(BaseModel):
    to: str
    body: str
    media_url: Optional[str] = None


class ReceiveSMSRequest(BaseModel):
    from_number: str
    body: str
    media_url: Optional[str] = None


class ExpectMessageRequest(BaseModel):
    phone: str
    purpose: str


class SMSResponse(BaseModel):
    to: str
    body: str
    media_url: Optional[str]
    timestamp: float


@app.post("/send", response_model=SMSResponse)
def send_sms(req: SendSMSRequest):
    sms = sms_svc.send_sms(req.to, req.body, req.media_url)
    return SMSResponse(to=sms.to, body=sms.body, media_url=sms.media_url, timestamp=sms.timestamp)


@app.post("/receive")
def receive_sms(req: ReceiveSMSRequest):
    sms_svc.receive_sms(req.from_number, req.body, req.media_url)
    return {"status": "received"}


@app.post("/expect")
def expect_message(req: ExpectMessageRequest):
    sms_svc.expect_message_from(req.phone, req.purpose)
    return {"status": "ok"}


@app.get("/inbox/{phone}", response_model=List[SMSResponse])
def get_inbox(phone: str):
    messages = sms_svc.get_inbox_for(phone)
    return [SMSResponse(to=m.to, body=m.body, media_url=m.media_url, timestamp=m.timestamp) for m in messages]


@app.get("/stats")
def stats():
    return sms_svc.stats()


@app.get("/health")
def health():
    return {"status": "ok", "service": "sms"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
