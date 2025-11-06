from __future__ import annotations
from typing import Optional
from .db import DatabaseService
from .fraud import FraudDetectionService


class VerificationRequired(Exception):
    pass


class WriteOperationService:
    """Service to perform writes with verification and fraud consent."""

    def __init__(self, db: DatabaseService, fraud: FraudDetectionService) -> None:
        self.db = db
        self.fraud = fraud

    def transfer(self, from_acct: str, to_acct: str, amount: float, verified: bool, context: Optional[dict] = None) -> dict:
        if not verified:
            raise VerificationRequired("Additional verification required for write operations")
        ok, reason = self.fraud.consent_for_write(from_acct, amount, context=context)
        if not ok:
            return {"status": "rejected", "reason": reason}
        tx = self.db.write_transaction(from_acct, to_acct, amount)
        return {"status": "ok", "transaction": self.db.dictify(tx)}
