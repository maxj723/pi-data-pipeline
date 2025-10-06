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
            node_id = packet.get("fromId", "unknown")
            msg = packet.get("decoded", {}).get("text", "")

            try:
                data = json.loads(msg)
                if isinstance(data, dict):
                    data["node_id"] = node_id
                    data["timestamp"] = ts
                    self.queue.put(data)
                    print(f"[{ts}] Received from {node_id}: {data}")
            except json.JSONDecodeError:
                print(f"Ignored non-JSON from {node_id}: {msg}")
        except Exception as e:
            print(f"Error handling packet: {e}")

    def start(self):
        """Initialize listener and subscribe to Meshtastic events."""
        self.interface = meshtastic.serial_interface.SerialInterface()
        pub.subscribe(self._on_receive, "meshtastic.receive")
        print("Meshtastic listener started.")
        return self.queue