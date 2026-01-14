"""
Flight Archiver Service
Subscribes to flight-update topic and archives all flight updates to local file storage using Dapr Output Binding.
"""

import os
import json
import logging
import http.client
from datetime import datetime
from fastapi import FastAPI, Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Dapr configuration
DAPR_HTTP_PORT = int(os.getenv("DAPR_HTTP_PORT", "3504"))
BINDING_NAME = "filebinding"  # Name of the output binding component

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "flight-archiver"}

@app.post("/flight-update")
async def flight_update_handler(request: Request):
    """
    Handle flight update messages from Dapr Pub/Sub.
    Archives each flight update to local file storage using Dapr Output Binding.
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
                    # If not JSON, try to parse as-is
                    flight_data = data
            else:
                flight_data = data
        else:
            # Direct JSON format
            flight_data = body
        
        if not flight_data:
            logger.warning("No flight data found in message")
            return {"status": "error", "message": "No flight data found"}
        
        # Add timestamp to flight data for archiving
        archive_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "flight": flight_data
        }
        
        # Use Dapr Output Binding to write to file storage via HTTP API
        # Format: POST http://localhost:<DAPR_HTTP_PORT>/v1.0/bindings/<binding_name>
        try:
            # Invoke output binding using HTTP API directly
            timestamp_str = datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')[:-3]  # Include milliseconds
            file_name = f"flight-{flight_data.get('icao24', 'unknown')}-{timestamp_str}.json"
            
            # Prepare binding request
            binding_request = {
                "operation": "create",
                "data": json.dumps(archive_record),
                "metadata": {
                    "fileName": file_name
                }
            }
            
            # Call Dapr HTTP API for bindings
            conn = http.client.HTTPConnection("127.0.0.1", DAPR_HTTP_PORT, timeout=5)
            try:
                conn.request(
                    "POST",
                    f"/v1.0/bindings/{BINDING_NAME}",
                    json.dumps(binding_request),
                    {"Content-Type": "application/json"}
                )
                response = conn.getresponse()
                response_data = response.read().decode('utf-8')
                
                if response.status >= 200 and response.status < 300:
                    logger.info(f"Archived flight update: {flight_data.get('callsign', 'unknown')} ({flight_data.get('icao24', 'unknown')})")
                    return {"status": "success", "archived": True}
                else:
                    logger.error(f"Binding API returned status {response.status}: {response_data}")
                    return {"status": "error", "message": f"HTTP {response.status}: {response_data}"}
            finally:
                conn.close()
            
        except Exception as binding_error:
            logger.error(f"Error writing to binding: {binding_error}")
            return {"status": "error", "message": str(binding_error)}
            
    except Exception as e:
        logger.error(f"Error processing flight update: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3004)

