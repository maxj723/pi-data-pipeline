from typing import Optional

class TelemetryPacket:
    """
    Represents a telemetry packet containing environmental metrics from a Meshtastic node.
    """

    def __init__(self, telemetry_data: dict, node_id: str, timestamp: str):
        """
        Initialize a TelemetryPacket with environment metrics and metadata.

        Args:
            telemetry_data: Dictionary containing environmentMetrics data
            node_id: ID of the node that sent the telemetry
            timestamp: Timestamp when the packet was received
        """

        self.node_id = node_id
        self.timestamp = timestamp

        self.temperature: Optional[float] = telemetry_data.get("temperature")
        self.relative_humidity: Optional[float] = telemetry_data.get("relativeHumidity")
        self.barometric_pressure: Optional[float] = telemetry_data.get("barometricPressure")
        self.gas_resistance: Optional[float] = telemetry_data.get("gasResistance")
        self.voltage: Optional[float] = telemetry_data.get("voltage")
        self.current: Optional[float] = telemetry_data.get("current")
        self.iaq: Optional[int] = telemetry_data.get("iaq")

    def __repr__(self):
        """String representation of the telemetry packet."""
        return (f"TelemetryPacket(node_id={self.node_id}, timestamp={self.timestamp}, "
                f"temp={self.temperature}, humidity={self.relative_humidity}, "
                f"pressure={self.barometric_pressure})")

    def to_dict(self) -> dict:
        """Convert the telemetry packet back to a dictionary format (snake_case for database)."""
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "temperature": self.temperature,
            "relative_humidity": self.relative_humidity,
            "barometric_pressure": self.barometric_pressure,
            "gas_resistance": self.gas_resistance,
            "voltage": self.voltage,
            "current": self.current,
            "iaq": self.iaq
        }
