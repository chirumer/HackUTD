"""Voice Service - HTTP API for STT and TTS."""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import time
from bankassist.services.voice import AzureVoiceService, Audio
from bankassist.utils.logger import ServiceLogger
from bankassist.utils.metrics import MetricsCollector

app = FastAPI(title="Voice Service")
voice_svc = AzureVoiceService()

# Initialize logger and metrics
logger = ServiceLogger("voice")
metrics = MetricsCollector("voice")
logger.info("Voice service starting up")


class TranscribeRequest(BaseModel):
    audio_bytes: str  # base64 encoded
    format: str = "wav"


class SynthesizeRequest(BaseModel):
    text: str


class TranscribeResponse(BaseModel):
    transcript: str


class SynthesizeResponse(BaseModel):
    audio_bytes: str  # base64 encoded
    format: str


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(req: TranscribeRequest):
    start_time = time.time()
    logger.info(f"Transcribing audio ({req.format} format)")
    metrics.increment("transcriptions_total")
    
    import base64
    audio_content = base64.b64decode(req.audio_bytes)
    logger.debug(f"Decoded {len(audio_content)} bytes of audio")
    
    audio = Audio(content=audio_content, format=req.format)
    transcript = voice_svc.transcribe(audio)
    
    elapsed = time.time() - start_time
    metrics.timing("transcription_duration", elapsed)
    logger.info(f"Transcription complete: '{transcript[:50]}...' ({elapsed:.2f}s)", duration=elapsed)
    
    return TranscribeResponse(transcript=transcript)


@app.post("/synthesize", response_model=SynthesizeResponse)
def synthesize(req: SynthesizeRequest):
    start_time = time.time()
    logger.info(f"Synthesizing text: '{req.text[:50]}...'")
    metrics.increment("syntheses_total")
    
    import base64
    audio = voice_svc.synthesize(req.text)
    audio_b64 = base64.b64encode(audio.content).decode("ascii")
    
    elapsed = time.time() - start_time
    metrics.timing("synthesis_duration", elapsed)
    logger.info(f"Synthesis complete ({len(audio.content)} bytes, {elapsed:.2f}s)", duration=elapsed)
    
    return SynthesizeResponse(audio_bytes=audio_b64, format=audio.format)


@app.get("/health")
def health():
    return {"status": "ok", "service": "voice"}


@app.get("/logs")
def get_logs(limit: int = 100):
    """Get recent logs from this service."""
    return logger.get_recent_logs(limit=limit)


@app.get("/metrics")
def get_metrics(period: Optional[int] = None):
    """Get metrics from this service."""
    return metrics.get_all_metrics(time_period_minutes=period)


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["voice"])
