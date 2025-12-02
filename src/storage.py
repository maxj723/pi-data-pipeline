from sqlalchemy import create_engine, text
import pandas as pd
from data_packet import TelemetryPacket

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
        try:
            if isinstance(data, TelemetryPacket):
                data = data.to_dict()

            df = pd.DataFrame([data])
            df.to_sql("sensor_db", con=self.engine, if_exists="append", index=False)
            print(f"Saved {len(df)} record(s) to DB.")

        except Exception as e:
            print(f"DB Save Error: {e}")
