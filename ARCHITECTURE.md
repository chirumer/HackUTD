# Microservices Architecture - Service Communication Map

## Service Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER (Voice Call)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │  Handler Service │  Port 8011 (Orchestrator)
                   │   (Routing &     │
                   │   Session Mgmt)  │
                   └────────┬─────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │   LLM    │      │   RAG    │      │   SMS    │
  │ Service  │      │ Service  │      │ Service  │
  │  8003    │      │  8004    │      │  8002    │
  └──────────┘      └──────────┘      └──────────┘
       │                  │                  │
       │                  │                  │
       ▼                  ▼                  ▼
  (General Q&A)    (Product Info)    (OTP/Notifications)


         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │ReadQuery │      │WriteOps  │      │Complaint │
  │ Service  │      │ Service  │      │ Service  │
  │  8007    │      │  8008    │      │  8009    │
  └────┬─────┘      └────┬─────┘      └──────────┘
       │                 │
       │                 │
       ▼                 ▼
  ┌──────────┐      ┌──────────┐
  │    DB    │◄─────│  Fraud   │
  │ Service  │      │Detection │
  │  8006    │      │ Service  │
  └──────────┘      │  8005    │
                    └──────────┘
                         │
                         ▼
                   (Consent Gate
                    & Alerts)

         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │QR Code   │      │  Voice   │      │Dashboard │
  │ Service  │      │ Service  │      │ Service  │
  │  8010    │      │  8001    │      │  8012    │
  └────┬─────┘      └──────────┘      └────┬─────┘
       │                 │                  │
       │            (STT/TTS)               │
       ▼                                    ▼
  ┌──────────┐                       (Admin View
  │  Fraud   │                        All Stats)
  │Detection │
  │  (Reuse) │
  └──────────┘
```

## Request Flow Examples

### 1. General Query Flow
```
User → Handler → LLM Service → Handler → User
     [8011]     [8003]         [8011]
```

### 2. Balance Check (with verification)
```
User → Handler → ReadQuery → (403 Verification Required)
                    ↓
                Handler → SMS Service (send OTP)
                    ↓
                Handler marks verified
                    ↓
                Handler → ReadQuery → DB Service
                    ↓
                Handler → User (balance response)
```

### 3. Money Transfer (with fraud check)
```
User → Handler → WriteOps Service
                    ↓
                 Fraud Service (consent check)
                    ↓
                 DB Service (write transaction)
                    ↓
                Handler → User (confirmation/rejection)
```

### 4. QR Code Generation
```
User → Handler → QR Service
                    ↓
                 Fraud Service (consent check)
                    ↓
                 Handler → SMS Service (send QR)
                    ↓
                Handler → User (confirmation)
```

### 5. Admin Dashboard
```
Admin → Dashboard Service
           ↓
        SMS Service (stats)
        Fraud Service (stats)
        Complaint Service (recent)
           ↓
        Dashboard → Admin (aggregated view)
```

## Service Responsibilities

| Service | Port | Role | Dependencies |
|---------|------|------|--------------|
| Handler | 8011 | Orchestrator, intent routing, session mgmt | All services |
| Voice | 8001 | STT/TTS conversion | None |
| SMS | 8002 | Send/receive messages, OTP | None |
| LLM | 8003 | General Q&A | None |
| RAG | 8004 | Product/offers info | None |
| Fraud | 8005 | Consent gate, alerts | None |
| DB | 8006 | Transactions, balances | None |
| ReadQuery | 8007 | NL→SQL reads | DB |
| WriteOps | 8008 | Transfers, writes | Fraud, DB |
| Complaint | 8009 | Lodge complaints | None |
| QR Code | 8010 | Generate QR codes | Fraud |
| Dashboard | 8012 | Admin stats aggregator | SMS, Fraud, Complaint |

## Inter-Service Communication

All services communicate via **HTTP/REST APIs**:
- Standard JSON request/response
- Each service has `/health` endpoint
- Services are stateless (session in Handler only)
- No shared database (each has own state)

## Startup & Shutdown

**Start all services:**
```bash
python3 start_services.py
```

**Test system:**
```bash
python3 demo_client.py
```

**Stop all services:**
Press `Ctrl+C` in start_services.py terminal

## Scaling Considerations

- Each service can be scaled independently
- Handler can be load-balanced (with external session store like Redis)
- DB service should use real database (PostgreSQL, MongoDB)
- Fraud service can run as background job + API
- Services can be containerized (Docker) and orchestrated (Kubernetes)
