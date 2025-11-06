# Dashboard Integration - Call Service Logging & Metrics

## ✅ Implementation Complete

All call service logging and metrics are now available in the live dashboard UI at **http://localhost:8014**

---

## 🎯 Features Implemented

### 1. **Call Service Metrics Endpoint** (`/metrics`)
Returns comprehensive real-time call statistics:

```json
{
  "totalCalls": 5,
  "answeredCalls": 5,
  "completedCalls": 4,
  "userHangups": 1,
  "systemHangups": 3,
  "activeCalls": 0,
  "totalDuration": "45.32s",
  "averageDuration": "11.33s",
  "transcriptionSuccess": 4,
  "transcriptionFailed": 1,
  "successRate": "80.0%"
}
```

**Access:** `http://localhost:8003/metrics`

---

### 2. **Call Service Logs Endpoint** (`/logs`)
Returns recent call activity logs (last 200 logs):

```json
[
  {
    "timestamp": "2025-11-06T10:30:45.123Z",
    "service": "call",
    "level": "INFO",
    "message": "📞 [CALL RECEIVED] Incoming call from: +1234567890",
    "phone": "+1234567890",
    "callSid": "CA1234567890abcdef",
    "totalCalls": 5
  },
  {
    "timestamp": "2025-11-06T10:30:46.456Z",
    "service": "call",
    "level": "INFO",
    "message": "✅ [CALL ANSWERED] Call CA1234567890abcdef answered and greeting played",
    "callSid": "CA1234567890abcdef",
    "phone": "+1234567890"
  }
]
```

**Access:** `http://localhost:8003/logs?limit=100`

---

### 3. **Live Dashboard UI Integration**

#### **Call Metrics Panel**
Displays real-time metrics with auto-refresh every 2 seconds:

- **Total Calls**: Total calls received
- **Answered**: Calls that were answered
- **Completed**: Successfully completed calls
- **Active Now**: Currently active calls
- **User Hangups**: Caller disconnected
- **System Hangups**: Application ended call
- **Avg Duration**: Average call length
- **Success Rate**: Transcription success percentage

#### **Active Calls List**
Shows live information for ongoing calls:
- Caller phone number
- Start time
- Duration (updating)
- Partial/complete transcripts

#### **Live Logs Stream**
Real-time log display with:
- Color-coded by level (INFO, WARNING, ERROR)
- Service name
- Timestamp
- Full message and context
- Auto-scroll to latest

---

## 📊 Call Lifecycle Logging

### Events Tracked:

1. **📞 CALL RECEIVED**
   - Triggered when call comes in
   - Logs: phone number, call SID, total calls count
   
2. **✅ CALL ANSWERED**
   - Triggered when call is answered
   - Logs: call SID, phone number
   
3. **🔴 CALL ENDING**
   - Triggered when call end initiated
   - Logs: call SID, reason (user/system), duration, transcript
   
4. **✅ CALL ENDED**
   - Triggered when call successfully terminates
   - Logs: status, reason, duration, metrics snapshot

5. **Partial Transcriptions**
   - Real-time speech-to-text updates
   - Logs each partial result

6. **Final Transcriptions**
   - Complete sentence detected
   - Forwarded to handler service

---

## 🔧 Technical Implementation

### Call Service (`service.js`)

#### Log Storage
```javascript
const logBuffer = [];
const MAX_LOGS = 200;

function log(level, message, extra = {}) {
  const timestamp = new Date().toISOString();
  const logEntry = { timestamp, service: SERVICE_NAME, level, message, ...extra };
  
  logBuffer.push(logEntry);
  if (logBuffer.length > MAX_LOGS) {
    logBuffer.shift();
  }
  
  console.log(`${timestamp} | ${SERVICE_NAME} | ${level} | ${message}`, extra);
}
```

#### Metrics Tracking
```javascript
const callMetrics = {
  totalCalls: 0,
  answeredCalls: 0,
  completedCalls: 0,
  userHangups: 0,
  systemHangups: 0,
  totalDuration: 0,
  averageDuration: 0,
  transcriptionSuccess: 0,
  transcriptionFailed: 0
};
```

#### Enhanced Call Ending
```javascript
async function endCallGracefully(callSid, transcript, reason = 'system') {
  // Calculate duration
  const duration = call ? (Date.now() - call.startedAt) / 1000 : 0;
  
  // Update metrics
  updateMetrics('completedCalls');
  if (reason === 'user') {
    updateMetrics('userHangups');
  } else {
    updateMetrics('systemHangups');
  }
  
  // Track duration
  callMetrics.totalDuration += duration;
  calculateAverageDuration();
  
  // Track transcription success
  if (transcript && transcript.length > 0) {
    updateMetrics('transcriptionSuccess');
  } else {
    updateMetrics('transcriptionFailed');
  }
  
  // Log with metrics
  log('INFO', '✅ [CALL ENDED] Call completed successfully', {
    callSid, status, reason,
    duration: `${duration.toFixed(2)}s`,
    metrics: { total, completed, avgDuration }
  });
}
```

---

### Dashboard UI Service (`service.py`)

#### Data Collection
```python
async def collect_all_metrics():
    """Collect metrics from all services."""
    data = {
        "timestamp": asyncio.get_event_loop().time(),
        "services": {},
        "logs": [],
        "call_metrics": {}
    }
    
    # Fetch call service metrics
    metrics_resp = requests.get(f"http://localhost:8003/metrics", timeout=1)
    data["call_metrics"] = metrics_resp.json()
    
    # Fetch active calls
    active_resp = requests.get(f"http://localhost:8003/active", timeout=1)
    data["call_metrics"]["active_calls_list"] = active_resp.json()
    
    # Fetch logs
    logs_resp = requests.get(f"http://localhost:8003/logs", timeout=1)
    data["logs"].extend(logs_resp.json())
    
    return data
```

