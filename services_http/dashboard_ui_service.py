"""Dashboard UI Service - Real-time monitoring web interface."""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
import asyncio
import json
from typing import List
from bankassist.config import get_service_url, SERVICE_PORTS

app = FastAPI(title="Dashboard UI Service")

# WebSocket connections for live updates
active_connections: List[WebSocket] = []


async def broadcast_update(data: dict):
    """Broadcast updates to all connected WebSocket clients."""
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except:
            active_connections.remove(connection)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live dashboard updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Send updates every 2 seconds
            await asyncio.sleep(2)
            
            # Collect data from all services
            update_data = await collect_all_metrics()
            await websocket.send_json(update_data)
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def collect_all_metrics():
    """Collect metrics from all services."""
    data = {
        "timestamp": asyncio.get_event_loop().time(),
        "services": {},
        "logs": []
    }
    
    for service_name, port in SERVICE_PORTS.items():
        if service_name == "dashboard_ui":
            continue
        
        try:
            # Get health status
            health_resp = requests.get(f"http://localhost:{port}/health", timeout=1)
            health = health_resp.json() if health_resp.status_code == 200 else {"status": "down"}
            
            # Get metrics if available
            try:
                metrics_resp = requests.get(f"http://localhost:{port}/metrics", timeout=1)
                metrics = metrics_resp.json() if metrics_resp.status_code == 200 else {}
            except:
                metrics = {}
            
            # Get logs if available
            try:
                logs_resp = requests.get(f"http://localhost:{port}/logs", timeout=1)
                logs = logs_resp.json() if logs_resp.status_code == 200 else []
                data["logs"].extend(logs)
            except:
                pass
            
            data["services"][service_name] = {
                "status": health.get("status", "unknown"),
                "port": port,
                "metrics": metrics
            }
        
        except Exception as e:
            data["services"][service_name] = {
                "status": "error",
                "port": port,
                "error": str(e)
            }
    
    # Sort logs by timestamp
    data["logs"].sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    data["logs"] = data["logs"][:100]  # Keep last 100 logs
    
    return data


