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
    'by_destination': {},
    'by_origin': {},
    'by_aircraft_type': {},
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

def infer_destination_from_flight(flight):
    """
    Infer destination airport from flight data.
    In mock mode, we'll use synthetic logic based on position and callsign.
    """
    # Major airports for demo purposes
    airports = {
        'KJFK': 'John F. Kennedy International Airport',
        'KLAX': 'Los Angeles International Airport',
        'EGLL': 'London Heathrow Airport',
        'YSSY': 'Sydney Kingsford Smith Airport',
        'OMDB': 'Dubai International Airport',
        'KORD': 'Chicago O\'Hare International Airport',
        'KDFW': 'Dallas/Fort Worth International Airport',
        'KATL': 'Hartsfield-Jackson Atlanta International Airport'
    }
    
    # Infer from position (closest major airport)
    lat = flight.get('latitude')
    lon = flight.get('longitude')
    
    if lat and lon:
        # Simple distance-based inference (for demo)
        # In real system, would use proper airport database
        airport_distances = {
            'KJFK': ((lat - 40.6413)**2 + (lon + 73.7781)**2)**0.5,
            'KLAX': ((lat - 33.9425)**2 + (lon + 118.4081)**2)**0.5,
            'EGLL': ((lat - 51.47)**2 + (lon + 0.4543)**2)**0.5,
            'YSSY': ((lat + 33.9399)**2 + (lon - 151.1753)**2)**0.5,
            'OMDB': ((lat - 25.2532)**2 + (lon - 55.3657)**2)**0.5,
            'KORD': ((lat - 41.9786)**2 + (lon + 87.9048)**2)**0.5,
            'KDFW': ((lat - 32.8998)**2 + (lon + 97.0403)**2)**0.5,
            'KATL': ((lat - 33.6407)**2 + (lon + 84.4277)**2)**0.5
        }
        
        # Find closest airport
        closest = min(airport_distances.items(), key=lambda x: x[1])
        if closest[1] < 50:  # Within reasonable distance (degrees)
            return closest[0]
    
    # Fallback: infer from callsign pattern (synthetic)
    callsign = flight.get('callsign', '').strip()
    if callsign:
        # Use flight number modulo to assign destination
        try:
            flight_num = int(''.join(filter(str.isdigit, callsign)) or '0')
            airport_list = list(airports.keys())
            return airport_list[flight_num % len(airport_list)]
        except:
            pass
    
    return 'Unknown'

def infer_origin_from_flight(flight):
    """
    Infer origin airport from flight data.
    In mock mode, we'll use synthetic logic.
    """
    # For demo, use origin_country to infer origin airport
    origin_country = flight.get('origin_country', '')
    
    # Map countries to common origin airports
    country_airports = {
        'United States': ['KJFK', 'KLAX', 'KORD', 'KDFW', 'KATL'],
        'United Kingdom': ['EGLL'],
        'Australia': ['YSSY'],
        'United Arab Emirates': ['OMDB']
    }
    
    if origin_country in country_airports:
        airports = country_airports[origin_country]
        # Use icao24 hash to consistently assign origin
        icao24 = flight.get('icao24', '')
        if icao24:
            idx = hash(icao24) % len(airports)
            return airports[idx]
        return airports[0]
    
    # Fallback: infer from callsign
    callsign = flight.get('callsign', '').strip()
    if callsign:
        try:
            flight_num = int(''.join(filter(str.isdigit, callsign)) or '0')
            # Use different offset for origin vs destination
            default_airports = ['KJFK', 'KLAX', 'EGLL', 'YSSY', 'OMDB']
            return default_airports[(flight_num + 1) % len(default_airports)]
        except:
            pass
    
    return 'Unknown'

