const express = require('express');
const dotenv = require('dotenv');
const path = require('path');
const { AzureOpenAI } = require('openai');

// Load environment variables
dotenv.config({ path: path.join(__dirname, '.env') });

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8004;
const SERVICE_NAME = process.env.SERVICE_NAME || 'llm';

// Azure OpenAI Configuration
const AZURE_OPENAI_API_KEY = process.env.AZURE_OPENAI_API_KEY;
const AZURE_OPENAI_ENDPOINT = process.env.AZURE_OPENAI_ENDPOINT;
const AZURE_OPENAI_DEPLOYMENT = process.env.AZURE_OPENAI_DEPLOYMENT;
const AZURE_OPENAI_API_VERSION = process.env.AZURE_OPENAI_API_VERSION || '2024-12-01-preview';

if (!AZURE_OPENAI_API_KEY || !AZURE_OPENAI_ENDPOINT || !AZURE_OPENAI_DEPLOYMENT) {
  console.error('ERROR: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT must be set in .env');
  process.exit(1);
}

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

// Azure OpenAI Service
class AzureOpenAIService {
  constructor() {
    this.client = new AzureOpenAI({
      apiKey: AZURE_OPENAI_API_KEY,
      endpoint: AZURE_OPENAI_ENDPOINT,
      apiVersion: AZURE_OPENAI_API_VERSION,
      deployment: AZURE_OPENAI_DEPLOYMENT
    });
    this.deployment = AZURE_OPENAI_DEPLOYMENT;
  }

  async generateAnswer(question, context = {}, conversationHistory = []) {
    const messages = [
      {
        role: 'system',
        content: 'You are a helpful banking assistant. Provide clear, concise answers to customer questions about their accounts and banking services.'
      }
    ];

    // Add context to system message if provided
    if (context && Object.keys(context).length > 0) {
      messages[0].content += `\n\nContext: ${JSON.stringify(context)}`;
    }

    // Add conversation history if provided
    if (conversationHistory && Array.isArray(conversationHistory) && conversationHistory.length > 0) {
      // Add all messages from conversation history
      messages.push(...conversationHistory);
    } else {
      // No history, just add the current question as a user message
      messages.push({
        role: 'user',
        content: question
      });
    }

    // Prepare request parameters
    const requestParams = {
      model: this.deployment,
      messages: messages,
      max_tokens: 150,
      temperature: 0.7,
    };

    // Log the full request
    log('INFO', '🔵 AZURE OPENAI API REQUEST', {
      request: JSON.stringify(requestParams, null, 2)
    });

    const result = await this.client.chat.completions.create(requestParams);

    // Log the full response
    log('INFO', '🟢 AZURE OPENAI API RESPONSE', {
      response: JSON.stringify({
        id: result.id,
        model: result.model,
        created: result.created,
        choices: result.choices,
        usage: result.usage,
        system_fingerprint: result.system_fingerprint
      }, null, 2)
    });

    return result.choices[0].message.content;
  }
}

const llmService = new AzureOpenAIService();

log('INFO', `LLM service starting up on port ${PORT} with Azure OpenAI`);
log('INFO', `Using deployment: ${AZURE_OPENAI_DEPLOYMENT}`);

// Health endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: SERVICE_NAME });
});

// Answer endpoint
app.post('/answer', async (req, res) => {
  const startTime = Date.now();
  const { question, context = {}, conversation_history = [] } = req.body;
  
  // Log what we received
  log('INFO', '=== LLM REQUEST RECEIVED ===');
  log('INFO', `Question: "${question}"`);
  log('INFO', `Conversation history length: ${conversation_history ? conversation_history.length : 0}`);
  if (conversation_history && conversation_history.length > 0) {
    log('INFO', 'Conversation history:');
    conversation_history.forEach((msg, idx) => {
      log('INFO', `  [${idx}] ${msg.role}: "${msg.content}"`);
    });
  } else {
    log('INFO', 'No conversation history provided');
  }
  log('INFO', '============================');
  
  // Validate question
  if (!question || typeof question !== 'string' || question.trim().length === 0) {
    log('ERROR', 'Empty or invalid question provided');
    return res.status(400).json({ error: 'Question is required and must be a non-empty string' });
  }
  
  log('INFO', `Answering question: '${question.substring(0, 50)}...'`, { context_keys: Object.keys(context) });
  incrementCounter('questions_total');
  
  try {
    // Generate answer using Azure OpenAI with conversation history
    const answer = await llmService.generateAnswer(question, context, conversation_history);
    
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
