#!/usr/bin/env python3
"""
Test script for weather-aware watering decisions.

This script tests the integration between ThresholdModel and WeatherService.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('src')))

from models.threshold_model import ThresholdModel
from datetime import datetime


def test_weather_integration():
    """Test weather service integration with threshold model."""

    print("=" * 70)
    print("WEATHER INTEGRATION TEST")
    print("=" * 70)
    print()

    # Test 1: Initialize model with weather enabled
    print("1. Initializing ThresholdModel with weather service...")
    try:
        model = ThresholdModel(enable_weather=True)
        print("   ✓ Model initialized successfully")
        print(f"   ✓ Weather enabled: {model.weather_enabled}")
        if model.weather_service:
            print("   ✓ Weather service is active")
        else:
            print("   ⚠ Weather service not available (this is expected if no API key)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    print()

    # Test 2: Analyze reading with low soil moisture (should recommend watering)
    print("2. Testing watering decision with low soil moisture...")
    test_reading = {
        "node_id": "!512397a3",
        "timestamp": datetime.now().isoformat(),
        "soil_moisture": 15.0,  # Low - below 20% threshold
        "temperature": 28.0,     # Hot
        "relative_humidity": 35.0,  # Dry
        "lux": 18000.0,          # Bright
        "voltage": 3.8
    }

    try:
        decisions = model.analyze(test_reading)

        # Find the soil moisture decision
        watering_decision = None
        for decision in decisions:
            if decision.primary_metric == "soil_moisture":
                watering_decision = decision
                break

        if watering_decision:
            print(f"   ✓ Decision generated")
            print(f"   → Decision: {watering_decision.decision_text}")
            print(f"   → Action: {watering_decision.action}")
            print(f"   → Severity: {watering_decision.severity}")
            print(f"   → Confidence: {watering_decision.confidence:.2f}")

            if watering_decision.context:
                print(f"   → Context: {watering_decision.context}")

                if "weather_skip" in watering_decision.context:
                    print("   ✓ Weather integration working - watering postponed due to rain!")
                elif "confidence_adjustment" in watering_decision.context:
                    print("   ✓ Weather integration working - confidence adjusted for precipitation")
                else:
                    print("   ℹ No weather factors detected (no rain forecast or API unavailable)")
            else:
                print("   ℹ No weather context (API key not configured or no precipitation expected)")
        else:
            print("   ✗ No watering decision generated")

    except Exception as e:
        print(f"   ✗ Error analyzing reading: {e}")
        import traceback
        traceback.print_exc()
    print()

    # Test 3: Test with weather disabled
    print("3. Testing with weather service disabled...")
    try:
        model_no_weather = ThresholdModel(enable_weather=False)
        print("   ✓ Model initialized without weather service")
        print(f"   ✓ Weather enabled: {model_no_weather.weather_enabled}")

        decisions = model_no_weather.analyze(test_reading)
        watering_decision = None
        for decision in decisions:
            if decision.primary_metric == "soil_moisture":
                watering_decision = decision
                break

        if watering_decision:
            print(f"   ✓ Decision: {watering_decision.decision_text}")
            print(f"   → No weather context expected: {'weather_skip' not in watering_decision.context}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()

    # Summary
    print("=" * 70)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. If you see 'Weather service not available', add your API key to:")
    print("     config/weather_config.json")
    print()
    print("  2. Get a free API key from:")
    print("     https://openweathermap.org/api")
    print()
    print("  3. Copy config/weather_config.example.json to config/weather_config.json")
    print("     and replace YOUR_OPENWEATHERMAP_API_KEY_HERE with your key")
    print()
    print("  4. Restart the collector to see weather-aware decisions in action!")
    print()


if __name__ == "__main__":
    test_weather_integration()