@app.get("/api/metrics/{service_name}")
async def get_service_metrics(service_name: str, period: int = 60):
    """Get metrics for a specific service."""
    if service_name not in SERVICE_PORTS:
        return {"error": "Service not found"}
    
    port = SERVICE_PORTS[service_name]
    try:
        resp = requests.get(f"http://localhost:{port}/metrics?period={period}", timeout=2)
        return resp.json() if resp.status_code == 200 else {"error": "No metrics"}
    except:
        return {"error": "Service unavailable"}


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the dashboard HTML."""
    return HTML_TEMPLATE


@app.get("/voice-test", response_class=HTMLResponse)
async def get_voice_test():
    """Serve the voice testing page with live transcription."""
    return VOICE_TEST_HTML


# Dark-themed dashboard HTML with live updates
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BankAssist Microservices Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #1f6feb 0%, #0d419d 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }
        
        h1 {
            color: white;
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #c9d1d9;
            font-size: 16px;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        .card h2 {
            color: #58a6ff;
            font-size: 20px;
            margin-bottom: 15px;
            border-bottom: 2px solid #21262d;
            padding-bottom: 10px;
        }
        
        .service-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            margin: 8px 0;
            background: #0d1117;
            border-radius: 8px;
            border-left: 3px solid #30363d;
            transition: all 0.3s;
        }
        
        .service-item:hover {
            background: #1c2128;
            transform: translateX(5px);
        }
        
        .service-item.healthy {
            border-left-color: #238636;
        }
        
        .service-item.down {
            border-left-color: #da3633;
        }
        
        .service-name {
            font-weight: bold;
            color: #c9d1d9;
        }
        
        .service-port {
            color: #8b949e;
            font-size: 14px;
        }
        
        .status-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status-ok {
            background: #238636;
            color: white;
        }
        
        .status-down {
            background: #da3633;
            color: white;
        }
        
        .logs-container {
            background: #0d1117;
            border-radius: 8px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        
        .log-entry {
            padding: 8px;
            margin: 4px 0;
            border-radius: 4px;
            background: #161b22;
            border-left: 3px solid #30363d;
        }
        
        .log-entry.INFO {
            border-left-color: #58a6ff;
        }
        
        .log-entry.WARNING {
            border-left-color: #d29922;
        }
        
        .log-entry.ERROR {
            border-left-color: #da3633;
        }
        
        .log-timestamp {
            color: #8b949e;
            font-size: 11px;
        }
        
        .log-service {
            color: #58a6ff;
            font-weight: bold;
        }
        
        .log-message {
            color: #c9d1d9;
            margin-top: 4px;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        select, button {
            background: #21262d;
            color: #c9d1d9;
            border: 1px solid #30363d;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        
        select:hover, button:hover {
            background: #30363d;
            border-color: #58a6ff;
        }
        
        .metric-value {
            font-size: 36px;
            font-weight: bold;
            color: #58a6ff;
            margin: 15px 0;
        }
        
        .metric-label {
            color: #8b949e;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .metric-box {
            background: #0d1117;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #30363d;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #0d1117;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #30363d;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #484f58;
        }
        
        .connection-status {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-left: 10px;
            background: #da3633;
        }
        
        .connection-status.connected {
            background: #238636;
            box-shadow: 0 0 10px #238636;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏦 BankAssist Microservices Dashboard</h1>
        <div class="subtitle">
            Real-time monitoring and metrics
            <span class="connection-status" id="wsStatus"></span>
        </div>
        <div style="margin-top: 15px;">
            <a href="/voice-test" style="background: rgba(88, 166, 255, 0.2); padding: 8px 16px; border-radius: 6px; color: #58a6ff; text-decoration: none; border: 1px solid #58a6ff;">
                🎤 Test Voice & Live Transcription
            </a>
        </div>
    </div>
    
    <div class="dashboard-grid">
        <div class="card">
            <h2>📊 Service Status</h2>
            <div id="servicesContainer"></div>
        </div>
        
        <div class="card">
            <h2>📈 System Metrics</h2>
            <div class="metrics-grid" id="systemMetrics"></div>
        </div>
    </div>
    
    <div class="card" style="margin-bottom: 30px;">
        <h2>📉 Time-Series Graphs</h2>
        <div class="controls">
            <select id="metricSelect">
                <option value="requests">Total Requests</option>
                <option value="fraud_checks">Fraud Checks</option>
                <option value="calls">Calls</option>
                <option value="sms">SMS Messages</option>
                <option value="transactions">Transactions</option>
            </select>
            <select id="periodSelect">
                <option value="5">Last 5 minutes</option>
                <option value="15">Last 15 minutes</option>
                <option value="60" selected>Last 1 hour</option>
                <option value="360">Last 6 hours</option>
                <option value="1440">Last 24 hours</option>
            </select>
            <button onclick="refreshChart()">Refresh</button>
        </div>
        <div class="chart-container">
            <canvas id="metricsChart"></canvas>
        </div>
    </div>
    
    <div class="card">
        <h2>📜 Live Logs</h2>
        <div class="logs-container" id="logsContainer"></div>
    </div>
    
    <script>
        let ws;
        let chart;
        let latestData = {};
        
        function connectWebSocket() {
            const wsUrl = `ws://${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                document.getElementById('wsStatus').classList.add('connected');
                console.log('WebSocket connected');
            };
            
            ws.onclose = () => {
                document.getElementById('wsStatus').classList.remove('connected');
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                latestData = data;
                updateDashboard(data);
            };
        }
        
        function updateDashboard(data) {
            // Update services status
            const servicesHtml = Object.entries(data.services || {}).map(([name, info]) => {
                const status = info.status === 'ok' ? 'healthy' : 'down';
                const badge = info.status === 'ok' ? 'status-ok' : 'status-down';
                return `
                    <div class="service-item ${status}">
                        <div>
                            <div class="service-name">${name}</div>
                            <div class="service-port">Port ${info.port}</div>
                        </div>
                        <span class="status-badge ${badge}">${info.status.toUpperCase()}</span>
                    </div>
                `;
            }).join('');
            document.getElementById('servicesContainer').innerHTML = servicesHtml;
            
            // Update system metrics
            updateSystemMetrics(data);
            
            // Update logs
            updateLogs(data.logs || []);
        }
        
        function updateSystemMetrics(data) {
            const metrics = {};
            let totalRequests = 0;
            let totalCalls = 0;
            let totalSMS = 0;
            
            Object.values(data.services || {}).forEach(service => {
                if (service.metrics && service.metrics.counters) {
                    Object.entries(service.metrics.counters).forEach(([key, value]) => {
                        if (key.includes('request')) totalRequests += value;
                        if (key.includes('call')) totalCalls += value;
                        if (key.includes('sms') || key.includes('message')) totalSMS += value;
                    });
                }
            });
            
            const healthyServices = Object.values(data.services || {}).filter(s => s.status === 'ok').length;
            const totalServices = Object.keys(data.services || {}).length;
            
            const metricsHtml = `
                <div class="metric-box">
                    <div class="metric-label">Healthy Services</div>
                    <div class="metric-value">${healthyServices}/${totalServices}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Total Requests</div>
                    <div class="metric-value">${totalRequests}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Active Calls</div>
                    <div class="metric-value">${totalCalls}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">SMS Sent</div>
                    <div class="metric-value">${totalSMS}</div>
                </div>
            `;
            document.getElementById('systemMetrics').innerHTML = metricsHtml;
        }
        
        function updateLogs(logs) {
            const logsHtml = logs.slice(0, 50).map(log => {
                const level = log.level || 'INFO';
                return `
                    <div class="log-entry ${level}">
                        <span class="log-timestamp">${new Date(log.timestamp).toLocaleTimeString()}</span>
                        <span class="log-service">[${log.service}]</span>
                        <div class="log-message">${log.message}</div>
                    </div>
                `;
            }).join('');
            document.getElementById('logsContainer').innerHTML = logsHtml;
        }
        
        function initChart() {
            const ctx = document.getElementById('metricsChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Metric Value',
                        data: [],
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88, 166, 255, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#c9d1d9' }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#8b949e' },
                            grid: { color: '#21262d' }
                        },
                        y: {
                            ticks: { color: '#8b949e' },
                            grid: { color: '#21262d' }
                        }
                    }
                }
            });
        }
        
        function refreshChart() {
            // In a real implementation, this would fetch time-series data
            // For now, we'll show a placeholder
            const labels = Array.from({length: 20}, (_, i) => `-${20-i}m`);
            const data = Array.from({length: 20}, () => Math.floor(Math.random() * 100));
            
            chart.data.labels = labels;
            chart.data.datasets[0].data = data;
            chart.update();
        }
        
        // Initialize
        connectWebSocket();
        initChart();
        refreshChart();
    </script>
</body>
</html>
"""


