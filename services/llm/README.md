# LLM Service

Large Language Model service for general Q&A

## Purpose

Provides conversational AI capabilities:
- **General Questions**: Answer banking-related queries
- **Conversational**: Natural language understanding
- **Context-Aware**: Maintains conversation context
- **Fallback**: Handles questions outside other services' scope

Uses simulated responses in development (replace with OpenAI in production).

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8004)
- `SERVICE_NAME`: Service identifier (default: llm)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: Model name (gpt-4, gpt-3.5-turbo)

## API Endpoints

### POST /answer
Get answer to question

**Request:**
```json
{"question": "How do I reset my PIN?"}
```

**Response:**
```json
{"answer": "To reset your PIN, visit..."}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "llm"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/llm
python service.py
```

Or with environment variables:
```bash
PORT=8004 python service.py
```

## Metrics Tracked

- `questions_answered`: Questions Answered
- `avg_response_time`: Avg Response Time

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

Handler (for general Q&A)

## Development

For development with simulated APIs, no environment configuration needed. For production:

1. Get OpenAI API key
2. Add `OPENAI_API_KEY` to `.env`
