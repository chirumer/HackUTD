"""Write Operation Service - HTTP API."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
from bankassist.config import get_service_url

app = FastAPI(title="Write Operation Service")
FRAUD_URL = get_service_url("fraud")
DB_URL = get_service_url("db")


class TransferRequest(BaseModel):
    from_acct: str
    to_acct: str
    amount: float
    verified: bool
    context: Optional[dict] = None


class TransferResponse(BaseModel):
    status: str
    reason: Optional[str] = None
    transaction: Optional[dict] = None


@app.post("/transfer", response_model=TransferResponse)
def transfer(req: TransferRequest):
    if not req.verified:
        raise HTTPException(status_code=403, detail="Additional verification required for write operations")
    
    # Check fraud consent
    consent_resp = requests.post(f"{FRAUD_URL}/consent", json={
        "account_id": req.from_acct,
        "amount": req.amount,
        "context": req.context or {}
    })
    consent_resp.raise_for_status()
    consent_data = consent_resp.json()
    
    if not consent_data["consented"]:
        return TransferResponse(status="rejected", reason=consent_data.get("reason"))
    
    # Ensure to_acct exists
    requests.post(f"{DB_URL}/ensure_account", json={"account_id": req.to_acct, "balance": 0.0})
    
    # Perform write
    tx_resp = requests.post(f"{DB_URL}/write_transaction", json={
        "account_id": req.from_acct,
        "counterparty": req.to_acct,
        "amount": req.amount
    })
    tx_resp.raise_for_status()
    tx_data = tx_resp.json()
    
    return TransferResponse(status="ok", transaction=tx_data)


@app.get("/health")
def health():
    return {"status": "ok", "service": "writeops"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["writeops"])
