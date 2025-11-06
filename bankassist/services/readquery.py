from __future__ import annotations
from typing import List
from .db import DatabaseService


class VerificationRequired(Exception):
    pass


class ReadQueryService:
    """Service that holds DB metadata and converts simple NL to SQL-like ops.
    This dummy version supports keywords like 'last transactions' and 'balance'.
    """

    def __init__(self, db: DatabaseService) -> None:
        self.db = db
        self.metadata = db.metadata

    def query(self, user_text: str, account_id: str, verified: bool) -> dict:
        if not verified:
            raise VerificationRequired("Additional verification required for account reads")
        lt = user_text.lower()
        if "last" in lt and "transaction" in lt:
            txs = self.db.read_transactions(account_id, limit=5)
            return {"type": "transactions", "items": [self.db.dictify(t) for t in txs]}
        if "balance" in lt:
            return {"type": "balance", "amount": self.db.balance_of(account_id)}
        # default
        return {"type": "unknown", "message": "Could not map to SQL query"}
