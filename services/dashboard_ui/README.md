# Dashboard UI Service

Live monitoring web dashboard with real-time updates

## Purpose

Real-time monitoring interface:
- **Live Updates**: WebSocket-based real-time data
- **Service Status**: Visual service health indicators
- **Log Streaming**: Live log feed from all services
- **Metrics Graphs**: Time-series visualization
- **Dark Theme**: Modern, easy-on-eyes interface

Web-based monitoring console for operations.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8014)
- `SERVICE_NAME`: Service identifier (default: dashboard_ui)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

*No service-specific environment variables required.*

## API Endpoints

### GET /
Dashboard HTML UI

**Response:**
```json
<html>...</html>
```

### WS /ws
WebSocket live updates

**Response:**
```json
JSON stream every 2s
```

### GET /api/metrics/{service}
Get service metrics

**Response:**
```json
{"counters": {...}, "gauges": {...}}
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "dashboard_ui"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/dashboard_ui
python service.py
```

Or with environment variables:
```bash
PORT=8014 python service.py
```

## Metrics Tracked

- `websocket_connections`: Websocket Connections
- `ui_page_views`: Ui Page Views

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

Dashboard, All services (for visualization)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Service works out-of-the-box in production.
