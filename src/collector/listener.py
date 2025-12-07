import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import time
from queue import Queue
from typing import Optional, Any
from .data_packet import DataPacket, EnvironmentPacket, PowerPacket


class MeshtasticListener:
    def __init__(self):
        self.queue: Queue[DataPacket] = Queue()
        self.interface: Optional[meshtastic.serial_interface.SerialInterface] = None

    def _get_node_id(self, packet: dict[str, Any]) -> str:
        return packet.get("fromId", "unknown")

    def _get_timestamp(self) -> str:
        return time.strftime('%Y-%m-%d %H:%M', time.localtime())

    def _process_environment_metrics(self, packet: dict[str, Any], telemetry_data: dict[str, Any]) -> None:
        env_metrics = telemetry_data["environmentMetrics"]
        environment_packet = EnvironmentPacket(
            env_metrics,
            self._get_node_id(packet),
            self._get_timestamp()
        )
        self.queue.put(environment_packet)

    def _process_power_metrics(self, packet: dict[str, Any], telemetry_data: dict[str, Any]) -> None:
        pow_metrics = telemetry_data["powerMetrics"]
        power_packet = PowerPacket(
            pow_metrics,
            self._get_node_id(packet),
            self._get_timestamp()
        )
        self.queue.put(power_packet)

    def _on_receive(self, packet: dict[str, Any], interface) -> None:
        try:
            decoded = packet.get("decoded", {})
            if "telemetry" not in decoded:
                return

            telemetry_data = decoded["telemetry"]
            print(f"Received Telemetry Data: {telemetry_data}")

            if "environmentMetrics" in telemetry_data:
                self._process_environment_metrics(packet, telemetry_data)
            elif "powerMetrics" in telemetry_data:
                self._process_power_metrics(packet, telemetry_data)

        except Exception as e:
            print(f"Error handling packet: {e}")

    def start(self) -> Queue[DataPacket]:
        self.interface = meshtastic.serial_interface.SerialInterface()
        pub.subscribe(self._on_receive, "meshtastic.receive")
        print("Meshtastic listener started.")
        return self.queue