# Voice Testing HTML with Live Transcription
VOICE_TEST_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Testing - Live Transcription</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #1f6feb 0%, #0d419d 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }
        
        h1 {
            color: white;
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        .card h2 {
            color: #58a6ff;
            font-size: 24px;
            margin-bottom: 20px;
        }
        
        .control-section {
            margin-bottom: 30px;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #8b949e;
            font-weight: 500;
        }
        
        input[type="text"], textarea {
            width: 100%;
            padding: 12px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #c9d1d9;
            font-size: 14px;
            font-family: inherit;
        }
        
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        button {
            background: #238636;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s;
            margin-right: 10px;
        }
        
        button:hover {
            background: #2ea043;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
        }
        
        button:disabled {
            background: #30363d;
            cursor: not-allowed;
            transform: none;
        }
        
        button.secondary {
            background: #1f6feb;
        }
        
        button.secondary:hover {
            background: #388bfd;
        }
        
        button.danger {
            background: #da3633;
        }
        
        button.danger:hover {
            background: #e5534b;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            background: #da3633;
        }
        
        .status-indicator.recording {
            background: #da3633;
            animation: pulse 1.5s infinite;
        }
        
        .status-indicator.connected {
            background: #238636;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .transcription-box {
            background: #0d1117;
            border: 2px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            min-height: 200px;
            margin-top: 20px;
        }
        
        .transcript-item {
            padding: 10px;
            margin: 8px 0;
            border-radius: 6px;
            background: #161b22;
        }
        
        .transcript-item.partial {
            border-left: 3px solid #d29922;
            opacity: 0.7;
        }
        
        .transcript-item.final {
            border-left: 3px solid #238636;
        }
        
        .timestamp {
            color: #8b949e;
            font-size: 12px;
            margin-bottom: 5px;
        }
        
        .text {
            color: #c9d1d9;
            font-size: 16px;
        }
        
        .audio-controls {
            margin-top: 20px;
        }
        
        audio {
            width: 100%;
            margin-top: 10px;
        }
        
        .status-message {
            padding: 12px;
            border-radius: 6px;
            margin-top: 15px;
        }
        
        .status-message.success {
            background: rgba(35, 134, 54, 0.2);
            border: 1px solid #238636;
            color: #238636;
        }
        
        .status-message.error {
            background: rgba(218, 54, 51, 0.2);
            border: 1px solid #da3633;
            color: #da3633;
        }
        
        .status-message.info {
            background: rgba(88, 166, 255, 0.2);
            border: 1px solid #58a6ff;
            color: #58a6ff;
        }
        
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #58a6ff;
            text-decoration: none;
        }
        
        .back-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <a href="/" class="back-link">← Back to Dashboard</a>
    
    <div class="header">
        <h1>🎤 Voice Testing - Live Transcription</h1>
        <div class="subtitle">Test TTS and real-time speech recognition</div>
    </div>
    
    <div class="card">
        <h2>1. Text-to-Speech (TTS)</h2>
        <div class="control-section">
            <div class="input-group">
                <label for="ttsInput">Enter text to convert to speech:</label>
                <textarea id="ttsInput" placeholder="Type something...">Hello, this is a test of the text to speech system. How are you doing today?</textarea>
            </div>
            <button id="synthesizeBtn" onclick="synthesizeSpeech()">🔊 Generate Speech</button>
            <div id="ttsStatus"></div>
            <div id="audioContainer" class="audio-controls"></div>
        </div>
    </div>
    
    <div class="card">
        <h2>2. Live Transcription (Speech-to-Text)</h2>
        <div class="control-section">
            <div style="margin-bottom: 20px;">
                <span class="status-indicator" id="wsIndicator"></span>
                <span id="wsStatus">Not Connected</span>
            </div>
            
            <div style="margin-bottom: 20px;">
                <button id="startMicBtn" onclick="startMicrophone()" class="secondary">
                    🎤 Start Microphone
                </button>
                <button id="stopMicBtn" onclick="stopMicrophone()" class="danger" disabled>
                    ⏹ Stop Microphone
                </button>
                <button onclick="testWithGeneratedAudio()" style="margin-left: 20px;">
                    🔄 Test with Generated Audio
                </button>
                <button onclick="clearTranscripts()">🗑️ Clear</button>
            </div>
            
            <div id="liveStatus"></div>
            
            <div class="transcription-box" id="transcriptionBox">
                <div style="color: #8b949e; text-align: center;">
                    Transcriptions will appear here...
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let wsConnection = null;
        let mediaRecorder = null;
        let audioContext = null;
        let generatedAudioBase64 = null;
        let currentAudioElement = null;
        
        // Connect to voice service WebSocket
        function connectWebSocket() {
            const wsUrl = 'ws://localhost:8001/live-transcribe';
            
            try {
                wsConnection = new WebSocket(wsUrl);
                
                wsConnection.onopen = () => {
                    console.log('WebSocket connected');
                    document.getElementById('wsIndicator').classList.add('connected');
                    document.getElementById('wsStatus').textContent = 'Connected to Voice Service';
                    showStatus('liveStatus', 'Connected to live transcription service', 'success');
                };
                
                wsConnection.onclose = () => {
                    console.log('WebSocket disconnected');
                    document.getElementById('wsIndicator').classList.remove('connected');
                    document.getElementById('wsStatus').textContent = 'Disconnected';
                    showStatus('liveStatus', 'Disconnected from service', 'error');
                    
                    // Try to reconnect after 3 seconds
                    setTimeout(connectWebSocket, 3000);
                };
                
                wsConnection.onmessage = (event) => {
                    const msg = JSON.parse(event.data);
                    console.log('Received:', msg);
                    
                    if (msg.type === 'partial') {
                        addTranscript(msg.text, 'partial', msg.timestamp);
                    } else if (msg.type === 'final') {
                        addTranscript(msg.text, 'final', msg.timestamp);
                    } else if (msg.type === 'error') {
                        showStatus('liveStatus', `Error: ${msg.error}`, 'error');
                    }
                };
                
                wsConnection.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    showStatus('liveStatus', 'WebSocket connection error', 'error');
                };
                
            } catch (err) {
                console.error('Failed to connect:', err);
                showStatus('liveStatus', 'Failed to connect to voice service', 'error');
            }
        }
        
        // Synthesize speech
        async function synthesizeSpeech() {
            const text = document.getElementById('ttsInput').value;
            if (!text.trim()) {
                showStatus('ttsStatus', 'Please enter some text', 'error');
                return;
            }
            
            const btn = document.getElementById('synthesizeBtn');
            btn.disabled = true;
            btn.textContent = '⏳ Generating...';
            
            try {
                const response = await fetch('http://localhost:8001/synthesize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                generatedAudioBase64 = data.audio_bytes;
                
                // Create audio element
                const audioBlob = base64ToBlob(data.audio_bytes, 'audio/wav');
                const audioUrl = URL.createObjectURL(audioBlob);
                
                const container = document.getElementById('audioContainer');
                container.innerHTML = `
                    <audio controls id="generatedAudio">
                        <source src="${audioUrl}" type="audio/wav">
                    </audio>
                `;
                
                currentAudioElement = document.getElementById('generatedAudio');
                
                showStatus('ttsStatus', '✓ Audio generated successfully! You can now test it with live transcription.', 'success');
                
            } catch (err) {
                console.error('TTS error:', err);
                showStatus('ttsStatus', `Error: ${err.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '🔊 Generate Speech';
            }
        }
        
        // Start microphone recording
        async function startMicrophone() {
            if (!wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
                showStatus('liveStatus', 'Please wait for WebSocket connection', 'error');
                return;
            }
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        sampleRate: 16000,
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true
                    } 
                });
                
                audioContext = new AudioContext({ sampleRate: 16000 });
                const source = audioContext.createMediaStreamSource(stream);
                const processor = audioContext.createScriptProcessor(4096, 1, 1);
                
                processor.onaudioprocess = (e) => {
                    if (wsConnection.readyState === WebSocket.OPEN) {
                        const inputData = e.inputBuffer.getChannelData(0);
                        const pcm16 = floatTo16BitPCM(inputData);
                        wsConnection.send(pcm16);
                    }
                };
                
                source.connect(processor);
                processor.connect(audioContext.destination);
                
                mediaRecorder = { stream, processor, source };
                
                document.getElementById('startMicBtn').disabled = true;
                document.getElementById('stopMicBtn').disabled = false;
                document.getElementById('wsIndicator').classList.add('recording');
                
                showStatus('liveStatus', '🎤 Recording... Speak now!', 'info');
                
            } catch (err) {
                console.error('Microphone error:', err);
                showStatus('liveStatus', `Microphone error: ${err.message}`, 'error');
            }
        }
        
        // Stop microphone recording
        function stopMicrophone() {
            if (mediaRecorder) {
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                mediaRecorder.processor.disconnect();
                mediaRecorder.source.disconnect();
                if (audioContext) {
                    audioContext.close();
                }
                mediaRecorder = null;
            }
            
            if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
                wsConnection.send(JSON.stringify({ type: 'stop' }));
            }
            
            document.getElementById('startMicBtn').disabled = false;
            document.getElementById('stopMicBtn').disabled = true;
            document.getElementById('wsIndicator').classList.remove('recording');
            
            showStatus('liveStatus', 'Recording stopped', 'info');
        }
        
        // Test with generated audio
        async function testWithGeneratedAudio() {
            if (!generatedAudioBase64) {
                showStatus('liveStatus', 'Please generate audio first using TTS above', 'error');
                return;
            }
            
            if (!wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
                showStatus('liveStatus', 'Please wait for WebSocket connection', 'error');
                return;
            }
            
            try {
                // Convert WAV to PCM16
                const audioBlob = base64ToBlob(generatedAudioBase64, 'audio/wav');
                const arrayBuffer = await audioBlob.arrayBuffer();
                const pcmData = extractPCMFromWAV(arrayBuffer);
                
                showStatus('liveStatus', 'Sending audio for transcription...', 'info');
                
                // Send audio data
                wsConnection.send(pcmData);
                
                // Stop after a delay
                setTimeout(() => {
                    wsConnection.send(JSON.stringify({ type: 'stop' }));
                    showStatus('liveStatus', 'Audio sent. Waiting for transcription...', 'info');
                }, 2000);
                
                // Also play the audio
                if (currentAudioElement) {
                    currentAudioElement.play();
                }
                
            } catch (err) {
                console.error('Test error:', err);
                showStatus('liveStatus', `Error: ${err.message}`, 'error');
            }
        }
        
        // Add transcript to display
        function addTranscript(text, type, timestamp) {
            const box = document.getElementById('transcriptionBox');
            
            // Remove placeholder
            if (box.querySelector('[style*="text-align: center"]')) {
                box.innerHTML = '';
            }
            
            const item = document.createElement('div');
            item.className = `transcript-item ${type}`;
            item.innerHTML = `
                <div class="timestamp">${new Date(timestamp).toLocaleTimeString()} - ${type.toUpperCase()}</div>
                <div class="text">${text}</div>
            `;
            
            box.appendChild(item);
            box.scrollTop = box.scrollHeight;
        }
        
        // Clear transcripts
        function clearTranscripts() {
            const box = document.getElementById('transcriptionBox');
            box.innerHTML = '<div style="color: #8b949e; text-align: center;">Transcriptions will appear here...</div>';
        }
        
        // Show status message
        function showStatus(elementId, message, type) {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="status-message ${type}">${message}</div>`;
        }
        
        // Helper: Convert base64 to Blob
        function base64ToBlob(base64, mimeType) {
            const byteCharacters = atob(base64);
            const byteArrays = [];
            
            for (let offset = 0; offset < byteCharacters.length; offset += 512) {
                const slice = byteCharacters.slice(offset, offset + 512);
                const byteNumbers = new Array(slice.length);
                for (let i = 0; i < slice.length; i++) {
                    byteNumbers[i] = slice.charCodeAt(i);
                }
                byteArrays.push(new Uint8Array(byteNumbers));
            }
            
            return new Blob(byteArrays, { type: mimeType });
        }
        
        // Helper: Extract PCM from WAV
        function extractPCMFromWAV(arrayBuffer) {
            const view = new DataView(arrayBuffer);
            let offset = 12;
            
            while (offset < view.byteLength) {
                const chunkId = String.fromCharCode(
                    view.getUint8(offset),
                    view.getUint8(offset + 1),
                    view.getUint8(offset + 2),
                    view.getUint8(offset + 3)
                );
                const chunkSize = view.getUint32(offset + 4, true);
                
                if (chunkId === 'data') {
                    return new Uint8Array(arrayBuffer, offset + 8, chunkSize);
                }
                
                offset += 8 + chunkSize;
            }
            
            // Fallback: standard 44-byte header
            return new Uint8Array(arrayBuffer, 44);
        }
        
        // Helper: Convert Float32 to PCM16
        function floatTo16BitPCM(float32Array) {
            const buffer = new ArrayBuffer(float32Array.length * 2);
            const view = new DataView(buffer);
            let offset = 0;
            for (let i = 0; i < float32Array.length; i++, offset += 2) {
                const s = Math.max(-1, Math.min(1, float32Array[i]));
                view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }
            return buffer;
        }
        
        // Initialize
        connectWebSocket();
    </script>
</body>
</html>
"""


@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard_ui"}


if __name__ == "__main__":
    import uvicorn
    from bankassist.config import SERVICE_PORTS
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORTS["dashboard_ui"])
