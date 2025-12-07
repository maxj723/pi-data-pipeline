from sqlalchemy import create_engine, text
from data_packet import DataPacket

class TimescaleStorage:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)

    def init_db(self):
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sensor_db (
                    id SERIAL,
                    node_id VARCHAR(32),
                    timestamp TIMESTAMP NOT NULL,
                    temperature FLOAT,
                    relative_humidity FLOAT,
                    soil_moisture FLOAT,
                    lux FLOAT,
                    voltage FLOAT,
                    UNIQUE (node_id, timestamp)
                );
            """))
            conn.execute(text("SELECT create_hypertable('sensor_db', 'timestamp', if_not_exists => TRUE);"))
        print("DB initialized.")

    def save(self, data):
        try:
            if isinstance(data, DataPacket):
                data = data.to_dict()

            # Get column names and create placeholders
            columns = list(data.keys())
            columns_str = ', '.join(columns)
            placeholders = ', '.join([f':{col}' for col in columns])

            # Build UPDATE clause for fields that have data (excluding node_id and timestamp)
            update_fields = [col for col in columns if col not in ['node_id', 'timestamp']]
            update_clause = ', '.join([f"{field} = EXCLUDED.{field}" for field in update_fields])

            # If no fields to update (only node_id and timestamp), just update timestamp
            if not update_clause:
                update_clause = "timestamp = EXCLUDED.timestamp"

            # UPSERT query
            query = text(f"""
                INSERT INTO sensor_db ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (node_id, timestamp)
                DO UPDATE SET {update_clause}
            """)

            with self.engine.begin() as conn:
                conn.execute(query, data)

            print(f"Saved/Updated record for {data.get('node_id')} at {data.get('timestamp')}")

        except Exception as e:
            print(f"DB Save Error: {e}")
