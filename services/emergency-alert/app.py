"""
Emergency Alert Service
Subscribes to flight-update topic and monitors for emergency squawk codes (7700, 7500, 7600).
Displays active alerts in a web UI and exposes REST API endpoints.
"""

import os
import json
import logging
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

PORT = int(os.getenv("PORT", "3005"))

# Emergency squawk codes
EMERGENCY_SQUAWK_CODES = {
    "7700": "General Emergency",
    "7500": "Aircraft Hijacking",
    "7600": "Radio Communication Failure"
}

# Store active alerts (in-memory, can be persisted to state store if needed)
# Format: {alert_id: {flight_data, timestamp, squawk_code, description}}
active_alerts: Dict[str, dict] = {}

# Store alert history (last 100 alerts)
alert_history: deque = deque(maxlen=100)

# Lock for thread safety (if needed)
alerts_lock = False

def get_alert_id(flight_data: dict) -> str:
    """Generate unique alert ID from flight data."""
    icao24 = flight_data.get('icao24', 'unknown')
    timestamp = datetime.utcnow().isoformat()
    return f"{icao24}-{timestamp}"

def check_emergency_squawk(flight_data: dict) -> Optional[str]:
    """Check if flight has an emergency squawk code."""
    squawk = flight_data.get('squawk')
    if not squawk:
        return None
    
    squawk_str = str(squawk).strip()
    if squawk_str in EMERGENCY_SQUAWK_CODES:
        return squawk_str
    
    return None

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "emergency-alert"}

