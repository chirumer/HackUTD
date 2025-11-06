"""Service configuration with port assignments and URLs."""

SERVICE_PORTS = {
    "voice": 8001,
    "sms": 8002,
    "llm": 8003,
    "rag": 8004,
    "fraud": 8005,
    "db": 8006,
    "readquery": 8007,
    "writeops": 8008,
    "complaint": 8009,
    "qr": 8010,
    "handler": 8011,
    "dashboard": 8012,
}

def get_service_url(service_name: str) -> str:
    """Get the full URL for a service."""
    port = SERVICE_PORTS.get(service_name)
    if not port:
        raise ValueError(f"Unknown service: {service_name}")
    return f"http://localhost:{port}"
