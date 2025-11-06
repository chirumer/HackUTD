# Elder Voice Banking - Microservices Architecture

This repository demonstrates a voice-first banking assistant for elder users using HTTP-based microservices with FastAPI. Each service runs independently and communicates via REST APIs.

- Natural voice interaction (via phone call) with STT/TTS
- Clear orchestration and verification flows
- Fraud consent gates for sensitive write operations
- SMS links for photos, OTPs, QR codes
- Admin dashboard and optional live monitoring UI

## Architecture Overview

### Microservices

Each service runs on its own port and communicates via HTTP:

- Voice Service (port 8001): STT and TTS conversion (simulated Azure Voice)
- SMS Service (port 8002): Send/receive SMS, OTPs, media
- Call Service (port 8003): Manage phone calls, track call history
- LLM Service (port 8004): General Q&A with context
- RAG Service (port 8005): Product/offers queries from bank documents
- Fraud Detection (port 8006): Consent gate for writes, alerts
- Database Service (port 8007): In-memory transactions and balances
- Read Query Service (port 8008): NL→SQL reads with verification
- Write Operations (port 8009): Transfers with fraud consent
- Complaint Service (port 8010): Lodge complaints with photos
- QR Code Service (port 8011): Generate payment QR codes
- Handler Service (port 8012): Orchestrator — routes intents, manages sessions
- Dashboard Service (port 8013): Admin JSON overview aggregating service stats
- (Optional) Dashboard UI Service (port 8014): Dark-themed live monitoring UI

### Architecture Diagram (Figma)

For a detailed visual of services and flows, see the Figma architecture board.

- Open the live diagram:
  https://www.figma.com/board/eb9AkxlV0AuihIJ5voMwUR/Elder-Banking-Voice-Assistant-Architecture--Updated-?node-id=0-1&t=uNYaExQRqs5JjRdb-1

