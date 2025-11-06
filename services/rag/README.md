# RAG Service

Retrieval-Augmented Generation for product/offers queries

## Purpose

Document-based question answering:
- **Product Info**: Query bank products from documentation
- **Offers**: Retrieve current promotions and offers
- **Policy Info**: Search policy documents
- **Vector Search**: Semantic search through documents

Uses simulated document search (replace with vector DB in production).

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8005)
- `SERVICE_NAME`: Service identifier (default: rag)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `OPENAI_API_KEY`: OpenAI API key for embeddings
- `VECTOR_DB_PATH`: Path to vector database

## API Endpoints

### POST /query
Query documents

**Request:**
```json
{"question": "What credit cards do you offer?"}
```

**Response:**
```json
{"answer": "From docs: We offer..."}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "rag"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/rag
python service.py
```

Or with environment variables:
```bash
PORT=8005 python service.py
```

## Metrics Tracked

- `queries_processed`: Queries Processed
- `documents_retrieved`: Documents Retrieved

## Dependencies

See `requirements.txt` for full list. Key dependencies:
- FastAPI - Web framework
- Uvicorn - ASGI server
- Pydantic - Data validation
- python-dotenv - Environment configuration

## Testing

Run tests for this service:

```bash
pytest test_service.py -v
```

## Related Services

Handler (for document queries)

## Development

For development with simulated APIs, no environment configuration needed. For production:

1. Set up vector database (ChromaDB)
2. Add `OPENAI_API_KEY` and `VECTOR_DB_PATH` to `.env`
