import os
import time
from .listener import MeshtasticListener
from .storage import TimescaleStorage


DB_URL = os.getenv("DATABASE_URL", "postgresql://group1:meshtastic4@localhost:5432/sensor_db")

def main():    
    print("Connecting to database...")
    storage = TimescaleStorage(DB_URL)
    try:
        storage.init_db()
    except Exception as e:
        print(f"Database initialization error: {e}")
        return

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
                    storage.save(telemetry_packet)

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
