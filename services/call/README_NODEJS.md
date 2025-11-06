# Call Service (Node.js + Twilio)

Twilio-based call handling service that receives phone calls, performs live transcription, and forwards to the handler service.

## Features

- **Incoming Call Handling**: Receives calls via Twilio webhook
- **Live Transcription**: Connects to voice service for real-time speech-to-text
- **Partial Logging**: Logs partial transcriptions as they arrive
- **Sentence Detection**: Detects complete sentences and forwards to handler
- **Auto Call End**: Ends call after receiving a complete sentence
- **Public URL**: Automatically exposes webhook via LocalTunnel

## How It Works

1. **Call Received**: Twilio receives a call and sends webhook to `/voice-webhook`
2. **WebSocket Stream**: Twilio streams audio to `/media-stream` via WebSocket
3. **Audio Processing**: Convert mulaw → PCM16, resample 8kHz → 16kHz
4. **Forward to Handler**: Audio is forwarded to handler service via WebSocket
5. **Handler to Voice**: Handler forwards audio to voice service for transcription
6. **Transcription Logging**: Handler logs partial and final transcriptions
7. **Results to Call**: Handler sends transcription results back to call service
8. **Sentence Complete**: When a complete sentence is detected:
   - Forward to handler service for intent processing
   - End the call gracefully
9. **Cleanup**: Close connections and remove from active calls

## Setup

### 1. Install Dependencies

```bash
cd services/call
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and set your Twilio credentials:

```bash
PORT=8003
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_NUMBER=+1234567890
HANDLER_URL=http://localhost:8012
VOICE_URL=http://localhost:8001
```

### 3. Start the Service

```bash
npm start
```

The service will:
- Start HTTP server on port 8003
- Establish LocalTunnel for public access
- Print the public webhook URL

### 4. Configure Twilio

1. Go to [Twilio Console - Phone Numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
2. Select your Twilio number
3. Under "Voice Configuration":
   - **A CALL COMES IN**: Webhook
   - **URL**: `https://your-tunnel-url.loca.lt/voice-webhook` (from console output)
   - **HTTP**: POST
4. Save

## Testing

Call your Twilio number and:
1. You'll hear: "Welcome to Bank Assist. Please tell us how we can help you today."
2. Speak a sentence (e.g., "What is my account balance?")
3. Watch the console for:
   - Partial transcriptions
   - Final sentence
   - Handler forwarding
   - Call ending

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "call"
}
```

### GET /public-url
Get the current public URL for webhooks.

**Response:**
```json
{
  "url": "https://your-tunnel-url.loca.lt"
}
```

### GET /active
Get all active calls.

**Response:**
```json
[
  {
    "call_id": "CA123...",
    "phone": "+1234567890",
    "started_at": 1699300000,
    "transcript": "What is my balance",
    "partials_count": 5
  }
]
```

### GET /call/:callSid
Get specific call details.

**Response:**
```json
{
  "call_id": "CA123...",
  "phone": "+1234567890",
  "started_at": 1699300000,
  "transcript": "What is my balance",
  "partials": [
    {
      "timestamp": 1699300001000,
      "text": "What"
    },
    {
      "timestamp": 1699300002000,
      "text": "What is"
    }
  ]
}
```

## Architecture

```
┌─────────────┐
│   Twilio    │
│   (Phone)   │
└──────┬──────┘
       │ Call comes in
       ▼
┌─────────────────┐
│  /voice-webhook │ ◄── TwiML Response
│   (HTTP POST)   │
└────────┬────────┘
         │ Creates WebSocket stream
         ▼
┌──────────────────┐
│ /media-stream    │
│  (WebSocket)     │
└────────┬─────────┘
         │ Audio chunks
         ▼
┌──────────────────┐      ┌─────────────────┐
│  Voice Service   │◄────►│  Partial Text   │
│ (Transcription)  │      │  Final Sentence │
└──────────────────┘      └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ Handler Service │
                          │  (Intent Route) │
                          └─────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │   End Call      │
                          └─────────────────┘
```

## Log Examples

```
2025-11-06T10:30:00.000Z | call | INFO | [WEBHOOK] Incoming call from: +1234567890
2025-11-06T10:30:00.100Z | call | INFO | [WS] Twilio connected to /media-stream
2025-11-06T10:30:00.200Z | call | INFO | [WS] Connected to voice service
2025-11-06T10:30:01.000Z | call | INFO | [PARTIAL] "What"
2025-11-06T10:30:01.500Z | call | INFO | [PARTIAL] "What is"
2025-11-06T10:30:02.000Z | call | INFO | [PARTIAL] "What is my"
2025-11-06T10:30:02.500Z | call | INFO | [PARTIAL] "What is my balance"
2025-11-06T10:30:03.000Z | call | INFO | [FINAL SENTENCE] "What is my balance?"
2025-11-06T10:30:03.100Z | call | INFO | [HANDLER] Forwarding sentence to handler
2025-11-06T10:30:03.200Z | call | INFO | [HANDLER] Response received
2025-11-06T10:30:04.000Z | call | INFO | [CALL] Ending call gracefully
2025-11-06T10:30:04.100Z | call | INFO | [CALL] Call ended successfully
```

## Dependencies

- **express**: HTTP server framework
- **twilio**: Twilio SDK for TwiML and API
- **ws**: WebSocket library
- **axios**: HTTP client for calling other services
- **localtunnel**: Expose local server to public internet
- **dotenv**: Environment variable management
- **body-parser**: Parse incoming request bodies
- **cors**: Enable CORS for cross-origin requests

## Troubleshooting

### LocalTunnel Connection Issues

If LocalTunnel fails to connect:
1. Check your internet connection
2. Try again (sometimes it takes a few tries)
3. Use ngrok as an alternative:
   ```bash
   ngrok http 8003
   ```
   Then use the ngrok URL in Twilio settings

### Twilio Webhook Not Receiving Calls

1. Verify the webhook URL is correct in Twilio console
2. Check that the service is running and accessible
3. Test the public URL in a browser: `https://your-url.loca.lt/health`
4. Check Twilio logs: https://console.twilio.com/us1/monitor/logs/calls

### Voice Service Connection Issues

1. Ensure voice service is running on port 8001
2. Check that `/live-transcribe` endpoint exists
3. Verify WebSocket connection in logs

### Handler Service Not Responding

1. Ensure handler service is running on port 8012
2. Check that `/handle` endpoint is accessible
3. Verify request format matches handler expectations

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| PORT | HTTP server port | 8003 |
| TWILIO_ACCOUNT_SID | Twilio account SID | Required |
| TWILIO_AUTH_TOKEN | Twilio auth token | Required |
| TWILIO_NUMBER | Twilio phone number | Required |
| HANDLER_URL | Handler service URL | http://localhost:8012 |
| VOICE_URL | Voice service URL | http://localhost:8001 |
| SERVICE_NAME | Service name for logging | call |
| LOG_LEVEL | Logging level | INFO |
| LOCALTUNNEL_SUBDOMAIN | Custom subdomain (optional) | Random |

## Notes

- The call automatically ends after receiving one complete sentence (configurable)
- All calls are tracked in memory (use Redis for production)
- LocalTunnel URLs are temporary and change on restart
- For production, use a permanent public URL (ngrok, AWS, etc.)
