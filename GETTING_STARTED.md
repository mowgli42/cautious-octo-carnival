# Getting Started with Dapr Flight Tracker Demo

This guide walks you through setting up and running the Dapr demo step by step.

## What This Demo Shows

This demo demonstrates Dapr's core features:
1. **Pub/Sub** - Services communicate via publish/subscribe messaging
2. **State Store** - Services persist data using Dapr state management
3. **Service Invocation** - Services call each other via Dapr (coming soon)

## Architecture Overview

```
adsb-feeder (Node.js)
  └─> Publishes to "flight-update" topic
         │
         ├─> fleet-stats (Python) - Subscribes and aggregates statistics
         └─> (More subscribers coming...)
```

## Prerequisites

- Docker and Docker Compose installed
- Basic understanding of microservices

## Step 1: Understanding Dapr Components

Dapr uses component configuration files. We've created:
- `components/pubsub.yaml` - Redis Pub/Sub configuration
- `components/statestore.yaml` - Redis State Store configuration
- `components/filebinding.yaml` - Local file storage for bindings (future)
- `components/secrets.yaml` - Local secrets store (future)
- `config.yaml` - Dapr runtime configuration (Zipkin tracing)

## Step 2: Running the Demo

### Option A: Using Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Watch logs
docker-compose logs -f
```

### Option B: Running Locally (For Development)

First, start Redis:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

Then run each service with Dapr CLI:

**Terminal 1 - Feeder Service:**
```bash
cd services/adsb-feeder
npm install
dapr run --app-id adsb-feeder --app-port 3000 --dapr-http-port 3500 --components-path ../../components -- node index.js
```

**Terminal 2 - Fleet Stats Service:**
```bash
cd services/fleet-stats
pip install -r requirements.txt
dapr run --app-id fleet-stats --app-port 3001 --dapr-http-port 3501 --components-path ../../components -- python app.py
```

## Step 3: Verify It's Working

### Check Feeder Service
```bash
curl http://localhost:3000/health
```

You should see logs showing flight updates being published:
```
Published: DL100 @ 40.23, -75.45
✓ Published 25 flight updates to topic 'flight-update'
```

### Check Fleet Stats Service
```bash
# Health check
curl http://localhost:3001/health

# Get statistics
curl http://localhost:3001/api/v1/fleet/stats/summary
curl http://localhost:3001/api/v1/fleet/stats/by-airline
```

You should see the stats service receiving updates and aggregating data.

## Step 4: Understanding How It Works

### Feeder Service (Node.js)
- **Location:** `services/adsb-feeder/index.js`
- **What it does:** 
  - Generates mock flight data (in mock mode)
  - Publishes to Dapr Pub/Sub using the Dapr JavaScript SDK
  - Uses: `daprClient.pubsub.publish()`

### Fleet Stats Service (Python)
- **Location:** `services/fleet-stats/app.py`
- **What it does:**
  - Subscribes to `flight-update` topic
  - Aggregates statistics by airline
  - Saves stats to Dapr State Store
  - Exposes REST API for querying stats

### Key Dapr Concepts Demonstrated

1. **Pub/Sub Decoupling**
   - Feeder doesn't know about subscribers
   - Subscribers don't know about the publisher
   - All communication goes through Dapr

2. **State Management**
   - Stats are persisted to Redis via Dapr
   - On restart, stats are reloaded automatically
   - No direct database connection needed

## Next Steps

Once this is working, we'll add:
1. Airport tracker service (Go)
2. Dashboard service (Svelte) using Service Invocation
3. Archiver service (Python) with Output Bindings
4. Emergency alert service (Python) with web UI

## Troubleshooting

### Services can't connect to Dapr sidecar
- Make sure Dapr placement service is running
- Check that ports 3500, 3501, etc. are not in use
- Verify Docker Compose sidecar has `network_mode: service:<app-name>`
- Ensure app container exposes Dapr HTTP port

### No messages being received
- Check Redis is running: `docker ps | grep redis`
- Verify Pub/Sub component config in `components/pubsub.yaml`
- Check subscription YAML routes match POST endpoint paths
- Verify subscription includes service in `scopes`
- Check Dapr logs: `dapr logs --app-id fleet-stats`

### State not persisting
- Verify State Store component config in `components/statestore.yaml`
- Check Redis is running and accessible
- Verify DaprClient initialization uses correct parameters for SDK version

### Service Invocation failing
- Use Dapr HTTP API directly: `http://localhost:<DAPR_PORT>/v1.0/invoke/<app-id>/method/<path>`
- If using SDK, verify method parameter format matches SDK version
- Check sidecar is ready before making calls

### Component initialization errors
- Ensure `secrets/secrets.json` exists (can be empty `{}`)
- Verify data volumes are mounted to sidecar
- Check component YAML files reference valid paths

**For detailed troubleshooting and best practices, see [DAPR_LESSONS_LEARNED.md](../DAPR_LESSONS_LEARNED.md)**

