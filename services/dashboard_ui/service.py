"""Dashboard UI Service - Real-time monitoring web interface."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
import asyncio
import json
from typing import List
from shared.config import get_service_url, SERVICE_PORTS

from services.dashboard_ui import config

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


@app.post("/api/voice/transcribe")
async def proxy_voice_transcribe(request_data: dict):
    """Proxy transcription requests to Voice service."""
    try:
        resp = requests.post(
            "http://localhost:8001/transcribe",
            json=request_data,
            timeout=30
        )
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/voice/synthesize")
async def proxy_voice_synthesize(request_data: dict):
    """Proxy synthesis requests to Voice service."""
    try:
        resp = requests.post(
            "http://localhost:8001/synthesize",
            json=request_data,
            timeout=30
        )
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/llm/answer")
async def proxy_llm_answer(request_data: dict):
    """Proxy LLM answer requests to LLM service."""
    try:
        resp = requests.post(
            "http://localhost:8004/answer",
            json=request_data,
            timeout=30
        )
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the dashboard HTML."""
    return HTML_TEMPLATE


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
        
        .test-section {
            margin-top: 15px;
            padding: 15px;
            background: #0d1117;
            border-radius: 8px;
            border: 1px solid #30363d;
        }
        
        .test-section h3 {
            color: #58a6ff;
            margin-bottom: 15px;
            font-size: 16px;
        }
        
        input[type="text"], textarea {
            width: 100%;
            background: #0d1117;
            color: #c9d1d9;
            border: 1px solid #30363d;
            padding: 10px;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
            margin-bottom: 10px;
        }
        
        input[type="text"]:focus, textarea:focus {
            outline: none;
            border-color: #58a6ff;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #1f6feb 0%, #0d419d 100%);
            color: white;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #da3633 0%, #a40e26 100%);
            color: white;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
            color: white;
        }
        
        .recording-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #da3633;
            border-radius: 50%;
            margin-right: 5px;
            animation: pulse-recording 1.5s infinite;
        }
        
        @keyframes pulse-recording {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        .test-output {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 12px;
            margin-top: 10px;
            min-height: 60px;
            color: #c9d1d9;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        
        .chat-messages {
            max-height: 300px;
            overflow-y: auto;
            margin-bottom: 10px;
        }
        
        .chat-message {
            padding: 10px;
            margin: 8px 0;
            border-radius: 8px;
            border-left: 3px solid #30363d;
        }
        
        .chat-message.user {
            background: #1c2128;
            border-left-color: #58a6ff;
        }
        
        .chat-message.assistant {
            background: #161b22;
            border-left-color: #238636;
        }
        
        .chat-label {
            font-weight: bold;
            font-size: 12px;
            color: #8b949e;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏦 BankAssist Microservices Dashboard</h1>
        <div class="subtitle">
            Real-time monitoring, metrics, and service testing
            <span class="connection-status" id="wsStatus"></span>
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
    
    <!-- Voice and LLM Testing -->
    <div class="dashboard-grid">
        <div class="card">
            <h2>🎤 Voice Service Testing</h2>
            <div class="test-section">
                <h3>Speech-to-Text (STT)</h3>
                <button id="startRecording" class="btn-primary" onclick="startRecording()">
                    <span id="recordingIcon">🎙️</span> Start Recording
                </button>
                <button id="stopRecording" class="btn-danger" onclick="stopRecording()" disabled>
                    ⏹️ Stop Recording
                </button>
                <div class="test-output" id="transcriptOutput">
                    <em>Click "Start Recording" to begin...</em>
                </div>
            </div>
            
            <div class="test-section">
                <h3>Text-to-Speech (TTS)</h3>
                <input type="text" id="ttsInput" placeholder="Enter text to synthesize..." value="Hello, welcome to our banking service!">
                <button class="btn-success" onclick="synthesizeSpeech()">🔊 Synthesize Speech</button>
                <audio id="audioPlayer" controls style="width: 100%; margin-top: 10px; display: none;"></audio>
                <div class="test-output" id="ttsOutput" style="display: none;"></div>
            </div>
        </div>
        
        <div class="card">
            <h2>🤖 LLM Chat Interface</h2>
            <div class="test-section">
                <div class="chat-messages" id="chatMessages">
                    <div class="chat-message assistant">
                        <div class="chat-label">ASSISTANT</div>
                        <div>Hello! I'm your AI banking assistant. How can I help you today?</div>
                    </div>
                </div>
                <input type="text" id="chatInput" placeholder="Ask a question..." onkeypress="if(event.key==='Enter') sendChatMessage()">
                <button class="btn-primary" onclick="sendChatMessage()">💬 Send</button>
                <button class="btn-danger" onclick="clearChat()" style="margin-left: 10px;">🗑️ Clear</button>
            </div>
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
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;
        
        // Use dashboard proxy endpoints instead of direct service calls
        const VOICE_API = '/api/voice';
        const LLM_API = '/api/llm';
        
        // Voice Service Testing
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    document.getElementById('transcriptOutput').innerHTML = '<em>🔄 Transcribing...</em>';
                    
                    try {
                        const reader = new FileReader();
                        reader.readAsDataURL(audioBlob);
                        reader.onloadend = async () => {
                            const base64Audio = reader.result.split(',')[1];
                            
                            const response = await fetch(`${VOICE_API}/transcribe`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    audio_bytes: base64Audio,
                                    format: 'wav'
                                })
                            });

                            const data = await response.json();
                            
                            if (response.ok) {
                                document.getElementById('transcriptOutput').innerHTML = 
                                    `<strong>Transcript:</strong><br>${data.transcript}`;
                            } else {
                                throw new Error(data.error || 'Transcription failed');
                            }
                        };
                    } catch (error) {
                        document.getElementById('transcriptOutput').innerHTML = 
                            `<span style="color: #da3633;">❌ Error: ${error.message}</span>`;
                    }
                };

                mediaRecorder.start();
                isRecording = true;
                document.getElementById('startRecording').disabled = true;
                document.getElementById('stopRecording').disabled = false;
                document.getElementById('recordingIcon').innerHTML = '<span class="recording-dot"></span>';
                document.getElementById('transcriptOutput').innerHTML = '<em>🎙️ Listening... speak now!</em>';

            } catch (error) {
                document.getElementById('transcriptOutput').innerHTML = 
                    `<span style="color: #da3633;">❌ Microphone access denied: ${error.message}</span>`;
            }
        }

        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                isRecording = false;
                document.getElementById('startRecording').disabled = false;
                document.getElementById('stopRecording').disabled = true;
                document.getElementById('recordingIcon').innerHTML = '🎙️';
            }
        }

        async function synthesizeSpeech() {
            const text = document.getElementById('ttsInput').value.trim();
            
            if (!text) {
                alert('Please enter some text');
                return;
            }

            document.getElementById('ttsOutput').style.display = 'block';
            document.getElementById('ttsOutput').innerHTML = '🔄 Synthesizing speech...';
            document.getElementById('audioPlayer').style.display = 'none';

            try {
                const response = await fetch(`${VOICE_API}/synthesize`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });

                const data = await response.json();

                if (response.ok) {
                    const audioData = `data:audio/wav;base64,${data.audio_bytes}`;
                    document.getElementById('audioPlayer').src = audioData;
                    document.getElementById('audioPlayer').style.display = 'block';
                    document.getElementById('audioPlayer').play();
                    document.getElementById('ttsOutput').innerHTML = '✅ Speech synthesized successfully!';
                    document.getElementById('ttsOutput').style.color = '#238636';
                } else {
                    throw new Error(data.error || 'Synthesis failed');
                }
            } catch (error) {
                document.getElementById('ttsOutput').innerHTML = `❌ Error: ${error.message}`;
                document.getElementById('ttsOutput').style.color = '#da3633';
            }
        }

        // LLM Chat Interface
        async function sendChatMessage() {
            const input = document.getElementById('chatInput');
            const question = input.value.trim();
            
            if (!question) return;
            
            // Add user message
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML += `
                <div class="chat-message user">
                    <div class="chat-label">YOU</div>
                    <div>${escapeHtml(question)}</div>
                </div>
            `;
            
            // Add loading message
            chatMessages.innerHTML += `
                <div class="chat-message assistant" id="loading-message">
                    <div class="chat-label">ASSISTANT</div>
                    <div>🔄 Thinking...</div>
                </div>
            `;
            
            chatMessages.scrollTop = chatMessages.scrollHeight;
            input.value = '';
            
            try {
                const response = await fetch(`${LLM_API}/answer`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question })
                });
                
                const data = await response.json();
                
                // Remove loading message
                document.getElementById('loading-message').remove();
                
                if (response.ok) {
                    chatMessages.innerHTML += `
                        <div class="chat-message assistant">
                            <div class="chat-label">ASSISTANT (Confidence: ${(data.confidence * 100).toFixed(1)}%)</div>
                            <div>${escapeHtml(data.answer)}</div>
                        </div>
                    `;
                } else {
                    throw new Error(data.error || 'Failed to get answer');
                }
            } catch (error) {
                document.getElementById('loading-message').remove();
                chatMessages.innerHTML += `
                    <div class="chat-message assistant">
                        <div class="chat-label">ERROR</div>
                        <div style="color: #da3633;">❌ ${escapeHtml(error.message)}</div>
                    </div>
                `;
            }
            
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function clearChat() {
            document.getElementById('chatMessages').innerHTML = `
                <div class="chat-message assistant">
                    <div class="chat-label">ASSISTANT</div>
                    <div>Hello! I'm your AI banking assistant. How can I help you today?</div>
                </div>
            `;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard_ui"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
