# Dapr ADS-B Messaging Demo - Expanded Plan

## 1. Overview
This document outlines an expanded architecture for the ADS-B Dapr demo. The goal is to demonstrate the core value propositions of Dapr—polyglot microservices, consistent building blocks (State, Pub/Sub, Bindings, Secrets), and observability—to a executive audience.

## 2. Business Goal
Demonstrate how Dapr decouples infrastructure from application logic, allowing developers to focus on business features (flight tracking, alerting, analytics) while Dapr handles the complexity of distributed systems (state, messaging, resilience).

## 3. Architecture Specification (OpenSpec Style)

### 3.1 Core Building Blocks Utilized
*   **Pub/Sub**: Decoupled event broadcasting (Flight positions).
*   **State Management**: Consistent key-value storage for service state (Fleet counts).
*   **Service Invocation**: Synchronous, secure inter-service HTTP/gRPC calls (Dashboard querying).
*   **Output Bindings**: Event-driven connection to external resources (Archival, Alerts).
*   **Secrets Management**: Secure access to sensitive config (API keys).

### 3.2 Services Definition

#### A. Data Ingestion
**Service:** `adsb-feeder`
*   **Role**: Polls OpenSky Network API for live flight data.
*   **Dapr Features**: 
    *   **Pub/Sub**: Publishes `flight-update` events.
    *   **Secrets**: Retrieves OpenSky API credentials via Dapr Secret Store.
*   **Language**: Node.js

#### B. Analytics & State
**Service:** `fleet-stats`
*   **Role**: Aggregates real-time statistics (e.g., active flights by airline).
*   **Dapr Features**:
    *   **Pub/Sub**: Subscribes to `flight-update`.
    *   **State Store**: Persists running totals to Redis/CosmosDB so data survives restarts.
*   **Language**: Python (demonstrates polyglot).

#### C. Geospatial Processing
**Service:** `airport-tracker`
*   **Role**: Identifies flights near key airports (geofencing).
*   **Dapr Features**:
    *   **Pub/Sub**: Subscribes to `flight-update`.
    *   **Service Invocation**: Exposes an HTTP endpoint `/arrivals/{airport_code}` for the Dashboard.
*   **Language**: Go (demonstrates polyglot).

#### D. External Integrations (New)
**Service:** `flight-archiver`
*   **Role**: Archives flight paths for historical analysis.
*   **Dapr Features**:
    *   **Output Binding**: Writes JSON payloads directly to S3/Azure Blob/Local File using a Dapr binding (no SDK code needed for specific storage provider).
    *   **Pub/Sub**: Subscribes to `flight-update`.
*   **Language**: Java/C#

**Service:** `emergency-alert`
*   **Role**: Monitors for emergency "squawk" codes (e.g., 7700).
*   **Dapr Features**:
    *   **Output Binding**: Triggers an external notification (SMTP/Twilio/Slack) when an emergency is detected.
    *   **Pub/Sub**: Subscribes to `flight-update`.

#### E. User Interface
**Service:** `flight-dashboard`
*   **Role**: Frontend for visualizing data.
*   **Dapr Features**:
    *   **Service Invocation**: Calls `fleet-stats` for totals and `airport-tracker` for arrival lists. Avoids direct database access.
*   **Language**: React/JavaScript (served via Nginx or Node).

## 4. Interaction Diagram (Mermaid)

```mermaid
graph TD
    %% Styles
    classDef dapr fill:#3bbaed,stroke:#005c8f,stroke-width:2px,color:white;
    classDef ext fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef app fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;

    %% External
    OpenSky[OpenSky API]:::ext
    S3[Blob Storage/S3]:::ext
    Redis[(Redis/State & PubSub)]:::ext
    Email[SMTP/Slack]:::ext
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
            ArchiveApp[Java App]:::app
            ArchiveDapr(Dapr Sidecar):::dapr
        end

        subgraph "Alert Service"
            AlertApp[C# App]:::app
            AlertDapr(Dapr Sidecar):::dapr
        end
        
        subgraph "Dashboard"
            DashApp[Web UI]:::app
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
    ArchiveDapr -->|Write File| S3
    
    Redis -->|Topic Subscription| AlertDapr
    AlertDapr -->|Check Squawk| AlertApp
    AlertApp -->|Binding API| AlertDapr
    AlertDapr -->|Send Alert| Email

    User -->|View| DashApp
    DashApp -->|Invoke Method| DashDapr
    DashDapr -->|Service Invocation| StatsDapr
    DashDapr -->|Service Invocation| TrackerDapr
```

## 5. Areas for Clarification & Risks

1.  **"OpenSpec" Definition**: Please confirm if "OpenSpec" refers to a specific industry standard (like OpenAPI/AsyncAPI) or just a structured "Open Specification" format as used above. I have assumed the latter for this high-level plan.
2.  **API Rate Limits**: The OpenSky Network free API has rate limits. For a live demo to a VP, we should ensure we have a cached dataset or a recorded playback mode ("Replay Service") to avoid empty screens if the API blocks us or no flights are visible.
3.  **Deployment Target**: Is the target environment Kubernetes (AKS/EKS/GKE) or Docker Compose? Dapr works on both, but the configuration (YAMLs) differs slightly. The diagram assumes a generic Dapr mesh.
4.  **Security Scope**: Do we need to demonstrate mTLS (automatic in Dapr) or specific ACLs for the Service Invocation?

## 6. Implementation Phases
1.  **Phase 1**: Setup Feeder + Redis + Fleet Stats (Basic Pub/Sub + State).
2.  **Phase 2**: Add Airport Tracker + Dashboard (Service Invocation).
3.  **Phase 3**: Add Archiver + Alerting (Bindings).
4.  **Phase 4**: Add "Replay Mode" for robust demos.
