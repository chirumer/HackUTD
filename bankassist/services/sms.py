from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import time


@dataclass
class SMS:
    to: str
    body: str
    media_url: Optional[str] = None
    timestamp: float = time.time()


class SMSService:
    """Dummy SMS service. Keeps an outbox and an inbox. Supports 'expected' messages.
    Messages not expected can be ignored by consumers.
    """

    def __init__(self) -> None:
        self.outbox: List[SMS] = []
        self.inbox: List[SMS] = []
        self.expected_from_numbers: Dict[str, str] = {}  # phone -> purpose

    def send_sms(self, to: str, body: str, media_url: Optional[str] = None) -> SMS:
        sms = SMS(to=to, body=body, media_url=media_url)
        self.outbox.append(sms)
        return sms

    def expect_message_from(self, phone: str, purpose: str) -> None:
        self.expected_from_numbers[phone] = purpose

    def receive_sms(self, from_number: str, body: str, media_url: Optional[str] = None) -> None:
        # Simulate inbound; store only if expected
        if from_number in self.expected_from_numbers:
            self.inbox.append(SMS(to=from_number, body=body, media_url=media_url))
            # clear expectation after one receive for simplicity
            self.expected_from_numbers.pop(from_number, None)

    def get_inbox_for(self, phone: str) -> List[SMS]:
        return [m for m in self.inbox if m.to == phone]

    def stats(self) -> dict:
        return {
            "outbox_count": len(self.outbox),
            "inbox_count": len(self.inbox),
            "active_expectations": len(self.expected_from_numbers),
        }
