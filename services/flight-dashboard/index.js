const express = require('express');
const http = require('http');

const app = express();
const PORT = process.env.PORT || 3002;
const DAPR_HTTP_PORT = process.env.DAPR_HTTP_PORT || 3502;

// Serve static files (frontend)
app.use(express.static('public'));

// Dapr Service Invocation endpoints
// These endpoints demonstrate calling fleet-stats via Dapr Service Invocation

// Helper function to call Dapr Service Invocation via HTTP API
// Format: http://localhost:<DAPR_HTTP_PORT>/v1.0/invoke/<APP_ID>/method/<METHOD_PATH>
function invokeDaprService(appId, methodPath, options = {}) {
  return new Promise((resolve, reject) => {
    const httpMethod = options.method || 'GET';
    const url = `/v1.0/invoke/${appId}/method/${methodPath}`;
    
    const req = http.request({
      hostname: '127.0.0.1',
      port: DAPR_HTTP_PORT,
      path: url,
      method: httpMethod,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      timeout: options.timeout || 5000 // 5 second timeout
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            resolve(data); // Return as-is if not JSON
          }
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    });
    
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });
    
    if (options.body) {
      req.write(JSON.stringify(options.body));
    }
    
    req.end();
  });
}

// Helper function to call Dapr Service Invocation with retry logic and exponential backoff
// This implements standard Dapr resilience patterns for handling transient failures
async function invokeDaprServiceWithRetry(appId, methodPath, options = {}) {
  const maxRetries = options.maxRetries || 3;
  const initialDelay = options.initialDelay || 100; // Start with 100ms
  const maxDelay = options.maxDelay || 2000; // Cap at 2 seconds
  
  let lastError;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await invokeDaprService(appId, methodPath, options);
    } catch (error) {
      lastError = error;
      
      // Don't retry on certain errors (e.g., 404, 400 - these are not transient)
      const errorMessage = error.message || '';
      if (errorMessage.includes('404') || errorMessage.includes('400')) {
        throw error; // Don't retry client errors
      }
      
      // If this is the last attempt, throw the error
      if (attempt === maxRetries - 1) {
        break;
      }
      
      // Calculate delay with exponential backoff
      const delay = Math.min(initialDelay * Math.pow(2, attempt), maxDelay);
      
      // Log retry attempt (only in development/debug mode)
      if (process.env.NODE_ENV !== 'production') {
        console.log(`⚠ Retrying Dapr service invocation (attempt ${attempt + 1}/${maxRetries}) after ${delay}ms: ${appId}/${methodPath}`);
      }
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  // All retries exhausted
  throw lastError;
}

// Proxy endpoint for fleet stats summary
app.get('/api/v1/fleet/stats/summary', async (req, res) => {
  try {
    // Use Dapr Service Invocation HTTP API with retry logic to call fleet-stats service
    // This calls: http://localhost:3502/v1.0/invoke/fleet-stats/method/api/v1/fleet/stats/summary
    const response = await invokeDaprServiceWithRetry(
      'fleet-stats',
      'api/v1/fleet/stats/summary',
      { method: 'GET' }
    );
    res.json(response);
  } catch (error) {
    console.error('Error calling fleet-stats via Dapr (all retries exhausted):', error);
    res.status(500).json({ 
      error: 'Failed to fetch fleet statistics',
      details: error.message 
    });
  }
});

// Proxy endpoint for fleet stats by airline
app.get('/api/v1/fleet/stats/by-airline', async (req, res) => {
  try {
    // Use Dapr Service Invocation HTTP API with retry logic to call fleet-stats service
    const response = await invokeDaprServiceWithRetry(
      'fleet-stats',
      'api/v1/fleet/stats/by-airline',
      { method: 'GET' }
    );
    res.json(response);
  } catch (error) {
    console.error('Error calling fleet-stats (all retries exhausted):', error);
    res.status(500).json({ 
      error: 'Failed to fetch airline statistics',
      details: error.message 
    });
  }
});

// Proxy endpoint for airport arrivals
app.get('/api/v1/airports/:code/arrivals', async (req, res) => {
  try {
    const airportCode = req.params.code;
    // Use Dapr Service Invocation HTTP API with retry logic to call airport-tracker service
    const response = await invokeDaprServiceWithRetry(
      'airport-tracker',
      `api/v1/airports/${airportCode}/arrivals`,
      { method: 'GET' }
    );
    res.json(response);
  } catch (error) {
    console.error('Error calling airport-tracker (all retries exhausted):', error);
    res.status(500).json({ 
      error: 'Failed to fetch airport arrivals',
      details: error.message 
    });
  }
});

// Proxy endpoint for airport list
app.get('/api/v1/airports', async (req, res) => {
  try {
    const response = await invokeDaprServiceWithRetry(
      'airport-tracker',
      'api/v1/airports',
      { method: 'GET' }
    );
    res.json(response);
  } catch (error) {
    console.error('Error calling airport-tracker (all retries exhausted):', error);
    res.status(500).json({ 
      error: 'Failed to fetch airports',
      details: error.message 
    });
  }
});

// Proxy endpoint for all flights
app.get('/api/v1/flights/all', async (req, res) => {
  try {
    const response = await invokeDaprServiceWithRetry(
      'airport-tracker',
      'api/v1/flights/all',
      { method: 'GET' }
    );
    res.json(response);
  } catch (error) {
    console.error('Error calling airport-tracker (all retries exhausted):', error);
    res.status(500).json({ 
      error: 'Failed to fetch all flights',
      details: error.message 
    });
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    service: 'flight-dashboard'
  });
});

// Dummy endpoint for /flight-update (dashboard doesn't subscribe, but Dapr may try to deliver)
// This prevents 404 errors in logs - the subscription scopes should prevent delivery, but
// adding this as a safety measure
app.post('/flight-update', (req, res) => {
  // Dashboard doesn't process flight updates - it uses Service Invocation instead
  res.status(200).json({ status: 'ok', note: 'Dashboard uses Service Invocation, not Pub/Sub' });
});

app.listen(PORT, () => {
  console.log(`🚀 Flight Dashboard service listening on port ${PORT}`);
  console.log(`📡 Dapr Service Invocation: Calling fleet-stats via Dapr HTTP API`);
  console.log(`   Format: http://localhost:${DAPR_HTTP_PORT}/v1.0/invoke/fleet-stats/method/<path>`);
  console.log(`🌐 Frontend available at http://localhost:${PORT}`);
});

