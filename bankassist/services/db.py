from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Transaction:
    id: int
    account_id: str
    counterparty: str
    amount: float
    type: str  # 'debit' or 'credit'


class DatabaseService:
    """In-memory DB for demo with simple schema and metadata."""

    def __init__(self) -> None:
        self._txs: List[Transaction] = []
        self._next_id = 1
        # pretend metadata
        self.metadata = {
            "transactions": ["id", "account_id", "counterparty", "amount", "type"],
            "accounts": ["account_id", "name", "balance"],
        }
        self._balances: dict[str, float] = {}

    def ensure_account(self, account_id: str, balance: float = 0.0) -> None:
        self._balances.setdefault(account_id, balance)

    def balance_of(self, account_id: str) -> float:
        return self._balances.get(account_id, 0.0)

    def write_transaction(self, account_id: str, counterparty: str, amount: float) -> Transaction:
        # debit from account_id
        self._balances[account_id] = self._balances.get(account_id, 0.0) - amount
        self._balances[counterparty] = self._balances.get(counterparty, 0.0) + amount
        tx = Transaction(self._next_id, account_id, counterparty, amount, "debit")
        self._txs.append(tx)
        self._next_id += 1
        return tx

    def read_transactions(self, account_id: str, limit: int = 10) -> List[Transaction]:
        return [t for t in self._txs if t.account_id == account_id][-limit:]

    def dictify(self, tx: Transaction) -> dict:
        return {
            "id": tx.id,
            "account_id": tx.account_id,
            "counterparty": tx.counterparty,
            "amount": tx.amount,
            "type": tx.type,
        }
