#!/usr/bin/env python3
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import json
import time

LOG_FILE = "meshtastic_messages.log"

def log_message(packet, interface):
    """
    Callback for every received Meshtastic message.
    Writes messages to a log file with timestamp and node info.
    """
    try:
        node_id = packet.get("fromId", "unknown")
        decoded = packet.get("decoded", {})
        msg = decoded.get("text", "")
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

        entry = {
            "timestamp": timestamp,
            "node_id": node_id,
            "raw_message": msg,
            "full_packet": decoded
        }

        # Append to log file
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"[{timestamp}] Logged message from {node_id}: {msg}")

    except Exception as e:
        print(f"Error logging message: {e}")

def main():
    print("🔌 Connecting to Meshtastic device...")
    interface = meshtastic.serial_interface.SerialInterface()  # auto-detects USB serial port
    pub.subscribe(log_message, "meshtastic.receive")
    print(f"📡 Listening for messages... (logging to {LOG_FILE})")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping logger.")
        interface.close()

if __name__ == "__main__":
    main()