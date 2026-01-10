# Dapr ADS-B Messaging Demo

This repository demonstrates the basic messaging capabilities of Dapr (Distributed Application Runtime) using a simple pub/sub pattern. We use an ADS-B (Automatic Dependent Surveillance-Broadcast) data feed as the data source. One service ingests and filters ADS-B data, then publishes it via Dapr to other subscribing services. These subscribers perform useful functions like computing fleet statistics and retrieving airport information.

The focus is on simplicity: minimal code, straightforward setup, and clear examples of Dapr's pub/sub messaging for inter-service communication in a distributed system.

## Features

- **ADS-B Feeder Service**: Ingests real-time ADS-B data from a public feed (e.g., via OpenSky Network API), applies basic filtering (e.g., by altitude or region), and publishes filtered messages to a Dapr pub/sub topic.
- **Fleet Statistics Service**: Subscribes to the pub/sub topic, aggregates aircraft data to compute fleet stats (e.g., count of active aircraft per airline, average speed/altitude).
- **Airport Information Service**: Subscribes to the topic, tracks aircraft near specified airports, and provides info like estimated arrivals/departures or traffic volume.
- **Dapr Integration**: Uses Dapr's pub/sub component (e.g., with Redis as the message broker) for decoupled messaging. Services are written in Node.js for simplicity, but Dapr allows easy extension to other languages.
- **Extensibility**: Easy to add more subscriber services for additional functions (e.g., alerting on low-altitude flights).

## Prerequisites

- Docker and Docker Compose (for running services and Dapr sidecars).
- Node.js (v18+).
- Dapr CLI installed (see [Dapr Quickstarts](https://docs.dapr.io/getting-started/)).
- Redis (used as the pub/sub broker; can be run via Docker).
- Access to an ADS-B data feed API key (e.g., from OpenSky Network; free tier available).

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/dapr-adsb-messaging-demo.git
   cd dapr-adsb-messaging-demo
   ```

2. Install dependencies for each service:
   ```
   cd feeder-service && npm install
   cd ../fleet-stats-service && npm install
   cd ../airport-info-service && npm install
   ```

3. Set up environment variables:
   - Create a `.env` file in the root directory with your ADS-B API credentials:
     ```
     ADSB_API_USERNAME=your_opensky_username
     ADSB_API_PASSWORD=your_opensky_password
     AIRPORT_ICAO_CODES=KJFK,EGLL  # Comma-separated ICAO codes for airports to monitor
     ```

4. Initialize Dapr:
   ```
   dapr init
   ```

## Usage

### Running Locally with Dapr

1. Start Redis (message broker):
   ```
   docker run -d -p 6379:6379 redis
   ```

2. Run each service with its Dapr sidecar in separate terminals:

   - Feeder Service:
     ```
     cd feeder-service
     dapr run --app-id feeder --app-port 3000 --dapr-http-port 3500 node app.js
     ```

   - Fleet Stats Service:
     ```
     cd fleet-stats-service
     dapr run --app-id fleet-stats --app-port 3001 --dapr-http-port 3501 node app.js
     ```

   - Airport Info Service:
     ```
     cd airport-info-service
     dapr run --app-id airport-info --app-port 3002 --dapr-http-port 3502 node app.js
     ```

3. The Feeder Service will start polling ADS-B data every 10 seconds, filter it (e.g., aircraft above 10,000 ft), and publish to the `adsb-updates` topic.

4. Subscribers will log processed data to the console. For example:
   - Fleet Stats: Outputs JSON with airline counts and averages.
   - Airport Info: Outputs arrival/departure estimates for monitored airports.

### Running with Docker Compose

For a one-command setup:
```
docker-compose up
```
This builds and runs all services with Dapr sidecars and Redis.

### Testing

- Monitor logs for published and subscribed messages.
- Use tools like `curl` to invoke service endpoints if needed (e.g., `curl http://localhost:3001/stats` for fleet stats summary).

## Architecture

- **Data Flow**:
  1. Feeder Service fetches ADS-B data via HTTP API.
  2. Filters data (e.g., by location or attributes).
  3. Publishes JSON messages to Dapr pub/sub topic `adsb-updates` using Dapr SDK.
  4. Subscriber services use Dapr SDK to subscribe to the topic and process incoming messages.

- **Dapr Components**:
  - Pub/Sub: Configured in `components/pubsub.yaml` (uses Redis).
  - No state management or bindings in this basic demo—focus is purely on messaging.

- **Code Structure**:
  - `feeder-service/`: Ingests and publishes.
  - `fleet-stats-service/`: Aggregates stats in memory (simple rolling window).
  - `airport-info-service/`: Uses geolocation math to match aircraft to airports.
  - `components/`: Dapr YAML configs shared across services.

This setup showcases Dapr's simplicity in handling messaging without tight coupling between services.

## Contributing

Contributions welcome! Keep it simple:
- Fork the repo.
- Add features (e.g., new subscriber services).
- Submit a PR with clear descriptions.

## License

Apache 2.0 License. See [LICENSE](LICENSE) for details.
