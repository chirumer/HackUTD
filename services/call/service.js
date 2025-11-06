const express = require('express');
const dotenv = require('dotenv');
const path = require('path');
const bodyParser = require('body-parser');
const cors = require('cors');
const http = require('http');
const { WebSocketServer } = require('ws');
const twilio = require('twilio');
const axios = require('axios');
const localtunnel = require('localtunnel');
const { spawn } = require('child_process');

// Load environment variables
dotenv.config({ path: path.join(__dirname, '.env') });

const PORT = process.env.PORT || 8003;
const SERVICE_NAME = process.env.SERVICE_NAME || 'call';
const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_NUMBER = process.env.TWILIO_NUMBER;
const HANDLER_URL = process.env.HANDLER_URL || 'http://localhost:8012';
const VOICE_URL = process.env.VOICE_URL || 'http://localhost:8001';
const LOCALTUNNEL_SUBDOMAIN = process.env.LOCALTUNNEL_SUBDOMAIN || '';

if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_NUMBER) {
  console.error('ERROR: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_NUMBER must be set in .env');
  process.exit(1);
}

const { twiml: Twiml } = twilio;
const twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

const app = express();
const server = http.createServer(app);

// Enable CORS
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:3001', 'http://localhost:8014'],
  credentials: true
}));

app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

// In-memory storage for active calls
const activeCalls = new Map();
const activeWebSockets = new Map(); // Store WebSocket references by callSid

// Call metrics
const callMetrics = {
  totalCalls: 0,
  answeredCalls: 0,
  completedCalls: 0,
  failedCalls: 0,
  userHangups: 0,
  systemHangups: 0,
  totalDuration: 0,
  averageDuration: 0,
  transcriptionSuccess: 0,
  transcriptionFailed: 0
};

// Log storage (keep last 200 logs)
const logBuffer = [];
const MAX_LOGS = 200;

// Logger
function log(level, message, extra = {}) {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    service: SERVICE_NAME,
    level,
    message,
    ...extra
  };
  
  // Add to buffer
  logBuffer.push(logEntry);
  if (logBuffer.length > MAX_LOGS) {
    logBuffer.shift(); // Remove oldest
  }
  
  // Also console log
  console.log(`${timestamp} | ${SERVICE_NAME} | ${level} | ${message}`, extra);
}

// Update metrics
function updateMetrics(metricName, value = 1) {
  if (metricName in callMetrics) {
    if (metricName === 'totalDuration' || metricName === 'averageDuration') {
      callMetrics[metricName] = value;
    } else {
      callMetrics[metricName] += value;
    }
  }
}

// Calculate average call duration
function calculateAverageDuration() {
  if (callMetrics.completedCalls > 0) {
    callMetrics.averageDuration = callMetrics.totalDuration / callMetrics.completedCalls;
  }
}

// Function to update Twilio webhook using Python script
function updateTwilioWebhook(webhookUrl) {
  const scriptPath = path.join(__dirname, 'scripts', 'change_webhook.py');
  
  log('INFO', `🔄 Updating Twilio webhook to: ${webhookUrl}`);
  
  const pythonProcess = spawn('python3', [scriptPath, '--url', webhookUrl], {
    cwd: path.join(__dirname, 'scripts'),
    env: process.env
  });
  
  let output = '';
  let errorOutput = '';
  
  pythonProcess.stdout.on('data', (data) => {
    output += data.toString();
  });
  
  pythonProcess.stderr.on('data', (data) => {
    errorOutput += data.toString();
  });
  
  pythonProcess.on('close', (code) => {
    if (code === 0) {
      log('INFO', `✅ Twilio webhook updated successfully`);
      console.log('\n' + '='.repeat(80));
      console.log('✅ TWILIO WEBHOOK AUTOMATICALLY UPDATED!');
      console.log('='.repeat(80));
      console.log(output.trim());
      console.log('='.repeat(80) + '\n');
    } else {
      log('ERROR', `❌ Failed to update Twilio webhook (exit code: ${code})`);
      if (errorOutput) {
        console.error('Error output:', errorOutput);
      }
      console.log('\n⚠️  You may need to manually update the Twilio webhook URL.\n');
    }
  });
  
  pythonProcess.on('error', (err) => {
    log('ERROR', `Failed to run webhook update script: ${err.message}`);
    console.log('\n⚠️  Could not automatically update Twilio webhook.');
    console.log('Please run manually:');
    console.log(`cd scripts && python3 change_webhook.py --url ${webhookUrl}\n`);
  });
}