@app.post("/flight-update")
async def flight_update_handler(request: Request):
    """
    Handle flight update messages from Dapr Pub/Sub.
    Checks for emergency squawk codes and creates alerts.
    """
    try:
        body = await request.json()
        
        # Extract flight data from CloudEvents format
        flight_data = None
        if 'data' in body:
            # CloudEvents format - data is base64 encoded or JSON string
            data = body['data']
            if isinstance(data, str):
                try:
                    flight_data = json.loads(data)
                except json.JSONDecodeError:
                    flight_data = data
            else:
                flight_data = data
        else:
            # Direct JSON format
            flight_data = body
        
        if not flight_data:
            logger.warning("No flight data found in message")
            return {"status": "error", "message": "No flight data found"}
        
        # Check for emergency squawk code
        squawk_code = check_emergency_squawk(flight_data)
        
        if squawk_code:
            # Emergency detected!
            alert_id = get_alert_id(flight_data)
            alert_description = EMERGENCY_SQUAWK_CODES[squawk_code]
            
            alert_record = {
                "alert_id": alert_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "squawk_code": squawk_code,
                "description": alert_description,
                "flight": {
                    "icao24": flight_data.get('icao24', 'unknown'),
                    "callsign": flight_data.get('callsign', 'unknown'),
                    "latitude": flight_data.get('latitude'),
                    "longitude": flight_data.get('longitude'),
                    "baro_altitude": flight_data.get('baro_altitude'),
                    "velocity": flight_data.get('velocity'),
                    "origin_country": flight_data.get('origin_country', 'unknown')
                }
            }
            
            # Store as active alert
            active_alerts[alert_id] = alert_record
            
            # Add to history
            alert_history.append(alert_record.copy())
            
            logger.warning(f"🚨 EMERGENCY ALERT: {alert_description} - Flight {flight_data.get('callsign', 'unknown')} ({flight_data.get('icao24', 'unknown')}) - Squawk: {squawk_code}")
            return {"status": "alert_created", "alert_id": alert_id, "squawk_code": squawk_code}
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing flight update: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/", response_class=HTMLResponse)
async def alerts_ui():
    """Web UI for displaying active emergency alerts."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emergency Alerts - ADS-B Tracker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        h1 {
            color: #d32f2f;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        
        .alert-badge {
            display: inline-block;
            background: #d32f2f;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        
        .alert-card {
            background: white;
            border-left: 5px solid #d32f2f;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .alert-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .alert-type {
            font-size: 24px;
            font-weight: bold;
            color: #d32f2f;
        }
        
        .squawk-code {
            background: #f44336;
            color: white;
            padding: 5px 12px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 14px;
        }
        
        .alert-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .detail-item {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
        }
        
        .detail-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .detail-value {
            font-size: 16px;
            font-weight: bold;
            color: #333;
        }
        
        .no-alerts {
            background: white;
            padding: 40px;
            text-align: center;
            border-radius: 10px;
            color: #666;
        }
        
        .no-alerts-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        
        .refresh-info {
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 20px;
            font-size: 14px;
        }
        
        .timestamp {
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚨 Emergency Alerts <span id="alertCount" class="alert-badge">0</span></h1>
            <p class="subtitle">Real-time monitoring of emergency squawk codes (7700, 7500, 7600)</p>
        </header>
        
        <div id="alertsContainer"></div>
        
        <p class="refresh-info">Auto-refreshing every 5 seconds</p>
    </div>
    
    <script>
        const alertTypes = {
            '7700': '🚨 General Emergency',
            '7500': '✈️ Aircraft Hijacking',
            '7600': '📻 Radio Communication Failure'
        };
        
        const alertColors = {
            '7700': '#d32f2f',
            '7500': '#c62828',
            '7600': '#ef6c00'
        };
        
        function formatTimestamp(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleString();
        }
        
        function renderAlerts(alerts) {
            const container = document.getElementById('alertsContainer');
            const countBadge = document.getElementById('alertCount');
            
            const alertsArray = Object.values(alerts);
            countBadge.textContent = alertsArray.length;
            
            if (alertsArray.length === 0) {
                container.innerHTML = `
                    <div class="no-alerts">
                        <div class="no-alerts-icon">✅</div>
                        <h2>No Active Emergency Alerts</h2>
                        <p>All flights are operating normally.</p>
                    </div>
                `;
                return;
            }
            
            // Sort by timestamp (most recent first)
            alertsArray.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            container.innerHTML = alertsArray.map(alert => {
                const flight = alert.flight;
                const color = alertColors[alert.squawk_code] || '#d32f2f';
                
                return `
                    <div class="alert-card" style="border-left-color: ${color}">
                        <div class="alert-header">
                            <div class="alert-type">${alertTypes[alert.squawk_code] || '🚨 Emergency'}</div>
                            <div class="squawk-code">Squawk: ${alert.squawk_code}</div>
                        </div>
                        <p style="color: #666; margin-bottom: 15px;">${alert.description}</p>
                        <div class="alert-details">
                            <div class="detail-item">
                                <div class="detail-label">Callsign</div>
                                <div class="detail-value">${flight.callsign || 'Unknown'}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">ICAO24</div>
                                <div class="detail-value">${flight.icao24 || 'Unknown'}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Origin</div>
                                <div class="detail-value">${flight.origin_country || 'Unknown'}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Altitude</div>
                                <div class="detail-value">${flight.baro_altitude ? flight.baro_altitude.toFixed(0) + ' m' : 'N/A'}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Speed</div>
                                <div class="detail-value">${flight.velocity ? flight.velocity.toFixed(0) + ' m/s' : 'N/A'}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Position</div>
                                <div class="detail-value">${flight.latitude ? flight.latitude.toFixed(4) + ', ' + flight.longitude.toFixed(4) : 'N/A'}</div>
                            </div>
                        </div>
                        <div class="timestamp" style="margin-top: 15px;">Alert Time: ${formatTimestamp(alert.timestamp)}</div>
                    </div>
                `;
            }).join('');
        }
        
        async function loadAlerts() {
            try {
                const response = await fetch('/api/v1/alerts/active');
                const data = await response.json();
                renderAlerts(data.alerts || {});
            } catch (error) {
                console.error('Error loading alerts:', error);
            }
        }
        
        // Load alerts on page load
        loadAlerts();
        
        // Auto-refresh every 5 seconds
        setInterval(loadAlerts, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/v1/alerts/active")
async def get_active_alerts():
    """Get all active emergency alerts."""
    return {
        "alerts": active_alerts,
        "count": len(active_alerts),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/v1/alerts/history")
async def get_alert_history(limit: int = 50):
    """Get alert history (most recent alerts)."""
    history_list = list(alert_history)
    # Sort by timestamp (most recent first)
    history_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    # Limit results
    history_list = history_list[:limit]
    
    return {
        "history": history_list,
        "count": len(history_list),
        "total": len(alert_history),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.delete("/api/v1/alerts/{alert_id}")
async def clear_alert(alert_id: str):
    """Clear a specific alert (mark as resolved)."""
    if alert_id in active_alerts:
        del active_alerts[alert_id]
        return {"status": "success", "message": f"Alert {alert_id} cleared"}
    return {"status": "error", "message": "Alert not found"}

@app.delete("/api/v1/alerts/clear-all")
async def clear_all_alerts():
    """Clear all active alerts."""
    count = len(active_alerts)
    active_alerts.clear()
    return {"status": "success", "message": f"Cleared {count} alerts"}

if __name__ == "__main__":
    import uvicorn
    logger.info("🚨 Emergency Alert Service starting...")
    logger.info(f"Monitoring for emergency squawk codes: {list(EMERGENCY_SQUAWK_CODES.keys())}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

