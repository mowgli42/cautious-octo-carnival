# dapr-demo Specification

## Purpose
TBD - created by archiving change dapr-demo. Update Purpose after archive.
## Requirements
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
The user interface SHALL be a single-page "Map-First" application.

#### Scenario: Unified View
- WHEN the user loads the dashboard
- THEN they must see the 3D Map (Cesium) filling the background
- AND statistical data (Fleet Counts, Arrivals) must be presented as floating HUD overlays on top of the map
- AND there must be no separate navigation pages (single view experience)

### Requirement: Mock Feeder Mode
The `adsb-feeder` service SHALL support a configurable "Mock Mode" that generates synthetic flight data instead of connecting to the live API.

#### Scenario: Mock Data Generation
- WHEN the service is started with `MOCK_MODE=true`
- THEN it must ignore external API credentials
- AND it must generate flight update events for a predefined set of airlines

#### Scenario: Specific Airlines
- WHEN in Mock Mode
- THEN the generated flights must include aircraft from: Delta, United, Southwest, Qantas, and Emirates

#### Scenario: Playback Loop
- WHEN in Mock Mode
- THEN the flight data must follow a deterministic 20-minute loop
- AND the loop must repeat indefinitely without interruption

