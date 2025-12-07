from sqlalchemy import create_engine, text
from typing import Optional, Any


class DataAPI:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)

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
        """Get statistics for all nodes (last 24 hours)"""
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

    def get_timeseries_data(self, node_id: Optional[str] = None, hours: int = 12) -> list[dict[str, Any]]:
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
        # TODO: Move this to a config file or database
        nodes = [
            {"node_id": "!512397a3", "lat": 41.698806, "lon": -86.236083, "name": "Dev Node"}
        ]

        stats = self.get_node_stats()
        node_data_map = {stat["node_id"]: stat for stat in stats}

        for node in nodes:
            if node["node_id"] in node_data_map:
                node.update(node_data_map[node["node_id"]])

        return nodes
