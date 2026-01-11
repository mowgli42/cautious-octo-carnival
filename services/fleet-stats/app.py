"""
Fleet Stats Service - Python service that subscribes to flight-update events
and aggregates statistics by airline, destination, origin, and aircraft type.

This demonstrates:
1. Dapr Pub/Sub subscription
2. Dapr State Store for persistence
"""

from fastapi import FastAPI, Request
from dapr.clients import DaprClient
import json
import os
import time

app = FastAPI(title="Fleet Stats Service")

PORT = int(os.getenv("PORT", "3001"))

# In-memory statistics (will be persisted to state store)
stats = {
    'by_airline': {},
    'total_active': 0,
    'last_update': None
}

# Dapr client for state operations
# Connect to Dapr sidecar on localhost (shared network namespace)
# Dapr Python SDK uses DAPR_HTTP_PORT environment variable automatically
dapr_client = DaprClient()

# State store component name
STATESTORE_NAME = 'statestore'

def get_airline_from_callsign(callsign):
    """Extract airline from callsign (first 2 letters)."""
    if not callsign or len(callsign) < 2:
        return 'Unknown'
    
    airline_codes = {
        'DL': 'Delta',
        'UA': 'United',
        'WN': 'Southwest',
        'QF': 'Qantas',
        'EK': 'Emirates'
    }
    
    code = callsign[:2].strip()
    return airline_codes.get(code, 'Other')

def load_stats_from_state():
    """Load statistics from Dapr state store."""
    global stats
    try:
        # Try to get stats from state store
        response = dapr_client.get_state(STATESTORE_NAME, "fleet:stats:summary")
        if response.data:
            stats = json.loads(response.data.decode('utf-8'))
            print(f"✓ Loaded stats from state store: {stats['total_active']} total flights")
    except Exception as e:
        print(f"⚠ Could not load from state store (first run?): {e}")
        # Start with empty stats
        stats = {
            'by_airline': {},
            'total_active': 0,
            'last_update': None
        }

def save_stats_to_state():
    """Save statistics to Dapr state store."""
    try:
        stats['last_update'] = time.time()
        dapr_client.save_state(
            STATESTORE_NAME,
            "fleet:stats:summary",
            json.dumps(stats).encode('utf-8')
        )
    except Exception as e:
        print(f"⚠ Error saving to state store: {e}")

# Subscribe to flight-update topic
# Dapr will call this endpoint when messages arrive on the flight-update topic
@app.post("/flight-update")
async def flight_update_handler(request: Request):
    """Handle flight update events from Pub/Sub."""
    try:
        # Get the raw request body
        body = await request.json()
        
        # Dapr wraps the data in CloudEvents format
        # Extract the actual flight data
        if 'data' in body:
            # CloudEvents format
            if isinstance(body['data'], str):
                flight = json.loads(body['data'])
            else:
                flight = body['data']
        elif 'data_base64' in body:
            # Base64 encoded data (unlikely but possible)
            import base64
            decoded = base64.b64decode(body['data_base64'])
            flight = json.loads(decoded.decode('utf-8'))
        else:
            # Direct data
            flight = body
        
        # Extract airline
        airline = get_airline_from_callsign(flight.get('callsign', ''))
        
        # Update statistics
        if airline not in stats['by_airline']:
            stats['by_airline'][airline] = {
                'count': 0,
                'total_altitude': 0,
                'total_velocity': 0,
                'samples': 0
            }
        
        # Count unique flights by tracking icao24
        # For simplicity, we'll just count updates (in real system, we'd track unique flights)
        stats['by_airline'][airline]['count'] += 1
        stats['by_airline'][airline]['samples'] += 1
        
        # Add altitude and velocity for averages
        if flight.get('baro_altitude'):
            stats['by_airline'][airline]['total_altitude'] += flight['baro_altitude']
        if flight.get('velocity'):
            stats['by_airline'][airline]['total_velocity'] += flight['velocity']
        
        # Calculate total active flights (sum of counts)
        stats['total_active'] = sum(a['count'] for a in stats['by_airline'].values())
        
        # Save to state store periodically (every 10 updates)
        if stats['total_active'] % 10 == 0:
            save_stats_to_state()
        
        print(f"📊 Updated stats: {airline} = {stats['by_airline'][airline]['count']} | Total: {stats['total_active']}")
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ Error processing flight update: {e}")
        return {"status": "error", "message": str(e)}

# REST API endpoints
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "fleet-stats"
    }

@app.get("/api/v1/fleet/stats/summary")
async def get_summary():
    """Get overall fleet statistics summary."""
    # Calculate averages
    summary = {
        "timestamp": time.time(),
        "total_active_flights": stats['total_active'],
        "by_airline": {},
        "airlines_with_10_plus_flights": []
    }
    
    for airline, data in stats['by_airline'].items():
        avg_altitude = data['total_altitude'] / data['samples'] if data['samples'] > 0 else 0
        avg_velocity = data['total_velocity'] / data['samples'] if data['samples'] > 0 else 0
        
        airline_stats = {
            "count": data['count'],
            "avg_altitude": round(avg_altitude, 2),
            "avg_velocity": round(avg_velocity, 2)
        }
        
        summary['by_airline'][airline] = airline_stats
        
        # Add to airlines with 10+ flights list
        if data['count'] > 10:
            summary['airlines_with_10_plus_flights'].append(airline)
    
    # Sort airlines with 10+ flights by count (descending)
    summary['airlines_with_10_plus_flights'].sort(
        key=lambda x: summary['by_airline'][x]['count'],
        reverse=True
    )
    
    return summary

@app.get("/api/v1/fleet/stats/by-airline")
async def get_by_airline():
    """Get statistics grouped by airline."""
    result = {}
    for airline, data in stats['by_airline'].items():
        avg_altitude = data['total_altitude'] / data['samples'] if data['samples'] > 0 else 0
        avg_velocity = data['total_velocity'] / data['samples'] if data['samples'] > 0 else 0
        
        result[airline] = {
            "count": data['count'],
            "avg_altitude": round(avg_altitude, 2),
            "avg_velocity": round(avg_velocity, 2)
        }
    return result

@app.get("/api/v1/fleet/stats/airlines-with-min-flights")
async def get_airlines_with_min_flights(min_flights: int = 10):
    """
    Get list of airlines with more than the specified number of flights.
    
    Query parameter:
    - min_flights: Minimum number of flights required (default: 10)
    """
    result = {
        "min_flights": min_flights,
        "airlines": [],
        "count": 0
    }
    
    for airline, data in stats['by_airline'].items():
        if data['count'] > min_flights:
            avg_altitude = data['total_altitude'] / data['samples'] if data['samples'] > 0 else 0
            avg_velocity = data['total_velocity'] / data['samples'] if data['samples'] > 0 else 0
            
            result['airlines'].append({
                "airline": airline,
                "count": data['count'],
                "avg_altitude": round(avg_altitude, 2),
                "avg_velocity": round(avg_velocity, 2)
            })
            result['count'] += 1
    
    # Sort by count (descending)
    result['airlines'].sort(key=lambda x: x['count'], reverse=True)
    
    return result

@app.on_event("startup")
async def startup():
    """Load statistics from state store on startup."""
    print("🚀 Fleet Stats Service starting...")
    load_stats_from_state()
    print(f"📊 Current stats: {stats['total_active']} total flights")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

