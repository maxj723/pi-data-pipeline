from flask import Flask, jsonify, Response, request
from flask_cors import CORS
import json
import time
import csv
import io
from datetime import datetime
import os

# Handle both relative and absolute imports
try:
    from .data_api import DataAPI
except ImportError:
    from data_api import DataAPI

try:
    from ..models import ThresholdDecisionModel
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from models import ThresholdDecisionModel


app = Flask(__name__)
CORS(app)

DB_URL = os.getenv("DATABASE_URL", "postgresql://group1:meshtastic4@localhost:5432/sensor_db")
api = DataAPI(DB_URL)

decision_model = ThresholdDecisionModel()

# Path to local decision storage file
DECISIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'decisions.json')

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
    """Get time-series data for charts with optional custom date range"""
    node_id = request.args.get('node_id', None)
    hours = request.args.get('hours', None, type=int)
    start_time = request.args.get('start', None)
    end_time = request.args.get('end', None)

    data = api.get_timeseries_data(
        node_id=node_id,
        hours=hours,
        start_time=start_time,
        end_time=end_time
    )
    return jsonify(data)

@app.route('/api/decisions', methods=['GET'])
def get_decisions():
    """Get decisions from local storage file"""
    try:
        if not os.path.exists(DECISIONS_FILE):
            return jsonify([])

        with open(DECISIONS_FILE, 'r') as f:
            decisions = json.load(f)

        # Return most recent decisions first
        decisions.reverse()

        # Apply limit if specified
        limit = request.args.get('limit', None, type=int)
        if limit:
            decisions = decisions[:limit]

        return jsonify(decisions)
    except Exception as e:
        print(f"Error reading decisions: {e}")
        return jsonify({"error": "Failed to read decisions"}), 500

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Export sensor data as CSV file with optional date range filtering"""
    start_time = request.args.get('start', None)
    end_time = request.args.get('end', None)
    node_id = request.args.get('node_id', None)

    # Get data from API
    data = api.get_export_data(start_time=start_time, end_time=end_time, node_id=node_id)

    if not data:
        return jsonify({"error": "No data found for the specified range"}), 404

    # Create CSV in memory
    output = io.StringIO()
    fieldnames = ['node_id', 'timestamp', 'temperature', 'relative_humidity', 'soil_moisture', 'lux', 'voltage']
    writer = csv.DictWriter(output, fieldnames=fieldnames)

    writer.writeheader()
    for row in data:
        writer.writerow(row)

    # Prepare response
    csv_data = output.getvalue()
    output.close()

    # Generate filename with timestamp
    filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    response = Response(csv_data, mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/api/decisions/clear', methods=['POST'])
def clear_decisions():
    """Clear all decisions from local storage"""
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(DECISIONS_FILE), exist_ok=True)

        # Count existing decisions
        count = 0
        if os.path.exists(DECISIONS_FILE):
            with open(DECISIONS_FILE, 'r') as f:
                decisions = json.load(f)
                count = len(decisions)

        # Clear the file
        with open(DECISIONS_FILE, 'w') as f:
            json.dump([], f)

        return jsonify({"message": f"Cleared {count} decisions", "count": count})
    except Exception as e:
        print(f"Error clearing decisions: {e}")
        return jsonify({"error": "Failed to clear decisions"}), 500

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
