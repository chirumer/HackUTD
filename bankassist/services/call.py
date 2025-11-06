from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import time


@dataclass
class Call:
    call_id: str
    phone: str
    direction: str  # 'inbound' or 'outbound'
    status: str  # 'ringing', 'in-progress', 'completed', 'failed'
    started_at: float
    ended_at: Optional[float] = None
    duration: Optional[int] = None  # in seconds
    transcript: Optional[str] = None


class CallService:
    """Manages phone calls - initiating, tracking, and logging calls.
    Separate from Voice Service which handles STT/TTS conversion.
    """

    def __init__(self) -> None:
        self.active_calls: dict[str, Call] = {}
        self.call_history: List[Call] = []
        self._next_call_id = 1

    def initiate_call(self, phone: str) -> Call:
        """Initiate an outbound call to a customer."""
        call_id = f"call_{self._next_call_id}"
        self._next_call_id += 1
        
        call = Call(
            call_id=call_id,
            phone=phone,
            direction="outbound",
            status="ringing",
            started_at=time.time()
        )
        self.active_calls[call_id] = call
        return call

    def receive_call(self, phone: str) -> Call:
        """Receive an inbound call from a customer."""
        call_id = f"call_{self._next_call_id}"
        self._next_call_id += 1
        
        call = Call(
            call_id=call_id,
            phone=phone,
            direction="inbound",
            status="ringing",
            started_at=time.time()
        )
        self.active_calls[call_id] = call
        return call

    def answer_call(self, call_id: str) -> bool:
        """Mark a call as answered and in progress."""
        if call_id not in self.active_calls:
            return False
        self.active_calls[call_id].status = "in-progress"
        return True

    def end_call(self, call_id: str, transcript: Optional[str] = None) -> bool:
        """End a call and move to history."""
        if call_id not in self.active_calls:
            return False
        
        call = self.active_calls.pop(call_id)
        call.status = "completed"
        call.ended_at = time.time()
        call.duration = int(call.ended_at - call.started_at)
        call.transcript = transcript
        
        self.call_history.append(call)
        return True

    def get_call(self, call_id: str) -> Optional[Call]:
        """Get call details by ID."""
        if call_id in self.active_calls:
            return self.active_calls[call_id]
        for call in self.call_history:
            if call.call_id == call_id:
                return call
        return None

    def get_active_calls(self) -> List[Call]:
        """Get all currently active calls."""
        return list(self.active_calls.values())

    def get_call_history(self, phone: Optional[str] = None, limit: int = 10) -> List[Call]:
        """Get call history, optionally filtered by phone number."""
        if phone:
            history = [c for c in self.call_history if c.phone == phone]
        else:
            history = self.call_history
        return history[-limit:]

    def stats(self) -> dict:
        """Get call statistics."""
        total_calls = len(self.call_history)
        inbound = sum(1 for c in self.call_history if c.direction == "inbound")
        outbound = total_calls - inbound
        
        completed = sum(1 for c in self.call_history if c.status == "completed")
        avg_duration = 0
        if completed > 0:
            total_duration = sum(c.duration or 0 for c in self.call_history if c.duration)
            avg_duration = total_duration / completed if completed else 0
        
        return {
            "active_calls": len(self.active_calls),
            "total_calls": total_calls,
            "inbound_calls": inbound,
            "outbound_calls": outbound,
            "completed_calls": completed,
            "avg_duration_seconds": round(avg_duration, 1)
        }
