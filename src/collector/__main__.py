import os
import sys
import time
from pathlib import Path
from .listener import MeshtasticListener
from .storage import TimescaleStorage
from .decision_storage import DecisionStorage

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent))
from models import ThresholdModel


DB_URL = os.getenv("DATABASE_URL", "postgresql://group1:meshtastic4@localhost:5432/sensor_db")

def main():
    print("Connecting to database...")
    storage = TimescaleStorage(DB_URL)
    try:
        storage.init_db()
    except Exception as e:
        print(f"Database initialization error: {e}")
        return

    print("Initializing decision model...")
    decision_model = ThresholdModel()
    decision_storage = DecisionStorage()
    print(f"Decision storage initialized at: {decision_storage.file_path}")

    print()
    print("Starting Meshtastic listener...")
    listener = MeshtasticListener()

    try:
        queue = listener.start()
        while True:
            try:
                if not queue.empty():
                    telemetry_packet = queue.get(timeout=1)
                    print(f"Received: {telemetry_packet}")

                    # Save sensor data to database
                    storage.save(telemetry_packet)

                    # Generate decision from the telemetry data
                    reading_dict = telemetry_packet.to_dict()
                    decision = decision_model.analyze(reading_dict)

                    # Save actionable decisions to local storage
                    if decision.is_actionable():
                        decision_dict = decision.to_dict()
                        decision_storage.save_decision(decision_dict)
                        print(f"  → Decision saved: {decision.decision_text}")

                else:
                    time.sleep(0.1)

            except KeyboardInterrupt:
                print("\n\nStopping listener...")
                break
            except Exception as e:
                print(f"Error processing message: {e}")
                time.sleep(1)

    except Exception as e:
        print(f"Failed to start listener: {e}")
        return

    print()
    print("Pipeline stopped successfully")

if __name__ == "__main__":
    main()
