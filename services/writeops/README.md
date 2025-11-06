# Write Operations Service

Write operations service for fund transfers

## Purpose

Handles money movement operations:
- **Transfers**: Move funds between accounts
- **Fraud Checks**: Coordinate with fraud detection
- **Verification**: Ensure user is verified
- **Atomic Operations**: Guarantee transfer completion

Critical path for financial transactions.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8009)
- `SERVICE_NAME`: Service identifier (default: writeops)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

*No service-specific environment variables required.*

## API Endpoints

### POST /transfer
Transfer funds

**Request:**
```json
{"from_acct": "alice", "to_acct": "bob", "amount": 50, "verified": true}
```

**Response:**
```json
{"status": "ok", "transaction": {...}}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "writeops"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/writeops
python service.py
```

Or with environment variables:
```bash
PORT=8009 python service.py
```

## Metrics Tracked

- `transfers_completed`: Transfers Completed
- `transfers_blocked`: Transfers Blocked
- `total_amount_transferred`: Total Amount Transferred

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

Handler, Fraud, Database (for writes)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Service works out-of-the-box in production.
