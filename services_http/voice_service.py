"""Voice Service - HTTP API for STT and TTS."""
from fastapi import FastAPI
from pydantic import BaseModel
from bankassist.services.voice import AzureVoiceService, Audio

app = FastAPI(title="Voice Service")
voice_svc = AzureVoiceService()


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
    import base64
    audio_content = base64.b64decode(req.audio_bytes)
    audio = Audio(content=audio_content, format=req.format)
    transcript = voice_svc.transcribe(audio)
    return TranscribeResponse(transcript=transcript)


@app.post("/synthesize", response_model=SynthesizeResponse)
def synthesize(req: SynthesizeRequest):
    import base64
    audio = voice_svc.synthesize(req.text)
    audio_b64 = base64.b64encode(audio.content).decode("ascii")
    return SynthesizeResponse(audio_bytes=audio_b64, format=audio.format)


@app.get("/health")
def health():
    return {"status": "ok", "service": "voice"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["voice"])
