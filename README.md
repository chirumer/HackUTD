# Elder Voice Banking - Microservices Architecture

This repository demonstrates a voice-first banking assistant for elder users using **HTTP-based microservices** with FastAPI. Each service runs independently and communicates via REST APIs.

## Architecture Overview

### Microservices

Each service runs on its own port and communicates via HTTP:

- **Voice Service** (port 8001): STT and TTS conversion (simulated Azure Voice)
- **SMS Service** (port 8002): Send/receive SMS, OTPs, media
- **LLM Service** (port 8003): General Q&A with context
- **RAG Service** (port 8004): Product/offers queries from bank documents
- **Fraud Detection** (port 8005): Consent gate for writes, alerts
- **Database Service** (port 8006): In-memory transactions and balances
- **Read Query Service** (port 8007): NL→SQL reads with verification
- **Write Operations** (port 8008): Transfers with fraud consent
- **Complaint Service** (port 8009): Lodge complaints with photos
- **QR Code Service** (port 8010): Generate payment QR codes
- **Handler Service** (port 8011): **Orchestrator** - routes intents, manages sessions
- **Dashboard Service** (port 8012): Admin view aggregating all service stats

### Communication Flow

```
User (Voice) → Handler Service → {LLM, RAG, ReadQuery, WriteOps, etc.} → Database/Fraud/SMS
                     ↓
              Orchestrates all services via HTTP
                     ↓
              Returns user-friendly response
```

The Handler is the **orchestrator** that:
- Classifies user intent (general, offers, read, write, complaint, QR)
- Routes to appropriate services via HTTP requests
- Manages verification flows (OTP via SMS)
- Coordinates fraud consent checks
- Returns friendly responses

## Project Layout

```
bankassist/
  services/          - Core service logic (business logic layer)
                      Used by HTTP services as their backend
  utils/             - Intent classifier
  config.py          - Service port configuration
services_http/       - FastAPI microservice HTTP APIs (12 services)
  voice_service.py        - Port 8001
  sms_service.py          - Port 8002
  llm_service.py          - Port 8003
  rag_service.py          - Port 8004
  fraud_service.py        - Port 8005
  db_service.py           - Port 8006
  readquery_service.py    - Port 8007
  writeops_service.py     - Port 8008
  complaint_service.py    - Port 8009
  qr_service.py           - Port 8010
  handler_service.py      - Port 8011 (orchestrator)
  dashboard_service.py    - Port 8012
start_services.py    - Boot all 12 services
demo_client.py       - HTTP client demo
logs/                - Service logs (auto-generated)
requirements.txt     - Python dependencies
README.md            - This file
ARCHITECTURE.md      - Service diagrams & flows
API_EXAMPLES.md      - API testing examples
```

## Setup

Install dependencies:

```bash
pip3 install -r requirements.txt
```

## Running the Application

### 1. Start All Services

In one terminal, boot all microservices:

```bash
python3 start_services.py
```

This will:
- Start 12 services in background processes
- Run health checks
- Display service endpoints
- Keep running until Ctrl+C

Expected output:
```
🚀 Starting all services...
Starting voice        on port 8001...
Starting sms          on port 8002...
...
✅ Started 12 services
✅ All services are healthy and ready!
```

### 2. Run the Demo

In another terminal, run the demo client:

```bash
python3 demo_client.py
```

This simulates a phone conversation with multiple intents (general query, balance check, transfer, QR code, complaint).

### 3. View Dashboard

While services are running, check the admin dashboard:

```bash
curl http://localhost:8012/status
```

Or visit in browser: http://localhost:8012/status

### 4. Stop Services

Press `Ctrl+C` in the terminal running `start_services.py`.

## Architecture Notes

### Why keep `bankassist/services/`?

The `bankassist/services/` folder contains the **core business logic** for each service. The HTTP services in `services_http/` are thin wrappers that:
1. Define FastAPI endpoints
2. Call the core logic from `bankassist/services/`
3. Handle HTTP serialization/deserialization

This separation allows:
- Business logic to be tested independently
- Easy migration to different frameworks (gRPC, GraphQL, etc.)
- Reusable logic across multiple interfaces

**Exception:** `handler_service.py` and `dashboard_service.py` contain their logic directly since they're purely orchestration services.

## Testing Individual Services

Each service has a `/health` endpoint:

```bash
curl http://localhost:8001/health  # Voice
curl http://localhost:8002/health  # SMS
curl http://localhost:8011/health  # Handler
```

Test the Handler directly:

```bash
curl -X POST http://localhost:8011/handle \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+15551234567",
    "account_id": "alice",
    "text": "What is my balance?",
    "verified": false
  }'
```

## Service Communication Examples

**Handler calls LLM for general query:**
```
POST http://localhost:8011/handle {"text": "hello"}
  └→ Handler → POST http://localhost:8003/answer {"question": "hello"}
```

**Handler calls WriteOps → Fraud → DB for transfer:**
```
POST http://localhost:8011/handle {"text": "transfer 50 to bob"}
  └→ Handler → POST http://localhost:8008/transfer
       └→ WriteOps → POST http://localhost:8005/consent (Fraud)
       └→ WriteOps → POST http://localhost:8006/write_transaction (DB)
```

## Run Unit Tests

Original unit tests still work with the service modules:

```bash
python3 -m unittest -v tests/test_flows.py
```

## Next Steps

- **Tests**: Create integration tests that hit the HTTP endpoints
- **Logging**: Add proper logging and monitoring (ELK stack, Prometheus)
- Containerize with Docker Compose for easier deployment
- Add API Gateway (Kong, Traefik) for routing and auth
- Implement service discovery (Consul, etcd)
- Replace in-memory stores with Redis/PostgreSQL
- Add message queue (RabbitMQ, Kafka) for async tasks
- Deploy to Kubernetes with auto-scaling
- Integrate real Azure Cognitive Services, Twilio, OpenAI
- Add authentication/authorization (OAuth2, JWT)
- Implement circuit breakers and retry logic
