"""Database Service - HTTP API."""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from bankassist.services.db import DatabaseService, Transaction

app = FastAPI(title="Database Service")
db_svc = DatabaseService()

# Seed account
db_svc.ensure_account("alice", balance=1500.0)


class EnsureAccountRequest(BaseModel):
    account_id: str
    balance: float = 0.0


class BalanceRequest(BaseModel):
    account_id: str


class BalanceResponse(BaseModel):
    account_id: str
    balance: float


class WriteTransactionRequest(BaseModel):
    account_id: str
    counterparty: str
    amount: float


class TransactionResponse(BaseModel):
    id: int
    account_id: str
    counterparty: str
    amount: float
    type: str


class ReadTransactionsRequest(BaseModel):
    account_id: str
    limit: int = 10


@app.post("/ensure_account")
def ensure_account(req: EnsureAccountRequest):
    db_svc.ensure_account(req.account_id, req.balance)
    return {"status": "ok"}


@app.post("/balance", response_model=BalanceResponse)
def get_balance(req: BalanceRequest):
    balance = db_svc.balance_of(req.account_id)
    return BalanceResponse(account_id=req.account_id, balance=balance)


@app.post("/write_transaction", response_model=TransactionResponse)
def write_transaction(req: WriteTransactionRequest):
    tx = db_svc.write_transaction(req.account_id, req.counterparty, req.amount)
    return TransactionResponse(id=tx.id, account_id=tx.account_id, counterparty=tx.counterparty, amount=tx.amount, type=tx.type)


@app.post("/read_transactions", response_model=List[TransactionResponse])
def read_transactions(req: ReadTransactionsRequest):
    txs = db_svc.read_transactions(req.account_id, req.limit)
    return [TransactionResponse(id=t.id, account_id=t.account_id, counterparty=t.counterparty, amount=t.amount, type=t.type) for t in txs]


@app.get("/health")
def health():
    return {"status": "ok", "service": "db"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["db"])
