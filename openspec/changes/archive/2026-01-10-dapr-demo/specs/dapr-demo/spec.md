# Delta for Dapr Demo Architecture

## ADDED Requirements

### Requirement: Polyglot Services
The system SHALL consist of services written in at least 3 distinct programming languages to demonstrate Dapr's language agnostic nature.

#### Scenario: Multi-language composition
- WHEN the system is running
- THEN it must include services in Node.js, Python, and Go/Java/C#
- AND all services must communicate via Dapr sidecars

### Requirement: State Management
The `fleet-stats` service SHALL persist aggregation data to a Dapr state store.

#### Scenario: Restart resilience
- WHEN the `fleet-stats` service is restarted
- THEN it must reload previous flight counts from the state store
- AND continue aggregating without data loss

### Requirement: Service Invocation
The `flight-dashboard` SHALL retrieve data from backend services using Dapr Service Invocation.

#### Scenario: Dashboard Data Fetch
- WHEN the dashboard needs active flight counts
- THEN it must invoke the `fleet-stats` service via Dapr (e.g., `/v1.0/invoke/fleet-stats/method/...`)
- AND not connect directly to the backend database

### Requirement: Output Bindings
The system SHALL use Dapr Output Bindings for external integrations.

#### Scenario: Archival
- WHEN a flight update is received by the `flight-archiver`
- THEN it must write the record to a blob storage binding

#### Scenario: Emergency Alert
- WHEN a "7700" squawk code is detected
- THEN the `emergency-alert` service must trigger a notification binding (e.g., SMTP/Twilio)

### Requirement: Svelte Dashboard
The user interface SHALL be built using Svelte.

#### Scenario: UI Rendering
- WHEN a user accesses the main URL
- THEN they are served a Svelte application
- AND the application displays real-time flight data

### Requirement: Cesium Visualization (Future)
The dashboard SHALL support 3D visualization using CesiumJS (Phase 5).

#### Scenario: 3D View
- WHEN the user selects "3D View"
- THEN the flight positions are rendered on a 3D globe using CesiumJS
