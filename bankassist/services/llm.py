from typing import Optional


class LLMService:
    """Dummy LLM for general queries using provided context.
    Returns a templated answer referencing the context key names.
    """

    def __init__(self, context: Optional[dict] = None) -> None:
        self.context = context or {"bank_name": "DemoBank", "hours": "9-5 M-F"}

    def answer(self, question: str) -> str:
        q = question.lower()
        if "hours" in q:
            return f"{self.context['bank_name']} is open {self.context['hours']}."
        if "help" in q or "hello" in q:
            return f"Hello! I'm your {self.context['bank_name']} assistant. How can I help today?"
        return f"Here's some general info about {self.context['bank_name']}. Ask about hours, cards, or accounts."
