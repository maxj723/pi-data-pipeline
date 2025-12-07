from flask import Flask, jsonify, Response, request
from flask_cors import CORS
import json
import time
from datetime import datetime
import os

from .data_api import DataAPI


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize DataAPI with database URL
DB_URL = os.getenv("DATABASE_URL", "postgresql://group1:meshtastic4@localhost:5432/sensor_db")
api = DataAPI(DB_URL)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/latest', methods=['GET'])
def get_latest():
    """Get latest sensor readings"""
    limit = request.args.get('limit', 50, type=int)
    data = api.get_latest_data(limit=limit)
    return jsonify(data)

@app.route('/api/historical', methods=['GET'])
def get_historical():
    """Get historical data"""
    hours = request.args.get('hours', 24, type=int)
    data = api.get_historical_data(hours=hours)
    return jsonify(data)

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Get node statistics"""
    stats = api.get_node_stats()
    return jsonify(stats)

@app.route('/api/nodes/locations', methods=['GET'])
def get_node_locations():
    """Get node locations with latest sensor data"""
    locations = api.get_node_locations()
    return jsonify(locations)

@app.route('/api/timeseries', methods=['GET'])
def get_timeseries():
    """Get time-series data for charts"""
    node_id = request.args.get('node_id', None)
    hours = request.args.get('hours', 12, type=int)
    data = api.get_timeseries_data(node_id=node_id, hours=hours)
    return jsonify(data)

# Temporary -- will replace with decision model class
@app.route('/api/decisions', methods=['GET'])
def get_decisions():
    """Get ML model decisions"""
    latest = api.get_latest_data(limit=10)

    decisions = []
    for reading in latest:
        # Simple rule-based decisions as placeholder
        decision_text = "Normal operation"
        action = "none"
        confidence = 0.95

        if reading.get("soil_moisture") and reading["soil_moisture"] < 30:
            decision_text = "Low soil moisture detected"
            action = "water_needed"
            confidence = 0.88
        elif reading.get("voltage") and reading["voltage"] < 3.0:
            decision_text = "Low voltage warning"
            action = "check_battery"
            confidence = 1.0
        elif reading.get("temperature") and reading["temperature"] > 35:
            decision_text = "High temperature alert"
            action = "monitor_temperature"
            confidence = 0.92

        decisions.append({
            "node_id": reading["node_id"],
            "decision": decision_text,
            "confidence": confidence,
            "timestamp": reading["timestamp"],
            "action": action,
            "metrics": {
                "soil_moisture": reading.get("soil_moisture"),
                "temperature": reading.get("temperature"),
                "voltage": reading.get("voltage")
            }
        })

    return jsonify(decisions)

@app.route('/api/stream')
def stream():
    """Server-Sent Events endpoint for real-time updates"""
    def event_stream():
        # Send initial comment to establish connection
        yield ": connected\n\n"

        last_id = None
        while True:
            try:
                # Get latest reading
                latest = api.get_latest_data(limit=1)
                if latest and latest[0]:
                    current_id = f"{latest[0].get('node_id')}_{latest[0].get('timestamp')}"

                    # Only send if it's new data
                    if current_id != last_id:
                        yield f"data: {json.dumps(latest[0])}\n\n"
                        last_id = current_id
                    else:
                        # Send keepalive comment
                        yield ": keepalive\n\n"
                else:
                    # Send keepalive if no data
                    yield ": keepalive\n\n"

                # Wait 3 seconds before next check
                time.sleep(3)
            except Exception as e:
                print(f"SSE Error: {e}")
                yield f": error {str(e)}\n\n"
                time.sleep(3)

    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
