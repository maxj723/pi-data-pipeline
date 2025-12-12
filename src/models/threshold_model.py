"""
Threshold-based decision model for sensor data analysis.

This model focuses on two actionable decisions:
1. Watering (soil moisture) - influenced by temperature, humidity, light, and weather
2. Charging (voltage) - influenced by light availability

Other sensors provide context to improve decision quality.
Weather integration prevents unnecessary watering when rain is forecast.
"""

from typing import Optional, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .base_model import BaseDecisionModel
from .decision import Decision, Severity, ActionType
from .weather_service import WeatherService
from utils.node_config import get_node_location


class ThresholdModel(BaseDecisionModel):
    """
    A threshold-based decision model that analyzes sensor readings
    and provides recommendations based on configurable thresholds.

    Environmental factors (temperature, humidity, lux) influence the
    urgency and confidence of actionable decisions (watering, charging).
    """

    def __init__(self, config: Optional[dict[str, Any]] = None, enable_weather: bool = True):
        """
        Initialize the threshold model with optional configuration.

        Args:
            config: Optional threshold configuration dictionary
            enable_weather: Whether to enable weather service integration (default: True)
        """
        super().__init__(config)
        if not self.config:
            self.config = self._get_default_config()

        # Initialize weather service if enabled
        self.weather_enabled = enable_weather
        self.weather_service = None
        if self.weather_enabled:
            try:
                self.weather_service = WeatherService()
                print("[INFO] Weather service initialized")
            except Exception as e:
                print(f"[WARNING] Failed to initialize weather service: {e}")
                print("[INFO] Continuing without weather integration")
                self.weather_enabled = False

    def _get_default_config(self) -> dict[str, Any]:
        """Get default threshold configuration."""
        return {
            "soil_moisture": {
                "critical_low": 10,
                "low": 20,
                "optimal_min": 25,
                "optimal_max": 40,
                "high": 45
            },
            "voltage": {
                "critical_low": 2.8,
                "low": 3.0,
                "optimal_min": 3.2,
                "optimal_max": 4.2
            },
            "temperature": {
                "cold": 10,      # Reduces water needs
                "optimal": 20,
                "hot": 30,       # Increases water needs
                "very_hot": 35   # Significantly increases water needs
            },
            "relative_humidity": {
                "dry": 40,       # Increases water needs
                "optimal": 60,
                "humid": 80      # Reduces water needs
            },
            "lux": {
                "dark": 100,
                "low_light": 1000,
                "moderate": 5000,
                "bright": 15000  # High evaporation, affects both water and charging
            }
        }

    def analyze(self, reading: dict[str, Any]) -> list[Decision]:
        """
        Analyze a single sensor reading and produce decisions.

        Returns decisions for each monitored metric (watering and charging).
        This allows multiple decisions per node to be displayed.

        Args:
            reading: Dictionary containing sensor data.

        Returns:
            List of Decision objects (one per primary_metric).
        """
        decisions = []

        # Generate watering decision if we have soil_moisture data
        soil_moisture = reading.get("soil_moisture")
        if soil_moisture is not None:
            watering_decision = self._analyze_watering(reading)
            if watering_decision:
                decisions.append(watering_decision)
            else:
                # No watering issues - add normal watering status
                decisions.append(Decision(
                    node_id=reading.get("node_id", "unknown"),
                    timestamp=reading.get("timestamp", ""),
                    decision_text="Soil moisture levels normal",
                    action=ActionType.NONE,
                    severity=Severity.NORMAL,
                    confidence=0.95,
                    primary_metric="soil_moisture",
                    primary_value=soil_moisture,
                    metrics=self._extract_metrics(reading),
                    model_type=self.model_type
                ))

        # Generate charging decision if we have voltage data
        voltage = reading.get("voltage")
        if voltage is not None:
            charging_decision = self._analyze_charging(reading)
            if charging_decision:
                decisions.append(charging_decision)
            else:
                # No charging issues - add normal voltage status
                decisions.append(Decision(
                    node_id=reading.get("node_id", "unknown"),
                    timestamp=reading.get("timestamp", ""),
                    decision_text="Battery voltage normal",
                    action=ActionType.NONE,
                    severity=Severity.NORMAL,
                    confidence=0.95,
                    primary_metric="voltage",
                    primary_value=voltage,
                    metrics=self._extract_metrics(reading),
                    model_type=self.model_type
                ))

        return decisions

    def _analyze_watering(self, reading: dict[str, Any]) -> Optional[Decision]:
        """
        Analyze watering needs based on soil moisture and environmental factors.

        Environmental influences:
        - High temperature → increases urgency
        - Low humidity → increases urgency
        - High light → increases urgency (more evaporation)
        """
        soil_moisture = reading.get("soil_moisture")
        if soil_moisture is None:
            return None

        thresholds = self.config["soil_moisture"]
        temp = reading.get("temperature")
        humidity = reading.get("relative_humidity")
        lux = reading.get("lux")

        # Base decision from soil moisture
        base_decision = None
        threshold_crossed = None

        if soil_moisture < thresholds["critical_low"]:
            base_decision = {
                "text": "Critical: Soil moisture extremely low",
                "action": ActionType.WATER_IMMEDIATELY,
                "severity": Severity.CRITICAL,
                "confidence": 0.95,
                "threshold": "critical_low"
            }
        elif soil_moisture < thresholds["low"]:
            base_decision = {
                "text": "Low soil moisture detected",
                "action": ActionType.WATER_NEEDED,
                "severity": Severity.WARNING,
                "confidence": 0.85,
                "threshold": "low"
            }
        elif soil_moisture > thresholds["high"]:
            base_decision = {
                "text": "Soil moisture high - reduce watering",
                "action": ActionType.REDUCE_WATERING,
                "severity": Severity.WARNING,
                "confidence": 0.80,
                "threshold": "high"
            }

        if not base_decision:
            return None

        # Check weather forecast if service is available
        node_id = reading.get("node_id", "unknown")
        weather_context = {}

        if self.weather_enabled and self.weather_service:
            # Get node location from config
            node_location = get_node_location(node_id)

            if node_location:
                lat = node_location.get("lat")
                lon = node_location.get("lon")
                name = node_location.get("name", "Unknown")

                if lat is not None and lon is not None:
                    # Check if we should skip watering due to rain/snow
                    should_skip, skip_reason = self.weather_service.should_skip_watering(
                        node_id, lat, lon, name
                    )

                    if should_skip and base_decision["action"] in [ActionType.WATER_IMMEDIATELY, ActionType.WATER_NEEDED]:
                        # Rain/snow expected - skip watering
                        return Decision(
                            node_id=node_id,
                            timestamp=reading.get("timestamp", ""),
                            decision_text=f"Watering postponed: {skip_reason}",
                            action=ActionType.NONE,
                            severity=Severity.NORMAL,
                            confidence=0.90,
                            primary_metric="soil_moisture",
                            primary_value=soil_moisture,
                            threshold_crossed=base_decision["threshold"],
                            context={"weather_skip": True, "weather_reason": skip_reason},
                            metrics=self._extract_metrics(reading),
                            model_type=self.model_type
                        )

                    # Get confidence adjustment based on weather
                    confidence_multiplier, adjustment_reason = self.weather_service.get_watering_confidence_adjustment(
                        node_id, lat, lon, name
                    )

                    if adjustment_reason:
                        weather_context["confidence_adjustment"] = adjustment_reason
                        weather_context["confidence_multiplier"] = confidence_multiplier

        # Adjust decision based on environmental factors
        decision_text = base_decision["text"]
        confidence = base_decision["confidence"]
        context = weather_context.copy()

        # Temperature influence
        if temp is not None:
            temp_thresholds = self.config["temperature"]
            if temp > temp_thresholds["very_hot"]:
                if base_decision["action"] in [ActionType.WATER_IMMEDIATELY, ActionType.WATER_NEEDED]:
                    decision_text += f" (very hot conditions: {temp:.1f}°C increasing evaporation)"
                    confidence = min(confidence + 0.05, 0.99)
                    context["temperature_factor"] = "very_hot"
            elif temp > temp_thresholds["hot"]:
                if base_decision["action"] in [ActionType.WATER_IMMEDIATELY, ActionType.WATER_NEEDED]:
                    decision_text += f" (hot conditions: {temp:.1f}°C)"
                    confidence = min(confidence + 0.03, 0.99)
                    context["temperature_factor"] = "hot"
            elif temp < temp_thresholds["cold"]:
                context["temperature_factor"] = "cold"
                # Cold weather reduces water needs - could lower urgency
                confidence = max(confidence - 0.05, 0.70)

        # Humidity influence
        if humidity is not None:
            humidity_thresholds = self.config["relative_humidity"]
            if humidity < humidity_thresholds["dry"]:
                if base_decision["action"] in [ActionType.WATER_IMMEDIATELY, ActionType.WATER_NEEDED]:
                    decision_text += f" (dry air: {humidity:.1f}% RH)"
                    confidence = min(confidence + 0.04, 0.99)
                    context["humidity_factor"] = "dry"

        # Light influence
        if lux is not None:
            lux_thresholds = self.config["lux"]
            if lux > lux_thresholds["bright"]:
                if base_decision["action"] in [ActionType.WATER_IMMEDIATELY, ActionType.WATER_NEEDED]:
                    decision_text += f" (bright sun increasing evaporation)"
                    confidence = min(confidence + 0.03, 0.99)
                    context["light_factor"] = "bright"

        # Apply weather confidence adjustment if available
        if "confidence_multiplier" in weather_context:
            confidence = confidence * weather_context["confidence_multiplier"]
            # Add weather info to decision text if confidence was reduced
            if weather_context["confidence_multiplier"] < 1.0:
                decision_text += f" (reduced confidence: {weather_context['confidence_adjustment']})"

        return Decision(
            node_id=reading.get("node_id", "unknown"),
            timestamp=reading.get("timestamp", ""),
            decision_text=decision_text,
            action=base_decision["action"],
            severity=base_decision["severity"],
            confidence=confidence,
            primary_metric="soil_moisture",
            primary_value=soil_moisture,
            threshold_crossed=base_decision["threshold"],
            context=context,
            metrics=self._extract_metrics(reading),
            model_type=self.model_type
        )

    def _analyze_charging(self, reading: dict[str, Any]) -> Optional[Decision]:
        """
        Analyze charging/power needs based on voltage and light availability.

        Environmental influences:
        - Low light → more conservative with power, higher urgency for charging
        """
        voltage = reading.get("voltage")
        if voltage is None:
            return None

        thresholds = self.config["voltage"]
        lux = reading.get("lux")

        # Base decision from voltage
        base_decision = None

        if voltage < thresholds["critical_low"]:
            base_decision = {
                "text": "Critical: Battery voltage critically low",
                "action": ActionType.CHARGE_BATTERY_URGENT,
                "severity": Severity.CRITICAL,
                "confidence": 0.98,
                "threshold": "critical_low"
            }
        elif voltage < thresholds["low"]:
            base_decision = {
                "text": "Low battery voltage",
                "action": ActionType.CHARGE_BATTERY,
                "severity": Severity.WARNING,
                "confidence": 0.90,
                "threshold": "low"
            }

        if not base_decision:
            return None

        # Adjust decision based on light availability
        decision_text = base_decision["text"]
        confidence = base_decision["confidence"]
        context = {}

        if lux is not None:
            lux_thresholds = self.config["lux"]
            if lux < lux_thresholds["dark"]:
                decision_text += " (no sunlight - check solar panel positioning)"
                confidence = min(confidence + 0.02, 0.99)
                context["light_factor"] = "dark"
                context["charging_capacity"] = "none"
            elif lux < lux_thresholds["low_light"]:
                decision_text += " (low light - limited solar charging)"
                context["light_factor"] = "low"
                context["charging_capacity"] = "limited"
            elif lux > lux_thresholds["bright"]:
                # Good sunlight but still low voltage - might be a panel issue
                decision_text += " (good sunlight available - check solar panel)"
                base_decision["action"] = ActionType.CHECK_SOLAR_PANEL
                context["light_factor"] = "bright"
                context["charging_capacity"] = "full"

        return Decision(
            node_id=reading.get("node_id", "unknown"),
            timestamp=reading.get("timestamp", ""),
            decision_text=decision_text,
            action=base_decision["action"],
            severity=base_decision["severity"],
            confidence=confidence,
            primary_metric="voltage",
            primary_value=voltage,
            threshold_crossed=base_decision["threshold"],
            context=context,
            metrics=self._extract_metrics(reading),
            model_type=self.model_type
        )

    def _extract_metrics(self, reading: dict[str, Any]) -> dict[str, Optional[float]]:
        """Extract all sensor metrics from a reading."""
        return {
            "soil_moisture": reading.get("soil_moisture"),
            "temperature": reading.get("temperature"),
            "relative_humidity": reading.get("relative_humidity"),
            "voltage": reading.get("voltage"),
            "lux": reading.get("lux")
        }
