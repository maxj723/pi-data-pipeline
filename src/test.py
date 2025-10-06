#!/usr/bin/env python3
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import time

LOG_FILE = "meshtastic_messages.log"

def log_message(packet, interface):
    """
    Callback for every received Meshtastic message.
    Logs all message text (no filtering or JSON parsing).
    """
    try:
        node_id = packet.get("fromId", "unknown")
        decoded = packet.get("decoded", {})
        msg = decoded.get("text", "")
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

        log_line = f"[{timestamp}] From {node_id}: {msg}\n"

        with open(LOG_FILE, "a") as f:
            f.write(log_line)

        print(log_line, end="")

    except Exception as e:
        print(f"Error logging message: {e}")

def main():
    print("🔌 Connecting to Meshtastic device...")
    interface = meshtastic.serial_interface.SerialInterface()  # Auto-detects serial port
    pub.subscribe(log_message, "meshtastic.receive")
    print(f"📡 Listening for ALL messages (logging to {LOG_FILE})")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping logger.")
        interface.close()

if __name__ == "__main__":
    main()