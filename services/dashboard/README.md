# Dashboard Service

Admin dashboard JSON API aggregating service stats

## Purpose

System monitoring API:
- **Status Aggregation**: Collect status from all services
- **Metrics Rollup**: Aggregate metrics across services
- **Health Checks**: Monitor service health
- **JSON API**: Provides data for dashboards and monitoring

Backend for admin and monitoring interfaces.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8013)
- `SERVICE_NAME`: Service identifier (default: dashboard)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

*No service-specific environment variables required.*

## API Endpoints

### GET /status
Get system status

**Response:**
```json
{"timestamp": ..., "services": {...}}
```

### GET /metrics
Get aggregated metrics

**Response:**
```json
{"total_requests": 100, ...}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "dashboard"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/dashboard
python service.py
```

Or with environment variables:
```bash
PORT=8013 python service.py
```

## Metrics Tracked

- `status_requests`: Status Requests
- `metrics_requests`: Metrics Requests

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

All services (for monitoring)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Service works out-of-the-box in production.
