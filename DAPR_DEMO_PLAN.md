# Dapr ADS-B Messaging Demo - Expanded Plan

## 1. Overview
This document outlines an expanded architecture for the ADS-B Dapr demo. The goal is to demonstrate the core value propositions of Dapr—polyglot microservices, consistent building blocks (State, Pub/Sub, Bindings, Secrets), and observability—to a executive audience.

## 2. Business Goal
Demonstrate how Dapr decouples infrastructure from application logic, allowing developers to focus on business features (flight tracking, alerting, analytics) while Dapr handles the complexity of distributed systems (state, messaging, resilience).

## 3. Architecture Specification (OpenSpec Style)

### 3.1 Core Building Blocks Utilized
*   **Pub/Sub**: Decoupled event broadcasting (Flight positions). Topic: `flight-update`.
*   **State Management**: Consistent key-value storage for service state (Fleet counts) using Redis.
*   **Service Invocation**: Synchronous, secure inter-service HTTP/gRPC calls (Dashboard querying).
*   **Output Bindings**: Event-driven connection to external resources (Local file storage for archival).
*   **Secrets Management**: Secure access to sensitive config (API keys) using local file store.

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
*   **Language**: Python

**Service:** `emergency-alert`
*   **Role**: Monitors for emergency "squawk" codes (7700, 7500, 7600) and displays alerts in web interface.
*   **Dapr Features**:
    *   **Pub/Sub**: Subscribes to `flight-update`.
    *   **Service Invocation**: Exposes web interface and API for alert management.
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

### Phase 3: Add Archiver (Local file binding) + Emergency Alert (Web display)
- **Dapr Integration Checklist:**
  - ✅ Output Bindings: Ensure `data-volume` is mounted correctly
  - ✅ Component Files: Verify binding component YAML references valid paths
  - ✅ Docker Compose: Mount required volumes to sidecar

### Phase 4: Add comprehensive fleet metrics (destination, origin, aircraft type)
- **Dapr Integration Checklist:**
  - ✅ Verify all subscriptions have correct routes
  - ✅ Ensure state store operations use correct component name

### Phase 5 (Future): Integrate CesiumJS for 3D visualization
- Already specified in spec.
- **Dapr Integration Considerations:**
  - WebSocket gateway or direct subscription via client SDK
  - Consider using Dapr HTTP API for service calls from frontend
