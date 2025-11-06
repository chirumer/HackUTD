from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import time


@dataclass
class FraudAlert:
    timestamp: float
    account_id: str
    reason: str
    amount: float


class FraudDetectionService:
    """Dummy fraud detection service.
    - Maintains alerts
    - Provides consent gate for write operations
    - Can be queried for details
    """

    def __init__(self, amount_threshold: float = 2000.0) -> None:
        self.amount_threshold = amount_threshold
        self.alerts: List[FraudAlert] = []
        self.total_checks: int = 0
        self.total_rejections: int = 0

    def consent_for_write(self, account_id: str, amount: float, context: Optional[dict] = None) -> tuple[bool, Optional[str]]:
        """Return (consented, reason). Reject if amount exceeds threshold or flagged context."""
        self.total_checks += 1
        if amount >= self.amount_threshold:
            self.total_rejections += 1
            reason = f"Amount {amount:.2f} exceeds threshold {self.amount_threshold:.2f}"
            self.alerts.append(FraudAlert(time.time(), account_id, reason, amount))
            return False, reason
        if context and context.get("suspicious_device"):
            self.total_rejections += 1
            reason = "Suspicious device fingerprint"
            self.alerts.append(FraudAlert(time.time(), account_id, reason, amount))
            return False, reason
        return True, None

    def latest_alerts(self, limit: int = 5) -> List[FraudAlert]:
        return self.alerts[-limit:]

    def stats(self) -> dict:
        return {
            "checks": self.total_checks,
            "rejections": self.total_rejections,
            "alerts": len(self.alerts),
            "threshold": self.amount_threshold,
        }
