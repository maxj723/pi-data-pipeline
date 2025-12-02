from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
import json
import time
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

class DataAPI:
    """
    REST API for serving sensor data from TimescaleDB
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)

    def get_latest_data(self, limit=50):
        """Get the most recent sensor readings"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT node_id, timestamp, soil_moisture, sunlight,
                       temperature, humidity, battery_percentage
                FROM sensor_db
                ORDER BY timestamp DESC
                LIMIT :limit
            """), {"limit": limit})

            data = []
            for row in result:
                data.append({
                    "node_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "soil_moisture": float(row[2]) if row[2] is not None else None,
                    "sunlight": float(row[3]) if row[3] is not None else None,
                    "temperature": float(row[4]) if row[4] is not None else None,
                    "humidity": float(row[5]) if row[5] is not None else None,
                    "battery_percentage": float(row[6]) if row[6] is not None else None
                })

            return data

    def get_historical_data(self, hours=24):
        """Get historical data for the past N hours"""

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT node_id, timestamp, soil_moisture, sunlight,
                       temperature, humidity, battery_percentage
                FROM sensor_db
                WHERE timestamp >= NOW() - INTERVAL ':hours hours'
                ORDER BY timestamp ASC
            """), {"hours": hours})

            data = []
            for row in result:
                data.append({
                    "node_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "soil_moisture": float(row[2]) if row[2] is not None else None,
                    "sunlight": float(row[3]) if row[3] is not None else None,
                    "temperature": float(row[4]) if row[4] is not None else None,
                    "humidity": float(row[5]) if row[5] is not None else None,
                    "battery_percentage": float(row[6]) if row[6] is not None else None
                })

            return data

    def get_node_stats(self):
        """Get statistics per node"""

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    node_id,
                    COUNT(*) as reading_count,
                    AVG(soil_moisture) as avg_soil_moisture,
                    AVG(sunlight) as avg_sunlight,
                    AVG(temperature) as avg_temp,
                    AVG(humidity) as avg_humidity,
                    AVG(battery_percentage) as avg_battery,
                    MAX(timestamp) as last_seen
                FROM sensor_db
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY node_id
                ORDER BY last_seen DESC
            """))

            stats = []
            for row in result:
                stats.append({
                    "node_id": row[0],
                    "reading_count": row[1],
                    "avg_soil_moisture": float(row[2]) if row[2] else None,
                    "avg_sunlight": float(row[3]) if row[3] else None,
                    "avg_temp": float(row[4]) if row[4] else None,
                    "avg_humidity": float(row[5]) if row[5] else None,
                    "avg_battery": float(row[6]) if row[6] else None,
                    "last_seen": row[7].isoformat() if row[7] else None
                })

            return stats

    def get_timeseries_data(self, node_id=None, hours=12):
        """Get time-series data for charting"""

        base_query = """
            SELECT
                time_bucket('5 minutes', timestamp) AS bucket,
                node_id,
                AVG(soil_moisture) as avg_soil_moisture,
                AVG(sunlight) as avg_sunlight,
                AVG(temperature) as avg_temp,
                AVG(humidity) as avg_humidity,
                AVG(battery_percentage) as avg_battery,
                MAX(temperature) as max_temp,
                MIN(temperature) as min_temp
            FROM sensor_db
            WHERE timestamp >= NOW() - INTERVAL ':hours hours'
        """

        if node_id:
            base_query += " AND node_id = :node_id"

        base_query += """
            GROUP BY bucket, node_id
            ORDER BY bucket ASC
        """

        with self.engine.connect() as conn:
            params = {"hours": hours}
            if node_id:
                params["node_id"] = node_id

            result = conn.execute(text(base_query), params)

            data = []
            for row in result:
                data.append({
                    "timestamp": row[0].isoformat() if row[0] else None,
                    "node_id": row[1],
                    "avg_soil_moisture": float(row[2]) if row[2] else None,
                    "avg_sunlight": float(row[3]) if row[3] else None,
                    "avg_temp": float(row[4]) if row[4] else None,
                    "avg_humidity": float(row[5]) if row[5] else None,
                    "avg_battery": float(row[6]) if row[6] else None,
                    "max_temp": float(row[7]) if row[7] else None,
                    "min_temp": float(row[8]) if row[8] else None
                })

            return data

    def get_node_locations(self):
        """Get node locations for map visualization"""

        nodes = [
            {"node_id": "!MOCK_NODE_1", "lat": 39.6837, "lon": -75.7497, "name": "Mock Node 1"},
            {"node_id": "!MOCK_NODE_2", "lat": 39.6847, "lon": -75.7507, "name": "Mock Node 2"},
            {"node_id": "!MOCK_NODE_3", "lat": 39.6857, "lon": -75.7487, "name": "Mock Node 3"}
        ]

        stats = self.get_node_stats()
        node_data_map = {stat["node_id"]: stat for stat in stats}

        for node in nodes:
            if node["node_id"] in node_data_map:
                node.update(node_data_map[node["node_id"]])

        return nodes

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
        elif reading.get("battery_percentage") and reading["battery_percentage"] < 20:
            decision_text = "Low battery warning"
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
                "battery": reading.get("battery_percentage")
            }
        })

    return jsonify(decisions)

@app.route('/api/stream')
def stream():
    """Server-Sent Events endpoint for real-time updates"""
    def event_stream():
        while True:
            # Check for new data every 3 seconds
            time.sleep(3)

            # Get latest reading
            latest = api.get_latest_data(limit=1)
            if latest:
                yield f"data: {json.dumps(latest[0])}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