// Public URL (will be set by localtunnel)
let PUBLIC_URL = `http://localhost:${PORT}`;

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: SERVICE_NAME });
});

app.get('/healthz', (req, res) => {
  res.send('ok');
});

// Get public URL
app.get('/public-url', (req, res) => {
  res.json({ url: PUBLIC_URL });
});

// Get call metrics
app.get('/metrics', (req, res) => {
  res.json({
    totalCalls: callMetrics.totalCalls,
    answeredCalls: callMetrics.answeredCalls,
    completedCalls: callMetrics.completedCalls,
    userHangups: callMetrics.userHangups,
    systemHangups: callMetrics.systemHangups,
    activeCalls: activeCalls.size,
    totalDuration: `${callMetrics.totalDuration.toFixed(2)}s`,
    averageDuration: `${callMetrics.averageDuration.toFixed(2)}s`,
    transcriptionSuccess: callMetrics.transcriptionSuccess,
    transcriptionFailed: callMetrics.transcriptionFailed,
    successRate: callMetrics.totalCalls > 0 
      ? `${((callMetrics.transcriptionSuccess / callMetrics.totalCalls) * 100).toFixed(1)}%` 
      : '0%'
  });
});

// Get logs
app.get('/logs', (req, res) => {
  const limit = parseInt(req.query.limit) || 100;
  const logs = logBuffer.slice(-limit).reverse(); // Most recent first
  res.json(logs);
});

// TwiML Voice webhook - called when a call comes in
app.post('/voice-webhook', (req, res) => {
  const callerPhone = req.body.From || req.body.Caller || 'unknown';
  const callSid = req.body.CallSid || 'unknown';
  
  updateMetrics('totalCalls');
  
  log('INFO', `📞 [CALL RECEIVED] Incoming call from: ${callerPhone}`, { 
    phone: callerPhone, 
    callSid: callSid,
    totalCalls: callMetrics.totalCalls
  });
  
  // Store call info
  activeCalls.set(callSid, {
    phone: callerPhone,
    callSid: callSid,
    startedAt: Date.now(),
    answeredAt: null,
    endedAt: null,
    transcript: '',
    partials: [],
    endReason: null
  });
  
  updateMetrics('answeredCalls');
  
  const response = new Twiml.VoiceResponse();
  
  // Greet the caller
  response.say({ voice: 'alice' }, 'Welcome to Bank Assist. Please tell us how we can help you today.');
  
  log('INFO', `✅ [CALL ANSWERED] Call ${callSid} answered and greeting played`, {
    callSid: callSid,
    phone: callerPhone
  });
  
  // Connect to WebSocket for live transcription
  const connect = response.connect();
  const stream = connect.stream({
    url: `${PUBLIC_URL.replace('https', 'wss').replace('http', 'ws')}/media-stream`,
    statusCallback: `${PUBLIC_URL}/stream-status`
  });
  
  // Pass metadata to WebSocket
  stream.parameter({ name: 'callSid', value: callSid });
  stream.parameter({ name: 'callerPhone', value: callerPhone });
  
  res.type('text/xml').send(response.toString());
});

// Stream status callback
app.post('/stream-status', (req, res) => {
  const status = req.body.StreamStatus;
  const sid = req.body.StreamSid;
  const callSid = req.body.CallSid;
  
  log('INFO', `[STREAM STATUS] ${status}`, { 
    streamSid: sid, 
    callSid: callSid 
  });
  
  if (status === 'closed') {
    log('INFO', '[STREAM STATUS] Stream closed', { details: req.body });
  }
  
  res.sendStatus(200);
});

