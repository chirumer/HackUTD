"""Voice Service Configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from service directory
service_dir = Path(__file__).parent
env_file = service_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Service Configuration
PORT = int(os.getenv("PORT", "8001"))
SERVICE_NAME = os.getenv("SERVICE_NAME", "voice")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Azure Voice API Configuration (optional, for production)
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")
