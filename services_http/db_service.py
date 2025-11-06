"""Database Service - HTTP API."""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import time
from bankassist.services.db import DatabaseService, Transaction
from bankassist.utils.logger import ServiceLogger
from bankassist.utils.metrics import MetricsCollector

app = FastAPI(title="Database Service")
db_svc = DatabaseService()

# Initialize logger and metrics
logger = ServiceLogger("database")
metrics = MetricsCollector("database")
logger.info("Database service starting up")

# Seed account
db_svc.ensure_account("alice", balance=1500.0)
logger.info("Seeded account 'alice' with $1500.00")


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
    logger.info(f"Ensuring account '{req.account_id}' with balance ${req.balance:.2f}", account=req.account_id)
    metrics.increment("accounts_ensured")
    db_svc.ensure_account(req.account_id, req.balance)
    return {"status": "ok"}


@app.post("/balance", response_model=BalanceResponse)
def get_balance(req: BalanceRequest):
    start_time = time.time()
    logger.debug(f"Reading balance for account '{req.account_id}'", account=req.account_id)
    metrics.increment("balance_reads")
    
    balance = db_svc.balance_of(req.account_id)
    
    elapsed = time.time() - start_time
    metrics.timing("balance_read_duration", elapsed)
    logger.info(f"Balance for '{req.account_id}': ${balance:.2f}", account=req.account_id, balance=balance)
    
    return BalanceResponse(account_id=req.account_id, balance=balance)


@app.post("/write_transaction", response_model=TransactionResponse)
def write_transaction(req: WriteTransactionRequest):
    start_time = time.time()
    logger.info(f"Writing transaction: {req.account_id} → {req.counterparty}: ${req.amount:.2f}", 
                account=req.account_id, counterparty=req.counterparty, amount=req.amount)
    metrics.increment("transactions_written")
    metrics.gauge("last_transaction_amount", req.amount)
    
    tx = db_svc.write_transaction(req.account_id, req.counterparty, req.amount)
    
    elapsed = time.time() - start_time
    metrics.timing("transaction_write_duration", elapsed)
    logger.info(f"Transaction #{tx.id} written successfully", tx_id=tx.id)
    
    return TransactionResponse(id=tx.id, account_id=tx.account_id, counterparty=tx.counterparty, amount=tx.amount, type=tx.type)


@app.post("/read_transactions", response_model=List[TransactionResponse])
def read_transactions(req: ReadTransactionsRequest):
    start_time = time.time()
    logger.debug(f"Reading {req.limit} transactions for '{req.account_id}'", account=req.account_id, limit=req.limit)
    metrics.increment("transaction_reads")
    
    txs = db_svc.read_transactions(req.account_id, req.limit)
    
    elapsed = time.time() - start_time
    metrics.timing("transaction_read_duration", elapsed)
    logger.info(f"Read {len(txs)} transactions for '{req.account_id}'", account=req.account_id, count=len(txs))
    
    return [TransactionResponse(id=t.id, account_id=t.account_id, counterparty=t.counterparty, amount=t.amount, type=t.type) for t in txs]


@app.get("/health")
def health():
    return {"status": "ok", "service": "db"}


@app.get("/logs")
def get_logs(limit: int = 100):
    """Get recent logs from this service."""
    return logger.get_recent_logs(limit=limit)


@app.get("/metrics")
def get_metrics(period: Optional[int] = None):
    """Get metrics from this service."""
    return metrics.get_all_metrics(time_period_minutes=period)


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["database"])
