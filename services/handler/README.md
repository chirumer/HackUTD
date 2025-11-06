# Handler Service

Main orchestrator routing requests to services

## Purpose

Central request orchestrator:
- **Intent Classification**: Determine user intent from text
- **Service Routing**: Route to appropriate microservice
- **Session Management**: Track user sessions and verification
- **Response Aggregation**: Combine responses from multiple services
- **Verification Flows**: Coordinate OTP and verification

The brain of the system - coordinates all other services.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8012)
- `SERVICE_NAME`: Service identifier (default: handler)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

*No service-specific environment variables required.*

## API Endpoints

### POST /handle
Handle user request

**Request:**
```json
{"phone": "+1234567890", "account_id": "alice", "text": "What is my balance?", "verified": false}
```

**Response:**
```json
{"reply": "...", "session_verified": true}
```

### POST /call/initiate
Initiate call

**Request:**
```json
{"phone": "+1234567890"}
```

**Response:**
```json
{"call_id": "call_123"}
```

### POST /call/end
End call

**Request:**
```json
{"call_id": "call_123", "transcript": "..."}
```

**Response:**
```json
{"status": "ended"}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "handler"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/handler
python service.py
```

Or with environment variables:
```bash
PORT=8012 python service.py
```

## Metrics Tracked

- `requests_total`: Requests Total
- `intent_general`: Intent General
- `intent_read`: Intent Read
- `intent_write`: Intent Write
- `calls_handled`: Calls Handled

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

All services (orchestrates everything)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Service works out-of-the-box in production.
