#!/usr/bin/env python3
"""
Main entry point for the Meshtastic data pipeline.
Listens for incoming Meshtastic packets and stores them in TimescaleDB.

Usage:
    python3 src/main.py

Environment Variables:
    DATABASE_URL - PostgreSQL connection string (default: postgresql://username:password@localhost:5432/sensor_db)
"""

import os
import time
from listener import MeshtasticListener
from storage import TimescaleStorage

# Database configuration
DB_URL = os.getenv("DATABASE_URL", "postgresql://group1:meshtastic4@localhost:5432/sensor_db")

def main():
    """Main loop that listens for Meshtastic messages and saves to database"""
    print("=" * 60)
    print("Meshtastic Data Pipeline")
    print("=" * 60)
    print()

    # Initialize storage
    print("Connecting to database...")
    storage = TimescaleStorage(DB_URL)

    # Ensure database is initialized
    try:
        storage.init_db()
        print("Database ready")
    except Exception as e:
        print(f"Database initialization error: {e}")
        print("Please check your database connection and try again.")
        return

    print()

    # Initialize and start listener
    print("Starting Meshtastic listener...")
    listener = MeshtasticListener()

    try:
        queue = listener.start()
        print("Listener started successfully")

        # Main loop - process messages from the queue
        while True:
            try:
                # Check if there's data in the queue (non-blocking with timeout)
                if not queue.empty():
                    telemetry_packet = queue.get(timeout=1)

                    # Log the received data
                    print(f"Received: {telemetry_packet}")

                    # Save to database
                    storage.save(telemetry_packet)

                else:
                    time.sleep(0.1)

            except KeyboardInterrupt:
                print("\n\nStopping listener...")
                break
            except Exception as e:
                print(f"Error processing message: {e}")
                time.sleep(1)  # Brief pause before continuing

    except Exception as e:
        print(f"Failed to start listener: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure your Meshtastic device is connected via USB")
        print("2. Check that you have permissions to access the serial port")
        print("3. Verify the device is not being used by another program")
        return

    print()
    print("=" * 60)
    print("Pipeline stopped successfully")
    print("=" * 60)

if __name__ == "__main__":
    main()