// WebSocket server for Twilio Media Streams
const wss = new WebSocketServer({ 
  server, 
  path: '/media-stream',
  clientTracking: true,
  perMessageDeflate: false,
  maxPayload: 100 * 1024 * 1024 // 100MB
});

wss.on('connection', (ws, req) => {
  log('INFO', '[WS] Twilio connected to /media-stream');
  
  let callSid = null;
  let callerPhone = null;
  let streamSid = null;
  let voiceWs = null;
  let fullTranscript = '';
  let currentSentence = '';
  
  // Set up ping/pong for connection health
  ws.isAlive = true;
  ws.on('pong', () => {
    ws.isAlive = true;
  });
  
  // Convert Twilio's mulaw audio to PCM16
  const mulawToPcm = (mulawBuffer) => {
    const mulawToLinear = [
      -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
      -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
      -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
      -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
      -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
      -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
      -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
      -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
      -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
      -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
      -876, -844, -812, -780, -748, -716, -684, -652,
      -620, -588, -556, -524, -492, -460, -428, -396,
      -372, -356, -340, -324, -308, -292, -276, -260,
      -244, -228, -212, -196, -180, -164, -148, -132,
      -120, -112, -104, -96, -88, -80, -72, -64,
      -56, -48, -40, -32, -24, -16, -8, 0,
      32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
      23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
      15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
      11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
      7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
      5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
      3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
      2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
      1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
      1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
      876, 844, 812, 780, 748, 716, 684, 652,
      620, 588, 556, 524, 492, 460, 428, 396,
      372, 356, 340, 324, 308, 292, 276, 260,
      244, 228, 212, 196, 180, 164, 148, 132,
      120, 112, 104, 96, 88, 80, 72, 64,
      56, 48, 40, 32, 24, 16, 8, 0
    ];

    const pcmBuffer = Buffer.alloc(mulawBuffer.length * 2);
    for (let i = 0; i < mulawBuffer.length; i++) {
      const sample = mulawToLinear[mulawBuffer[i]];
      pcmBuffer.writeInt16LE(sample, i * 2);
    }
    return pcmBuffer;
  };

  // Resample from 8kHz to 16kHz (simple linear interpolation)
  const resample8to16 = (pcm8k) => {
    // pcm8k is PCM16 at 8kHz (2 bytes per sample)
    const numSamples8k = pcm8k.length / 2;
    const numSamples16k = numSamples8k * 2;
    const pcm16k = Buffer.alloc(numSamples16k * 2);
    
    for (let i = 0; i < numSamples8k - 1; i++) {
      const sample1 = pcm8k.readInt16LE(i * 2);
      const sample2 = pcm8k.readInt16LE((i + 1) * 2);
      
      // Write original sample
      pcm16k.writeInt16LE(sample1, i * 4);
      
      // Interpolate intermediate sample
      const interpolated = Math.floor((sample1 + sample2) / 2);
      pcm16k.writeInt16LE(interpolated, i * 4 + 2);
    }
    
    // Handle last sample
    const lastSample = pcm8k.readInt16LE((numSamples8k - 1) * 2);
    pcm16k.writeInt16LE(lastSample, (numSamples8k - 1) * 4);
    pcm16k.writeInt16LE(lastSample, (numSamples8k - 1) * 4 + 2);
    
    return pcm16k;
  };

  // Connect to handler service for live transcription (handler connects to voice service)
  const connectToVoiceService = () => {
    try {
      const WebSocket = require('ws');
      const handlerWsUrl = HANDLER_URL.replace('http', 'ws') + '/call/stream';
      
      log('INFO', `[WS] Connecting to handler service: ${handlerWsUrl}`);
      voiceWs = new WebSocket(handlerWsUrl);
      
      voiceWs.on('open', () => {
        log('INFO', '[WS] Connected to handler service for live transcription');
        
        // Send start message with call metadata
        voiceWs.send(JSON.stringify({
          type: 'start',
          call_sid: callSid,
          phone: callerPhone
        }));
        
        // Store voice WebSocket reference
        const wsRefs = activeWebSockets.get(callSid);
        if (wsRefs) {
          wsRefs.voiceWs = voiceWs;
        }
      });
      
      voiceWs.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          
          if (message.type === 'partial') {
            // Partial transcription from handler (handler already logged it)
            if (activeCalls.has(callSid)) {
              const call = activeCalls.get(callSid);
              call.partials.push({
                timestamp: Date.now(),
                text: message.text
              });
            }
            
            currentSentence = message.text;
          } 
          else if (message.type === 'final') {
            // Complete sentence detected (handler already logged it)
            fullTranscript += message.text + ' ';
            
            if (activeCalls.has(callSid)) {
              const call = activeCalls.get(callSid);
              call.transcript = fullTranscript.trim();
            }
            
            // Forward to handler service for intent processing
            forwardToHandler(callSid, callerPhone, message.text);
            
            // End the call after receiving a complete sentence
            setTimeout(() => {
              endCallGracefully(callSid, fullTranscript.trim());
            }, 1000);
          }
        } catch (err) {
          log('ERROR', '[WS] Error processing handler service message', { error: err.message });
        }
      });
      
      voiceWs.on('error', (err) => {
        log('ERROR', '[WS] Handler service error', { error: err.message });
      });
      
      voiceWs.on('close', () => {
        log('INFO', '[WS] Handler service connection closed');
      });
    } catch (err) {
      log('ERROR', '[WS] Failed to connect to handler service', { error: err.message });
    }
  };
  
  // Forward completed sentence to handler service
  const forwardToHandler = async (callSid, phone, text) => {
    try {
      log('INFO', `[HANDLER] Forwarding sentence to handler`, { 
        callSid: callSid,
        phone: phone,
        text: text 
      });
      
      const response = await axios.post(`${HANDLER_URL}/handle`, {
        phone: phone,
        account_id: phone, // Using phone as account_id for now
        text: text,
        verified: false
      });
      
      log('INFO', `[HANDLER] Response received`, { 
        reply: response.data.reply 
      });
      
      // Optionally speak the response back to the caller
      // (This would require additional Twilio TTS integration)
      
    } catch (err) {
      log('ERROR', '[HANDLER] Failed to forward to handler', { 
        error: err.message,
        status: err.response?.status,
        data: err.response?.data,
        stack: err.stack
      });
    }
  };  // End call gracefully
  const endCallGracefully = async (callSid, transcript, reason = 'system') => {
    try {
      const call = activeCalls.get(callSid);
      const duration = call ? (Date.now() - call.startedAt) / 1000 : 0;
      
      log('INFO', `🔴 [CALL ENDING] Initiating call end`, { 
        callSid: callSid,
        transcript: transcript,
        reason: reason,
        duration: `${duration.toFixed(2)}s`
      });
      
      // Update call record
      if (call) {
        call.endedAt = Date.now();
        call.endReason = reason;
        call.transcript = transcript;
      }
      
      // Get WebSocket references for this call
      const wsRefs = activeWebSockets.get(callSid);
      
      // Notify handler service - using query params for FastAPI
      try {
        const url = `${HANDLER_URL}/call/end?call_id=${encodeURIComponent(callSid)}&transcript=${encodeURIComponent(transcript || '')}`;
        await axios.post(url);
        log('INFO', `[CALL] Handler notified of call end`, { callSid: callSid });
      } catch (handlerErr) {
        log('ERROR', '[CALL] Failed to notify handler', { 
          error: handlerErr.message,
          status: handlerErr.response?.status,
          data: handlerErr.response?.data
        });
      }
      
      // End the Twilio call using the API
      try {
        const twilioCall = await twilioClient.calls(callSid).update({ status: 'completed' });
        
        // Update metrics
        updateMetrics('completedCalls');
        if (reason === 'user') {
          updateMetrics('userHangups');
        } else {
          updateMetrics('systemHangups');
        }
        
        // Track duration
        if (duration > 0) {
          callMetrics.totalDuration += duration;
          calculateAverageDuration();
        }
        
        // Track transcription success
        if (transcript && transcript.length > 0) {
          updateMetrics('transcriptionSuccess');
        } else {
          updateMetrics('transcriptionFailed');
        }
        
        log('INFO', `✅ [CALL ENDED] Call completed successfully`, { 
          callSid: callSid,
          status: twilioCall.status,
          reason: reason,
          duration: `${duration.toFixed(2)}s`,
          transcriptLength: transcript ? transcript.length : 0,
          metrics: {
            total: callMetrics.totalCalls,
            completed: callMetrics.completedCalls,
            avgDuration: `${callMetrics.averageDuration.toFixed(2)}s`
          }
        });
      } catch (twilioErr) {
        log('ERROR', `[CALL] Failed to end Twilio call via API`, { 
          error: twilioErr.message,
          code: twilioErr.code
        });
      }
      
      // Clean up WebSocket connections
      if (wsRefs) {
        if (wsRefs.voiceWs && wsRefs.voiceWs.readyState === 1) {
          // Send stop message before closing
          try {
            wsRefs.voiceWs.send(JSON.stringify({ type: 'stop' }));
          } catch (e) {
            // Ignore if already closed
          }
          wsRefs.voiceWs.close();
          log('INFO', '[CALL] Handler WebSocket closed', { callSid: callSid });
        }
        if (wsRefs.twilioWs && wsRefs.twilioWs.readyState === 1) {
          wsRefs.twilioWs.close();
          log('INFO', '[CALL] Twilio WebSocket closed', { callSid: callSid });
        }
        activeWebSockets.delete(callSid);
      }
      
      // Remove from active calls
      activeCalls.delete(callSid);
      
    } catch (err) {
      log('ERROR', '[CALL] Failed to end call gracefully', { 
        error: err.message,
        status: err.response?.status,
        data: err.response?.data,
        stack: err.stack
      });
    }
  };
  
  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data.toString());
      
      if (message.event === 'start') {
        // Stream started
        streamSid = message.streamSid;
        callSid = message.start.callSid;
        callerPhone = message.start.customParameters?.callerPhone || 'unknown';
        
        log('INFO', '[WS] Stream started', { 
          streamSid: streamSid,
          callSid: callSid,
          phone: callerPhone 
        });
        
        // Store WebSocket references for this call
        activeWebSockets.set(callSid, {
          twilioWs: ws,
          voiceWs: null // Will be set when voice service connects
        });
        
        // Connect to voice service
        connectToVoiceService();
      } 
      else if (message.event === 'media') {
        // Twilio sends mulaw encoded audio at 8kHz, base64 encoded
        // We need to decode, convert to PCM16, and resample to 16kHz for Azure
        if (voiceWs && voiceWs.readyState === 1 && message.media?.payload) {
          try {
            // Decode base64 mulaw audio (8kHz)
            const mulawBuffer = Buffer.from(message.media.payload, 'base64');
            
            // Convert mulaw to PCM16 (still 8kHz)
            const pcm8k = mulawToPcm(mulawBuffer);
            
            // Resample from 8kHz to 16kHz
            const pcm16k = resample8to16(pcm8k);
            
            // Send PCM16 @ 16kHz audio to voice service
            voiceWs.send(pcm16k);
          } catch (err) {
            log('ERROR', '[WS] Error processing audio', { error: err.message });
          }
        }
      } 
      else if (message.event === 'stop') {
        log('INFO', '[WS] Stream stopped', { callSid: callSid });
        
        if (voiceWs) {
          voiceWs.close();
        }
      }
    } catch (err) {
      log('ERROR', '[WS] Error processing message', { error: err.message });
    }
  });
  
  ws.on('close', () => {
    log('INFO', '[WS] Twilio connection closed', { callSid: callSid });
    
    // Clean up voice WebSocket
    if (voiceWs) {
      voiceWs.close();
    }
    
    // Clean up stored references
    activeWebSockets.delete(callSid);
    activeCalls.delete(callSid);
  });
  
  ws.on('error', (err) => {
    log('ERROR', '[WS] WebSocket error', { error: err.message });
  });
});