Embedding options for other docs:
- Inline link (recommended for GitHub READMEs):
  [Architecture diagram — Figma board](https://www.figma.com/board/eb9AkxlV0AuihIJ5voMwUR/Elder-Banking-Voice-Assistant-Architecture--Updated-?node-id=0-1&t=uNYaExQRqs5JjRdb-1)
- Export an image from Figma (File → Export) to docs/architecture.png and reference:
  ![Architecture diagram](docs/architecture.png)

### Communication Flow

```
User (Call/Voice) → Voice Service (STT) → Handler Service
         ↓                                   │
       Voice (TTS) ←──────── Response  ◄─────┘
                         │
                         ├─ General Q&A → LLM Service
                         ├─ Offers → RAG Service
                         ├─ Read (balance/txns) → ReadQuery → Database
                         ├─ Write (transfer) → WriteOps → Fraud → Database
                         ├─ Complaint → Complaint Service (+SMS link for photo)
                         └─ QR Code → QR Service (+SMS delivery)
```

The Handler is the orchestrator that:
- Classifies user intent (general, offers, read, write, complaint, QR)
- Routes to appropriate services via HTTP requests
- Manages verification flows (e.g., OTP via SMS)
- Coordinates fraud consent checks for writes/QRs
- Returns friendly responses and triggers SMS/call updates

## Project Layout

```
bankassist/
  services/            # Core business logic for each capability
  utils/               # Intent classification, logging, metrics (if present)
  config.py            # Service port configuration

services_http/         # FastAPI microservices (HTTP API layer)
  voice_service.py         # 8001
  sms_service.py           # 8002
  call_service.py          # 8003
  llm_service.py           # 8004
  rag_service.py           # 8005
  fraud_service.py         # 8006
  db_service.py            # 8007
  readquery_service.py     # 8008
  writeops_service.py      # 8009
  complaint_service.py     # 8010
  qr_service.py            # 8011
  handler_service.py       # 8012
  dashboard_service.py     # 8013
  dashboard_ui_service.py  # 8014 (optional, live monitoring UI)

start_services.py      # Boot all services and run health checks
demo_client.py         # End-to-end demo driver
requirements.txt       # Python dependencies
logs/                  # Service logs (auto-generated)
ARCHITECTURE.md        # Service diagrams & flows
API_EXAMPLES.md        # API testing examples
README.md              # This file
```

## Setup

Prerequisites:
- Python 3.9+ (macOS recommended)
- pip

Install dependencies:

```bash
pip3 install -r requirements.txt
```

If you use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

## Running the Application

### 1) Start all services

In one terminal, boot the microservices:

```bash
python3 start_services.py
```

This will:
- Start all services in background processes
- Run health checks
- Print endpoints and status
- Stream minimal logs (detailed logs go to logs/)

### 2) Run the demo

In another terminal:

```bash
python3 demo_client.py
```

This simulates a user conversation covering:
- General Q&A
- Offers (RAG)
- Balance read (with verification if needed)
- Transfer write (fraud consent gate)
- QR code issuance (sent via SMS)
- Complaint filing (with upload link via SMS)

### 3) Open dashboards

- JSON Admin Dashboard:
  http://localhost:8013/status

- Optional Live Monitoring UI (dark theme):
  http://localhost:8014
  - Live service status cards
  - Streaming logs
  - Time-range selectors
  - Graphs (e.g., DB calls, calls received, SMS sent)

### 4) Verify health, logs, metrics

- Health:
  ```bash
  curl -s http://localhost:8012/health | python3 -m json.tool
  ```

- Recent logs (per service):
  ```bash
  curl -s "http://localhost:8012/logs?limit=100" | python3 -m json.tool
  ```

- Metrics (past 60 minutes):
  ```bash
  curl -s "http://localhost:8013/metrics?time_period_minutes=60" | python3 -m json.tool
  ```

### 5) Stop services

Press Ctrl+C in the terminal running start_services.py.

## Expected Output (sample)

Service bootstrap (abbrev.):
```
[boot] starting 14 services...
[ok] voice (8001)
[ok] sms (8002)
[ok] call (8003)
[ok] llm (8004)
[ok] rag (8005)
[ok] fraud (8006)
[ok] database (8007)
[ok] readquery (8008)
[ok] writeops (8009)
[ok] complaint (8010)
[ok] qr (8011)
[ok] handler (8012)
[ok] dashboard (8013)
[ok] dashboard_ui (8014)
All services healthy.
```

Demo highlights:
```
User: Hello, can you help me?
Assistant: Hello! I'm your ElderCare Bank assistant. How can I help today?

User: What savings accounts do you offer?
Assistant: From docs [savings]: Savings accounts with 3.5% APY and no monthly fees.

User: What's my balance?
Assistant: For your security, we sent a verification code via SMS...

User: Transfer 50 to Bob
Assistant: Transferred $50.00 to Bob. Your new balance is $1450.00.

User: Create a QR code for 20
Assistant: A QR code for $20.00 was sent via SMS.

User: I'd like to file a complaint
Assistant: I just texted you a secure link. After you upload a photo, I’ll file your complaint.
```

## Monitoring and Observability

- Extensive structured logging to logs/ per service
- Per-service endpoints:
  - GET /health — basic health
  - GET /logs?limit=100 — recent logs
  - GET /metrics?time_period_minutes=60 — counters/timers for the selected window
- Dashboard Service aggregates system metrics at /status and /metrics
- Optional Dashboard UI streams logs and renders graphs with time-range controls

Common metrics (examples):
- voice.stt.count, voice.tts.count
- handler.requests.total, handler.intent.general/read/write/rag/complaint/qr
- db.read.count, db.write.count, db.transactions
- fraud.consent.checks, fraud.rejections, fraud.alerts
- sms.sent, sms.received
- call.active, call.started, call.ended

## Configuration

- Ports are defined in bankassist/config.py
- Update thresholds (e.g., fraud amount limits) in the corresponding service logic
- If you change ports, update start_services.py accordingly

## Troubleshooting

- Port already in use:
  - macOS: lsof -i :8001 and kill the PID
- PYTHONPATH issues:
  - Run from repo root or set: export PYTHONPATH="$PWD"
- Services don’t start:
  - Check logs/*.log for stack traces
- Dashboard UI blank:
  - Ensure dashboard_ui_service.py is running (port 8014)

## Security Notes (prototype)

- OTP and verification flows are simulated
- No real bank data; in-memory database only
- Fraud detection is heuristic, for demo purposes
- Replace dummy implementations with real providers (Azure Cognitive Services, Twilio, etc.) before production

## Links

- Figma architecture diagram:
  https://www.figma.com/board/eb9AkxlV0AuihIJ5voMwUR/Elder-Banking-Voice-Assistant-Architecture--Updated-?node-id=0-1&t=uNYaExQRqs5JjRdb-1
- API examples: see API_EXAMPLES.md
- Service internals: see bankassist/services and services_http/

## License

MIT (for demo purposes). Review and adapt before production use.