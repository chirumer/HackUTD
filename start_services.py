#!/usr/bin/env python3
"""Start all microservices in separate processes."""
import subprocess
import time
import sys
import os
import signal
import requests
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.config import SERVICE_PORTS

# List of all services in the new services/ directory
SERVICES = [
    "voice",
    "sms",
    "call",
    "llm",
    "rag",
    "fraud",
    "database",
    "readquery",
    "writeops",
    "complaint",
    "qr",
    "handler",
    "dashboard_ui",
]

processes = []


def start_services():
    """Start all services in background."""
    services_base_dir = project_root / "services"
    
    # Set PYTHONPATH to include project root
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    print("🚀 Starting all services...")
    print("-" * 60)
    
    for service_name in SERVICES:
        service_dir = services_base_dir / service_name
        
        # Check for Node.js service first (service.js), then Python (service.py)
        node_service_path = service_dir / "service.js"
        python_service_path = service_dir / "service.py"
        
        if node_service_path.exists():
            # Node.js service
            port = SERVICE_PORTS.get(service_name)
            print(f"Starting {service_name:12} on port {port} (Node.js)...")
            
            # Create log files for each service
            log_dir = project_root / "logs"
            log_dir.mkdir(exist_ok=True)
            stdout_log = log_dir / f"{service_name}_stdout.log"
            stderr_log = log_dir / f"{service_name}_stderr.log"
            
            proc = subprocess.Popen(
                ["node", "service.js"],
                stdout=open(stdout_log, 'w'),
                stderr=open(stderr_log, 'w'),
                cwd=str(service_dir),
                env=env
            )
            processes.append((service_name, port, proc))
            time.sleep(0.5)
            
        elif python_service_path.exists():
            # Python service
            port = SERVICE_PORTS.get(service_name)
            print(f"Starting {service_name:12} on port {port} (Python)...")
            
            # Create log files for each service
            log_dir = project_root / "logs"
            log_dir.mkdir(exist_ok=True)
            stdout_log = log_dir / f"{service_name}_stdout.log"
            stderr_log = log_dir / f"{service_name}_stderr.log"
            
            proc = subprocess.Popen(
                [sys.executable, str(python_service_path)],
                stdout=open(stdout_log, 'w'),
                stderr=open(stderr_log, 'w'),
                cwd=str(project_root),
                env=env  # Pass environment with PYTHONPATH
            )
            processes.append((service_name, port, proc))
            time.sleep(0.5)
            
        else:
            print(f"⚠️  Warning: No service.py or service.js found in {service_dir}, skipping...")
            continue
    
    print("-" * 60)
    print(f"✅ Started {len(processes)} services")
    print("\nService endpoints:")
    for name, port, _ in processes:
        print(f"  {name:15} → http://localhost:{port}")
    
    print("\n🎨 Dashboard UI: http://localhost:8014")
    print("🎯 Handler:      http://localhost:8012/handle")
    print("\nPress Ctrl+C to stop all services")


def shutdown_services(signum=None, frame=None):
    """Stop all services gracefully."""
    print("\n🛑 Shutting down services...")
    for name, port, proc in processes:
        print(f"Stopping {name}...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("✅ All services stopped")
    if signum is not None:
        sys.exit(0)


def kill_all_services():
    """Kill all running services by process name."""
    print("🛑 Killing all services...")
    
    # Kill Python services
    python_services = [
        "sms", "rag", "fraud", "database", "readquery", 
        "writeops", "complaint", "qr", "handler", "dashboard_ui"
    ]
    
    for service in python_services:
        try:
            subprocess.run(
                ["pkill", "-f", f"python.*services/{service}/service.py"],
                check=False,
                capture_output=True
            )
            print(f"  ✓ Killed {service}")
        except Exception as e:
            print(f"  ✗ Failed to kill {service}: {e}")
    
    # Kill Node.js services
    node_services = ["voice", "call", "llm"]
    
    for service in node_services:
        try:
            subprocess.run(
                ["pkill", "-f", f"node.*services/{service}/service.js"],
                check=False,
                capture_output=True
            )
            print(f"  ✓ Killed {service}")
        except Exception as e:
            print(f"  ✗ Failed to kill {service}: {e}")
    
    # Also kill start_services.py if running
    try:
        subprocess.run(
            ["pkill", "-f", "python.*start_services.py"],
            check=False,
            capture_output=True
        )
    except:
        pass
    
    print("✅ All services killed")



def check_health():
    """Check if services are responding."""
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


def update_twilio_webhook():
    """Update Twilio webhook URL after call service starts."""
    print("\n🔄 Updating Twilio webhook...")
    
    # Wait for call service to establish LocalTunnel
    time.sleep(5)
    
    try:
        # Get the public URL from call service
        resp = requests.get("http://localhost:8003/public-url", timeout=5)
        if resp.status_code == 200:
            webhook_url = resp.json().get('url')
            if webhook_url:
                webhook_url = f"{webhook_url}/voice-webhook"
                print(f"📞 Webhook URL: {webhook_url}")
                
                # Run the webhook update script
                script_path = project_root / "services" / "call" / "scripts" / "change_webhook.py"
                result = subprocess.run(
                    [sys.executable, str(script_path), "--url", webhook_url],
                    cwd=str(script_path.parent),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print("✅ Twilio webhook updated successfully!")
                    print(f"\n{'='*60}")
                    print("🎉 APPLICATION READY TO RECEIVE CALLS!")
                    print(f"{'='*60}")
                    print(f"📱 Call: +18559581055")
                    print(f"🌐 Webhook: {webhook_url}")
                    print(f"{'='*60}\n")
                else:
                    print(f"⚠️  Webhook update failed: {result.stderr}")
            else:
                print("⚠️  Could not get public URL from call service")
        else:
            print("⚠️  Call service not responding")
    except Exception as e:
        print(f"⚠️  Failed to update webhook: {e}")
        print("You may need to manually update the Twilio webhook URL")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Manage microservices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 start_services.py start      # Start all services
  python3 start_services.py stop       # Stop all services
  python3 start_services.py restart    # Restart all services
  python3 start_services.py            # Default: start all services
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=["start", "stop", "restart"],
        help="Command to execute (default: start)"
    )
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "stop":
        kill_all_services()
        sys.exit(0)
    
    elif args.command == "restart":
        kill_all_services()
        print("\n⏳ Waiting for processes to terminate...")
        time.sleep(2)
        # Continue to start services below
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_services)
    signal.signal(signal.SIGTERM, shutdown_services)
    
    try:
        start_services()
        
        if check_health():
            print("\n✅ All services are healthy and ready!")
        else:
            print("\n⚠️  Some services failed health check")
        
        # Update Twilio webhook for call service
        update_twilio_webhook()
        
        # Keep running
        print("\nServices running... (Ctrl+C to stop)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_services()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        shutdown_services()
