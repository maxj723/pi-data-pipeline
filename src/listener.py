import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import time
from queue import Queue
from data_packet import TelemetryPacket

class MeshtasticListener:
    """
    Handles connection to a Meshtastic node and listens for incoming packets.
    Decoded messages are pushed into a queue for downstream processing.
    """

    def __init__(self):
        self.queue = Queue()
        self.interface = None

    def _on_receive(self, packet, interface):
        """ Callback for each received Meshtastic packet. """

        try:
            if "telemetry" in packet.get("decoded", {}):

                telemetry_data = packet["decoded"]["telemetry"]
                if "environmentMetrics" in telemetry_data:
                    node_id = packet.get("fromId", "unknown")
                    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

                    env_metrics = telemetry_data["environmentMetrics"]
                    telemetry_packet = TelemetryPacket(env_metrics, node_id, ts)

                    self.queue.put(telemetry_packet)
                    print(f"[{ts}] Received Telemetry from {node_id}: {telemetry_packet}")

        except Exception as e:
            print(f"Error handling packet: {e}")

    def start(self):
        """ Initialize listener and subscribe to Meshtastic events. """

        self.interface = meshtastic.serial_interface.SerialInterface()
        pub.subscribe(self._on_receive, "meshtastic.receive")
        print("Meshtastic listener started.")
        
        return self.queue
