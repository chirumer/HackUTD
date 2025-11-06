# Fraud Detection Service

Fraud detection and transaction consent service

## Purpose

Security and fraud prevention:
- **Amount Checks**: Flag transactions above threshold
- **Consent Gates**: Require explicit consent for large transfers
- **Alert Generation**: Notify on suspicious activity
- **Risk Scoring**: Evaluate transaction risk

Configurable thresholds for different transaction types.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8006)
- `SERVICE_NAME`: Service identifier (default: fraud)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `FRAUD_THRESHOLD_AMOUNT`: Amount threshold for fraud checks (default: 1000)
- `ALERT_EMAIL`: Email address for fraud alerts

## API Endpoints

### POST /consent
Check transaction consent

**Request:**
```json
{"account_id": "alice", "amount": 500, "context": {}}
```

**Response:**
```json
{"consented": true, "reason": null}
```

### POST /alert
Generate fraud alert

**Request:**
```json
{"account_id": "alice", "reason": "Large transfer", "amount": 5000}
```

**Response:**
```json
{"alert_id": 1, "status": "sent"}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "fraud"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/fraud
python service.py
```

Or with environment variables:
```bash
PORT=8006 python service.py
```

## Metrics Tracked

- `checks_performed`: Checks Performed
- `checks_blocked`: Checks Blocked
- `alerts_generated`: Alerts Generated

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

WriteOps, QR (for security checks)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Configure `FRAUD_THRESHOLD_AMOUNT` and `ALERT_EMAIL` in `.env`
