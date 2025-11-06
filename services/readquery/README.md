# Read Query Service

Natural language to SQL read query service

## Purpose

Converts user questions to database reads:
- **Balance Queries**: "What's my balance?"
- **Transaction History**: "Show my last 5 transactions"
- **NL to SQL**: Maps natural language to read operations
- **Verification**: Requires verification for sensitive data

Routes to database service for actual data retrieval.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8008)
- `SERVICE_NAME`: Service identifier (default: readquery)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

*No service-specific environment variables required.*

## API Endpoints

### POST /query
Query account data

**Request:**
```json
{"user_text": "What is my balance?", "account_id": "alice", "verified": true}
```

**Response:**
```json
{"type": "balance", "amount": 1500.0}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "readquery"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/readquery
python service.py
```

Or with environment variables:
```bash
PORT=8008 python service.py
```

## Metrics Tracked

- `queries_processed`: Queries Processed
- `balance_queries`: Balance Queries
- `transaction_queries`: Transaction Queries

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

Handler, Database (for reads)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Service works out-of-the-box in production.
