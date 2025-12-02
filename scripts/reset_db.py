#!/usr/bin/env python3
"""
Reset TimescaleDB by clearing all data from sensor_db table.
This script erases all data but keeps the table structure and hypertable intact.

Usage:
    python3 reset_db.py

Environment Variables:
    DATABASE_URL - PostgreSQL connection string (default: postgresql://group1:meshtastic4@localhost:5432/sensor_db)
"""

import os
from sqlalchemy import create_engine, text

# Database configuration (same as main.py)
DB_URL = os.getenv("DATABASE_URL", "postgresql://group1:meshtastic4@localhost:5432/sensor_db")

def reset_database():
    """Clear all data from sensor_db table"""
    print("=" * 60)
    print("TimescaleDB Reset Script")
    print("=" * 60)
    print()

    # Confirm with user
    print("WARNING: This will delete ALL data from the sensor_db table!")
    print(f"Database: {DB_URL.split('@')[1] if '@' in DB_URL else DB_URL}")
    print()

    confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("Reset cancelled.")
        return

    print()
    print("Connecting to database...")

    try:
        engine = create_engine(DB_URL, pool_pre_ping=True)

        with engine.begin() as conn:
            # Get count before deletion
            result = conn.execute(text("SELECT COUNT(*) FROM sensor_db"))
            count = result.scalar()
            print(f"Found {count} records in sensor_db table")
            print()

            # Truncate the table (fast delete that preserves structure)
            print("Clearing all data...")
            conn.execute(text("TRUNCATE TABLE sensor_db"))
            print("✓ All data cleared successfully!")
            print()

            # Verify
            result = conn.execute(text("SELECT COUNT(*) FROM sensor_db"))
            new_count = result.scalar()
            print(f"Records remaining: {new_count}")

        print()
        print("=" * 60)
        print("Database reset complete!")
        print("The sensor_db table structure and hypertable remain intact.")
        print("=" * 60)

    except Exception as e:
        print(f"Error resetting database: {e}")
        print()
        print("Please check your database connection and try again.")
        return 1

    return 0

if __name__ == "__main__":
    exit(reset_database())
