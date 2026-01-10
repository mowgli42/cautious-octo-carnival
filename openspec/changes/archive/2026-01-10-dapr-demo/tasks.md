# Implementation Tasks

## 1. Core Infrastructure & Feeder
- [ ] 1.1 Update `adsb-feeder` (Node.js) to use Dapr Secrets for OpenSky API keys
- [ ] 1.2 Validate `adsb-feeder` publishes to `flight-update` topic

## 2. Analytics Service (Python)
- [ ] 2.1 Create `fleet-stats` service in Python
- [ ] 2.2 Implement Dapr Pub/Sub subscription to `flight-update`
- [ ] 2.3 Implement Dapr State Store logic to persist flight counts (Redis)

## 3. Geospatial Service (Go)
- [ ] 3.1 Create `airport-tracker` service in Go
- [ ] 3.2 Implement Pub/Sub subscription for flight updates
- [ ] 3.3 Expose HTTP endpoint `/arrivals/{code}` for Service Invocation

## 4. Bindings & Integrations (Java/C#)
- [ ] 4.1 Create `flight-archiver` (Java/C#)
- [ ] 4.2 Configure Dapr Output Binding for local file/S3
- [ ] 4.3 Create `emergency-alert` (C#)
- [ ] 4.4 Configure Dapr Output Binding for SMTP/Console mock

## 5. Dashboard (Svelte)
- [ ] 5.1 Initialize new Svelte project `flight-dashboard`
- [ ] 5.2 Implement Dapr Service Invocation client to fetch stats
- [ ] 5.3 Implement real-time view of flight data

## 6. Documentation & Diagram
- [ ] 6.1 Update main README.md with new architecture
- [ ] 6.2 Include Mermaid diagram in documentation
- [ ] 6.3 Document prerequisites and run instructions
