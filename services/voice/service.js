const express = require('express');
const dotenv = require('dotenv');
const path = require('path');

// Load environment variables
dotenv.config({ path: path.join(__dirname, '.env') });

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8001;
const SERVICE_NAME = process.env.SERVICE_NAME || 'voice';

// In-memory log buffer for dashboard
const logBuffer = [];
const MAX_LOG_BUFFER = 100;

// Metrics storage
const metrics = {
  counters: {},
  gauges: {},
  timings: []
};

// Logger functions
function log(level, message, extra = {}) {
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    service: SERVICE_NAME,
    message,
    extra
  };
  
  logBuffer.push(entry);
  if (logBuffer.length > MAX_LOG_BUFFER) {
    logBuffer.shift();
  }
  
  console.log(`${entry.timestamp} | ${SERVICE_NAME} | ${level} | ${message}`);
}

// Metrics functions
function incrementCounter(name, value = 1) {
  if (!metrics.counters[name]) {
    metrics.counters[name] = 0;
  }
  metrics.counters[name] += value;
}

function setGauge(name, value) {
  metrics.gauges[name] = value;
}

function recordTiming(name, duration) {
  metrics.timings.push({
    name,
    timestamp: Date.now() / 1000,
    value: duration
  });
  
  // Keep only last 1000 timing entries
  if (metrics.timings.length > 1000) {
    metrics.timings = metrics.timings.slice(-1000);
  }
}

// Simulated Azure Voice Service
class AzureVoiceService {
  transcribe(audioData) {
    // Simulate transcription
    const transcripts = [
      "Hello, can you help me?",
      "What's my balance?",
      "Transfer 50 to Bob",
      "Show me my last transactions"
    ];
    return transcripts[Math.floor(Math.random() * transcripts.length)];
  }
  
  synthesize(text) {
    // Simulate audio generation
    const fakeAudio = Buffer.from(`SIMULATED_AUDIO_FOR: ${text}`);
    return {
      content: fakeAudio,
      format: 'wav'
    };
  }
}

const voiceService = new AzureVoiceService();

log('INFO', `Voice service starting up on port ${PORT}`);

// Health endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: SERVICE_NAME });
});

// Transcribe endpoint (STT)
app.post('/transcribe', (req, res) => {
  const startTime = Date.now();
  const { audio_bytes, format = 'wav' } = req.body;
  
  log('INFO', `Transcribing audio (${format} format)`);
  incrementCounter('transcriptions_total');
  
  try {
    // Decode base64 audio
    const audioBuffer = Buffer.from(audio_bytes, 'base64');
    log('DEBUG', `Decoded ${audioBuffer.length} bytes of audio`);
    
    // Perform transcription
    const transcript = voiceService.transcribe(audioBuffer);
    
    const elapsed = (Date.now() - startTime) / 1000;
    recordTiming('transcription_duration', elapsed);
    
    log('INFO', `Transcription complete: '${transcript.substring(0, 50)}...' (${elapsed.toFixed(2)}s)`, { duration: elapsed });
    
    res.json({ transcript });
  } catch (error) {
    log('ERROR', `Transcription failed: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

// Synthesize endpoint (TTS)
app.post('/synthesize', (req, res) => {
  const startTime = Date.now();
  const { text } = req.body;
  
  log('INFO', `Synthesizing text: '${text.substring(0, 50)}...'`);
  incrementCounter('syntheses_total');
  
  try {
    // Perform synthesis
    const audio = voiceService.synthesize(text);
    const audioB64 = audio.content.toString('base64');
    
    const elapsed = (Date.now() - startTime) / 1000;
    recordTiming('synthesis_duration', elapsed);
    
    log('INFO', `Synthesis complete (${audio.content.length} bytes, ${elapsed.toFixed(2)}s)`, { duration: elapsed });
    
    res.json({
      audio_bytes: audioB64,
      format: audio.format
    });
  } catch (error) {
    log('ERROR', `Synthesis failed: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

// Logs endpoint
app.get('/logs', (req, res) => {
  const limit = parseInt(req.query.limit) || 100;
  const recentLogs = logBuffer.slice(-limit);
  res.json(recentLogs);
});

// Metrics endpoint
app.get('/metrics', (req, res) => {
  const periodMinutes = parseInt(req.query.period) || 60;
  const cutoffTime = (Date.now() / 1000) - (periodMinutes * 60);
  
  const filteredTimings = metrics.timings.filter(t => t.timestamp >= cutoffTime);
  
  res.json({
    service: SERVICE_NAME,
    timestamp: Date.now() / 1000,
    counters: metrics.counters,
    gauges: metrics.gauges,
    time_series: {
      transcription_duration: filteredTimings.filter(t => t.name === 'transcription_duration'),
      synthesis_duration: filteredTimings.filter(t => t.name === 'synthesis_duration')
    }
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🎤 Voice service (Node.js) listening on port ${PORT}`);
  log('INFO', `Voice service ready on port ${PORT}`);
});
