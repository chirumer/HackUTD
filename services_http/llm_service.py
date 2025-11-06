"""LLM Service - HTTP API for general queries."""
from fastapi import FastAPI
from pydantic import BaseModel
from bankassist.services.llm import LLMService

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
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["llm"])
