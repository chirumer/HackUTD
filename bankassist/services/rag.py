from typing import List, Tuple


class RAGService:
    """Dummy Retrieval-Augmented Generation over bank documents.
    Uses naive keyword matching and returns top snippets.
    """

    def __init__(self) -> None:
        self.docs: List[Tuple[str, str]] = [
            ("credit_cards", "We offer Platinum and Gold cards with rewards."),
            ("savings", "Savings accounts with 3.5% APY and no monthly fees."),
            ("loans", "Personal loans up to $50k with flexible terms."),
        ]

    def query(self, question: str) -> str:
        q = question.lower()
        # lightweight keyword routing
        if any(k in q for k in ["credit", "card", "cards"]):
            key, text = self.docs[0]
            return f"From docs [{key}]: {text}"
        if any(k in q for k in ["saving", "savings", "apy"]):
            key, text = self.docs[1]
            return f"From docs [{key}]: {text}"
        if any(k in q for k in ["loan", "loans"]):
            key, text = self.docs[2]
            return f"From docs [{key}]: {text}"
        for key, text in self.docs:
            if key in q or any(w in q for w in text.lower().split()[:3]):
                return f"From docs [{key}]: {text}"
        return "I couldn't find a specific product match. We offer accounts, cards, and loans."
