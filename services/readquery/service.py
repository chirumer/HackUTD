"""Read Query Service - HTTP API."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from shared.config import get_service_url

from services.readquery import config

app = FastAPI(title="Read Query Service")
DB_URL = get_service_url("database")


class QueryRequest(BaseModel):
    user_text: str
    account_id: str
    verified: bool


class QueryResponse(BaseModel):
    type: str
    items: list = []
    amount: float = 0.0
    message: str = ""


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.verified:
        raise HTTPException(status_code=403, detail="Additional verification required for account reads")
    
    lt = req.user_text.lower()
    if "last" in lt and "transaction" in lt:
        # Call DB service
        resp = requests.post(f"{DB_URL}/read_transactions", json={"account_id": req.account_id, "limit": 5})
        resp.raise_for_status()
        txs = resp.json()
        return QueryResponse(type="transactions", items=txs)
    
    if "balance" in lt:
        # Call DB service
        resp = requests.post(f"{DB_URL}/balance", json={"account_id": req.account_id})
        resp.raise_for_status()
        data = resp.json()
        return QueryResponse(type="balance", amount=data["balance"])
    
    return QueryResponse(type="unknown", message="Could not map to SQL query")


@app.get("/health")
def health():
    return {"status": "ok", "service": "readquery"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
