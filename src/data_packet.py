from typing import Optional

class TelemetryPacket:
    def __init__(self, telemetry_data: dict, node_id: str, timestamp: str):
        self.node_id = node_id
        self.timestamp = timestamp

        self.temperature: Optional[float] = telemetry_data.get("temperature")
        self.relative_humidity: Optional[float] = telemetry_data.get("relativeHumidity")
        self.soil_moisture: Optional[float] = telemetry_data.get("soilMoisture")
        self.lux: Optional[float] = telemetry_data.get("lux")
        self.voltage: Optional[float] = telemetry_data.get("voltage")

    def __repr__(self):
        return (f"TelemetryPacket(node_id={self.node_id}, timestamp={self.timestamp}, "
                f"temp={self.temperature}, humidity={self.relative_humidity}, "
                f"soil moisture={self.soil_moisture}, lux={self.lux}, "
                f"voltage={self.voltage})")

    def to_dict(self) -> dict:
        return {
            "node_id":              self.node_id,
            "timestamp":            self.timestamp,
            "temperature":          self.temperature,
            "relative_humidity":    self.relative_humidity,
            "soil_moisture":        self.soil_moisture,
            "lux":                  self.lux,
            "voltage":              self.voltage,
        }
