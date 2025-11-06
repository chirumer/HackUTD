"""Fraud Detection Service - HTTP API."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from bankassist.services.fraud import FraudDetectionService, FraudAlert

from services.fraud import config

app = FastAPI(title="Fraud Detection Service")
fraud_svc = FraudDetectionService(amount_threshold=1000.0)


class ConsentRequest(BaseModel):
    account_id: str
    amount: float
    context: Optional[dict] = None


class ConsentResponse(BaseModel):
    consented: bool
    reason: Optional[str]


class AlertResponse(BaseModel):
    timestamp: float
    account_id: str
    reason: str
    amount: float


@app.post("/consent", response_model=ConsentResponse)
def consent_for_write(req: ConsentRequest):
    ok, reason = fraud_svc.consent_for_write(req.account_id, req.amount, req.context)
    return ConsentResponse(consented=ok, reason=reason)


@app.get("/alerts", response_model=List[AlertResponse])
def latest_alerts(limit: int = 5):
    alerts = fraud_svc.latest_alerts(limit)
    return [AlertResponse(timestamp=a.timestamp, account_id=a.account_id, reason=a.reason, amount=a.amount) for a in alerts]


@app.get("/stats")
def stats():
    return fraud_svc.stats()


@app.get("/health")
def health():
    return {"status": "ok", "service": "fraud"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
