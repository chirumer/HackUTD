# Voice Service

Speech-to-text (STT) and text-to-speech (TTS) conversion service.

## Purpose

Handles all voice interaction capabilities:
- **Transcribe**: Convert audio to text (STT)
- **Synthesize**: Convert text to audio (TTS)

Uses simulated Azure Voice API (replace with real implementation in production).

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Variables

- `PORT`: HTTP port for this service (default: 8001)
- `SERVICE_NAME`: Service identifier (default: voice)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Optional Variables (Production)

- `AZURE_SPEECH_KEY`: Azure Cognitive Services Speech API key
- `AZURE_SPEECH_REGION`: Azure region (e.g., eastus, westus)

## API Endpoints

### POST /transcribe
Convert audio to text.

**Request:**
```json
{
  "audio_bytes": "base64_encoded_audio",
  "format": "wav"
}
```

**Response:**
```json
{
  "transcript": "Hello, how can I help you?"
}
```

### POST /synthesize
Convert text to audio.

**Request:**
```json
{
  "text": "Your balance is $1500.00"
}
```

**Response:**
```json
{
  "audio_bytes": "base64_encoded_audio",
  "format": "wav"
}
```

### GET /health
Health check endpoint.

### GET /logs?limit=100
Get recent log entries.

### GET /metrics?period=60
Get metrics for the specified time period (minutes).

## Running Standalone

```bash
cd services/voice
python service.py
```

Or with environment variables:
```bash
PORT=8001 python service.py
```

## Metrics Tracked

- `transcriptions_total`: Number of STT operations
- `syntheses_total`: Number of TTS operations
- `transcription_duration`: Time to transcribe audio
- `synthesis_duration`: Time to synthesize speech

## Dependencies

- FastAPI
- Pydantic
- bankassist.services.voice (core voice logic)
- shared.utils (logger, metrics)
