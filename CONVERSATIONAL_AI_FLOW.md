# Conversational AI Call Flow

## Overview
The system implements a real-time, bidirectional voice AI assistant that can have natural conversations with callers. The handler service orchestrates transcription, LLM processing, and text-to-speech responses while maintaining continuous audio streaming.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Caller    │────▶│ Call Service │────▶│ Handler Service │────▶│Voice Service │
│  (Phone)    │◀────│   (Twilio)   │◀────│  (Orchestrator) │◀────│  (Azure STT) │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
                            │                      │
                            │                      ▼
                            │              ┌──────────────┐
                            │              │ LLM Service  │
                            │              │  (AI Brain)  │
                            │              └──────────────┘
                            │                      │
                            │                      ▼
                            │              ┌──────────────┐
                            └─────────────▶│Voice Service │
                                           │  (Azure TTS) │
                                           └──────────────┘
```

---

## Detailed Flow

### 1. **Call Initialization**
```
User calls → Twilio → Call Service /voice-webhook
```
- Call service answers the call
- Creates WebSocket connection to Twilio Media Streams
- Connects to Handler Service via WebSocket (`/call/stream`)
- Sends start message with `call_sid` and `phone`

### 2. **Welcome Message**
```
Handler → Voice Service (TTS) → Handler → Call Service → Twilio → User
```
- Handler sends: "Hello! I'm your AI banking assistant. How can I help you today?"
- Voice service generates WAV audio
- Handler sends `play_audio` message to call service
- Call service plays audio to caller via Twilio

### 3. **User Speaks (Continuous Loop)**
```
User speaks → Twilio → Call Service → Handler → Voice Service (STT)
```

**Partial Transcription (Real-time):**
- Voice service sends `{type: 'partial', text: '...'}` every ~100ms
- Handler logs: `[PARTIAL] "Hello I need"`
- Forwarded to call service for display/logging
- **Transcription continues during LLM processing**

**Final Transcription (Complete sentence):**
- Voice service detects sentence completion
- Sends `{type: 'final', text: 'Hello I need help with my account'}`
- Handler logs: `[FINAL SENTENCE] "Hello I need help with my account"`

### 4. **LLM Processing (Asynchronous)**
```
Handler → LLM Service (async task while transcription continues)
```
- Handler creates async task: `process_with_llm(user_text)`
- Logs: `Processing with LLM: "Hello I need help with my account"`
- LLM service processes the question
- **Audio stream continues - user can still speak**

### 5. **AI Response Generation**
```
LLM → Handler → Voice Service (TTS) → Handler → Call Service → User
```
- LLM returns answer: "I'd be happy to help with your account. What specifically do you need?"
- Handler logs: `[ASSISTANT RESPONSE] "I'd be happy to help..."`
- Handler calls Voice Service `/synthesize` endpoint
- Receives base64 WAV audio
- Sends `{type: 'play_audio', audio: '...', format: 'wav'}` to call service
- Call service plays audio to user

### 6. **Conversation Continues**
- Loop back to step 3
- User can speak again (even while assistant is still responding)
- System handles overlapping speech gracefully

### 7. **Natural Call Ending**
```
User: "Thank you, goodbye"
```
- Transcription: `[FINAL SENTENCE] "Thank you goodbye"`
- Handler detects end phrase (`goodbye`, `bye`, `that's all`, etc.)
- Handler logs: "User requested call end"
- Handler responds: "Thank you for calling. Goodbye!"
- Waits 3 seconds for TTS to play
- Sends `{type: 'end_call', reason: 'user_completed'}` to call service
- Call service ends call gracefully

---

## Message Protocol

### Call Service → Handler

**Start Stream:**
```json
{
  "type": "start",
  "call_sid": "CA1234567890abcdef",
  "phone": "+1234567890"
}
```

**Audio Data:**
```
Binary PCM16 audio @ 16kHz (raw bytes)
```

**Stop Stream:**
```json
{
  "type": "stop"
}
```

### Handler → Call Service

**Partial Transcription:**
```json
{
  "type": "partial",
  "text": "Hello I need help"
}
```

**Final Transcription:**
```json
{
  "type": "final",
  "text": "Hello I need help with my account"
}
```

**Play TTS Audio:**
```json
{
  "type": "play_audio",
  "audio": "base64_encoded_wav_data...",
  "format": "wav"
}
```

**Request Call End:**
```json
{
  "type": "end_call",
  "reason": "user_completed"
}
```

### Handler → Voice Service (STT)

**Audio Stream:**
```
Binary PCM16 audio @ 16kHz
```

**Stop:**
```json
{
  "type": "stop"
}
```

### Voice Service → Handler

**Started:**
```json
{
  "type": "started",
  "session_id": "..."
}
```

**Partial:**
```json
{
  "type": "partial",
  "text": "Hello I need"
}
```

**Final:**
```json
{
  "type": "final",
  "text": "Hello I need help with my account"
}
```

**Error:**
```json
{
  "type": "error",
  "error": "Transcription failed"
}
```

### Handler → LLM Service

**Request:**
```json
{
  "question": "Hello I need help with my account"
}
```

**Response:**
```json
{
  "answer": "I'd be happy to help with your account. What specifically do you need?",
  "confidence": 0.95
}
```

### Handler → Voice Service (TTS)

**Request:**
```json
{
  "text": "I'd be happy to help with your account."
}
```

**Response:**
```json
{
  "audio_bytes": "base64_encoded_wav...",
  "duration": 3.5,
  "sample_rate": 16000
}
```

