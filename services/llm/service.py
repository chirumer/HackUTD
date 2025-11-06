"""LLM Service - HTTP API for general queries."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from fastapi import FastAPI
from pydantic import BaseModel
from bankassist.services.llm import LLMService

from services.llm import config

app = FastAPI(title="LLM Service")
llm_svc = LLMService({"bank_name": "ElderCare Bank", "hours": "8-6 M-F"})


class AnswerRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str


@app.post("/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest):
    ans = llm_svc.answer(req.question)
    return AnswerResponse(answer=ans)


@app.get("/health")
def health():
    return {"status": "ok", "service": "llm"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
