import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import json
import time
from queue import Queue

class MeshtasticListener:
    """
    Handles connection to a Meshtastic node and listens for incoming packets.
    Decoded messages are pushed into a queue for downstream processing.
    """
    def __init__(self):
        self.queue = Queue()
        self.interface = None

    def _on_receive(self, packet, interface):
        """Callback for each received Meshtastic packet."""
        try:

            if packet.get("decoded", {}).get("portnum") == "ENVIRONMENTAL_MEASUREMENT":
                print(f"Received Environmental Telemetry: {packet}")

            # node_id = packet.get("fromId", "unknown")
            # msg = packet.get("decoded", {}).get("text", "")
            # ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

            # try:
            #     msg = msg.strip()
            #     data = json.loads(msg)
            #     if isinstance(data, dict):
            #         data["timestamp"] = ts
            #         data["node_id"] = node_id

            #         self.queue.put(data)
            #         print(f"[{ts}] Received from {node_id}: {data}")

            #     # data = {
            #     #     "timestamp": ts,
            #     #     "node_id": node_id,
            #     #     "message": msg
            #     # }
            #     # self.queue.put(data)
            #     # print(f"[{ts}] From {node_id}: {msg}")

            # except json.JSONDecodeError:
            #     print(f"Ignored non-JSON from {node_id}: {msg}")
        except Exception as e:
            print(f"Error handling packet: {e}")

    def start(self):
        """Initialize listener and subscribe to Meshtastic events."""
        self.interface = meshtastic.serial_interface.SerialInterface()
        pub.subscribe(self._on_receive, "meshtastic.receive")
        print("Meshtastic listener started.")
        return self.queue