from sqlalchemy import create_engine, text
import pandas as pd

class TimescaleStorage:
    """
    Handles connection to a TimescaleDB instance and writes data into it.
    """
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)

    def init_db(self):
        """Creates sensor_data table and hypertable if not exists."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sensor_db (
                    id SERIAL PRIMARY KEY,
                    node_id VARCHAR(32),
                    timestamp TIMESTAMP NOT NULL,
                    soil_moisture FLOAT,
                    sunlight FLOAT,
                    temperature FLOAT,
                    humidity FLOAT,
                    battery_percentage FLOAT
                );
            """))
            conn.execute(text("SELECT create_hypertable('sensor_db', 'timestamp', if_not_exists => TRUE);"))
        print("DB initialized.")

    def save(self, data: dict):
        """Insert single record or list of records."""
        try:
            df = pd.DataFrame([data]) if isinstance(data, dict) else pd.DataFrame(data)
            df.to_sql("sensor_db", con=self.engine, if_exists="append", index=False)
            print(f"Saved {len(df)} record(s) to DB.")
        except Exception as e:
            print(f"DB Save Error: {e}")
