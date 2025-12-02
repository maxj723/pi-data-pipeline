from sqlalchemy import create_engine, text
from data_packet import EnvironmentPacket, PowerPacket

class TimescaleStorage:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)

    def init_db(self):
        """Creates sensor_db table and hypertable if not exists."""
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
        """Insert or update record using UPSERT logic.
        If a record with the same (node_id, timestamp) exists, merge the new data."""
        try:
            if isinstance(data, EnvironmentPacket) or isinstance(data, PowerPacket):
                data = data.to_dict()

            # Build column list and values dynamically based on provided data
            columns = ['node_id', 'timestamp']
            values = [data.get('node_id'), data.get('timestamp')]

            # Add optional sensor fields if they exist in the data
            optional_fields = ['temperature', 'relative_humidity', 'soil_moisture', 'lux', 'voltage']
            for field in optional_fields:
                if field in data and data[field] is not None:
                    columns.append(field)
                    values.append(data[field])

            # Create placeholders for SQL
            placeholders = ', '.join([f':{i}' for i in range(len(values))])
            columns_str = ', '.join(columns)

            # Build UPDATE clause - only update non-NULL values from new data
            update_pairs = []
            for field in optional_fields:
                if field in data and data[field] is not None:
                    update_pairs.append(f"{field} = EXCLUDED.{field}")

            update_clause = ', '.join(update_pairs) if update_pairs else "timestamp = EXCLUDED.timestamp"

            # UPSERT query
            query = text(f"""
                INSERT INTO sensor_db ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (node_id, timestamp)
                DO UPDATE SET {update_clause}
            """)

            with self.engine.begin() as conn:
                conn.execute(query, values)

            print(f"Saved/Updated record for {data.get('node_id')} at {data.get('timestamp')}")

        except Exception as e:
            print(f"DB Save Error: {e}")
