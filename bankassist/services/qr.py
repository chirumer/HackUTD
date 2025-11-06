from __future__ import annotations
import base64
import json
from typing import Optional
from .fraud import FraudDetectionService


class QRCodeService:
    """Dummy QR code generator that returns a base64 payload string as QR representation."""

    def __init__(self, fraud: FraudDetectionService) -> None:
        self.fraud = fraud

    def create_qr(self, account_id: str, amount: float, verified: bool, context: Optional[dict] = None) -> dict:
        if not verified:
            return {"status": "rejected", "reason": "verification required"}
        ok, reason = self.fraud.consent_for_write(account_id, amount, context=context)
        if not ok:
            return {"status": "rejected", "reason": reason}
        payload = {"account_id": account_id, "amount": amount}
        qr_code = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        return {"status": "ok", "qr_code": qr_code}
