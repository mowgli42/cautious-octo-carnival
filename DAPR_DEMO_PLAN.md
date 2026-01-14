# Dapr ADS-B Messaging Demo - Expanded Plan

## 1. Overview
This document outlines an expanded architecture for the ADS-B Dapr demo. The goal is to demonstrate the core value propositions of Dapr—polyglot microservices, consistent building blocks (State, Pub/Sub, Bindings, Secrets), and observability—to a executive audience.

## 2. Business Goal
Demonstrate how Dapr decouples infrastructure from application logic, allowing developers to focus on business features (flight tracking, alerting, analytics) while Dapr handles the complexity of distributed systems (state, messaging, resilience). Additionally, demonstrate Dapr's platform-agnostic nature by showing how the same code runs locally (Docker Compose) and in cloud environments (Kubernetes) without code changes.

## 3. Architecture Specification (OpenSpec Style)

### 3.1 Core Building Blocks Utilized
*   **Pub/Sub**: Decoupled event broadcasting (Flight positions). Topic: `flight-update`.
*   **State Management**: Consistent key-value storage for service state (Fleet counts) using Redis.
*   **Service Invocation**: Synchronous, secure inter-service HTTP/gRPC calls (Dashboard querying).
*   **Output Bindings**: Event-driven connection to external resources (Local file storage for archival).
*   **Secrets Management**: Secure access to sensitive config (API keys) using local file store.

### 3.1.2 Dapr Benefits vs Direct REST API Communication

This demo explicitly uses Dapr building blocks instead of direct REST API calls to demonstrate the value of Dapr's abstraction layer. Here's how each building block provides benefits over direct implementation:

#### Pub/Sub vs Direct HTTP Webhooks
**Without Dapr (Direct REST API approach):**
- Publisher must know all subscriber endpoints
- Tight coupling: adding subscribers requires code changes
- Need to implement retry logic, circuit breakers, dead letter queues
- Manual service discovery and health checking
- No built-in message ordering or at-least-once delivery guarantees

