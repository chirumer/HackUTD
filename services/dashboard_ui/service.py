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
        "logs": [],
        "call_metrics": {}
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
                
                # Special handling for call service metrics
                if service_name == "call" and metrics:
                    data["call_metrics"] = metrics
            except:
                metrics = {}
            
            # Get logs if available
            try:
                logs_resp = requests.get(f"http://localhost:{port}/logs", timeout=1)
                logs = logs_resp.json() if logs_resp.status_code == 200 else []
                data["logs"].extend(logs)
            except:
                pass
            
            # Get active calls for call service
            if service_name == "call":
                try:
                    active_resp = requests.get(f"http://localhost:{port}/active", timeout=1)
                    if active_resp.status_code == 200:
                        active_calls = active_resp.json()
                        if "call_metrics" not in data:
                            data["call_metrics"] = {}
                        data["call_metrics"]["active_calls_list"] = active_calls
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


@app.get("/api/conversations/completed")
async def proxy_conversations_completed(limit: int = 50):
    """Proxy request to get completed conversations from handler service."""
    try:
        resp = requests.get(
            f"http://localhost:8012/conversations/completed?limit={limit}",
            timeout=5
        )
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e), "completed_conversations": [], "count": 0}


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
            <h2>� Call Service Metrics</h2>
            <div class="metrics-grid" id="callMetrics">
                <div class="metric-box">
                    <div class="metric-label">Total Calls</div>
                    <div class="metric-value" id="totalCalls">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Answered</div>
                    <div class="metric-value" id="answeredCalls">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Completed</div>
                    <div class="metric-value" id="completedCalls">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Active Now</div>
                    <div class="metric-value" id="activeCalls">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">User Hangups</div>
                    <div class="metric-value" id="userHangups">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">System Hangups</div>
                    <div class="metric-value" id="systemHangups">0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Avg Duration</div>
                    <div class="metric-value" id="avgDuration">0s</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Success Rate</div>
                    <div class="metric-value" id="successRate">0%</div>
                </div>
            </div>
            <div style="margin-top: 20px; padding: 15px; background: #0d1117; border-radius: 8px; border: 1px solid #30363d;">
                <h3 style="color: #58a6ff; margin-bottom: 10px; font-size: 14px;">📋 Active Calls</h3>
                <div id="activeCallsList" style="max-height: 200px; overflow-y: auto;">
                    <em style="color: #8b949e;">No active calls</em>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>�📈 System Metrics</h2>
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
        <h2>� Completed Call Conversations</h2>
        <div class="controls">
            <button onclick="refreshConversations()">🔄 Refresh</button>
            <span id="conversationCount" style="color: #8b949e; margin-left: 10px;">Loading...</span>
        </div>
        <div id="conversationsContainer" style="max-height: 600px; overflow-y: auto;">
            <em style="color: #8b949e;">Loading conversations...</em>
        </div>
    </div>
    
    <div class="card">
        <h2>�📜 Live Logs</h2>
        <div class="logs-container" id="logsContainer"></div>
    </div>
    
    <script>
        let ws;
        let chart;
        let latestData = {};
        let voiceWs = null;
        let mediaRecorder = null;
        let audioContext = null;
        let audioProcessor = null;
        let isRecording = false;
        
        // Use dashboard proxy endpoints instead of direct service calls
        const VOICE_API = '/api/voice';
        const LLM_API = '/api/llm';
        const VOICE_WS_URL = 'ws://localhost:8001/live-transcribe';
        
        // Voice Service Testing - Live Transcription
        async function startRecording() {
            console.log('startRecording called');
            
            try {
                document.getElementById('transcriptOutput').innerHTML = '<em>🔄 Connecting to voice service...</em>';
                
                // Connect to voice service WebSocket
                console.log('Connecting to WebSocket:', VOICE_WS_URL);
                voiceWs = new WebSocket(VOICE_WS_URL);
                
                voiceWs.onopen = async () => {
                    console.log('✓ Voice WebSocket connected');
                    document.getElementById('transcriptOutput').innerHTML = '<em>🎙️ Requesting microphone access...</em>';
                    
                    try {
                        // Start microphone
                        console.log('Requesting microphone access...');
                        const stream = await navigator.mediaDevices.getUserMedia({ 
                            audio: {
                                sampleRate: 16000,
                                channelCount: 1,
                                echoCancellation: true,
                                noiseSuppression: true
                            } 
                        });
                        
                        console.log('✓ Microphone access granted');
                        audioContext = new AudioContext({ sampleRate: 16000 });
                        const source = audioContext.createMediaStreamSource(stream);
                        audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);
                        
                        let chunkCount = 0;
                        audioProcessor.onaudioprocess = (e) => {
                            if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                                const inputData = e.inputBuffer.getChannelData(0);
                                const pcm16 = floatTo16BitPCM(inputData);
                                voiceWs.send(pcm16);
                                chunkCount++;
                                if (chunkCount % 10 === 0) {
                                    console.log('Sent audio chunk', chunkCount);
                                }
                            }
                        };
                        
                        source.connect(audioProcessor);
                        audioProcessor.connect(audioContext.destination);
                        
                        mediaRecorder = { stream, source, audioProcessor };
                        isRecording = true;
                        
                        document.getElementById('startRecording').disabled = true;
                        document.getElementById('stopRecording').disabled = false;
                        document.getElementById('recordingIcon').innerHTML = '<span class="recording-dot"></span>';
                        document.getElementById('transcriptOutput').innerHTML = '<div style="color: #58a6ff;"><strong>🎙️ Recording... Speak now!</strong></div><hr style="margin: 10px 0; border-color: #30363d;">';
                        console.log('✓ Recording started');
                    } catch (micError) {
                        console.error('Microphone error:', micError);
                        document.getElementById('transcriptOutput').innerHTML = 
                            `<span style="color: #da3633;">❌ Microphone error: ${micError.message}</span>`;
                        if (voiceWs) voiceWs.close();
                    }
                };
                
                voiceWs.onmessage = (event) => {
                    const msg = JSON.parse(event.data);
                    console.log('Voice WS message:', msg);
                    
                    if (msg.type === 'started') {
                        console.log('✓ Live transcription started');
                    } else if (msg.type === 'partial') {
                        // Show partial transcription (real-time updates)
                        console.log('Partial:', msg.text);
                        const output = document.getElementById('transcriptOutput');
                        const lines = output.innerHTML.split('<hr')[0];
                        output.innerHTML = lines + '<hr style="margin: 10px 0; border-color: #30363d;">' +
                            `<div style="color: #8b949e; font-style: italic;">Partial: ${escapeHtml(msg.text)}</div>`;
                        output.scrollTop = output.scrollHeight;
                    } else if (msg.type === 'final') {
                        // Show final transcription
                        console.log('Final:', msg.text);
                        const output = document.getElementById('transcriptOutput');
                        const timestamp = new Date().toLocaleTimeString();
                        output.innerHTML += `<div style="color: #238636; margin-top: 5px;"><strong>[${timestamp}]</strong> ${escapeHtml(msg.text)}</div>`;
                        output.scrollTop = output.scrollHeight;
                    } else if (msg.type === 'error') {
                        console.error('Transcription error:', msg.error);
                        document.getElementById('transcriptOutput').innerHTML += 
                            `<div style="color: #da3633;">❌ Error: ${escapeHtml(msg.error)}</div>`;
                    } else if (msg.type === 'stopped') {
                        console.log('Live transcription stopped');
                    }
                };
                
                voiceWs.onerror = (error) => {
                    console.error('Voice WebSocket error:', error);
                    document.getElementById('transcriptOutput').innerHTML = 
                        '<span style="color: #da3633;">❌ Failed to connect to voice service. Make sure it is running on port 8001.</span>';
                    stopRecording();
                };
                
                voiceWs.onclose = () => {
                    console.log('Voice WebSocket closed');
                };
                
            } catch (error) {
                console.error('Recording error:', error);
                document.getElementById('transcriptOutput').innerHTML = 
                    `<span style="color: #da3633;">❌ Error: ${error.message}</span>`;
                stopRecording();
            }
        }

        function stopRecording() {
            if (mediaRecorder) {
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                if (audioProcessor) {
                    audioProcessor.disconnect();
                }
                if (mediaRecorder.source) {
                    mediaRecorder.source.disconnect();
                }
                if (audioContext) {
                    audioContext.close();
                }
                mediaRecorder = null;
                audioProcessor = null;
                audioContext = null;
            }
            
            if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                voiceWs.send(JSON.stringify({ type: 'stop' }));
                voiceWs.close();
            }
            voiceWs = null;
            
            isRecording = false;
            document.getElementById('startRecording').disabled = false;
            document.getElementById('stopRecording').disabled = true;
            document.getElementById('recordingIcon').innerHTML = '🎙️';
            
            const output = document.getElementById('transcriptOutput');
            if (output.innerHTML.includes('Recording')) {
                output.innerHTML += '<div style="color: #8b949e; margin-top: 10px;"><em>Recording stopped.</em></div>';
            }
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
            
            // Update call metrics
            updateCallMetrics(data.call_metrics || {});
            
            // Update system metrics
            updateSystemMetrics(data);
            
            // Update logs
            updateLogs(data.logs || []);
        }
        
        function updateCallMetrics(metrics) {
            if (Object.keys(metrics).length === 0) {
                // No metrics available
                document.getElementById('totalCalls').textContent = '-';
                document.getElementById('answeredCalls').textContent = '-';
                document.getElementById('completedCalls').textContent = '-';
                document.getElementById('activeCalls').textContent = '-';
                document.getElementById('userHangups').textContent = '-';
                document.getElementById('systemHangups').textContent = '-';
                document.getElementById('avgDuration').textContent = '-';
                document.getElementById('successRate').textContent = '-';
                return;
            }
            
            // Update call metric values
            document.getElementById('totalCalls').textContent = metrics.totalCalls || 0;
            document.getElementById('answeredCalls').textContent = metrics.answeredCalls || 0;
            document.getElementById('completedCalls').textContent = metrics.completedCalls || 0;
            document.getElementById('activeCalls').textContent = metrics.activeCalls || 0;
            document.getElementById('userHangups').textContent = metrics.userHangups || 0;
            document.getElementById('systemHangups').textContent = metrics.systemHangups || 0;
            document.getElementById('avgDuration').textContent = metrics.averageDuration || '0s';
            document.getElementById('successRate').textContent = metrics.successRate || '0%';
            
            // Update active calls list
            const activeCallsList = document.getElementById('activeCallsList');
            if (metrics.active_calls_list && metrics.active_calls_list.length > 0) {
                const callsHtml = metrics.active_calls_list.map(call => {
                    const startTime = new Date(call.started_at * 1000).toLocaleTimeString();
                    const duration = Math.floor((Date.now() / 1000) - call.started_at);
                    return `
                        <div style="padding: 8px; margin: 4px 0; background: #161b22; border-radius: 4px; border-left: 3px solid #58a6ff;">
                            <div style="font-weight: bold; color: #c9d1d9;">📞 ${escapeHtml(call.phone)}</div>
                            <div style="font-size: 12px; color: #8b949e; margin-top: 4px;">
                                Started: ${startTime} | Duration: ${duration}s
                            </div>
                            ${call.transcript ? `<div style="font-size: 12px; color: #c9d1d9; margin-top: 4px; font-style: italic;">"${escapeHtml(call.transcript)}"</div>` : ''}
                        </div>
                    `;
                }).join('');
                activeCallsList.innerHTML = callsHtml;
            } else {
                activeCallsList.innerHTML = '<em style="color: #8b949e;">No active calls</em>';
            }
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
        
        // Conversations Functions
        async function refreshConversations() {
            try {
                const response = await fetch('/api/conversations/completed');
                const data = await response.json();
                
                const container = document.getElementById('conversationsContainer');
                const countSpan = document.getElementById('conversationCount');
                
                countSpan.textContent = `${data.count} completed conversation(s)`;
                
                if (data.completed_conversations && data.completed_conversations.length > 0) {
                    const conversationsHtml = data.completed_conversations.map((conv, index) => {
                        const startTime = new Date(conv.started_at * 1000).toLocaleString();
                        const duration = conv.ended_at ? ((conv.ended_at - conv.started_at).toFixed(1)) : 'N/A';
                        const messageCount = conv.messages.length;
                        
                        const messagesHtml = conv.messages.map(msg => {
                            const role = msg.role === 'user' ? 'USER' : 'ASSISTANT';
                            const roleClass = msg.role === 'user' ? 'user' : 'assistant';
                            const icon = msg.role === 'user' ? '👤' : '🤖';
                            const timestamp = new Date(msg.timestamp * 1000).toLocaleTimeString();
                            
                            return `
                                <div class="chat-message ${roleClass}" style="margin: 8px 0;">
                                    <div class="chat-label">${icon} ${role} <span style="color: #8b949e; font-weight: normal; font-size: 11px;">[${timestamp}]</span></div>
                                    <div>${escapeHtml(msg.text)}</div>
                                </div>
                            `;
                        }).join('');
                        
                        return `
                            <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin: 10px 0;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #30363d;">
                                    <div>
                                        <div style="font-weight: bold; color: #58a6ff; font-size: 16px;">
                                            📞 Call ${index + 1}
                                        </div>
                                        <div style="color: #8b949e; font-size: 13px; margin-top: 4px;">
                                            ${escapeHtml(conv.phone)} • ${startTime}
                                        </div>
                                    </div>
                                    <div style="text-align: right;">
                                        <div style="color: #238636; font-weight: bold;">${duration}s</div>
                                        <div style="color: #8b949e; font-size: 12px;">${messageCount} messages</div>
                                    </div>
                                </div>
                                <div style="max-height: 300px; overflow-y: auto;">
                                    ${messagesHtml}
                                </div>
                            </div>
                        `;
                    }).join('');
                    
                    container.innerHTML = conversationsHtml;
                } else {
                    container.innerHTML = '<em style="color: #8b949e;">No completed conversations yet</em>';
                }
            } catch (error) {
                console.error('Error fetching conversations:', error);
                document.getElementById('conversationsContainer').innerHTML = 
                    `<span style="color: #da3633;">❌ Error loading conversations: ${error.message}</span>`;
            }
        }
        
        // Initialize
        connectWebSocket();
        initChart();
        refreshChart();
        refreshConversations();
        
        // Auto-refresh conversations every 30 seconds
        setInterval(refreshConversations, 30000);
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
