const express = require('express');
const { DaprClient } = require('@dapr/dapr');

const app = express();
const PORT = process.env.PORT || 3000;
const MOCK_MODE = process.env.MOCK_MODE === 'true';

// Initialize Dapr client
// In Docker, the sidecar runs in the same network namespace, so we use localhost
// The sidecar HTTP port defaults to 3500 (DAPR_HTTP_PORT env var)
const DAPR_HTTP_PORT = process.env.DAPR_HTTP_PORT || 3500;
const daprClient = new DaprClient({
  daprHost: 'localhost',  // sidecar host (same container in Docker)
  daprPort: DAPR_HTTP_PORT.toString()  // sidecar HTTP port
});

const PUBSUB_NAME = 'pubsub';
const TOPIC_NAME = 'flight-update';

// Mock flight data generator
class MockFlightGenerator {
  constructor() {
    this.airlines = ['Delta', 'United', 'Southwest', 'Qantas', 'Emirates'];
    this.airlineCodes = {
      'Delta': 'DL',
      'United': 'UA',
      'Southwest': 'WN',
      'Qantas': 'QF',
      'Emirates': 'EK'
    };
    this.flights = [];
    this.startTime = Date.now();
    this.loopDuration = 20 * 60 * 1000; // 20 minutes in milliseconds
    
    // Initialize flights for the airlines
    this.initializeFlights();
  }

  initializeFlights() {
    let flightNumber = 100;
    this.airlines.forEach((airline, idx) => {
      // Create 5-10 flights per airline
      const numFlights = 5 + Math.floor(Math.random() * 6);
      for (let i = 0; i < numFlights; i++) {
        const icao24 = this.generateICAO24();
        this.flights.push({
          icao24: icao24,
          callsign: `${this.airlineCodes[airline]}${flightNumber + i}`,
          airline: airline,
          airlineCode: this.airlineCodes[airline],
          // Start positions around major airports
          startLat: 40.0 + (idx * 10) + (Math.random() * 5),
          startLon: -75.0 - (idx * 10) + (Math.random() * 5),
          // Destination positions
          endLat: 50.0 + (idx * 5) + (Math.random() * 5),
          endLon: -80.0 + (idx * 5) + (Math.random() * 5),
          speed: 200 + Math.random() * 50, // m/s
          altitude: 10000 + Math.random() * 35000, // meters
        });
      }
      flightNumber += 1000;
    });
  }

  generateICAO24() {
    // Generate a random ICAO24 hex identifier
    return Math.floor(Math.random() * 0xFFFFFF).toString(16).toUpperCase().padStart(6, '0');
  }

  getCurrentPosition(flight, elapsed) {
    const progress = (elapsed % this.loopDuration) / this.loopDuration;
    
    // Interpolate between start and end position
    const lat = flight.startLat + (flight.endLat - flight.startLat) * progress;
    const lon = flight.startLon + (flight.endLon - flight.startLon) * progress;
    
    // Add some variation
    const latVariation = (Math.sin(progress * Math.PI * 2) * 0.5);
    const lonVariation = (Math.cos(progress * Math.PI * 2) * 0.5);
    
    return {
      latitude: lat + latVariation,
      longitude: lon + lonVariation,
      altitude: flight.altitude + Math.sin(progress * Math.PI * 4) * 2000,
      velocity: flight.speed + Math.random() * 10 - 5,
      true_track: (progress * 360) % 360,
      vertical_rate: Math.sin(progress * Math.PI * 6) * 5,
    };
  }

  generateFlights() {
    const elapsed = Date.now() - this.startTime;
    const updates = [];
    
    this.flights.forEach(flight => {
      const pos = this.getCurrentPosition(flight, elapsed);
      
      // Create flight update message matching the schema
      const flightUpdate = {
        icao24: flight.icao24,
        callsign: flight.callsign.trim().padEnd(8, ' '),
        origin_country: 'United States',
        time_position: Math.floor(Date.now() / 1000),
        last_contact: Math.floor(Date.now() / 1000),
        longitude: pos.longitude,
        latitude: pos.latitude,
        baro_altitude: pos.altitude,
        geo_altitude: pos.altitude,
        on_ground: false,
        velocity: pos.velocity,
        true_track: pos.true_track,
        vertical_rate: pos.vertical_rate,
        squawk: '1200', // Normal squawk code
        spi: false,
        position_source: 0, // ADS-B
        timestamp: Math.floor(Date.now() / 1000),
        // Additional fields for our demo
        airline: flight.airline,
        airlineCode: flight.airlineCode
      };
      
      // Occasionally add emergency squawk codes
      if (Math.random() < 0.02) { // 2% chance
        flightUpdate.squawk = ['7700', '7500', '7600'][Math.floor(Math.random() * 3)];
      }
      
      updates.push(flightUpdate);
    });
    
    return updates;
  }
}

// Initialize mock generator if in mock mode
let mockGenerator = null;
if (MOCK_MODE) {
  mockGenerator = new MockFlightGenerator();
  console.log('✓ Mock Mode enabled - generating synthetic flight data');
  console.log(`  Total flights: ${mockGenerator.flights.length}`);
}

// Publish flight updates
async function publishFlightUpdates() {
  try {
    let flightUpdates = [];
    
    if (MOCK_MODE && mockGenerator) {
      flightUpdates = mockGenerator.generateFlights();
    } else {
      // TODO: In real mode, fetch from OpenSky Network API
      // Real API integration planned for Phase 6 - see DAPR_DEMO_PLAN.md
      console.log('Real API mode not yet implemented - using mock mode');
      if (!mockGenerator) {
        mockGenerator = new MockFlightGenerator();
      }
      flightUpdates = mockGenerator.generateFlights();
    }

    // Publish each flight update to Dapr Pub/Sub
    for (const update of flightUpdates) {
      await daprClient.pubsub.publish(PUBSUB_NAME, TOPIC_NAME, update);
      console.log(`Published: ${update.callsign.trim()} @ ${update.latitude.toFixed(2)}, ${update.longitude.toFixed(2)}`);
    }
    
    console.log(`✓ Published ${flightUpdates.length} flight updates to topic '${TOPIC_NAME}'`);
  } catch (error) {
    console.error('Error publishing flight updates:', error);
  }
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    mode: MOCK_MODE ? 'mock' : 'real',
    service: 'adsb-feeder'
  });
});

app.listen(PORT, () => {
  console.log(`🚀 ADS-B Feeder service listening on port ${PORT}`);
  console.log(`📡 Dapr Pub/Sub: ${PUBSUB_NAME} / Topic: ${TOPIC_NAME}`);
  
  // Start publishing flight updates every 5 seconds
  publishFlightUpdates();
  setInterval(publishFlightUpdates, 5000);
});

