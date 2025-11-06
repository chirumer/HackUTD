"""Dashboard Service - HTTP API."""
from fastapi import FastAPI
import requests
from bankassist.config import get_service_url

app = FastAPI(title="Dashboard Service")


@app.get("/status")
def status():
    """Aggregate status from all services."""
    sms_url = get_service_url("sms")
    fraud_url = get_service_url("fraud")
    complaint_url = get_service_url("complaint")
    
    try:
        sms_stats = requests.get(f"{sms_url}/stats").json()
    except:
        sms_stats = {"error": "unavailable"}
    
    try:
        fraud_stats = requests.get(f"{fraud_url}/stats").json()
    except:
        fraud_stats = {"error": "unavailable"}
    
    try:
        complaint_resp = requests.get(f"{complaint_url}/recent", params={"limit": 5}).json()
        complaint_stats = {
            "count": len(complaint_resp),
            "latest_ids": [c["id"] for c in complaint_resp]
        }
    except:
        complaint_stats = {"error": "unavailable"}
    
    return {
        "sms": sms_stats,
        "fraud": fraud_stats,
        "complaints": complaint_stats,
        "db": {"note": "redacted for security"},
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["dashboard"])
