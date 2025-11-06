# Call Service

Phone call management and tracking service

## Purpose

Manages all voice call operations:
- **Initiate Calls**: Start outbound calls to customers
- **Receive Calls**: Handle inbound customer calls
- **Call Tracking**: Monitor active calls and history
- **Transcripts**: Store call transcripts and duration

Uses simulated calls in development (replace with Twilio in production).

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8003)
- `SERVICE_NAME`: Service identifier (default: call)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `TWILIO_ACCOUNT_SID`: Twilio account identifier
- `TWILIO_AUTH_TOKEN`: Twilio authentication token

## API Endpoints

### POST /initiate
Start outbound call

**Request:**
```json
{"phone": "+1234567890"}
```

**Response:**
```json
{"call_id": "call_123", "status": "initiated"}
```

### POST /receive
Handle inbound call

**Request:**
```json
{"phone": "+1234567890"}
```

**Response:**
```json
{"call_id": "call_123", "status": "ringing"}
```

### POST /answer
Answer a call

**Request:**
```json
{"call_id": "call_123"}
```

**Response:**
```json
{"status": "answered"}
```

### POST /end
End a call

**Request:**
```json
{"call_id": "call_123", "transcript": "..."}
```

**Response:**
```json
{"status": "ended", "duration": 45.2}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "call"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/call
python service.py
```

Or with environment variables:
```bash
PORT=8003 python service.py
```

## Metrics Tracked

- `calls_initiated`: Calls Initiated
- `calls_received`: Calls Received
- `calls_active`: Calls Active
- `avg_call_duration`: Avg Call Duration

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

Handler (for call management)

## Development

For development with simulated APIs, no environment configuration needed. For production:

1. Sign up for Twilio
2. Add `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` to `.env`
