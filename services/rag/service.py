"""RAG Service - HTTP API for product/offers queries."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from fastapi import FastAPI
from pydantic import BaseModel
from bankassist.services.rag import RAGService

from services.rag import config

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
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