#### WebSocket Streaming
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live dashboard updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            await asyncio.sleep(2)  # Update every 2 seconds
            update_data = await collect_all_metrics()
            await websocket.send_json(update_data)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
```

---

## 🚀 Usage

### 1. Start All Services
```bash
cd /Users/chiru/Desktop/HackUTD
python3 start_services.py
```

### 2. Access Dashboard
Open browser: **http://localhost:8014**

### 3. Make Test Call
Call your Twilio number: **+18559581055**

### 4. Monitor in Real-Time
- Watch metrics update live
- See call appear in "Active Calls"
- View transcription in real-time
- Track call completion and metrics

---

## 📈 Dashboard Sections

### Service Status
- ✅ All 14 microservices health status
- Port numbers
- Online/offline indicators
- Auto-refresh

### Call Service Metrics (NEW)
- 8 real-time metric boxes
- Active calls list with live updates
- Caller info, duration, transcripts
- Auto-updating every 2 seconds

### System Metrics
- Healthy services count
- Total requests across all services
- Active calls
- SMS sent

### Live Logs (ENHANCED)
- Real-time log streaming from all services
- Call service logs with emoji indicators
- Color-coded by severity
- Last 100 logs displayed
- Auto-scroll

### Time-Series Graphs
- Historical metrics visualization
- Multiple time ranges
- Multiple metric types

### Voice & LLM Testing
- Speech-to-text testing
- Text-to-speech synthesis
- LLM chat interface

---

## 🎨 Log Format Examples

### Call Received
```
2025-11-06T10:30:45.123Z | call | INFO | 📞 [CALL RECEIVED] Incoming call from: +1234567890
{ phone: '+1234567890', callSid: 'CA123...', totalCalls: 5 }
```

### Call Answered
```
2025-11-06T10:30:46.456Z | call | INFO | ✅ [CALL ANSWERED] Call CA123... answered and greeting played
{ callSid: 'CA123...', phone: '+1234567890' }
```

### Partial Transcription
```
2025-11-06T10:30:50.789Z | call | INFO | [PARTIAL] "Please help me"
{ callSid: 'CA123...', phone: '+1234567890' }
```

### Final Sentence
```
2025-11-06T10:30:52.012Z | call | INFO | [FINAL SENTENCE] "Please help me make some payments."
{ callSid: 'CA123...', phone: '+1234567890' }
```

### Call Ending
```
2025-11-06T10:30:53.345Z | call | INFO | 🔴 [CALL ENDING] Initiating call end
{ callSid: 'CA123...', transcript: 'Please help me make some payments.', reason: 'system', duration: '7.22s' }
```

### Call Ended
```
2025-11-06T10:30:54.678Z | call | INFO | ✅ [CALL ENDED] Call completed successfully
{ 
  callSid: 'CA123...', 
  status: 'completed', 
  reason: 'system', 
  duration: '8.55s',
  transcriptLength: 36,
  metrics: { total: 5, completed: 4, avgDuration: '10.23s' }
}
```

---

## 🔍 API Endpoints

### Call Service

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Call statistics |
| `/logs` | GET | Recent logs (limit=N) |
| `/active` | GET | Active calls list |
| `/call/:callSid` | GET | Specific call info |
| `/voice-webhook` | POST | Twilio webhook |
| `/media-stream` | WS | Audio streaming |
| `/public-url` | GET | Get tunnel URL |

### Dashboard UI

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/ws` | WS | Live updates stream |
| `/health` | GET | Health check |
| `/api/metrics/:service` | GET | Service metrics |
| `/api/voice/transcribe` | POST | Voice proxy |
| `/api/voice/synthesize` | POST | TTS proxy |
| `/api/llm/answer` | POST | LLM proxy |

---

## ✅ Verification Checklist

- [x] Call metrics endpoint working (`/metrics`)
- [x] Logs endpoint working (`/logs`)
- [x] Active calls endpoint working (`/active`)
- [x] Dashboard UI fetches call metrics
- [x] Dashboard UI displays call metrics in real-time
- [x] Dashboard UI shows active calls
- [x] Dashboard UI streams logs
- [x] WebSocket auto-refresh (2s interval)
- [x] Call lifecycle logging complete
- [x] Metrics tracking user vs system hangups
- [x] Average duration calculation
- [x] Transcription success rate tracking
- [x] Enhanced logging with emojis
- [x] All services start with one command
- [x] Automatic Twilio webhook update

---

## 📝 Notes

- **Log Buffer Size**: 200 logs (configurable via `MAX_LOGS`)
- **Dashboard Refresh**: 2 seconds (configurable in WebSocket)
- **Metrics Retention**: In-memory (resets on restart)
- **Log Format**: Structured JSON with metadata
- **Timezone**: All timestamps in ISO 8601 UTC

---

## 🎯 Next Steps (Optional Enhancements)

1. **Persistent Storage**: Save metrics/logs to database
2. **Alert System**: Notifications for errors/anomalies
3. **Export Functions**: Download logs/metrics as CSV/JSON
4. **Advanced Filtering**: Filter logs by level, time range, search
5. **Call Recording**: Store audio for playback
6. **Analytics**: Charts for call patterns, peak times
7. **User Authentication**: Secure dashboard access

---

**Status**: ✅ **FULLY OPERATIONAL**

**Last Updated**: November 6, 2025

**Services**: 14/14 Running

**Dashboard**: http://localhost:8014