---

## Key Features

### ✅ **Continuous Transcription**
- Transcription never stops during conversation
- Partial results show real-time understanding
- User can interrupt or continue speaking

### ✅ **Asynchronous Processing**
- LLM processing doesn't block audio stream
- Multiple questions can be queued
- Responses play in order received

### ✅ **Natural Conversation**
- Detects end-of-sentence automatically
- No "press button to speak" required
- Handles conversational flow naturally

### ✅ **Intelligent Call Ending**
- Detects goodbye phrases
- Confirms end before hanging up
- Allows user to gracefully exit

### ✅ **Error Handling**
- TTS failures send apologetic message
- Transcription errors logged and reported
- Connection drops handled gracefully

---

## Handler Service Implementation

### WebSocket Endpoint: `/call/stream`

**Concurrent Tasks:**
1. `forward_from_call_to_voice()` - Forwards audio to voice service
2. `forward_from_voice_to_call()` - Processes transcriptions, calls LLM, sends TTS

**Key Functions:**

#### `send_tts_to_caller(text)`
- Generates TTS from text
- Encodes as base64
- Sends to call service for playback
- Logs assistant response
- Tracks metrics

#### `process_with_llm(user_text)`
- Async task (doesn't block)
- Calls LLM service with user question
- Gets AI answer
- Calls `send_tts_to_caller()` with answer
- Handles errors gracefully

#### End Phrase Detection
```python
end_phrases = ['goodbye', 'bye', 'thank you goodbye', 'that\'s all', 'hang up', 'end call']
if any(phrase in user_text.lower() for phrase in end_phrases):
    # End conversation
```

---

## Call Service Implementation

### Message Handling

**`play_audio` Message:**
```javascript
if (message.type === 'play_audio') {
  // Receive base64 WAV audio from handler
  // Convert to appropriate format for Twilio
  // Play to caller via media stream
  // Track in call record
}
```

**`end_call` Message:**
```javascript
if (message.type === 'end_call') {
  // Handler requests call termination
  // End gracefully after 500ms
  endCallGracefully(callSid, fullTranscript, 'system');
}
```

---

## Metrics Tracked

### Handler Service
- `transcriptions_completed` - Final sentences processed
- `llm_queries` - Questions sent to LLM
- `tts_responses_sent` - Audio responses generated
- `calls_ended` - Calls terminated

### Call Service
- `totalCalls` - Total calls received
- `answeredCalls` - Calls answered
- `completedCalls` - Calls ended successfully
- `systemHangups` - App-initiated ends
- `userHangups` - User-initiated ends
- `transcriptionSuccess` - Calls with transcripts
- `averageDuration` - Average call length

---

## Example Conversation

```
[SYSTEM] Call received from +1234567890
[SYSTEM] Call answered, connecting to handler
[ASSISTANT] "Hello! I'm your AI banking assistant. How can I help you today?"

[PARTIAL] "I need"
[PARTIAL] "I need to check"
[PARTIAL] "I need to check my balance"
[FINAL SENTENCE] "I need to check my balance"
[SYSTEM] Processing with LLM: "I need to check my balance"
[ASSISTANT RESPONSE] "I'd be happy to help you check your balance. Let me look that up for you."

[PARTIAL] "Thank"
[PARTIAL] "Thank you"
[FINAL SENTENCE] "Thank you that's all"
[SYSTEM] User requested call end
[ASSISTANT RESPONSE] "Thank you for calling. Goodbye!"
[SYSTEM] Call ended - reason: user_completed, duration: 34.5s
```

---

## Production Considerations

### Audio Streaming
Currently, TTS audio playback is simplified. For production:
1. Convert WAV to mulaw @ 8kHz for Twilio
2. Stream audio chunks in real-time
3. Handle audio buffering and timing
4. Implement proper audio mixing if needed

### Concurrency
- Multiple calls handled simultaneously
- Each call has isolated WebSocket connection
- Async LLM processing per call
- No blocking between conversations

### Latency Optimization
- Stream TTS audio as it generates (chunked)
- Pre-cache common responses
- Use streaming LLM APIs
- Optimize audio format conversions

### Error Recovery
- Reconnect on WebSocket drops
- Retry failed LLM calls
- Fallback responses for errors
- Graceful degradation

---

## Testing

### Manual Testing
1. Start all services: `python3 start_services.py`
2. Call your Twilio number
3. Speak naturally to the AI
4. Verify responses are relevant
5. Say "goodbye" to end call

### Automated Testing
1. Test WebSocket connections
2. Mock LLM responses
3. Verify audio format conversions
4. Test end phrase detection
5. Measure response latency

---

## Future Enhancements

### Voice Activity Detection
- Detect when user stops speaking
- Reduce latency before LLM processing
- Better turn-taking

### Context Awareness
- Maintain conversation history
- Reference previous statements
- Multi-turn dialogues

### Intent Classification
- Route to specialized handlers
- Trigger specific actions (transfers, balance checks)
- Direct integration with banking services

### Sentiment Analysis
- Detect frustration or confusion
- Escalate to human agent
- Adjust response tone

### Multi-Language Support
- Detect caller language
- Use appropriate TTS voice
- Translate conversations

---

**Status**: ✅ **Fully Implemented**

**Last Updated**: November 6, 2025

**Architecture**: Call Service → Handler Service (Orchestrator) → Voice Service (STT/TTS) + LLM Service
