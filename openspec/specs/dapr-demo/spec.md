# dapr-demo Specification

## Purpose
Demonstrate Dapr's core value propositions—polyglot microservices, consistent building blocks (State, Pub/Sub, Bindings, Secrets), and observability—to an executive audience using real-time ADS-B flight tracking data. The system decouples infrastructure from application logic, allowing developers to focus on business features (flight tracking, alerting, analytics) while Dapr handles the complexity of distributed systems (state, messaging, resilience).

## Requirements
### Requirement: Polyglot Services
The system SHALL consist of services written in at least 3 distinct programming languages to demonstrate Dapr's language agnostic nature.

#### Scenario: Multi-language composition
- WHEN the system is running
- THEN it must include services in Node.js, Python, and Go
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
- THEN it must invoke the `fleet-stats` service via Dapr (e.g., `/v1.0/invoke/fleet-stats/method/api/v1/fleet/stats/summary`)
- AND not connect directly to the backend database

### Requirement: Output Bindings
The system SHALL use Dapr Output Bindings for external integrations.

#### Scenario: Archival
- WHEN a flight update is received by the `flight-archiver`
- THEN it must write the record to a local file storage binding

### Requirement: Emergency Alert Web Display
The `emergency-alert` service SHALL provide a separate web interface for displaying emergency alerts.

#### Scenario: Emergency Alert Display
- WHEN an emergency squawk code (7700, 7500, 7600) is detected
- THEN the alert must be displayed in a web interface at `/alerts`
- AND the interface must show a table with: callsign, icao24, squawk code, position, altitude, velocity, timestamp, and status
- AND the table must auto-refresh for real-time updates
- AND the service must expose REST endpoints for active and historical alerts

### Requirement: Fleet Statistics Metrics
The `fleet-stats` service SHALL aggregate statistics by airline, destination airport, origin airport, and aircraft type.

#### Scenario: Comprehensive Metrics
- WHEN flight updates are received
- THEN the service must aggregate statistics grouped by:
  - Airline
  - Destination airport
  - Origin airport
  - Aircraft type
- AND the service must expose REST endpoints for each metric type:
  - `GET /api/v1/fleet/stats/summary` - Overall statistics
  - `GET /api/v1/fleet/stats/by-airline` - Statistics grouped by airline
  - `GET /api/v1/fleet/stats/by-destination` - Statistics grouped by destination airport
  - `GET /api/v1/fleet/stats/by-origin` - Statistics grouped by origin airport
  - `GET /api/v1/fleet/stats/by-aircraft-type` - Statistics grouped by aircraft type

### Requirement: Airport Geofencing Configuration
Airport geofencing parameters SHALL be configured via a configuration file.

#### Scenario: File-Based Configuration
- WHEN the `airport-tracker` service starts
- THEN it must read airport geofencing configuration from a file (JSON or YAML)
- AND the configuration must include: ICAO code, name, latitude, longitude, geofence radius (in kilometers), and altitude thresholds (for arrival/departure detection)
- AND flights within the geofence radius and below threshold altitude must be identified as arriving or departing
- AND the service must expose REST endpoints:
  - `GET /api/v1/airports/{airport_code}/arrivals` - Flights arriving at specified airport
  - `GET /api/v1/airports/{airport_code}/departures` - Flights departing from specified airport
  - `GET /api/v1/airports/{airport_code}/nearby` - All flights within geofence of airport
  - `GET /api/v1/airports` - List of monitored airports

### Requirement: Svelte Dashboard
The user interface SHALL be a single-page "Map-First" application.

#### Scenario: Unified View
- WHEN the user loads the dashboard
- THEN they must see the 3D Map (Cesium) filling the background
- AND statistical data (Fleet Counts, Arrivals) must be presented as floating HUD overlays on top of the map
- AND there must be no separate navigation pages (single view experience)

### Requirement: Mock Feeder Mode
The `adsb-feeder` service SHALL support a configurable "Mock Mode" that generates synthetic flight data instead of connecting to the live API.

**Note:** Real OpenSky Network API integration is planned for Phase 6. Mock mode is the default to ensure demo reliability.

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

### Requirement: UI Mockups
The system development SHALL begin with the creation of high-fidelity static mockups for the dashboard.

#### Scenario: Mockup Generation
- WHEN the project starts
- THEN a set of static HTML/Svelte pages must be generated
- AND these pages must visually represent the "Map-First" layout with Cesium background and HUD overlays

#### Scenario: Stakeholder Review
- WHEN the mockups are generated
- THEN they must be presented to the user for review
- AND backend implementation SHALL NOT begin until the visual layout is approved

### Requirement: Deployment Target
The system SHALL be deployable using Docker Compose.

#### Scenario: Docker Compose Deployment
- WHEN deploying the system
- THEN all services must run via Docker Compose
- AND Dapr components must be configured for Docker Compose environment

### Requirement: Dapr Component Configuration
Dapr components SHALL use simple configurations suitable for demonstration.

#### Scenario: Simplified Components
- WHEN configuring Dapr
- THEN Pub/Sub and State Store must use Redis
- AND Output Bindings must use local file storage
- AND Secrets must use local file store
- AND the Pub/Sub topic name must be `flight-update`

### Requirement: Flight Update Message Schema
Flight update events SHALL conform to a standardized JSON schema based on ADS-B data.

#### Scenario: Message Format
- WHEN the `adsb-feeder` service publishes a flight update
- THEN the message must be published to topic `flight-update`
- AND the message must contain the following fields:
  - `icao24` (string): Aircraft unique identifier
  - `callsign` (string): Flight callsign
  - `origin_country` (string): Country of origin
  - `time_position` (integer): Unix timestamp of position update
  - `last_contact` (integer): Unix timestamp of last contact
  - `longitude` (float): Aircraft longitude
  - `latitude` (float): Aircraft latitude
  - `baro_altitude` (float): Barometric altitude in meters (nullable)
  - `geo_altitude` (float): Geometric altitude in meters (nullable)
  - `on_ground` (boolean): Whether aircraft is on ground
  - `velocity` (float): Horizontal velocity in m/s (nullable)
  - `true_track` (float): True track angle in degrees (nullable)
  - `vertical_rate` (float): Vertical rate in m/s (nullable)
  - `squawk` (string): Transponder squawk code
  - `spi` (boolean): Special purpose indicator
  - `position_source` (integer): Position source type
  - `timestamp` (integer): Event timestamp (Unix epoch)

