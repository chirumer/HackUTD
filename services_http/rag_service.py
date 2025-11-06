"""RAG Service - HTTP API for product/offers queries."""
from fastapi import FastAPI
from pydantic import BaseModel
from bankassist.services.rag import RAGService

app = FastAPI(title="RAG Service")
rag_svc = RAGService()


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    ans = rag_svc.query(req.question)
    return QueryResponse(answer=ans)


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["rag"])
