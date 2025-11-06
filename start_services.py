#!/usr/bin/env python3
"""Start all microservices in separate processes."""
import subprocess
import time
import sys
import os
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bankassist.config import SERVICE_PORTS

SERVICES = [
    "voice_service.py",
    "sms_service.py",
    "call_service.py",
    "llm_service.py",
    "rag_service.py",
    "fraud_service.py",
    "db_service.py",
    "readquery_service.py",
    "writeops_service.py",
    "complaint_service.py",
    "qr_service.py",
    "handler_service.py",
    "dashboard_service.py",
]

processes = []


def start_services():
    """Start all services in background."""
    services_dir = project_root / "services_http"
    
    # Set PYTHONPATH to include project root
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    print("🚀 Starting all services...")
    print("-" * 60)
    
    for service_file in SERVICES:
        service_path = services_dir / service_file
        service_name = service_file.replace("_service.py", "")
        port = SERVICE_PORTS.get(service_name)
        
        print(f"Starting {service_name:12} on port {port}...")
        
        # Start service in background
        # Create log files for each service
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        stdout_log = log_dir / f"{service_name}_stdout.log"
        stderr_log = log_dir / f"{service_name}_stderr.log"
        
        proc = subprocess.Popen(
            [sys.executable, str(service_path)],
            stdout=open(stdout_log, 'w'),
            stderr=open(stderr_log, 'w'),
            cwd=str(project_root),
            env=env  # Pass environment with PYTHONPATH
        )
        processes.append((service_name, port, proc))
        time.sleep(0.5)  # Small delay between starts
    
    print("-" * 60)
    print(f"✅ Started {len(processes)} services")
    print("\nService endpoints:")
    for name, port, _ in processes:
        print(f"  {name:12} → http://localhost:{port}")
    
    print("\n📊 Dashboard: http://localhost:8013/status")
    print("🎯 Handler:   http://localhost:8012/handle")
    print("\nPress Ctrl+C to stop all services")


def shutdown_services(signum=None, frame=None):
    """Stop all services gracefully."""
    print("\n\n🛑 Shutting down services...")
    for name, port, proc in processes:
        print(f"Stopping {name}...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("✅ All services stopped")
    sys.exit(0)


def check_health():
    """Check if services are responding."""
    import requests
    time.sleep(4)  # Wait longer for services to start
    
    print("\n🔍 Health check...")
    healthy = 0
    for name, port, proc in processes:
        try:
            resp = requests.get(f"http://localhost:{port}/health", timeout=2)
            if resp.status_code == 200:
                healthy += 1
                print(f"  ✓ {name}")
            else:
                print(f"  ✗ {name} (HTTP {resp.status_code})")
        except Exception as e:
            print(f"  ✗ {name} ({e})")
    
    print(f"\n{healthy}/{len(processes)} services healthy")
    return healthy == len(processes)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown_services)
    signal.signal(signal.SIGTERM, shutdown_services)
    
    try:
        start_services()
        
        if check_health():
            print("\n✅ All services are healthy and ready!")
        else:
            print("\n⚠️  Some services failed health check")
        
        # Keep running
        print("\nServices running... (Ctrl+C to stop)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_services()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        shutdown_services()
