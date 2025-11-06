"""Writeops Service Configuration."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Load .env file from service directory
    service_dir = Path(__file__).parent
    env_file = service_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # dotenv not installed, just use environment variables
    pass

# Service Configuration
PORT = int(os.getenv("PORT", "8009"))
SERVICE_NAME = os.getenv("SERVICE_NAME", "writeops")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Add service-specific config here as needed
