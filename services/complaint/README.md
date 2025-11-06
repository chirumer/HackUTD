# Complaint Service

Customer complaint filing with photo upload support

## Purpose

Complaint management system:
- **Lodge Complaints**: File customer complaints
- **Photo Upload**: Support image attachments
- **SMS Links**: Send secure upload links
- **Tracking**: Track complaint status and IDs

Provides customer service support workflow.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8010)
- `SERVICE_NAME`: Service identifier (default: complaint)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `UPLOAD_STORAGE_PATH`: Path for uploaded complaint files
- `MAX_FILE_SIZE_MB`: Maximum file size in megabytes

## API Endpoints

### POST /lodge
File a complaint

**Request:**
```json
{"phone": "+1234567890", "text": "Wrong charge", "image_url": "..."}
```

**Response:**
```json
{"id": 1, "status": "filed"}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "complaint"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/complaint
python service.py
```

Or with environment variables:
```bash
PORT=8010 python service.py
```

## Metrics Tracked

- `complaints_filed`: Complaints Filed
- `complaints_with_images`: Complaints With Images

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

Handler, SMS (for complaint filing)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Service works out-of-the-box in production.
