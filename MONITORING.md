# 📊 Monitoring & Observability Guide

## Overview

The BankAssist microservices architecture includes comprehensive monitoring and observability features:

- **Structured Logging**: All services log extensively with timestamps, log levels, and context
- **Metrics Collection**: Time-series metrics tracking for requests, transactions, calls, and more
- **Live Dashboard**: Real-time web dashboard showing service status, logs, and graphs
- **Health Endpoints**: All services expose health check endpoints
- **Logs API**: Each service exposes `/logs` endpoint for recent log entries
- **Metrics API**: Each service exposes `/metrics` endpoint for time-series data

## Dashboard UI

Access the live monitoring dashboard at: **http://localhost:8014**

### Features

✨ **Dark-themed** modern UI optimized for monitoring  
🔄 **Live updates** via WebSockets (2-second refresh)  
📊 **Real-time graphs** with customizable time periods  
📜 **Live log streaming** from all services  
🎯 **Service health status** with color-coded indicators  
📈 **System-wide metrics** aggregation

### Dashboard Sections

#### 1. Service Status
- Shows all 14 microservices with real-time status
- Color-coded indicators (green=healthy, red=down)
- Port numbers for each service
- Hover effects for better UX

#### 2. System Metrics
Grid showing key metrics:
- **Healthy Services**: X/14 services online
- **Total Requests**: Aggregate request count
- **Active Calls**: Number of calls in progress
- **SMS Sent**: Total SMS messages

#### 3. Time-Series Graphs
Interactive charts with controls:
- **Metric selector**: Choose from requests, fraud checks, calls, SMS, transactions
- **Time period**: 5min, 15min, 1hr, 6hr, 24hr
- **Auto-refresh**: Updates every 2 seconds via WebSocket
- Powered by Chart.js

#### 4. Live Logs
- Real-time log streaming from all services
- Color-coded by log level (INFO=blue, WARNING=yellow, ERROR=red)
- Shows timestamp, service name, and message
- Auto-scrolling with last 50 entries visible

## Service Logging

### Logger Utility

All services use the `ServiceLogger` class from `bankassist/utils/logger.py`:

```python
from bankassist.utils.logger import ServiceLogger

logger = ServiceLogger("my_service")
logger.info("Processing request", user_id=123, action="transfer")
logger.warning("Rate limit approaching", remaining=5)
logger.error("Database connection failed", error=str(e))
```

### Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical messages for very severe errors

### Structured Logging

Logs include:
- `timestamp`: ISO 8601 formatted timestamp
- `service`: Service name
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message`: Human-readable message
- `context`: Additional key-value pairs

Example log entry:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "service": "handler",
  "level": "INFO",
  "message": "Handling request from +1234567890",
  "phone": "+1234567890",
  "account": "alice"
}
```

## Metrics Collection

### Metrics Utility

All services use the `MetricsCollector` class from `bankassist/utils/metrics.py`:

```python
from bankassist.utils.metrics import MetricsCollector

metrics = MetricsCollector("my_service")
metrics.increment("requests_total")  # Counter
metrics.gauge("active_connections", 42)  # Gauge
metrics.timing("request_duration", 0.125)  # Timing in seconds
```

### Metric Types

1. **Counters**: Monotonically increasing values
   - Example: `requests_total`, `transactions_written`, `calls_initiated`
   
2. **Gauges**: Point-in-time values that can go up or down
   - Example: `active_connections`, `queue_size`, `last_transaction_amount`
   
3. **Timings**: Duration measurements in seconds
   - Example: `request_duration`, `db_query_time`, `api_response_time`

### Time-Series Storage

- Each metric stores up to 1000 datapoints
- Older datapoints automatically evicted (FIFO)
- Timestamps recorded automatically
- Query by time period via API

## API Endpoints

### Health Check
**All services**: `GET /health`

Returns service health status:
```json
{
  "status": "ok",
  "service": "handler"
}
```

### Logs Endpoint
**All services**: `GET /logs?limit=100`

Returns recent log entries:
```json
[
  {
    "timestamp": "2024-01-15T10:30:45.123Z",
    "service": "handler",
    "level": "INFO",
    "message": "Request processed successfully"
  }
]
```

### Metrics Endpoint
**All services**: `GET /metrics?period=60`

Returns metrics for the specified time period (in minutes):
```json
{
  "counters": {
    "requests_total": 1234,
    "transactions_written": 56
  },
  "gauges": {
    "active_connections": 42
  },
  "timings": [
    {
      "name": "request_duration",
      "timestamp": "2024-01-15T10:30:45.123Z",
      "value": 0.125
    }
  ]
}
```

## Service-Specific Metrics

