#!/usr/bin/env python3
"""
Recreate TimescaleDB with the correct schema.
This script drops the existing sensor_db table and recreates it with the updated schema.

Usage:
    python3 recreate_db.py

Environment Variables:
    DATABASE_URL - PostgreSQL connection string (default: postgresql://group1:meshtastic4@localhost:5432/sensor_db)
"""

import os
from sqlalchemy import create_engine, text

# Database configuration (same as main.py)
DB_URL = os.getenv("DATABASE_URL", "postgresql://group1:meshtastic4@localhost:5432/sensor_db")

def recreate_database():
    """Drop and recreate sensor_db table with correct schema"""
    print("=" * 60)
    print("TimescaleDB Recreation Script")
    print("=" * 60)
    print()

    # Confirm with user
    print("WARNING: This will DELETE the sensor_db table and all its data!")
    print(f"Database: {DB_URL.split('@')[1] if '@' in DB_URL else DB_URL}")
    print()
    print("The table will be recreated with the new schema:")
    print("  - node_id (VARCHAR)")
    print("  - timestamp (TIMESTAMP)")
    print("  - temperature (FLOAT)")
    print("  - relative_humidity (FLOAT)")
    print("  - soil_moisture (FLOAT)")
    print("  - lux (FLOAT)")
    print("  - voltage (FLOAT)")
    print()

    confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("Recreation cancelled.")
        return

    print()
    print("Connecting to database...")

    try:
        engine = create_engine(DB_URL, pool_pre_ping=True)

        with engine.begin() as conn:
            # Check if table exists and get count
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM sensor_db"))
                count = result.scalar()
                print(f"Found existing sensor_db table with {count} records")
                print()
            except:
                print("No existing sensor_db table found")
                print()

            # Drop the table if it exists
            print("Dropping sensor_db table...")
            conn.execute(text("DROP TABLE IF EXISTS sensor_db CASCADE"))
            print("✓ Table dropped successfully!")
            print()

            # Create new table with correct schema
            print("Creating new sensor_db table with updated schema...")
            conn.execute(text("""
                CREATE TABLE sensor_db (
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
            print("✓ Table created successfully!")
            print()

            # Convert to hypertable
            print("Converting to TimescaleDB hypertable...")
            conn.execute(text("SELECT create_hypertable('sensor_db', 'timestamp', if_not_exists => TRUE);"))
            print("✓ Hypertable created successfully!")
            print()

        print("=" * 60)
        print("Database recreation complete!")
        print("The sensor_db table is ready with the new schema.")
        print("=" * 60)

    except Exception as e:
        print(f"Error recreating database: {e}")
        print()
        print("Please check your database connection and try again.")
        return 1

    return 0

if __name__ == "__main__":
    exit(recreate_database())
