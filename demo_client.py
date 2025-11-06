#!/usr/bin/env python3
"""Demo client that calls the Handler service HTTP API."""
import requests
import time
from bankassist.config import get_service_url

HANDLER_URL = get_service_url("handler")
DASHBOARD_URL = get_service_url("dashboard")
SMS_URL = get_service_url("sms")
CALL_URL = get_service_url("call")


def demo_conversation():
    """Simulate a conversation through the Handler service."""
    
    # User info
    phone = "+15551234567"
    account_id = "alice"
    
    print("\n" + "=" * 70)
    print("🎤 VOICE BANKING DEMO - HTTP Microservices Architecture")
    print("=" * 70)
    print(f"\nCaller: {phone}")
    print(f"Account: {account_id}\n")
    
    # Initiate call
    print("📞 Initiating call...")
    try:
        call_resp = requests.post(f"{HANDLER_URL}/call/receive", params={"phone": phone}, timeout=2)
        call_resp.raise_for_status()
        call_data = call_resp.json()
        call_id = call_data["call_id"]
        print(f"✓ Call connected (ID: {call_id})\n")
    except:
        print("⚠️  Could not initiate call tracking (continuing anyway)\n")
        call_id = None
    
    conversations = [
        "Hello, can you help me?",
        "What savings account do you offer?",
        "What's my balance?",
        "Transfer 1200 to bob",
        "Create a QR code for 20",
        "I want to file a complaint about a wrong charge",
        "Show my last transactions",
    ]
    
    print("=" * 70)
    print("🎤 VOICE BANKING DEMO - HTTP Microservices Architecture")
    print("=" * 70)
    print(f"\nCaller: {phone}")
    print(f"Account: {account_id}\n")
    
    for utterance in conversations:
        print(f"\n{'User:':<12} {utterance}")
        
        try:
            # Call Handler service
            resp = requests.post(f"{HANDLER_URL}/handle", json={
                "phone": phone,
                "account_id": account_id,
                "text": utterance,
                "verified": False
            }, timeout=5)
            
            resp.raise_for_status()
            result = resp.json()
            
            print(f"{'Assistant:':<12} {result['reply']}")
            
            time.sleep(0.5)  # Small delay between requests
            
        except requests.exceptions.RequestException as e:
            print(f"{'Error:':<12} Failed to reach handler service: {e}")
            print("\n⚠️  Make sure all services are running: python3 start_services.py")
            return
    
    # End call
    if call_id:
        print("\n📞 Ending call...")
        try:
            full_transcript = " | ".join(conversations)
            requests.post(f"{HANDLER_URL}/call/end", params={"call_id": call_id, "transcript": full_transcript}, timeout=2)
            print(f"✓ Call ended (ID: {call_id})")
        except:
            pass
    
    # Show SMS outbox
    print("\n" + "=" * 70)
    print("📱 SMS OUTBOX")
    print("=" * 70)
    try:
        sms_stats = requests.get(f"{SMS_URL}/stats", timeout=2).json()
        print(f"Total messages sent: {sms_stats.get('outbox_count', 0)}")
    except:
        print("Could not fetch SMS stats")
    
    # Show dashboard
    print("\n" + "=" * 70)
    print("📊 SYSTEM DASHBOARD")
    print("=" * 70)
    try:
        dashboard = requests.get(f"{DASHBOARD_URL}/status", timeout=2).json()
        
        print("\nSMS Service:")
        sms = dashboard.get("sms", {})
        print(f"  Outbox: {sms.get('outbox_count', 0)} messages")
        print(f"  Inbox:  {sms.get('inbox_count', 0)} messages")
        
        print("\nCall Service:")
        call = dashboard.get("call", {})
        print(f"  Active calls:   {call.get('active_calls', 0)}")
        print(f"  Total calls:    {call.get('total_calls', 0)}")
        print(f"  Avg duration:   {call.get('avg_duration_seconds', 0)}s")
        
        print("\nFraud Detection:")
        fraud = dashboard.get("fraud", {})
        print(f"  Checks:     {fraud.get('checks', 0)}")
        print(f"  Rejections: {fraud.get('rejections', 0)}")
        print(f"  Alerts:     {fraud.get('alerts', 0)}")
        print(f"  Threshold:  ${fraud.get('threshold', 0):.2f}")
        
        print("\nComplaints:")
        complaints = dashboard.get("complaints", {})
        print(f"  Total: {complaints.get('count', 0)}")
        if complaints.get('latest_ids'):
            print(f"  Latest IDs: {complaints.get('latest_ids', [])}")
        
    except requests.exceptions.RequestException:
        print("Could not fetch dashboard stats")
    
    print("\n" + "=" * 70)
    print("✅ Demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    print("\nWaiting for services to be ready...")
    time.sleep(1)
    
    # Quick health check
    try:
        resp = requests.get(f"{HANDLER_URL}/health", timeout=2)
        if resp.status_code == 200:
            print("✓ Handler service is ready\n")
        else:
            print(f"⚠️  Handler service returned {resp.status_code}")
    except requests.exceptions.RequestException:
        print("\n❌ Handler service is not responding!")
        print("Please start services first: python3 start_services.py\n")
        exit(1)
    
    demo_conversation()
