const express = require('express');
const dotenv = require('dotenv');
const path = require('path');

// Load environment variables
dotenv.config({ path: path.join(__dirname, '.env') });

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8004;
const SERVICE_NAME = process.env.SERVICE_NAME || 'llm';

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

// Simulated LLM Service
class OpenAIService {
  generateAnswer(question) {
    const simulations = [
      "Based on our records, I can help you with that. Let me pull up the relevant information.",
      "That's a great question. Here's what I found in our database.",
      "I understand your concern. Let me provide you with the most current information.",
      "According to our policies, here's how we handle that situation.",
      "I've analyzed your request and here's my recommendation."
    ];
    
    return simulations[Math.floor(Math.random() * simulations.length)];
  }
}

const llmService = new OpenAIService();

log('INFO', `LLM service starting up on port ${PORT}`);

// Health endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: SERVICE_NAME });
});

// Answer endpoint
app.post('/answer', (req, res) => {
  const startTime = Date.now();
  const { question, context = {} } = req.body;
  
  log('INFO', `Answering question: '${question.substring(0, 50)}...'`, { context_keys: Object.keys(context) });
  incrementCounter('questions_total');
  
  try {
    // Generate answer using LLM
    const answer = llmService.generateAnswer(question);
    
    const elapsed = (Date.now() - startTime) / 1000;
    recordTiming('answer_duration', elapsed);
    
    log('INFO', `Answer generated: '${answer.substring(0, 50)}...' (${elapsed.toFixed(2)}s)`, { duration: elapsed });
    
    res.json({
      answer,
      confidence: 0.85 + Math.random() * 0.1
    });
  } catch (error) {
    log('ERROR', `Question answering failed: ${error.message}`);
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
      answer_duration: filteredTimings.filter(t => t.name === 'answer_duration')
    }
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🤖 LLM service (Node.js) listening on port ${PORT}`);
  log('INFO', `LLM service ready on port ${PORT}`);
});
