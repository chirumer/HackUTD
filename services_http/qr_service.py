"""QR Code Service - HTTP API."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
import json
import base64
from bankassist.config import get_service_url

app = FastAPI(title="QR Code Service")
FRAUD_URL = get_service_url("fraud")


class CreateQRRequest(BaseModel):
    account_id: str
    amount: float
    verified: bool
    context: Optional[dict] = None


class CreateQRResponse(BaseModel):
    status: str
    reason: Optional[str] = None
    qr_code: Optional[str] = None


@app.post("/create", response_model=CreateQRResponse)
def create_qr(req: CreateQRRequest):
    if not req.verified:
        return CreateQRResponse(status="rejected", reason="verification required")
    
    # Check fraud consent
    consent_resp = requests.post(f"{FRAUD_URL}/consent", json={
        "account_id": req.account_id,
        "amount": req.amount,
        "context": req.context or {}
    })
    consent_resp.raise_for_status()
    consent_data = consent_resp.json()
    
    if not consent_data["consented"]:
        return CreateQRResponse(status="rejected", reason=consent_data.get("reason"))
    
    # Create QR payload
    payload = {"account_id": req.account_id, "amount": req.amount}
    qr_code = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    
    return CreateQRResponse(status="ok", qr_code=qr_code)


@app.get("/health")
def health():
    return {"status": "ok", "service": "qr"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["qr"])
