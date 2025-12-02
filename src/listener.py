import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import time
from queue import Queue
from data_packet import EnvironmentPacket, PowerPacket

class MeshtasticListener:
    """
    Handles connection to a Meshtastic node and listens for incoming packets.
    Decoded messages are pushed into a queue for downstream processing.
    """

    def __init__(self):
        self.queue = Queue()
        self.interface = None

    def _on_receive(self, packet, interface):
        try:
            if "telemetry" in packet.get("decoded", {}):
                telemetry_data = packet["decoded"]["telemetry"]
                print(f'Telemetry data: {telemetry_data}')

                if "environmentMetrics" in telemetry_data:
                    node_id = packet.get("fromId", "unknown")
                    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

                    env_metrics = telemetry_data["environmentMetrics"]
                    environment_packet = EnvironmentPacket(env_metrics, node_id, ts)

                    self.queue.put(environment_packet)
                    print(f"[{ts}] Received Telemetry from {node_id}: {environment_packet}")

                elif "powerMetrics" in telemetry_data:
                    node_id = packet.get("fromId", "unknown")
                    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

                    pow_metrics = telemetry_data["powerMetrics"]
                    power_packet = PowerPacket(pow_metrics, node_id, ts)

                    self.queue.put(power_packet)
                    print(f"[{ts}] Received Telemetry from {node_id}: {power_packet}")

        except Exception as e:
            print(f"Error handling packet: {e}")

    def start(self):
        self.interface = meshtastic.serial_interface.SerialInterface()
        pub.subscribe(self._on_receive, "meshtastic.receive")
        print("Meshtastic listener started.")
        
        return self.queue
