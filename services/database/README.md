# Database Service

In-memory database for accounts and transactions

## Purpose

Core data storage:
- **Account Management**: Create and manage customer accounts
- **Balance Tracking**: Store and retrieve account balances
- **Transactions**: Record transaction history
- **ACID Operations**: Ensure data consistency

Uses in-memory storage (replace with Redis/PostgreSQL in production).

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8007)
- `SERVICE_NAME`: Service identifier (default: database)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `DB_TYPE`: Database type (memory, redis, postgres)
- `REDIS_URL`: Redis connection string

## API Endpoints

### POST /ensure_account
Create/verify account

**Request:**
```json
{"account_id": "alice", "balance": 1500.0}
```

**Response:**
```json
{"status": "ok"}
```

### POST /balance
Get account balance

**Request:**
```json
{"account_id": "alice"}
```

**Response:**
```json
{"account_id": "alice", "balance": 1500.0}
```

### POST /write_transaction
Record transaction

**Request:**
```json
{"account_id": "alice", "counterparty": "bob", "amount": 50}
```

**Response:**
```json
{"id": 1, "type": "debit", ...}
```

### POST /read_transactions
Get transaction history

**Request:**
```json
{"account_id": "alice", "limit": 10}
```

**Response:**
```json
[{"id": 1, ...}]
```


### GET /health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "database"}
```

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/database
python service.py
```

Or with environment variables:
```bash
PORT=8007 python service.py
```

## Metrics Tracked

- `accounts_created`: Accounts Created
- `balance_reads`: Balance Reads
- `transactions_written`: Transactions Written

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

ReadQuery, WriteOps (for data storage)

## Development

For development with simulated APIs, no environment configuration needed. For production:

Replace in-memory storage with Redis or PostgreSQL. Update `.env` with connection details.
