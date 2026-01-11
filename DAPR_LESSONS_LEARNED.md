# Dapr Integration Lessons Learned

This document captures key lessons learned during Dapr integration, focusing on making Dapr connections straightforward and avoiding common pitfalls.

## Overview

While Dapr is designed to make distributed systems development easy, there were several configuration and SDK issues encountered that took longer than expected. This document summarizes those issues and the solutions that work reliably.

## Key Lessons

### 1. Use Dapr HTTP API Directly for Service Invocation

**Issue:** The `@dapr/dapr` Node.js SDK's `invoker.invoke()` method had confusing syntax and parameter requirements that led to errors.

**Solution:** Use Dapr's HTTP API directly, which is simpler and well-documented:

```javascript
// Instead of: daprClient.invoker.invoke(appId, methodName, options)
// Use direct HTTP API:
const response = await http.request({
  hostname: '127.0.0.1',
  port: DAPR_HTTP_PORT,
  path: `/v1.0/invoke/${appId}/method/${methodPath}`,
  method: 'GET'
});
```

**Reference:** [Dapr Service Invocation HTTP API](https://docs.dapr.io/reference/api/service_invocation_api/)

**Best Practice:** For new services, start with the HTTP API approach - it's straightforward, well-documented, and works consistently.

### 2. Python Dapr SDK: Use POST Endpoints for Subscriptions

**Issue:** The `dapr.ext.fastapi.DaprApp` decorator doesn't exist in current Dapr Python SDK versions.

**Solution:** Create a POST endpoint that Dapr will call when messages arrive:

```python
@app.post("/flight-update")
async def flight_update_handler(request: Request):
    body = await request.json()
    # Extract data from CloudEvents format
    if 'data' in body:
        flight = json.loads(body['data']) if isinstance(body['data'], str) else body['data']
    else:
        flight = body
    # Process the message
    return {"status": "success"}
```

**Configuration:** Create a subscription file in `components/subscription.yaml`:
```yaml
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: flight-update-subscription
spec:
  topic: flight-update
  routes:
    default: /flight-update
  pubsubname: pubsub
  scopes:
    - fleet-stats  # Only specific services subscribe
```

**Best Practice:** Always verify subscription endpoints are POST routes that match your subscription configuration.

### 3. Python DaprClient Initialization

**Issue:** `DaprClient` initialization parameters differ from documentation examples. Using `dapr_http_port` parameter caused errors.

**Solution:** Use correct initialization format:
```python
DAPR_HTTP_PORT = int(os.getenv("DAPR_HTTP_PORT", "3501"))
dapr_client = DaprClient(address="http://localhost", http_port=DAPR_HTTP_PORT)
```

**Best Practice:** Check the actual Dapr Python SDK version and use its documented initialization format.

### 4. Docker Compose Sidecar Network Configuration

**Issue:** Sidecar containers using `network_mode: service:<app-name>` couldn't resolve Redis hostname, causing connection failures.

**Solution:** Ensure both the app container and its sidecar can access required services:
- App container must be on `dapr-network` to reach Redis/placement
- Sidecar uses `network_mode: service:<app-name>` to share network namespace
- Both containers need `depends_on` for Redis and dapr-placement
- App container exposes Dapr HTTP port: `"3502:3502"` so sidecar can bind to it

**Best Practice:** Always include infrastructure services (Redis, dapr-placement) in `depends_on` for both app and sidecar containers.

### 5. Required Component Files Must Exist

**Issue:** Dapr sidecar fails if component configuration files reference files that don't exist:
- Secrets component expects `/secrets/secrets.json`
- File binding expects `/data` directory

**Solution:** 
- Create `secrets/secrets.json` file (can be empty `{}` for demo)
- Mount Docker volumes for data directories
- Ensure all component references are valid before starting services

**Best Practice:** Create a startup checklist that includes:
- [ ] `secrets/secrets.json` exists
- [ ] Data volumes created
- [ ] All component YAML files reference valid paths

### 6. Sidecar Readiness

**Issue:** Applications trying to use Dapr immediately on startup fail because sidecar isn't ready yet.

**Solution:** 
- **Standard Dapr Practice**: Don't wait for sidecar explicitly - just make calls and handle errors
- For HTTP API approach: Make HTTP requests, handle connection errors gracefully with retries
- For SDK approach: Initialize SDK normally, handle errors with retry logic
- Dapr sidecar waits for app to be ready before routing messages TO the app
- **Do NOT use SDK readiness methods** (like `WaitForSidecarAsync`) unless you need Dapr at startup for secrets/config

**Best Practice:** 
- Use HTTP API directly (recommended) or SDK with error handling
- Implement retry logic with exponential backoff for transient failures
- Don't use SDK readiness methods - they're not recommended for general service communication
- Our approach (direct HTTP calls, error handling) is aligned with standard Dapr practices

**Note:** See `DAPR_SIDECAR_READINESS.md` for detailed explanation of why SDK readiness methods are discouraged.

### 7. Component Configuration Consistency

**Issue:** Component configurations must match between:
- Component YAML files
- Subscription YAML files  
- Service application code

**Solution:** Use consistent naming:
- Component name: `pubsub` (matches `pubsubname` in subscriptions)
- Topic name: `flight-update` (matches across all services)
- State store name: `statestore` (used in code)

**Best Practice:** Define component names once and reference them consistently across all services.

## Recommended Patterns

### Node.js Service with Dapr (Pub/Sub)

```javascript
const { DaprClient } = require('@dapr/dapr');

const daprClient = new DaprClient({
  daprHost: 'localhost',
  daprPort: process.env.DAPR_HTTP_PORT || '3500'
});

// Publish - SDK works well
await daprClient.pubsub.publish('pubsub', 'flight-update', data);
```

### Node.js Service with Dapr (Service Invocation)

```javascript
const http = require('http');

// Use HTTP API directly - simpler and more reliable
function invokeService(appId, methodPath, options = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: '127.0.0.1',
      port: DAPR_HTTP_PORT,
      path: `/v1.0/invoke/${appId}/method/${methodPath}`,
      method: options.method || 'GET',
      headers: { 'Content-Type': 'application/json' }
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => resolve(JSON.parse(data)));
    });
    req.on('error', reject);
    if (options.body) req.write(JSON.stringify(options.body));
    req.end();
  });
}
```

### Python Service with Dapr (Pub/Sub)

```python
from fastapi import FastAPI, Request
from dapr.clients import DaprClient

app = FastAPI()

# Initialize Dapr client
dapr_client = DaprClient(address="http://localhost", http_port=3501)

# Subscription endpoint (POST, not decorator)
@app.post("/flight-update")
async def handler(request: Request):
    body = await request.json()
    data = json.loads(body['data']) if isinstance(body['data'], str) else body['data']
    # Process message
    return {"status": "success"}
```

### Python Service with Dapr (State Store)

```python
# Save state
dapr_client.save_state(
    store_name='statestore',
    key='fleet:stats:summary',
    value=json.dumps(stats).encode('utf-8')
)

# Load state
response = dapr_client.get_state(store_name='statestore', key='fleet:stats:summary')
if response.data:
    stats = json.loads(response.data.decode('utf-8'))
```

## Docker Compose Checklist

When adding a new service with Dapr:

- [ ] Service container exposes both app port and Dapr HTTP port
- [ ] Sidecar uses `network_mode: service:<app-name>`
- [ ] Sidecar has `depends_on` for app container, Redis, and dapr-placement
- [ ] Sidecar mounts `./components:/components` volume
- [ ] Sidecar mounts `./secrets:/secrets:ro` volume (if using secrets)
- [ ] Sidecar mounts `data-volume:/data` volume (if using file bindings)
- [ ] App container is on `dapr-network`
- [ ] Component files exist and are valid YAML
- [ ] Subscription YAML includes service in `scopes` if subscribing

## Common Pitfalls to Avoid

1. **Don't use SDK `invoker.invoke()` syntax without verifying exact parameter format** - Use HTTP API instead
2. **Don't use `dapr.ext.fastapi` decorators** - Create POST endpoints manually
3. **Don't forget component file prerequisites** - Secrets files and data directories must exist
4. **Don't assume sidecar is ready immediately** - Implement proper startup sequencing
5. **Don't mix network modes** - Use `network_mode: service:<app>` consistently for sidecars
6. **Don't hardcode Dapr ports** - Use environment variables

## References

- [Dapr Service Invocation API](https://docs.dapr.io/reference/api/service_invocation_api/)
- [Dapr Pub/Sub API](https://docs.dapr.io/reference/api/pubsub_api/)
- [Dapr State Management API](https://docs.dapr.io/reference/api/state_api/)
- [Dapr Python SDK Documentation](https://docs.dapr.io/developing-applications/sdks/python/)
- [Dapr JavaScript SDK Documentation](https://docs.dapr.io/developing-applications/sdks/js/)

## Summary

**Key Takeaway:** While Dapr SDKs provide convenience, the HTTP API approach is often simpler, more reliable, and easier to understand. For new services, consider starting with HTTP API calls and only use SDKs when they provide clear value.

