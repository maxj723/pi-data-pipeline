from typing import Optional


class DataPacket:
    def __init__(self, node_id: str, timestamp: str):
        self.node_id = node_id
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        """Returns base dictionary with common fields"""
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
        }


class EnvironmentPacket(DataPacket):
    def __init__(self, telemetry_data: dict, node_id: str, timestamp: str):
        super().__init__(node_id, timestamp)
        self.temperature: Optional[float] = telemetry_data.get("temperature")
        self.relative_humidity: Optional[float] = telemetry_data.get("relativeHumidity")
        self.soil_moisture: Optional[float] = telemetry_data.get("soilMoisture")
        self.lux: Optional[float] = telemetry_data.get("lux")

    def __repr__(self):
        return (f"EnvironmentPacket(node_id={self.node_id}, timestamp={self.timestamp}, "
                f"temp={self.temperature}, humidity={self.relative_humidity}, "
                f"soil moisture={self.soil_moisture}, lux={self.lux})")

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "temperature": self.temperature,
            "relative_humidity": self.relative_humidity,
            "soil_moisture": self.soil_moisture,
            "lux": self.lux,
        }


class PowerPacket(DataPacket):
    def __init__(self, telemetry_data: dict, node_id: str, timestamp: str):
        super().__init__(node_id, timestamp)
        self.voltage: Optional[float] = telemetry_data.get("ch1Voltage")

    def __repr__(self):
        return (f"PowerPacket(node_id={self.node_id}, timestamp={self.timestamp}, "
                f"voltage={self.voltage})")

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "voltage": self.voltage,
        }