// WebSocket health check
const wsHealthCheck = setInterval(() => {
  wss.clients.forEach((ws) => {
    if (ws.isAlive === false) {
      log('INFO', '[WS] Terminating inactive connection');
      return ws.terminate();
    }
    ws.isAlive = false;
    ws.ping();
  });
}, 30000);

wss.on('close', () => {
  clearInterval(wsHealthCheck);
});

// API endpoints for compatibility

app.get('/active', (req, res) => {
  const calls = Array.from(activeCalls.values()).map(call => ({
    call_id: call.callSid,
    phone: call.phone,
    started_at: call.startedAt / 1000,
    transcript: call.transcript,
    partials_count: call.partials.length
  }));
  
  res.json(calls);
});

app.get('/call/:callSid', (req, res) => {
  const call = activeCalls.get(req.params.callSid);
  
  if (!call) {
    return res.status(404).json({ error: 'Call not found' });
  }
  
  res.json({
    call_id: call.callSid,
    phone: call.phone,
    started_at: call.startedAt / 1000,
    transcript: call.transcript,
    partials: call.partials
  });
});

// Start server
server.listen(PORT, async () => {
  log('INFO', `HTTP+WS listening on :${PORT}`);
  log('INFO', `TwiML webhook: POST ${PUBLIC_URL}/voice-webhook`);
  log('INFO', `WSS endpoint: ${PUBLIC_URL.replace('http', 'ws')}/media-stream`);
  
  // Set up localtunnel for public access
  try {
    const tunnelOptions = { 
      port: PORT,
      host: 'https://localtunnel.me'
    };
    
    if (LOCALTUNNEL_SUBDOMAIN) {
      tunnelOptions.subdomain = LOCALTUNNEL_SUBDOMAIN;
    }
    
    const tunnel = await localtunnel(tunnelOptions);
    PUBLIC_URL = tunnel.url;
    
    console.log('\n' + '='.repeat(80));
    console.log('🌍 PUBLIC URL FOR TWILIO WEBHOOK:');
    console.log('');
    console.log(`   ${PUBLIC_URL}/voice-webhook`);
    console.log('');
    console.log('📞 Configure this URL in your Twilio phone number settings:');
    console.log('   1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming');
    console.log(`   2. Select your number: ${TWILIO_NUMBER}`);
    console.log('   3. Under "Voice Configuration", set:');
    console.log('      - A CALL COMES IN: Webhook');
    console.log(`      - URL: ${PUBLIC_URL}/voice-webhook`);
    console.log('      - HTTP: POST');
    console.log('');
    console.log('🎤 Test by calling your Twilio number!');
    console.log('='.repeat(80) + '\n');
    
    log('INFO', `LocalTunnel established: ${PUBLIC_URL}`);
    
    // Automatically update Twilio webhook
    updateTwilioWebhook(`${PUBLIC_URL}/voice-webhook`);
    
    tunnel.on('close', () => {
      log('WARNING', 'LocalTunnel closed');
    });
    
    tunnel.on('error', (err) => {
      log('ERROR', 'LocalTunnel error', { error: err.message });
    });
    
  } catch (err) {
    log('ERROR', 'Failed to establish LocalTunnel', { error: err.message });
    log('WARNING', `Using local URL: ${PUBLIC_URL}`);
    log('WARNING', 'You will need to manually expose this service for Twilio to access it');
  }
});

// Graceful shutdown
process.on('SIGTERM', () => {
  log('INFO', 'SIGTERM received, closing server gracefully');
  server.close(() => {
    log('INFO', 'Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  log('INFO', 'SIGINT received, closing server gracefully');
  server.close(() => {
    log('INFO', 'Server closed');
    process.exit(0);
  });
});
