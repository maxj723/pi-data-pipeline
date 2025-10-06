#!/usr/bin/env python3
import time
from listener import MeshtasticListener

LOG_FILE = "meshtastic_messages.log"

def main():
    print("🔧 Initializing Meshtastic listener...")
    listener = MeshtasticListener()
    q = listener.start()

    print(f"📡 Listening for messages... Logging to {LOG_FILE}\n")

    try:
        while True:
            if not q.empty():
                data = q.get()
                log_line = (f"[{data['timestamp']}] From {data['node_id']}: \n"
                           f"temperature: {data['temperature']}, \n"
                           f"humidity: {data['humidity']}\n")

                # Write to file
                with open(LOG_FILE, "a") as f:
                    f.write(log_line)

                # Print to terminal
                print(log_line, end="")

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n🛑 Stopping listener.")
    except Exception as e:
        print(f"⚠️ Error in main loop: {e}")

if __name__ == "__main__":
    main()