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
  - [ ] **3.2.1** Create POST endpoint `/flight-update` for subscription (not decorator)
  - [ ] **3.2.2** Create subscription YAML in `components/subscription.yaml` with correct scope
  - [ ] **3.2.3** Verify subscription endpoint matches YAML route path
- [ ] 3.3 Expose HTTP endpoint `/arrivals/{code}` for Service Invocation
  - [ ] **3.3.1** Use Dapr HTTP API format: `/v1.0/invoke/<app-id>/method/<path>` (preferred over SDK)
- [ ] 3.4 Docker Compose integration
  - [ ] **3.4.1** Sidecar uses `network_mode: service:<app-name>`
  - [ ] **3.4.2** Both app and sidecar have `depends_on` for Redis and dapr-placement
  - [ ] **3.4.3** App container exposes Dapr HTTP port: `"350X:350X"`
  - [ ] **3.4.4** Verify component files exist before starting

## 4. Bindings & Integrations (Java/C#)
- [ ] 4.1 Create `flight-archiver` (Java/C#)
- [ ] 4.2 Configure Dapr Output Binding for local file/S3
  - [ ] **4.2.1** Ensure `data-volume` is mounted to sidecar at `/data`
  - [ ] **4.2.2** Verify binding component YAML references valid path
- [ ] 4.3 Create `emergency-alert` (C#)
- [ ] 4.4 Configure Dapr Output Binding for SMTP/Console mock
- [ ] 4.5 Docker Compose integration (repeat checklist from 3.4)

## 5. Dashboard (Svelte/Node.js)
- [ ] 5.1 Initialize new Svelte project `flight-dashboard` (or Node.js backend with static frontend)
- [ ] 5.2 Implement Dapr Service Invocation client to fetch stats
  - [ ] **5.2.1** Use Dapr HTTP API directly: `http://localhost:<DAPR_PORT>/v1.0/invoke/<app-id>/method/<path>` (simpler than SDK)
  - [ ] **5.2.2** If using SDK, verify parameter format matches SDK version
- [ ] 5.3 Implement real-time view of flight data
- [ ] 5.4 Docker Compose integration (repeat checklist from 3.4)

## 6. Documentation & Diagram
- [ ] 6.1 Update main README.md with new architecture
- [ ] 6.2 Include Mermaid diagram in documentation
- [ ] 6.3 Document prerequisites and run instructions
