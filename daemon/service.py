# daemon/service.py
import logging
import time
from pathlib import Path

# local imports
from voice.listener import listen
from voice.speaker import speak
from ai.intent_extractor import extract_intent
from engine.intent_router import route

# ensure logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "daemon.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def run():
    speak("VAL is running")
    logging.info("VAL daemon started")
    
    pending_intent = None

    while True:
        try:
            command = listen()
            if not command:
                # brief sleep to avoid tight loop
                time.sleep(0.1)
                continue

            logging.info(f"Received voice command: {command!r}")

            if pending_intent:
                if "confirm" in command.lower() or "yes" in command.lower():
                    speak("Confirmed.")
                    intent = pending_intent
                    pending_intent = None
                else:
                    speak("Cancelled.")
                    pending_intent = None
                    continue
            else:
                intent = extract_intent(command)
                logging.info(f"Extracted intent: {intent!r}")

                # Dangerous Action Check
                is_dangerous = intent.get("intent") in ["delete_file", "delete_folder"] or \
                               intent.get("action") in ["delete_file", "delete_folder", "force_delete"]

                if is_dangerous:
                    pending_intent = intent
                    speak("Are you sure? Say confirm.")
                    continue

            result = route(intent)

            if result == "__STOP__":
                speak("Stopping VAL")
                logging.info("Daemon stopped by voice command")
                break

            logging.info(f"Action result: {result!r}")
            if "No intent detected" in result:
                speak("Sorry, I did not understand that. You can say things like create folder, create file, or create a project.")
            else:
                speak(result)

        except KeyboardInterrupt:
            logging.info("Daemon stopped by user (KeyboardInterrupt)")
            speak("Stopping")
            break
        except Exception as e:
            logging.exception("Error in daemon loop")
            # keep daemon alive; notify user
            try:
                speak("An error occurred. Check logs.")
            except Exception:
                pass
            # small backoff before next listen
            time.sleep(1)