def infer_aircraft_type_from_flight(flight):
    """
    Infer aircraft type from flight data.
    In mock mode, use synthetic logic based on callsign patterns.
    """
    callsign = flight.get('callsign', '').strip()
    
    # Aircraft type lookup based on airline and flight number patterns
    # This is synthetic for demo purposes
    aircraft_types = {
        'Narrow Body': ['B737', 'A320', 'A321', 'B757'],
        'Wide Body': ['B777', 'B787', 'A330', 'A350', 'B747'],
        'Regional': ['CRJ', 'ERJ', 'E175', 'E190'],
        'Cargo': ['B767', 'B777F', 'A330F']
    }
    
    # Use callsign hash to consistently assign aircraft type
    if callsign:
        hash_val = hash(callsign) % 100
        if hash_val < 50:
            return 'Narrow Body'
        elif hash_val < 80:
            return 'Wide Body'
        elif hash_val < 95:
            return 'Regional'
        else:
            return 'Cargo'
    
    # Fallback based on altitude/velocity (synthetic)
    altitude = flight.get('baro_altitude', 0) or 0
    velocity = flight.get('velocity', 0) or 0
    
    if altitude > 10000 and velocity > 200:
        return 'Wide Body'
    elif altitude > 5000:
        return 'Narrow Body'
    else:
        return 'Regional'

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
            'by_destination': {},
            'by_origin': {},
            'by_aircraft_type': {},
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
        
        # Infer destination and origin
        destination = infer_destination_from_flight(flight)
        origin = infer_origin_from_flight(flight)
        aircraft_type = infer_aircraft_type_from_flight(flight)
        
        # Update airline statistics
        if airline not in stats['by_airline']:
            stats['by_airline'][airline] = {
                'count': 0,
                'total_altitude': 0,
                'total_velocity': 0,
                'samples': 0
            }
        
        stats['by_airline'][airline]['count'] += 1
        stats['by_airline'][airline]['samples'] += 1
        
        if flight.get('baro_altitude'):
            stats['by_airline'][airline]['total_altitude'] += flight['baro_altitude']
        if flight.get('velocity'):
            stats['by_airline'][airline]['total_velocity'] += flight['velocity']
        
        # Update destination statistics
        if destination not in stats['by_destination']:
            stats['by_destination'][destination] = {
                'count': 0,
                'total_altitude': 0,
                'total_velocity': 0,
                'samples': 0
            }
        
        stats['by_destination'][destination]['count'] += 1
        stats['by_destination'][destination]['samples'] += 1
        
        if flight.get('baro_altitude'):
            stats['by_destination'][destination]['total_altitude'] += flight['baro_altitude']
        if flight.get('velocity'):
            stats['by_destination'][destination]['total_velocity'] += flight['velocity']
        
        # Update origin statistics
        if origin not in stats['by_origin']:
            stats['by_origin'][origin] = {
                'count': 0,
                'total_altitude': 0,
                'total_velocity': 0,
                'samples': 0
            }
        
        stats['by_origin'][origin]['count'] += 1
        stats['by_origin'][origin]['samples'] += 1
        
        if flight.get('baro_altitude'):
            stats['by_origin'][origin]['total_altitude'] += flight['baro_altitude']
        if flight.get('velocity'):
            stats['by_origin'][origin]['total_velocity'] += flight['velocity']
        
        # Update aircraft type statistics
        if aircraft_type not in stats['by_aircraft_type']:
            stats['by_aircraft_type'][aircraft_type] = {
                'count': 0,
                'total_altitude': 0,
                'total_velocity': 0,
                'samples': 0
            }
        
        stats['by_aircraft_type'][aircraft_type]['count'] += 1
        stats['by_aircraft_type'][aircraft_type]['samples'] += 1
        
        if flight.get('baro_altitude'):
            stats['by_aircraft_type'][aircraft_type]['total_altitude'] += flight['baro_altitude']
        if flight.get('velocity'):
            stats['by_aircraft_type'][aircraft_type]['total_velocity'] += flight['velocity']
        
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

@app.get("/api/v1/fleet/stats/by-destination")
async def get_by_destination():
    """Get statistics grouped by destination airport."""
    result = {}
    for destination, data in stats['by_destination'].items():
        avg_altitude = data['total_altitude'] / data['samples'] if data['samples'] > 0 else 0
        avg_velocity = data['total_velocity'] / data['samples'] if data['samples'] > 0 else 0
        
        result[destination] = {
            "count": data['count'],
            "avg_altitude": round(avg_altitude, 2),
            "avg_velocity": round(avg_velocity, 2)
        }
    return result

@app.get("/api/v1/fleet/stats/by-origin")
async def get_by_origin():
    """Get statistics grouped by origin airport."""
    result = {}
    for origin, data in stats['by_origin'].items():
        avg_altitude = data['total_altitude'] / data['samples'] if data['samples'] > 0 else 0
        avg_velocity = data['total_velocity'] / data['samples'] if data['samples'] > 0 else 0
        
        result[origin] = {
            "count": data['count'],
            "avg_altitude": round(avg_altitude, 2),
            "avg_velocity": round(avg_velocity, 2)
        }
    return result

@app.get("/api/v1/fleet/stats/by-aircraft-type")
async def get_by_aircraft_type():
    """Get statistics grouped by aircraft type."""
    result = {}
    for aircraft_type, data in stats['by_aircraft_type'].items():
        avg_altitude = data['total_altitude'] / data['samples'] if data['samples'] > 0 else 0
        avg_velocity = data['total_velocity'] / data['samples'] if data['samples'] > 0 else 0
        
        result[aircraft_type] = {
            "count": data['count'],
            "avg_altitude": round(avg_altitude, 2),
            "avg_velocity": round(avg_velocity, 2)
        }
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

