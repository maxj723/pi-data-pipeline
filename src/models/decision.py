from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """Severity levels for decisions."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    NORMAL = "normal"


class ActionType(Enum):
    # Soil moisture actions
    WATER_IMMEDIATELY = "water_immediately"
    WATER_NEEDED = "water_needed"
    REDUCE_WATERING = "reduce_watering"

    # Voltage/power actions
    CHARGE_BATTERY_URGENT = "charge_battery_urgent"
    CHARGE_BATTERY = "charge_battery"
    CHECK_SOLAR_PANEL = "check_solar_panel"

    # Monitoring actions
    MONITOR = "monitor"
    NONE = "none"


@dataclass
class Decision:

    # Core decision fields
    node_id: str
    timestamp: str
    decision_text: str
    action: ActionType
    severity: Severity
    confidence: float

    # Context and supporting data
    primary_metric: str  # The main metric driving this decision (e.g., "soil_moisture", "voltage")
    primary_value: Optional[float] = None
    threshold_crossed: Optional[str] = None  # e.g., "critical_low", "high"

    # Environmental context
    context: dict[str, Any] = field(default_factory=dict)

    # All sensor metrics for reference
    metrics: dict[str, Optional[float]] = field(default_factory=dict)

    # Model metadata
    model_type: str = "unknown"
    model_version: str = "1.0"

    def __post_init__(self):
        # Convert string enums to Enum objects if passed as strings
        if isinstance(self.action, str):
            self.action = ActionType(self.action)
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity)

        # Validate confidence is between 0 and 1
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)

        # Convert enums to their string values
        result['action'] = self.action.value
        result['severity'] = self.severity.value

        return result

    def is_actionable(self) -> bool:
        return self.action != ActionType.NONE and self.severity in [Severity.CRITICAL, Severity.WARNING]

    def get_priority(self) -> int:
        severity_priority = {
            Severity.CRITICAL: 100,
            Severity.WARNING: 50,
            Severity.INFO: 10,
            Severity.NORMAL: 0
        }

        # Base priority on severity, adjust by confidence
        base = severity_priority.get(self.severity, 0)
        return int(base * self.confidence)

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.node_id}: {self.decision_text} (action: {self.action.value})"

    def __repr__(self) -> str:
        return (f"Decision(node_id='{self.node_id}', severity={self.severity.value}, "
                f"action={self.action.value}, confidence={self.confidence})")