**With Dapr:**
- Publisher only knows topic name (`flight-update`)
- Loose coupling: subscribers register independently via subscription YAML
- Built-in retry, circuit breaker, and dead letter queue (configurable)
- Automatic service discovery via Dapr sidecar
- Message delivery guarantees handled by Dapr and underlying broker (Redis)
- **Alignment with Dapr Best Practice:** Topic-based pub/sub decouples producers and consumers - see [Dapr Pub/Sub documentation](https://docs.dapr.io/developing-applications/building-blocks/pubsub/pubsub-overview/)

**Example in our demo:**
- `adsb-feeder` publishes to `flight-update` topic without knowing who subscribes
- `fleet-stats`, `airport-tracker`, `flight-archiver`, `emergency-alert` subscribe independently
- Adding new subscribers requires no code changes to publisher

#### Service Invocation vs Direct HTTP Calls
**Without Dapr (Direct REST API approach):**
- Must hardcode service URLs or implement service discovery
- No automatic retry, timeout, or circuit breaker
- Must implement mTLS manually for secure communication
- Cross-service tracing requires manual correlation ID propagation
- Service location changes require code/config updates

**With Dapr:**
- Use service ID instead of URLs: `/v1.0/invoke/fleet-stats/method/api/v1/fleet/stats/summary`
- Automatic retry, timeout, and circuit breaker (configurable via policies)
- Automatic mTLS for secure communication (built into Dapr)
- Automatic distributed tracing with correlation IDs
- Service location abstracted - works locally and in cloud without code changes
- **Alignment with Dapr Best Practice:** Service-to-service invocation via app-id - see [Dapr Service Invocation documentation](https://docs.dapr.io/developing-applications/building-blocks/service-invocation/service-invocation-overview/)

**Example in our demo:**
- `flight-dashboard` calls `fleet-stats` via `/v1.0/invoke/fleet-stats/method/...`
- No hardcoded URLs - works in Docker Compose and Kubernetes
- Automatic retry logic handles transient failures
- Distributed tracing automatically included (Zipkin)

#### State Management vs Direct Database Access
**Without Dapr (Direct REST API/Database approach):**
- Services must know database connection strings
- Need to implement connection pooling, retry logic
- Must handle database failover and replication
- Tight coupling to specific database (Redis, PostgreSQL, etc.)
- Changes to database require code changes

**With Dapr:**
- Services use abstract state store name (`statestore`)
- Connection pooling and retry handled by Dapr
- Failover and replication handled by Dapr and underlying store
- Can switch state stores (Redis → Cosmos DB) with config change only
- **Alignment with Dapr Best Practice:** State store abstraction - see [Dapr State Management documentation](https://docs.dapr.io/developing-applications/building-blocks/state-management/state-management-overview/)

**Example in our demo:**
- `fleet-stats` uses `statestore` abstraction
- Currently Redis locally, can switch to Azure Cosmos DB or AWS DynamoDB in cloud
- No code changes required - only component YAML changes

#### Output Bindings vs Direct File System/Cloud SDK
**Without Dapr (Direct approach):**
- Must implement file system access or cloud SDK (AWS S3, Azure Blob)
- Need to handle retry, error handling, credentials
- Tight coupling to specific storage solution
- Changes require code changes

**With Dapr:**
- Use binding name (`filebinding`)
- Retry and error handling handled by Dapr
- Credentials via Dapr Secrets
- Can switch from local file → S3 → Azure Blob with config change only
- **Alignment with Dapr Best Practice:** Output bindings for external resources - see [Dapr Bindings documentation](https://docs.dapr.io/developing-applications/building-blocks/bindings/bindings-overview/)

**Example in our demo:**
- `flight-archiver` uses output binding abstraction
- Local file storage in demo, can switch to cloud storage in production
- No code changes - only component YAML changes

### 3.1.1 Flight Update Message Schema
The `flight-update` topic publishes events with the following JSON schema:
```json
{
  "icao24": "string",
  "callsign": "string",
  "origin_country": "string",
  "time_position": "integer",
  "last_contact": "integer",
  "longitude": "float",
  "latitude": "float",
  "baro_altitude": "float",
  "geo_altitude": "float",
  "on_ground": "boolean",
  "velocity": "float",
  "true_track": "float",
  "vertical_rate": "float",
  "squawk": "string",
  "spi": "boolean",
  "position_source": "integer",
  "timestamp": "integer"
}
```

### 3.2 Services Definition

#### A. Data Ingestion
**Service:** `adsb-feeder`
*   **Role**: Polls OpenSky Network API for live flight data (or generates mock data).
*   **Dapr Features**: 
    *   **Pub/Sub**: Publishes `flight-update` events to topic `flight-update`.
    *   **Secrets**: Retrieves OpenSky API credentials via Dapr Secret Store (local file).
*   **Language**: Node.js

#### B. Analytics & State
**Service:** `fleet-stats`
*   **Role**: Aggregates real-time statistics by airline, destination, origin, and aircraft type.
*   **Dapr Features**:
    *   **Pub/Sub**: Subscribes to `flight-update`.
    *   **State Store**: Persists running totals to Redis so data survives restarts.
*   **Dapr Best Practice Alignment:**
    *   Creates POST endpoint for Pub/Sub subscription (matches [Dapr Pub/Sub Python tutorial](https://docs.dapr.io/developing-applications/building-blocks/pubsub/howto-publish-subscribe/))
    *   Uses Python Dapr SDK `DaprClient` for state operations (matches [Dapr Python SDK examples](https://docs.dapr.io/developing-applications/sdks/python/))
    *   State store abstraction allows switching from Redis to cloud state stores
*   **API Endpoints**: 
    *   `GET /api/v1/fleet/stats/summary` - Overall statistics
    *   `GET /api/v1/fleet/stats/by-airline` - Statistics grouped by airline
    *   `GET /api/v1/fleet/stats/by-destination` - Statistics grouped by destination airport
    *   `GET /api/v1/fleet/stats/by-origin` - Statistics grouped by origin airport
    *   `GET /api/v1/fleet/stats/by-aircraft-type` - Statistics grouped by aircraft type
*   **Language**: Python

#### C. Geospatial Processing
**Service:** `airport-tracker`
*   **Role**: Identifies flights near key airports (geofencing) using configuration file.
*   **Dapr Features**:
    *   **Pub/Sub**: Subscribes to `flight-update`.
    *   **Service Invocation**: Exposes REST endpoints for airport arrivals/departures.
*   **Dapr Best Practice Alignment:**
    *   Creates POST endpoint for Pub/Sub subscription (matches Dapr pub/sub subscription pattern)
    *   Exposes REST endpoints for Service Invocation (no direct database access)
    *   Follows standard Dapr CloudEvents format for pub/sub messages
*   **API Endpoints**:
    *   `GET /api/v1/airports/{airport_code}/arrivals` - Flights arriving at specified airport
    *   `GET /api/v1/airports/{airport_code}/departures` - Flights departing from specified airport
    *   `GET /api/v1/airports/{airport_code}/nearby` - All flights within geofence of airport
    *   `GET /api/v1/airports` - List of monitored airports
*   **Configuration**: Reads airport geofencing config from file (JSON/YAML) with radius and altitude thresholds.
*   **Language**: Go

#### D. External Integrations
**Service:** `flight-archiver`
*   **Role**: Archives flight paths for historical analysis.
*   **Dapr Features**:
    *   **Output Binding**: Writes JSON payloads to local file storage using Dapr binding.
    *   **Pub/Sub**: Subscribes to `flight-update`.
*   **Dapr Best Practice Alignment:**
    *   Uses Dapr Output Binding abstraction (matches [Dapr Bindings tutorial](https://docs.dapr.io/developing-applications/building-blocks/bindings/howto-bindings/))
    *   Binding abstraction allows switching from local file to cloud storage (S3, Azure Blob)
    *   Pub/Sub subscription follows standard Dapr pattern
*   **Language**: Python

**Service:** `emergency-alert`
*   **Role**: Monitors for emergency "squawk" codes (7700, 7500, 7600) and displays alerts in web interface.
*   **Dapr Features**:
    *   **Pub/Sub**: Subscribes to `flight-update`.
    *   **Service Invocation**: Exposes web interface and API for alert management.
*   **Dapr Best Practice Alignment:**
    *   Pub/Sub subscription follows standard Dapr CloudEvents format
    *   Uses Service Invocation for web UI to API communication
    *   No direct database access - all data via Dapr building blocks
*   **API Endpoints**:
    *   `GET /alerts` - Web UI showing active emergency alerts table
    *   `GET /api/v1/alerts/active` - JSON API for active alerts
    *   `GET /api/v1/alerts/history` - JSON API for historical alerts
*   **Language**: Python

#### E. User Interface
**Service:** `flight-dashboard`
*   **Role**: Frontend for visualizing data.
*   **Dapr Features**:
    *   **Service Invocation**: Calls `fleet-stats` for totals and `airport-tracker` for arrival lists. Avoids direct database access.
*   **Dapr Best Practice Alignment:**
    *   Uses Dapr HTTP API directly for Service Invocation (matches [Dapr Service Invocation HTTP API](https://docs.dapr.io/reference/api/service_invocation_api/))
    *   Implements retry logic with exponential backoff (standard Dapr resilience pattern)
    *   No direct database access - all data via Service Invocation
    *   Service location abstracted - works in Docker Compose and Kubernetes
*   **Language**: Svelte/JavaScript (served via Nginx or Node).

## 4. Interaction Diagram (Mermaid)

```mermaid
graph TD
    %% Styles
    classDef dapr fill:#3bbaed,stroke:#005c8f,stroke-width:2px,color:white;
    classDef ext fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef app fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;

    %% External
    OpenSky[OpenSky API]:::ext
    LocalFile[Local File Storage]:::ext
    Redis[(Redis/State & PubSub)]:::ext
    User((VP/User)):::ext

    %% Services
    subgraph "Dapr Mesh"
        direction TB
        
        subgraph "Feeder Service"
            FeederApp[Node.js App]:::app
            FeederDapr(Dapr Sidecar):::dapr
        end
        
        subgraph "Fleet Stats Service"
            StatsApp[Python App]:::app
            StatsDapr(Dapr Sidecar):::dapr
        end
        
        subgraph "Airport Tracker"
            TrackerApp[Go App]:::app
            TrackerDapr(Dapr Sidecar):::dapr
        end
        
        subgraph "Archiver Service"
            ArchiveApp[Python App]:::app
            ArchiveDapr(Dapr Sidecar):::dapr
        end

        subgraph "Alert Service"
            AlertApp[Python App]:::app
            AlertDapr(Dapr Sidecar):::dapr
        end
        
        subgraph "Dashboard"
            DashApp[Svelte UI]:::app
            DashDapr(Dapr Sidecar):::dapr
        end
    end

    %% Flows
    OpenSky -->|Polls Data| FeederApp
    FeederApp -->|Secrets API| FeederDapr
    FeederDapr -->|Pub/Sub 'flight-update'| Redis
    
    Redis -->|Topic Subscription| StatsDapr
    StatsDapr -->|Process| StatsApp
    StatsApp -->|State API (Save)| StatsDapr
    StatsDapr -->|Persist| Redis

    Redis -->|Topic Subscription| TrackerDapr
    TrackerDapr -->|Process| TrackerApp
    
    Redis -->|Topic Subscription| ArchiveDapr
    ArchiveDapr -->|Process| ArchiveApp
    ArchiveApp -->|Binding API| ArchiveDapr
    ArchiveDapr -->|Write File| LocalFile[Local File Storage]:::ext
    
    Redis -->|Topic Subscription| AlertDapr
    AlertDapr -->|Check Squawk| AlertApp
    AlertApp -->|Web Display| User

    User -->|View| DashApp
    DashApp -->|Invoke Method| DashDapr
    DashDapr -->|Service Invocation| StatsDapr
    DashDapr -->|Service Invocation| TrackerDapr
```

## 5. Future Enhancements
### 5.1 3D Flight Visualization
*   **Technology**: CesiumJS (3D Geospatial Visualization).
*   **Integration**:
    *   Update `flight-dashboard` (Svelte) to include a Cesium viewer component.
    *   Stream real-time flight positions from Dapr Pub/Sub (via a WebSocket gateway service or direct subscription if supported by client SDK) to the Cesium viewer.
    *   Visualize flight paths (historical) from the `flight-archiver` data.
*   **Value**: Provides a high-fidelity "Digital Twin" view of the airspace, suitable for operations centers.

## 6. Areas for Clarification & Risks

1.  ~~**"OpenSpec" Definition**: Resolved - OpenSpec refers to the spec-driven development framework (https://github.com/Fission-AI/OpenSpec).~~
2.  **API Rate Limits**: The OpenSky Network free API has rate limits. Mock Mode addresses this with a 20-minute deterministic loop for reliable demos.
3.  ~~**Deployment Target**: Resolved - Target is Docker Compose for simplified demonstration.~~
4.  ~~**Security Scope**: Resolved - Using local file secrets store for demo simplicity. mTLS is automatic in Dapr but not explicitly demonstrated.~~
5.  **Aircraft Type Detection**: OpenSky Network basic API doesn't provide aircraft type. Options: use OpenSky aircraft database API, local lookup table, or infer from mock data.
6.  **Destination/Origin Inference**: OpenSky Network doesn't provide destination/origin directly. Options: parse from callsign patterns, use trajectory analysis, or use mock data for demo.

## 7. Implementation Phases

**Important:** Before implementing each phase, review [DAPR_LESSONS_LEARNED.md](DAPR_LESSONS_LEARNED.md) for Dapr integration best practices and common pitfalls.

### Phase 1: Setup Feeder + Redis + Fleet Stats (Basic Pub/Sub + State)
- Includes Mock Mode support.
- **Dapr Integration Checklist:**
  - ✅ Pub/Sub: Use `@dapr/dapr` SDK for publishing (works well)
  - ✅ Pub/Sub: Create POST endpoints for subscriptions (Python/FastAPI)
  - ✅ State Store: Use `DaprClient` with correct initialization parameters
  - ✅ Docker Compose: Proper sidecar network configuration

### Phase 2: Add Airport Tracker + Dashboard (Svelte + Service Invocation)
- Includes airport geofencing config file.
- **Dapr Integration Checklist:**
  - ✅ Service Invocation: Use Dapr HTTP API directly (`/v1.0/invoke/<app-id>/method/<path>`) - simpler than SDK
  - ✅ Pub/Sub: Go service should create POST endpoint for subscription
  - ✅ Docker Compose: Ensure sidecar has proper `depends_on` and network_mode
- **Dapr Best Practice References:**
  - Service Invocation: [Dapr Service Invocation Tutorial](https://docs.dapr.io/developing-applications/building-blocks/service-invocation/howto-invoke-discover-services/)
  - Pub/Sub (Go): [Dapr Go SDK examples](https://docs.dapr.io/developing-applications/sdks/go/)
  - Resilience: Implements retry logic with exponential backoff (standard Dapr pattern)

### Phase 3: Add Output Bindings and Archiver Service
- **Incremental Step 3a: Implement flight-archiver (Python + Output Bindings)**
  - Subscribe to `flight-update` topic
  - Use Dapr Output Binding to write JSON to local file storage
  - Archive all flight updates with timestamp
  - **Dapr Integration Checklist:**
    - ✅ Output Bindings: Ensure `data-volume` is mounted correctly
    - ✅ Component Files: Verify binding component YAML references valid paths
    - ✅ Docker Compose: Mount required volumes to sidecar
    - ✅ Pub/Sub: Create POST endpoint for subscription
  - **Dapr Best Practice References:**
    - Output Bindings: [Dapr Bindings Tutorial](https://docs.dapr.io/developing-applications/building-blocks/bindings/howto-bindings/)
    - Pub/Sub: Follows standard Dapr subscription pattern
  - **SDK Migration Opportunity:** Consider using the Python Dapr SDK for Output Bindings to showcase SDK capabilities.

- **Incremental Step 3b: Implement emergency-alert (Python + Pub/Sub + Service Invocation)**
  - Subscribe to `flight-update` topic
  - Filter for emergency squawk codes (7700, 7500, 7600)
  - Store active alerts in memory/state
  - Expose web UI at `/alerts` for active alerts table
  - Expose REST API endpoints: `/api/v1/alerts/active`, `/api/v1/alerts/history`
  - **Dapr Integration Checklist:**
    - ✅ Pub/Sub: Create POST endpoint for subscription
    - ✅ State Store: Optionally persist alerts (future enhancement)
    - ✅ Service Invocation: Web UI calls API endpoints
    - ✅ Docker Compose: Follow same patterns as fleet-stats
  - **Dapr Best Practice References:**
    - Pub/Sub: [Dapr Pub/Sub Tutorial](https://docs.dapr.io/developing-applications/building-blocks/pubsub/howto-publish-subscribe/)
    - State Management: [Dapr State Management Tutorial](https://docs.dapr.io/developing-applications/building-blocks/state-management/howto-get-save-state/)
    - Service Invocation: Web UI uses Service Invocation for API calls

### Phase 4: Add Comprehensive Fleet Metrics (Incremental Enhancements)
- **Enhancement 4a: Add destination and origin tracking to fleet-stats**
  - Parse destination/origin from flight data or callsign patterns
  - Add aggregation by destination airport
  - Add aggregation by origin airport
  - Expose endpoints: `/api/v1/fleet/stats/by-destination`, `/api/v1/fleet/stats/by-origin`
  - **Dapr Integration Checklist:**
    - ✅ Verify all subscriptions have correct routes
    - ✅ Ensure state store operations use correct component name
  - **Dapr Best Practice References:**
    - State Management: Extends existing state store usage pattern
    - Follows same Dapr patterns as Phase 1
  
- **Enhancement 4b: Add aircraft type tracking (optional - depends on data availability)**
  - If mock mode: Infer from callsign patterns or use lookup table
  - If real API mode: Use OpenSky aircraft database API (requires additional API calls)
  - Add aggregation by aircraft type
  - Expose endpoint: `/api/v1/fleet/stats/by-aircraft-type`
  - **Dapr Best Practice References:**
    - State Management: Extends existing state store usage pattern
    - Follows same Dapr patterns as Phase 1
  - **Note:** In mock mode, destination/origin/aircraft type will be synthetic. Real API mode requires additional OpenSky API endpoints or local lookup tables.

### Phase 5 (Future): Integrate CesiumJS for 3D visualization
- Already specified in spec.
- **Dapr Integration Considerations:**
  - WebSocket gateway or direct subscription via client SDK
  - Consider using Dapr HTTP API for service calls from frontend

## 8. Data Feed Configuration

### Mock Mode (Current - Default)
- **Purpose:** Deterministic demo data for reliable presentations
- **Configuration:** Set `MOCK_MODE=true` environment variable
- **Features:**
  - Generates synthetic flight data for 5 airlines (Delta, United, Southwest, Qantas, Emirates)
  - 20-minute deterministic loop
  - No API keys required
  - Always works regardless of network/external API availability
- **Use Case:** Default for demos, development, testing

### Real API Mode (Future - Phase 6)
- **Purpose:** Live flight tracking with real ADS-B data
- **Configuration:** Set `MOCK_MODE=false` and provide OpenSky API credentials via Dapr Secrets
- **Requirements:**
  - OpenSky Network API account (free tier available)
  - API credentials stored in `secrets/secrets.json`
  - Network access to OpenSky API
- **Limitations:**
  - Subject to OpenSky API rate limits
  - Requires internet connectivity
  - May have data gaps during API outages
- **Use Case:** Production demos, integration testing with real data

### Switching Between Modes
1. **Mock Mode (Default):**
   ```yaml
   # docker-compose.yml
   environment:
     - MOCK_MODE=true  # or omit (defaults to true)
   ```

2. **Real API Mode:**
   ```yaml
   # docker-compose.yml
   environment:
     - MOCK_MODE=false
   ```
   ```json
   // secrets/secrets.json
   {
     "opensky": {
       "username": "your_username",
       "password": "your_password"
     }
   }
   ```

3. **Service Logic:**
   - If `MOCK_MODE=false` and credentials exist → Use OpenSky API
   - Otherwise → Fall back to mock mode

## 9. Cloud Migration Path

This demo is designed to run locally using Docker Compose, but the same code can migrate to a distributed cloud architecture without changes. This demonstrates Dapr's platform-agnostic nature and portability benefits.

### Current Architecture (Local - Docker Compose)
- **Infrastructure:** Docker Compose with containers on same host
- **Components:** Redis (local), local file storage, local secrets file
- **Network:** Docker bridge network
- **Deployment:** Single `docker-compose up` command
- **Scaling:** Manual (replicate containers in docker-compose.yml)

### Target Architecture (Cloud - Kubernetes)
- **Infrastructure:** Kubernetes cluster (any cloud provider)
- **Components:** Managed Redis (Azure Cache, AWS ElastiCache), cloud storage (S3, Azure Blob), cloud secrets (Azure Key Vault, AWS Secrets Manager)
- **Network:** Kubernetes service mesh (Dapr handles this)
- **Deployment:** Kubernetes manifests (Deployments, Services)
- **Scaling:** Kubernetes horizontal pod autoscaling

### Migration Benefits of Using Dapr

**1. No Code Changes Required**
- Application code remains identical
- Same Dapr building blocks (Pub/Sub, State, Service Invocation, Bindings)
- Same API calls (HTTP API or SDK)

**2. Component Configuration Changes Only**
- Update component YAML files to point to cloud services
- Example: Change Redis component from local Redis to Azure Cache for Redis
- No application code changes needed

**3. Platform Abstraction**
- Dapr abstracts Kubernetes, service mesh, networking
- Same application works on Docker Compose, Kubernetes, VMs, or edge devices
- **Alignment with Dapr Philosophy:** Write once, run anywhere - see [Dapr Overview](https://docs.dapr.io/concepts/overview/)

### Migration Steps (High-Level)

**Step 1: Containerization (Already Done)**
- Services are already containerized (Dockerfiles exist)
- Images can be pushed to container registry (Docker Hub, ACR, ECR)

**Step 2: Component Configuration Updates**
- Update `components/pubsub.yaml`: Change Redis host to managed Redis endpoint
- Update `components/statestore.yaml`: Change to managed Redis or cloud state store
- Update `components/filebinding.yaml`: Change to cloud storage binding (S3, Azure Blob)
- Update `components/secrets.yaml`: Change to cloud secrets store (Key Vault, Secrets Manager)

**Step 3: Kubernetes Deployment**
- Create Kubernetes Deployments for each service
- Add Dapr annotations to enable sidecar injection
- Create Kubernetes Services for service discovery
- Deploy Dapr components (same YAML files, different config values)

**Step 4: Observability and Operations**
- Use cloud-managed Zipkin/Jaeger for distributed tracing
- Enable Dapr metrics (Prometheus/Grafana)
- Configure logging (cloud logging services)
- Set up health checks and readiness probes

**Step 5: Production Enhancements**
- Enable Dapr mTLS (automatic in Kubernetes)
- Configure Dapr resilience policies (retry, timeout, circuit breaker)
- Set up horizontal pod autoscaling
- Configure resource limits and requests

### Component Migration Examples

**Pub/Sub Component (Local → Cloud):**
```yaml
# Local (docker-compose.yml environment)
redisHost: redis:6379

# Cloud (Kubernetes with Azure Cache for Redis)
redisHost: my-redis.redis.cache.windows.net:6380
redisPassword: <from Azure Key Vault via Dapr Secrets>
enableTLS: true
```

**State Store Component (Local → Cloud):**
```yaml
# Local (Redis)
redisHost: redis:6379

# Cloud Option 1 (Azure Cosmos DB)
componentType: state.azure.cosmosdb
metadata:
  url: <Cosmos DB endpoint>
  masterKey: <from Azure Key Vault>

# Cloud Option 2 (AWS DynamoDB)
componentType: state.aws.dynamodb
metadata:
  tableName: fleet-stats
  region: us-east-1
```

**Output Binding (Local → Cloud):**
```yaml
# Local (File Storage)
componentType: bindings.localstorage
metadata:
  rootPath: /data

# Cloud (Azure Blob Storage)
componentType: bindings.azure.blobstorage
metadata:
  storageAccount: mystorageaccount
  containerName: flight-archive

# Cloud (AWS S3)
componentType: bindings.aws.s3
metadata:
  bucket: flight-archive
  region: us-east-1
```

### Dapr Best Practices for Cloud Migration

1. **Use Component Scoping**: Limit component access to specific services using `scopes` in component YAML
2. **Enable mTLS**: Automatic in Kubernetes - no code changes needed
3. **Configure Resilience Policies**: Use Dapr configuration to define retry, timeout, circuit breaker policies
4. **Use Distributed Tracing**: Already enabled (Zipkin) - works the same in cloud
5. **Leverage Dapr Configuration API**: For dynamic configuration updates without redeployment

**Reference:** [Dapr Production Readiness Checklist](https://docs.dapr.io/operations/configuration/production-ready-checklist/)

### Benefits Demonstrated

By using Dapr in this demo, we've built a system that:
- **Works locally** (Docker Compose) for development and demos
- **Migrates to cloud** (Kubernetes) with configuration changes only
- **No code changes** required for cloud migration
- **Platform agnostic** - works on any Kubernetes distribution (AKS, EKS, GKE, on-premises)
- **Vendor agnostic** - can switch cloud providers by changing component configurations

This demonstrates the core value proposition of Dapr: **Write your application logic once, deploy it anywhere.**

### Phase 6: OpenSky Network API Integration (Real Data Feeds)
- **Objective:** Replace mock data with real ADS-B data from OpenSky Network
- **Prerequisites:**
  - OpenSky Network API account (free tier)
  - Understanding of OpenSky API rate limits
  - Network connectivity to OpenSky API
  
- **Implementation Steps:**
  1. **Add OpenSky API client to adsb-feeder**
     - Implement HTTP client for OpenSky States API
     - Map OpenSky response format to our flight-update schema
     - Handle API rate limiting and errors gracefully
     - Fall back to mock mode if API unavailable
  
  2. **Configure Dapr Secrets for API credentials**
     - Store OpenSky username/password in `secrets/secrets.json`
     - Use Dapr Secrets API to retrieve credentials
     - Remove credentials from environment variables
  
  3. **Add data filtering/region selection**
     - Filter flights by region/bounding box (optional)
     - Limit number of flights to avoid overwhelming system
     - Handle missing data fields gracefully
  
  4. **Update documentation**
     - Document OpenSky API setup process
     - Document rate limits and best practices
     - Update README with real API mode instructions
  
- **Dapr Integration Checklist:**
  - ✅ Secrets Management: Use Dapr Secrets API (already configured)
  - ✅ Error Handling: Graceful fallback to mock mode on API failures
  - ✅ Rate Limiting: Implement request throttling if needed
  - ✅ Data Transformation: Map OpenSky format to flight-update schema

- **Testing Strategy:**
  - Test with OpenSky free tier (rate limited)
  - Verify graceful degradation when API is unavailable
  - Compare mock vs real data for schema consistency
