#!/usr/bin/env python3
"""Generate traffic to test monitoring dashboard."""
import requests
import time
import random

HANDLER_URL = "http://localhost:8012"

def test_monitoring():
    print("🔬 Generating traffic for monitoring dashboard...\n")
    
    # Test various intents
    test_cases = [
        "What's my balance?",
        "Show me my last 5 transactions",
        "What credit cards do you offer?",
        "Transfer $25 to merchant",
        "How do I file a complaint?",
        "Generate a QR code for $15",
        "What are your interest rates?",
        "Transfer $1500 to bob",  # Should trigger fraud detection
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] Testing: {text[:50]}...")
        
        try:
            resp = requests.post(f"{HANDLER_URL}/handle", json={
                "phone": "+1234567890",
                "account_id": "alice",
                "text": text,
                "verified": False
            }, timeout=5)
            
            if resp.status_code == 200:
                result = resp.json()
                print(f"  ✓ {result['reply'][:80]}...")
            else:
                print(f"  ✗ HTTP {resp.status_code}")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Random delay to make traffic more realistic
        time.sleep(random.uniform(0.5, 2.0))
    
    print("\n✅ Traffic generation complete!")
    print("📊 Check the dashboard at http://localhost:8014")
    print("   You should see:")
    print("   - Request counts increasing")
    print("   - Live logs streaming")
    print("   - Service health status")
    print("   - Metrics graphs updating")

if __name__ == "__main__":
    test_monitoring()
