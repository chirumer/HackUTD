from dataclasses import dataclass
from typing import Any


@dataclass
class Audio:
    content: bytes
    format: str = "wav"


class AzureVoiceService:
    """Dummy Azure voice service that does STT and TTS.
    In this demo, STT just unwraps a text payload; TTS wraps text to Audio.
    """

    def transcribe(self, audio: Audio) -> str:
        # In real life: call Azure Speech to Text
        # Here we assume audio.content holds utf-8 text for simplicity
        try:
            return audio.content.decode("utf-8")
        except Exception:
            return ""

    def synthesize(self, text: str) -> Audio:
        # In real life: call Azure Text to Speech
        # Here we just wrap the text bytes
        return Audio(content=text.encode("utf-8"), format="wav")

    def place_call_and_listen(self, scripted_user_text: str) -> tuple[str, Audio]:
        """Simulate a call leg: get user's text and produce our spoken reply audio."""
        transcript = scripted_user_text
        tts_audio = self.synthesize("Thanks, we received: " + scripted_user_text)
        return transcript, tts_audio
