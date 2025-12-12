from sqlalchemy import create_engine, text
from typing import Optional, Any
import json
import os
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.node_config import get_all_nodes


class DataAPI:
    def __init__(self, db_url: str, decisions_file: Optional[str] = None):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)

        if decisions_file:
            self.decisions_file = decisions_file
        else:
            project_root = Path(__file__).parent.parent.parent
            self.decisions_file = str(project_root / 'data' / 'decisions.json')

    def get_latest_data(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT node_id, timestamp, temperature, relative_humidity,
                       soil_moisture, lux, voltage
                FROM sensor_db
                ORDER BY timestamp DESC
                LIMIT :limit
            """), {"limit": limit})

            data = []
            for row in result:
                data.append({
                    "node_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "temperature": float(row[2]) if row[2] is not None else None,
                    "relative_humidity": float(row[3]) if row[3] is not None else None,
                    "soil_moisture": float(row[4]) if row[4] is not None else None,
                    "lux": float(row[5]) if row[5] is not None else None,
                    "voltage": float(row[6]) if row[6] is not None else None
                })

            return data

    def get_historical_data(self, hours: int = 24) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT node_id, timestamp, temperature, relative_humidity,
                       soil_moisture, lux, voltage
                FROM sensor_db
                WHERE timestamp >= NOW() - INTERVAL ':hours hours'
                ORDER BY timestamp ASC
            """), {"hours": hours})

            data = []
            for row in result:
                data.append({
                    "node_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "temperature": float(row[2]) if row[2] is not None else None,
                    "relative_humidity": float(row[3]) if row[3] is not None else None,
                    "soil_moisture": float(row[4]) if row[4] is not None else None,
                    "lux": float(row[5]) if row[5] is not None else None,
                    "voltage": float(row[6]) if row[6] is not None else None
                })

            return data

    def get_node_stats(self) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    node_id,
                    COUNT(*) as reading_count,
                    AVG(temperature) as avg_temp,
                    AVG(relative_humidity) as avg_humidity,
                    AVG(soil_moisture) as avg_soil_moisture,
                    AVG(lux) as avg_lux,
                    AVG(voltage) as avg_voltage,
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
                    "avg_temp": float(row[2]) if row[2] else None,
                    "avg_humidity": float(row[3]) if row[3] else None,
                    "avg_soil_moisture": float(row[4]) if row[4] else None,
                    "avg_lux": float(row[5]) if row[5] else None,
                    "avg_voltage": float(row[6]) if row[6] else None,
                    "last_seen": row[7].isoformat() if row[7] else None
                })

            return stats

    def get_timeseries_data(self, node_id: Optional[str] = None, hours: Optional[int] = None, start_time: Optional[str] = None, end_time: Optional[str] = None) -> list[dict[str, Any]]:
        base_query = """
            SELECT
                time_bucket('5 minutes', timestamp) AS bucket,
                node_id,
                AVG(temperature) as avg_temp,
                AVG(relative_humidity) as avg_humidity,
                AVG(soil_moisture) as avg_soil_moisture,
                AVG(lux) as avg_lux,
                AVG(voltage) as avg_voltage,
                MAX(temperature) as max_temp,
                MIN(temperature) as min_temp
            FROM sensor_db
            WHERE 1=1
        """

        params = {}

        # Handle time range
        if start_time and end_time:
            base_query += " AND timestamp >= :start_time AND timestamp <= :end_time"
            params["start_time"] = start_time
            params["end_time"] = end_time
        elif hours:
            base_query += " AND timestamp >= NOW() - INTERVAL ':hours hours'"
            params["hours"] = hours
        else:
            # Default to 12 hours if nothing specified
            base_query += " AND timestamp >= NOW() - INTERVAL '12 hours'"

        if node_id:
            base_query += " AND node_id = :node_id"
            params["node_id"] = node_id

        base_query += """
            GROUP BY bucket, node_id
            ORDER BY bucket ASC
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(base_query), params)

            data = []
            for row in result:
                data.append({
                    "timestamp": row[0].isoformat() if row[0] else None,
                    "node_id": row[1],
                    "avg_temp": float(row[2]) if row[2] else None,
                    "avg_humidity": float(row[3]) if row[3] else None,
                    "avg_soil_moisture": float(row[4]) if row[4] else None,
                    "avg_lux": float(row[5]) if row[5] else None,
                    "avg_voltage": float(row[6]) if row[6] else None,
                    "max_temp": float(row[7]) if row[7] else None,
                    "min_temp": float(row[8]) if row[8] else None
                })

            return data

    def get_node_locations(self) -> list[dict[str, Any]]:
        """
        Get node locations from config file and enrich with latest stats.

        Returns:
            List of node dictionaries with location and sensor statistics.
        """
        # Load nodes from config file
        nodes = get_all_nodes()

        # Enrich with latest sensor statistics
        stats = self.get_node_stats()
        node_data_map = {stat["node_id"]: stat for stat in stats}

        for node in nodes:
            if node["node_id"] in node_data_map:
                node.update(node_data_map[node["node_id"]])

        return nodes

    def get_export_data(self, start_time: Optional[str] = None, end_time: Optional[str] = None, node_id: Optional[str] = None) -> list[dict[str, Any]]:
        query = """
            SELECT
                node_id,
                timestamp,
                temperature,
                relative_humidity,
                soil_moisture,
                lux,
                voltage
            FROM sensor_db
            WHERE 1=1
        """

        params = {}

        if start_time:
            query += " AND timestamp >= :start_time"
            params["start_time"] = start_time

        if end_time:
            query += " AND timestamp <= :end_time"
            params["end_time"] = end_time

        if node_id:
            query += " AND node_id = :node_id"
            params["node_id"] = node_id

        query += " ORDER BY timestamp ASC"

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)

            data = []
            for row in result:
                data.append({
                    "node_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "temperature": float(row[2]) if row[2] is not None else None,
                    "relative_humidity": float(row[3]) if row[3] is not None else None,
                    "soil_moisture": float(row[4]) if row[4] is not None else None,
                    "lux": float(row[5]) if row[5] is not None else None,
                    "voltage": float(row[6]) if row[6] is not None else None
                })

            return data

    # ==================== Decision Management ====================

    def get_decisions(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """
        Get decisions from local storage file.

        Args:
            limit: Optional limit on number of decisions to return.

        Returns:
            List of decision dictionaries.
        """
        try:
            if not os.path.exists(self.decisions_file):
                return []

            with open(self.decisions_file, 'r') as f:
                content = f.read()
                data = json.loads(content)

            # Handle both dict (new format) and list (legacy format)
            if isinstance(data, dict):
                decisions = list(data.values())
            else:
                decisions = data

            # Sort by timestamp (most recent first)
            decisions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            # Apply limit if specified
            if limit:
                decisions = decisions[:limit]

            return decisions

        except Exception as e:
            print(f"[ERROR] Error reading decisions: {e}")
            import traceback
            traceback.print_exc()
            raise

    def clear_decisions(self) -> int:
        """
        Clear all decisions from local storage.

        Returns:
            Number of decisions cleared.
        """
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.decisions_file), exist_ok=True)

            # Count existing decisions
            count = 0
            if os.path.exists(self.decisions_file):
                with open(self.decisions_file, 'r') as f:
                    data = json.load(f)
                    # Handle both dict and list formats
                    count = len(data) if data else 0

            # Clear the file (use dict format)
            with open(self.decisions_file, 'w') as f:
                json.dump({}, f)

            return count

        except Exception as e:
            print(f"[ERROR] Error clearing decisions: {e}")
            raise
