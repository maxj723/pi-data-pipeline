"""
Weather service for fetching and analyzing weather forecasts.

This service integrates with OpenWeatherMap API to determine if precipitation
is expected, which influences watering decisions.
"""

import json
import requests
from pathlib import Path
from typing import Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import time


@dataclass
class WeatherForecast:
    """Weather forecast data for a location."""
    node_id: str
    location_name: str
    lat: float
    lon: float
    timestamp: str
    forecast_hours: int
    precipitation_expected: bool
    precipitation_probability: float  # 0.0 to 1.0
    precipitation_amount_mm: float
    precipitation_types: list[str]  # e.g., ["Rain", "Drizzle"]
    temperature_avg: Optional[float] = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class WeatherCache:
    """Simple in-memory cache for weather forecasts."""

    def __init__(self, duration_minutes: int = 30, max_entries: int = 100):
        """
        Initialize weather cache.

        Args:
            duration_minutes: How long to cache entries (default 30 minutes)
            max_entries: Maximum number of cached entries
        """
        self.duration_minutes = duration_minutes
        self.max_entries = max_entries
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Optional[WeatherForecast]:
        """
        Get cached forecast if still valid.

        Args:
            key: Cache key (usually node_id)

        Returns:
            WeatherForecast if cached and valid, None otherwise
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        cached_time = entry.get("timestamp")

        if not cached_time:
            return None

        # Check if cache is still valid
        age_minutes = (datetime.now() - cached_time).total_seconds() / 60
        if age_minutes > self.duration_minutes:
            # Cache expired
            del self._cache[key]
            return None

        return entry.get("forecast")

    def set(self, key: str, forecast: WeatherForecast) -> None:
        """
        Cache a forecast.

        Args:
            key: Cache key (usually node_id)
            forecast: WeatherForecast to cache
        """
        # Implement simple LRU by removing oldest if at capacity
        if len(self._cache) >= self.max_entries:
            oldest_key = min(self._cache.keys(),
                           key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]

        self._cache[key] = {
            "timestamp": datetime.now(),
            "forecast": forecast
        }

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count


class WeatherService:
    """Service for fetching and analyzing weather forecasts."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize weather service.

        Args:
            config_path: Path to weather_config.json. If None, uses default.
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = str(project_root / 'config' / 'weather_config.json')

        self.config = self._load_config(config_path)

        # Initialize cache if enabled
        if self.config.get("cache", {}).get("enabled", True):
            cache_duration = self.config["cache"].get("duration_minutes", 30)
            max_entries = self.config["cache"].get("max_entries", 100)
            self.cache = WeatherCache(cache_duration, max_entries)
        else:
            self.cache = None

    def _load_config(self, config_path: str) -> dict[str, Any]:
        """Load weather configuration from file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load weather config: {e}")
            # Return minimal default config
            return {
                "api": {
                    "provider": "openweathermap",
                    "base_url": "https://api.openweathermap.org/data/2.5",
                    "api_key": "",
                    "timeout_seconds": 10
                },
                "forecast": {
                    "hours_ahead": 24,
                    "precipitation_threshold_mm": 1.0
                },
                "cache": {"enabled": False}
            }

    def get_forecast(self, node_id: str, lat: float, lon: float,
                     node_name: str = "Unknown") -> Optional[WeatherForecast]:
        """
        Get weather forecast for a location.

        Args:
            node_id: Node identifier
            lat: Latitude
            lon: Longitude
            node_name: Human-readable location name

        Returns:
            WeatherForecast object if successful, None on error
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(node_id)
            if cached:
                return cached

        # Fetch from API
        forecast = self._fetch_from_api(node_id, lat, lon, node_name)

        # Cache the result if successful
        if forecast and self.cache:
            self.cache.set(node_id, forecast)

        return forecast

    def _fetch_from_api(self, node_id: str, lat: float, lon: float,
                        node_name: str) -> Optional[WeatherForecast]:
        """
        Fetch forecast from OpenWeatherMap API.

        Args:
            node_id: Node identifier
            lat: Latitude
            lon: Longitude
            node_name: Location name

        Returns:
            WeatherForecast or None on error
        """
        api_config = self.config.get("api", {})
        api_key = api_config.get("api_key", "")

        if not api_key or api_key == "YOUR_OPENWEATHERMAP_API_KEY_HERE":
            print(f"[WARNING] No valid OpenWeatherMap API key configured")
            return None

        base_url = api_config.get("base_url", "https://api.openweathermap.org/data/2.5")
        timeout = api_config.get("timeout_seconds", 10)

        # Use OpenWeatherMap 5-day/3-hour forecast API
        url = f"{base_url}/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric"  # Get temperature in Celsius
        }

        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            return self._parse_forecast(node_id, node_name, lat, lon, data)

        except requests.exceptions.Timeout:
            print(f"[ERROR] Weather API timeout for node {node_id}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Weather API request failed for node {node_id}: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error fetching weather for node {node_id}: {e}")
            return None

    def _parse_forecast(self, node_id: str, node_name: str, lat: float,
                       lon: float, api_data: dict[str, Any]) -> Optional[WeatherForecast]:
        """
        Parse OpenWeatherMap API response.

        Args:
            node_id: Node identifier
            node_name: Location name
            lat: Latitude
            lon: Longitude
            api_data: Raw API response data

        Returns:
            WeatherForecast object
        """
        try:
            forecast_config = self.config.get("forecast", {})
            hours_ahead = forecast_config.get("hours_ahead", 24)
            precip_threshold = forecast_config.get("precipitation_threshold_mm", 1.0)
            precip_types = forecast_config.get("precipitation_types", ["Rain", "Drizzle", "Snow"])

            # Get forecast list from API response
            forecast_list = api_data.get("list", [])
            if not forecast_list:
                return None

            # Filter forecasts within our time window
            now = datetime.now()
            cutoff_time = now + timedelta(hours=hours_ahead)

            total_precip_mm = 0.0
            max_precip_prob = 0.0
            found_precip_types = set()
            temps = []

            for item in forecast_list:
                # Parse forecast timestamp
                forecast_time = datetime.fromtimestamp(item.get("dt", 0))

                # Only look at forecasts within our window
                if forecast_time > cutoff_time:
                    break

                # Get precipitation data
                rain_mm = item.get("rain", {}).get("3h", 0.0)  # 3-hour accumulation
                snow_mm = item.get("snow", {}).get("3h", 0.0)
                total_precip_mm += rain_mm + snow_mm

                # Get precipitation probability
                pop = item.get("pop", 0.0)  # Probability of precipitation (0-1)
                max_precip_prob = max(max_precip_prob, pop)

                # Check weather conditions
                weather_list = item.get("weather", [])
                for weather in weather_list:
                    main_weather = weather.get("main", "")
                    if main_weather in precip_types:
                        found_precip_types.add(main_weather)

                # Collect temperature data
                temp = item.get("main", {}).get("temp")
                if temp is not None:
                    temps.append(temp)

            # Determine if precipitation is expected
            precipitation_expected = (
                total_precip_mm >= precip_threshold or
                max_precip_prob > 0.5 or
                len(found_precip_types) > 0
            )

            # Calculate average temperature
            avg_temp = sum(temps) / len(temps) if temps else None

            # Create description
            if precipitation_expected:
                precip_str = ", ".join(sorted(found_precip_types)) if found_precip_types else "precipitation"
                description = f"{precip_str} expected in next {hours_ahead}h ({total_precip_mm:.1f}mm, {max_precip_prob*100:.0f}% prob)"
            else:
                description = f"No significant precipitation expected in next {hours_ahead}h"

            return WeatherForecast(
                node_id=node_id,
                location_name=node_name,
                lat=lat,
                lon=lon,
                timestamp=datetime.now().isoformat(),
                forecast_hours=hours_ahead,
                precipitation_expected=precipitation_expected,
                precipitation_probability=max_precip_prob,
                precipitation_amount_mm=total_precip_mm,
                precipitation_types=sorted(found_precip_types),
                temperature_avg=avg_temp,
                description=description
            )

        except Exception as e:
            print(f"[ERROR] Failed to parse weather forecast: {e}")
            return None

    def should_skip_watering(self, node_id: str, lat: float, lon: float,
                            node_name: str = "Unknown") -> Tuple[bool, Optional[str]]:
        """
        Determine if watering should be skipped due to expected precipitation.

        Args:
            node_id: Node identifier
            lat: Latitude
            lon: Longitude
            node_name: Location name

        Returns:
            Tuple of (should_skip, reason)
            - should_skip: True if watering should be skipped
            - reason: Human-readable explanation (None if should not skip)
        """
        forecast = self.get_forecast(node_id, lat, lon, node_name)

        if not forecast:
            # No forecast available - don't skip (fail open)
            return (False, None)

        decision_rules = self.config.get("decision_rules", {})

        if not forecast.precipitation_expected:
            return (False, None)

        # Check if we should skip based on precipitation type
        skip_rain = decision_rules.get("skip_watering_if_rain_expected", True)
        skip_snow = decision_rules.get("skip_watering_if_snow_expected", True)

        has_rain = any(p in ["Rain", "Drizzle"] for p in forecast.precipitation_types)
        has_snow = "Snow" in forecast.precipitation_types

        if (has_rain and skip_rain) or (has_snow and skip_snow):
            return (True, forecast.description)

        return (False, None)

    def get_watering_confidence_adjustment(self, node_id: str, lat: float,
                                          lon: float, node_name: str = "Unknown") -> Tuple[float, Optional[str]]:
        """
        Get confidence adjustment factor for watering decisions based on weather.

        Args:
            node_id: Node identifier
            lat: Latitude
            lon: Longitude
            node_name: Location name

        Returns:
            Tuple of (confidence_multiplier, reason)
            - confidence_multiplier: Factor to multiply watering confidence by (0.0-1.0)
            - reason: Explanation of adjustment (None if no adjustment)
        """
        forecast = self.get_forecast(node_id, lat, lon, node_name)

        if not forecast or not forecast.precipitation_expected:
            return (1.0, None)  # No adjustment

        decision_rules = self.config.get("decision_rules", {})

        # Determine reduction based on precipitation amount
        if forecast.precipitation_amount_mm > 5.0:
            # Heavy rain expected
            reduction = decision_rules.get("confidence_reduction_heavy_rain", 0.7)
            reason = f"Heavy precipitation expected ({forecast.precipitation_amount_mm:.1f}mm)"
        else:
            # Light rain expected
            reduction = decision_rules.get("confidence_reduction_light_rain", 0.3)
            reason = f"Light precipitation expected ({forecast.precipitation_amount_mm:.1f}mm)"

        # Return multiplier (1.0 - reduction)
        return (1.0 - reduction, reason)