### Handler Service (8012)
- `requests_total`: Total requests handled
- `intent_{name}`: Count per intent type (general, read, write, etc.)
- `calls_ended`: Number of calls terminated
- `request_duration`: Time to process requests

### Voice Service (8001)
- `transcriptions_total`: Total speech-to-text conversions
- `syntheses_total`: Total text-to-speech conversions
- `transcription_duration`: Time to transcribe audio
- `synthesis_duration`: Time to synthesize speech

### Database Service (8007)
- `accounts_ensured`: Accounts created/verified
- `balance_reads`: Balance query count
- `transactions_written`: Transactions recorded
- `transaction_reads`: Transaction history queries
- `last_transaction_amount`: Most recent transaction value
- `balance_read_duration`: Balance query timing
- `transaction_write_duration`: Transaction write timing

### Call Service (8003)
- `calls_initiated`: Outbound calls started
- `calls_received`: Inbound calls received
- `calls_answered`: Calls answered
- `calls_ended`: Calls terminated
- `call_duration`: Average call length

### SMS Service (8002)
- `messages_sent`: SMS messages sent
- `messages_received`: SMS messages received
- `expect_calls`: OTP expectations set

### Fraud Detection Service (8006)
- `checks_performed`: Total fraud checks
- `checks_passed`: Checks that passed
- `checks_blocked`: Checks that blocked transactions
- `check_duration`: Time to perform fraud check

## Monitoring Best Practices

### 1. Log Appropriately
- **DEBUG**: Implementation details, variable values
- **INFO**: Normal operations, state changes
- **WARNING**: Recoverable issues, rate limits
- **ERROR**: Failures requiring attention
- **CRITICAL**: System-threatening issues

### 2. Track Key Metrics
- Request rates and latencies
- Error rates and types
- Resource utilization
- Business metrics (transactions, calls, etc.)

### 3. Use Context
Always include relevant context in logs:
```python
logger.info("Transfer completed", 
            from_account=from_acct,
            to_account=to_acct,
            amount=amount,
            tx_id=tx.id)
```

### 4. Monitor Timing
Track operation durations:
```python
start = time.time()
# ... perform operation ...
elapsed = time.time() - start
metrics.timing("operation_duration", elapsed)
```

### 5. Dashboard Usage
- Check service health at a glance
- Monitor request patterns over time
- Investigate errors via live logs
- Adjust time periods for different views

## WebSocket Protocol

The dashboard uses WebSocket for live updates:

**Connection**: `ws://localhost:8014/ws`

**Update Frequency**: Every 2 seconds

**Message Format**:
```json
{
  "timestamp": 1234567890.123,
  "services": {
    "handler": {
      "status": "ok",
      "port": 8012,
      "metrics": { ... }
    },
    ...
  },
  "logs": [...]
}
```

## Troubleshooting

### Dashboard Not Loading
1. Check if dashboard_ui service is running: `lsof -i :8014`
2. Verify WebSocket connection in browser console
3. Check logs: `tail logs/dashboard_ui_stdout.log`

### Missing Metrics
1. Ensure service has `/metrics` endpoint
2. Check if logger/metrics initialized in service
3. Verify metrics.increment/gauge/timing calls

### Service Shows as Down
1. Check service logs in `logs/` directory
2. Verify port not already in use
3. Test health endpoint: `curl http://localhost:PORT/health`

### Logs Not Appearing
1. Confirm `/logs` endpoint exists on service
2. Check if logger is initialized
3. Verify log statements are being executed

## Architecture

```
┌─────────────────────────────────────────────┐
│         Dashboard UI (Port 8014)            │
│  - WebSocket Server                         │
│  - Static HTML/CSS/JS                       │
│  - Live Updates Every 2s                    │
└─────────────────────────────────────────────┘
                    ▲
                    │ WebSocket + HTTP
                    ▼
┌─────────────────────────────────────────────┐
│         All Microservices                   │
│  - /health  → Health check                  │
│  - /logs    → Recent log entries            │
│  - /metrics → Time-series metrics           │
│                                             │
│  Each service:                              │
│  - ServiceLogger instance                   │
│  - MetricsCollector instance                │
│  - Structured logging                       │
│  - Metric tracking                          │
└─────────────────────────────────────────────┘
```

## Next Steps

1. **Alerting**: Add alerts for critical metrics
2. **Persistence**: Store logs/metrics in database
3. **Dashboards**: Create custom dashboards per service
4. **Correlation**: Link logs across services by request ID
5. **Analysis**: Add log search and filtering
6. **Export**: Export metrics to Prometheus/Grafana

## Resources

- **Dashboard UI**: http://localhost:8014
- **Handler API**: http://localhost:8012
- **Logs Directory**: `/logs/`
- **Logger Utility**: `bankassist/utils/logger.py`
- **Metrics Utility**: `bankassist/utils/metrics.py`
