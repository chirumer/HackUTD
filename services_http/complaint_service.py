"""Complaint Service - HTTP API."""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from bankassist.services.complaint import ComplaintService, Complaint

app = FastAPI(title="Complaint Service")
complaint_svc = ComplaintService()


class LodgeRequest(BaseModel):
    phone: str
    text: str
    image_url: Optional[str] = None


class ComplaintResponse(BaseModel):
    id: int
    phone: str
    text: str
    image_url: Optional[str]
    timestamp: float


@app.post("/lodge", response_model=ComplaintResponse)
def lodge(req: LodgeRequest):
    c = complaint_svc.lodge(req.phone, req.text, req.image_url)
    return ComplaintResponse(id=c.id, phone=c.phone, text=c.text, image_url=c.image_url, timestamp=c.timestamp)


@app.get("/recent", response_model=List[ComplaintResponse])
def recent(limit: int = 5):
    complaints = complaint_svc.list_recent(limit)
    return [ComplaintResponse(id=c.id, phone=c.phone, text=c.text, image_url=c.image_url, timestamp=c.timestamp) for c in complaints]


@app.get("/health")
def health():
    return {"status": "ok", "service": "complaint"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["complaint"])
