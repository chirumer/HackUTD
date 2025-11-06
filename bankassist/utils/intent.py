from __future__ import annotations


def classify_intent(text: str) -> str:
    lt = text.lower()
    if any(w in lt for w in ["transfer", "send money", "pay", "move"]):
        return "write"
    if any(w in lt for w in ["how much", "balance", "last transactions", "transactions"]):
        return "read"
    if any(w in lt for w in ["offer", "card", "loan", "savings", "what do you have"]):
        return "offers"
    if any(w in lt for w in ["complaint", "issue", "problem", "fraud report"]):
        return "complaint"
    if any(w in lt for w in ["qr", "qr code", "merchant"]):
        return "qr"
    return "general"
