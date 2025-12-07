"""
Test Data Generator for Dashboard Testing

This script generates fake sensor data and inserts it into the database
for testing the web dashboard before real nodes are deployed.

Usage:
    python scripts/test_data_generator.py
"""

import random
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from src.collector.storage import TimescaleStorage


# Database configuration
DB_URL = os.getenv("DATABASE_URL", "postgresql://group1:meshtastic4@localhost:5432/sensor_db")

# Test node IDs
TEST_NODES = [
    "!MOCK_NODE_1",
    "!MOCK_NODE_2",
    "!MOCK_NODE_3"
]


def generate_sensor_reading(node_id: str) -> Dict[str, Any]:
    """
    Generate realistic fake sensor data matching the current database schema.

    Schema fields:
    - node_id: VARCHAR(32)
    - timestamp: TIMESTAMP
    - temperature: FLOAT (°C)
    - relative_humidity: FLOAT (%)
    - soil_moisture: FLOAT (%)
    - lux: FLOAT (light intensity)
    - voltage: FLOAT (V)
    """
    # Base values with some randomness
    base_temp = 22.0 + random.uniform(-3, 8)  # 19-30°C
    base_humidity = 50.0 + random.uniform(-15, 25)  # 35-75%
    base_soil = 45.0 + random.uniform(-20, 30)  # 25-75%
    base_lux = 5000.0 + random.uniform(-2000, 3000)  # 3000-8000 lux
    base_voltage = 3.7 + random.uniform(-0.5, 0.4)  # 3.2-4.1V (typical LiPo range)

    # Add correlations for realism
    # Higher temp -> lower humidity
    if base_temp > 27:
        base_humidity -= 10

    # Higher lux (more sun) -> higher temp, lower soil moisture
    if base_lux > 7000:
        base_temp += 2
        base_soil -= 5

    # Clamp values to realistic ranges
    reading = {
        "node_id": node_id,
        "timestamp": datetime.now(),
        "temperature": round(base_temp, 1),
        "relative_humidity": round(max(0, min(100, base_humidity)), 1),
        "soil_moisture": round(max(0, min(100, base_soil)), 1),
        "lux": round(max(0, base_lux), 1),
        "voltage": round(max(3.0, min(4.2, base_voltage)), 2),
    }

    return reading

def generate_historical_data(storage: TimescaleStorage, hours: int = 24, interval_minutes: int = 5) -> None:
    """
    Generate historical data for the past N hours.

    Args:
        storage: TimescaleStorage instance
        hours: Number of hours of historical data to generate
        interval_minutes: Interval between readings in minutes
    """
    print(f"Generating {hours} hours of historical data...")

    start_time = datetime.now() - timedelta(hours=hours)
    current_time = start_time
    end_time = datetime.now()

    count = 0
    while current_time <= end_time:
        for node_id in TEST_NODES:
            reading = generate_sensor_reading(node_id)
            reading["timestamp"] = current_time

            storage.save(reading)
            count += 1

            if count % 50 == 0:
                print(f"Generated {count} readings...")

        current_time += timedelta(minutes=interval_minutes)

    print(f"✅ Generated {count} total readings")


def generate_live_data(storage: TimescaleStorage, duration_seconds: int = 60, interval_seconds: int = 5) -> None:
    """
    Generate live data for testing real-time updates.

    Args:
        storage: TimescaleStorage instance
        duration_seconds: How long to generate data for
        interval_seconds: Interval between readings in seconds
    """
    print(f"Generating live data for {duration_seconds} seconds...")
    print("Check your dashboard to see real-time updates!")

    start_time = time.time()
    count = 0

    while time.time() - start_time < duration_seconds:
        for node_id in TEST_NODES:
            reading = generate_sensor_reading(node_id)
            storage.save(reading)
            count += 1

            print(f"[{datetime.now().strftime('%H:%M:%S')}] {node_id}: "
                  f"Temp={reading['temperature']}°C, "
                  f"Humidity={reading['relative_humidity']:.1f}%, "
                  f"Soil={reading['soil_moisture']:.1f}%, "
                  f"Voltage={reading['voltage']:.2f}V")

        time.sleep(interval_seconds)

    print(f"✅ Generated {count} live readings")

def main() -> None:
    """Main entry point for test data generation."""
    print("=" * 60)
    print("Test Data Generator for Meshtastic Sensor Dashboard")
    print("=" * 60)
    print()

    # Initialize storage
    storage = TimescaleStorage(DB_URL)

    # Ensure database is initialized
    try:
        storage.init_db()
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
        print("Continuing anyway...")

    print()
    print("Choose an option:")
    print("1. Generate historical data (past 24 hours)")
    print("2. Generate live data (60 seconds)")
    print("3. Generate both")
    print()

    choice = input("Enter choice (1-3): ").strip()

    if choice == "1":
        generate_historical_data(storage, hours=24, interval_minutes=5)
    elif choice == "2":
        generate_live_data(storage, duration_seconds=60, interval_seconds=5)
    elif choice == "3":
        generate_historical_data(storage, hours=24, interval_minutes=5)
        print()
        input("Press Enter to start generating live data...")
        generate_live_data(storage, duration_seconds=60, interval_seconds=5)
    else:
        print("❌ Invalid choice!")
        return

    print()
    print("=" * 60)
    print("✅ Done! Your dashboard should now show data.")
    print("=" * 60)


if __name__ == "__main__":
    main()
