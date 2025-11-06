# API Examples - Testing Individual Services

## Handler Service (Main Entry Point)

**Handle a user query:**
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

**Expected response:**
```json
{
  "reply": "For your security, we sent you a verification code (OTP)...",
  "session_verified": true
}
```

## LLM Service

**Ask a general question:**
```bash
curl -X POST http://localhost:8003/answer \
  -H "Content-Type: application/json" \
  -d '{"question": "What are your hours?"}'
```

**Response:**
```json
{
  "answer": "ElderCare Bank is open 8-6 M-F."
}
```

## RAG Service

**Query product information:**
```bash
curl -X POST http://localhost:8004/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Do you have credit cards?"}'
```

**Response:**
```json
{
  "answer": "From docs [credit_cards]: We offer Platinum and Gold cards with rewards."
}
```

## SMS Service

**Send an SMS:**
```bash
curl -X POST http://localhost:8002/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+15551234567",
    "body": "Your OTP is 123456"
  }'
```

**Get SMS stats:**
```bash
curl http://localhost:8002/stats
```

**Response:**
```json
{
  "outbox_count": 3,
  "inbox_count": 1,
  "active_expectations": 0
}
```

## Fraud Detection Service

**Request consent for a transaction:**
```bash
curl -X POST http://localhost:8005/consent \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "alice",
    "amount": 500.0,
    "context": {}
  }'
```

**Response (approved):**
```json
{
  "consented": true,
  "reason": null
}
```

**Response (rejected - amount too high):**
```json
{
  "consented": false,
  "reason": "Amount 1500.00 exceeds threshold 1000.00"
}
```

**Get fraud alerts:**
```bash
curl http://localhost:8005/alerts?limit=5
```

**Get fraud stats:**
```bash
curl http://localhost:8005/stats
```

## Database Service

**Ensure account exists:**
```bash
curl -X POST http://localhost:8006/ensure_account \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "bob",
    "balance": 500.0
  }'
```

**Check balance:**
```bash
curl -X POST http://localhost:8006/balance \
  -H "Content-Type: application/json" \
  -d '{"account_id": "alice"}'
```

**Write a transaction:**
```bash
curl -X POST http://localhost:8006/write_transaction \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "alice",
    "counterparty": "bob",
    "amount": 50.0
  }'
```

**Read transactions:**
```bash
curl -X POST http://localhost:8006/read_transactions \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "alice",
    "limit": 10
  }'
```

## Read Query Service

**Query balance (requires verification):**
```bash
curl -X POST http://localhost:8007/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_text": "What is my balance?",
    "account_id": "alice",
    "verified": true
  }'
```

**Response:**
```json
{
  "type": "balance",
  "amount": 1450.0,
  "items": [],
  "message": ""
}
```

## Write Operations Service

**Transfer money:**
```bash
curl -X POST http://localhost:8008/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "from_acct": "alice",
    "to_acct": "bob",
    "amount": 50.0,
    "verified": true,
    "context": {}
  }'
```

**Response (success):**
```json
{
  "status": "ok",
  "transaction": {
    "id": 1,
    "account_id": "alice",
    "counterparty": "bob",
    "amount": 50.0,
    "type": "debit"
  }
}
```

**Response (fraud rejection):**
```json
{
  "status": "rejected",
  "reason": "Amount 1500.00 exceeds threshold 1000.00"
}
```

## Complaint Service

**Lodge a complaint:**
```bash
curl -X POST http://localhost:8009/lodge \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+15551234567",
    "text": "Wrong charge on my account",
    "image_url": "https://example.com/photo.jpg"
  }'
```

**Get recent complaints:**
```bash
curl http://localhost:8009/recent?limit=5
```

## QR Code Service

**Create a QR code:**
```bash
curl -X POST http://localhost:8010/create \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "alice",
    "amount": 25.0,
    "verified": true,
    "context": {}
  }'
```

**Response:**
```json
{
  "status": "ok",
  "qr_code": "eyJhY2NvdW50X2lkIjogImFsaWNlIiwgImFtb3VudCI6IDI1LjB9"
}
```

## Dashboard Service

**Get system status:**
```bash
curl http://localhost:8012/status | python3 -m json.tool
```

**Response:**
```json
{
  "sms": {
    "outbox_count": 3,
    "inbox_count": 1,
    "active_expectations": 0
  },
  "fraud": {
    "checks": 2,
    "rejections": 1,
    "alerts": 1,
    "threshold": 1000.0
  },
  "complaints": {
    "count": 1,
    "latest_ids": [1]
  },
  "db": {
    "note": "redacted for security"
  }
}
```

## Voice Service

**Transcribe audio:**
```bash
curl -X POST http://localhost:8001/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "audio_bytes": "SGVsbG8sIHdvcmxkIQ==",
    "format": "wav"
  }'
```

**Synthesize text to speech:**
```bash
curl -X POST http://localhost:8001/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, welcome to ElderCare Bank"}'
```

## Health Checks

**Check if all services are running:**
```bash
for port in 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011 8012; do
  echo "Port $port: $(curl -s http://localhost:$port/health)"
done
```

## Testing Workflows

**Complete transfer workflow:**
```bash
# 1. Start transfer (will check fraud)
curl -X POST http://localhost:8011/handle \
  -H "Content-Type: application/json" \
  -d '{"phone": "+15551234567", "account_id": "alice", "text": "transfer 50 to bob", "verified": true}'

# 2. Check fraud stats
curl http://localhost:8005/stats

# 3. Check database balance
curl -X POST http://localhost:8006/balance \
  -H "Content-Type: application/json" \
  -d '{"account_id": "alice"}'
```

**Fraud rejection workflow:**
```bash
# Try to transfer amount above threshold
curl -X POST http://localhost:8011/handle \
  -H "Content-Type: application/json" \
  -d '{"phone": "+15551234567", "account_id": "alice", "text": "transfer 1500 to bob", "verified": true}'

# Check alerts
curl http://localhost:8005/alerts
```
