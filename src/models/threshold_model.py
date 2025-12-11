"""
Threshold-based decision model for sensor data analysis.

This model focuses on two actionable decisions:
1. Watering (soil moisture) - influenced by temperature, humidity, and light
2. Charging (voltage) - influenced by light availability

Other sensors provide context to improve decision quality.
"""

from typing import Optional, Any
from .base_model import BaseDecisionModel
from .decision import Decision, Severity, ActionType


class ThresholdModel(BaseDecisionModel):
    """
    A threshold-based decision model that analyzes sensor readings
    and provides recommendations based on configurable thresholds.

    Environmental factors (temperature, humidity, lux) influence the
    urgency and confidence of actionable decisions (watering, charging).
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the threshold model with optional configuration."""
        super().__init__(config)
        if not self.config:
            self.config = self._get_default_config()

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

    def analyze(self, reading: dict[str, Any]) -> Decision:
        """
        Analyze a single sensor reading and produce a decision.

        Prioritizes actionable decisions (watering, charging) and uses
        environmental sensors to adjust urgency and confidence.

        Args:
            reading: Dictionary containing sensor data.

        Returns:
            Decision object with standardized output.
        """
        # Check for actionable issues (watering and charging)
        watering_decision = self._analyze_watering(reading)
        charging_decision = self._analyze_charging(reading)

        # Prioritize decisions by severity
        decisions = []
        if watering_decision:
            decisions.append(watering_decision)
        if charging_decision:
            decisions.append(charging_decision)

        if not decisions:
            # No actionable issues - normal operation
            return Decision(
                node_id=reading.get("node_id", "unknown"),
                timestamp=reading.get("timestamp", ""),
                decision_text="Normal operation - all systems optimal",
                action=ActionType.NONE,
                severity=Severity.NORMAL,
                confidence=0.95,
                primary_metric="none",
                metrics=self._extract_metrics(reading),
                model_type=self.model_type
            )

        # Return the highest priority decision
        decisions.sort(key=lambda d: d.get_priority(), reverse=True)
        return decisions[0]

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

        # Adjust decision based on environmental factors
        decision_text = base_decision["text"]
        confidence = base_decision["confidence"]
        context = {}

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
