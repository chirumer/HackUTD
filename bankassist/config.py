"""Service configuration with port assignments and URLs."""

SERVICE_PORTS = {
    "voice": 8001,
    "sms": 8002,
    "call": 8003,
    "llm": 8004,
    "rag": 8005,
    "fraud": 8006,
    "database": 8007,
    "readquery": 8008,
    "write_ops": 8009,
    "complaint": 8010,
    "qr": 8011,
    "handler": 8012,
    "dashboard_ui": 8014,
}

def get_service_url(service_name: str) -> str:
    """Get the full URL for a service."""
    port = SERVICE_PORTS.get(service_name)
    if not port:
        raise ValueError(f"Unknown service: {service_name}")
    return f"http://localhost:{port}"
