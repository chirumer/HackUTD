# SMS Service

SMS messaging service for OTPs, notifications, and media links

## Purpose

Handles all SMS communication:
- **Send SMS**: Dispatch text messages to phone numbers
- **Receive SMS**: Process incoming SMS messages  
- **OTP Management**: Generate and validate one-time passwords
- **Media Links**: Send URLs for photo uploads and QR codes

Uses simulated SMS in development (replace with Twilio in production).

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8002)
- `SERVICE_NAME`: Service identifier (default: sms)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `TWILIO_ACCOUNT_SID`: Twilio account identifier
- `TWILIO_AUTH_TOKEN`: Twilio authentication token
- `TWILIO_PHONE_NUMBER`: Twilio phone number for sending

## API Endpoints

### POST /send
Send an SMS message

**Request:**
```json
{"to": "+1234567890", "body": "Your code is 1234"}
```

**Response:**
```json
{"status": "sent", "message_id": "msg_123"}
```

### POST /receive
Receive an SMS message

**Request:**
```json
{"from": "+1234567890", "body": "1234"}
```

**Response:**
```json
{"status": "received"}
```

### POST /expect
Set up OTP expectation

**Request:**
```json
{"phone": "+1234567890"}
```

**Response:**
```json
{"otp": "1234"}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "sms"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/sms
python service.py
```

Or with environment variables:
```bash
PORT=8002 python service.py
```

## Metrics Tracked

- `messages_sent`: Messages Sent
- `messages_received`: Messages Received
- `otp_generated`: Otp Generated

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

Handler, Complaint, QR (for messaging)

## Development

For development with simulated APIs, no environment configuration needed. For production:

1. Sign up for Twilio
2. Add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` to `.env`
