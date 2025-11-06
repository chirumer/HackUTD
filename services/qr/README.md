# QR Code Service

QR code generation for payments

## Purpose

Payment QR code generation:
- **Create QR Codes**: Generate payment QR codes
- **Amount Encoding**: Embed payment amount and account
- **Expiry Management**: Set QR code expiration
- **SMS Delivery**: Send QR codes via SMS

Enables contactless payment workflows.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8011)
- `SERVICE_NAME`: Service identifier (default: qr)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `QR_EXPIRY_MINUTES`: QR code expiration time in minutes

## API Endpoints

### POST /create
Generate QR code

**Request:**
```json
{"account_id": "alice", "amount": 20, "verified": true}
```

**Response:**
```json
{"status": "ok", "qr_code_url": "..."}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "qr"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/qr
python service.py
```

Or with environment variables:
```bash
PORT=8011 python service.py
```

## Metrics Tracked

- `qr_codes_generated`: Qr Codes Generated
- `qr_codes_expired`: Qr Codes Expired

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

Handler, SMS, Fraud (for QR generation)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Service works out-of-the-box in production.
