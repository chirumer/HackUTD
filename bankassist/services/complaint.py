from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import time


@dataclass
class Complaint:
    id: int
    phone: str
    text: str
    image_url: Optional[str]
    timestamp: float


class ComplaintService:
    """Dummy complaint service that stores complaints with optional image."""

    def __init__(self) -> None:
        self._complaints: List[Complaint] = []
        self._next_id = 1

    def lodge(self, phone: str, text: str, image_url: Optional[str]) -> Complaint:
        c = Complaint(self._next_id, phone, text, image_url, time.time())
        self._complaints.append(c)
        self._next_id += 1
        return c

    def list_recent(self, limit: int = 5) -> List[Complaint]:
        return self._complaints[-limit:]
