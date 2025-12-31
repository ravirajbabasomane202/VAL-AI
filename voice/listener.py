# voice/listener.py
import sounddevice as sd
import queue
import json
import time
import sys
from vosk import Model, KaldiRecognizer
from pathlib import Path

# Optional: VAD for better silence detection
try:
    import webrtcvad
except ImportError:
    webrtcvad = None
    print("⚠️ webrtcvad not installed. Run: pip install webrtcvad")

# Optional: Windows sound for feedback
try:
    import winsound
except ImportError:
    winsound = None

_q = queue.Queue()
MODEL_DIR = Path("models/vosk-small-en-us")
if not MODEL_DIR.exists():
    raise RuntimeError("Vosk model not found at models/vosk-small-en-us. See README to download it.")

_model = Model(str(MODEL_DIR))
_rec = KaldiRecognizer(_model, 16000)

# Audio configuration
SAMPLE_RATE = 16000
# webrtcvad requires 10, 20, or 30ms frames. 30ms @ 16kHz = 480 samples.
BLOCK_SIZE = 480 

_vad = webrtcvad.Vad(1) if webrtcvad else None

def _callback(indata, frames, time, status):
    _q.put(bytes(indata))

def _play_beep(freq=1000, duration=200):
    if winsound:
        try:
            winsound.Beep(freq, duration)
        except:
            pass

def listen():
    """
    Blocks until a final recognition result is available and returns text.
    Uses a state machine: IDLE -> LISTENING -> PROCESSING.
    """
    state = "IDLE"
    silence_start = time.time()
    speech_buffer = []
    
    # Settings
    SILENCE_TIMEOUT = 1.2 # seconds
    
    print("\n[💤 IDLE] Waiting for 'Hey Val'...")
    
    # Clear queue and reset recognizer for fresh start
    with _q.mutex:
        _q.queue.clear()
    _rec.Reset()

    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                               dtype="int16", channels=1, callback=_callback):
            while True:
                data = _q.get()
                
                # 1. VAD Check (Voice Activity Detection)
                is_speech = False
                if _vad:
                    try:
                        is_speech = _vad.is_speech(data, SAMPLE_RATE)
                    except:
                        pass
                
                if is_speech:
                    silence_start = time.time()
                    if state == "LISTENING":
                        sys.stdout.write("·")
                        sys.stdout.flush()

                # 2. Vosk Processing
                if _rec.AcceptWaveform(data):
                    res = json.loads(_rec.Result())
                    text = res.get("text", "")
                    
                    # Reset silence timeout if we get a finalized sentence
                    if text:
                        silence_start = time.time()

                    if state == "IDLE":
                        if "hey val" in text:
                            state = "LISTENING"
                            print("\n[🎤 LISTENING] Wake word detected!")
                            _play_beep(1000, 200)
                            speech_buffer.append(text)
                            silence_start = time.time()
                    elif state == "LISTENING":
                        if text:
                            speech_buffer.append(text)
                else:
                    # Partial results for quick triggers
                    res = json.loads(_rec.PartialResult())
                    partial = res.get("partial", "")
                    
                    if state == "IDLE":
                        if "hey val" in partial:
                            state = "LISTENING"
                            print("\n[🎤 LISTENING] Wake word detected!")
                            _play_beep(1000, 200)
                            silence_start = time.time()
                            
                    elif state == "LISTENING":
                        # Check for commands
                        if "execute" in partial:
                            print("\n[⚙️ EXECUTING] Execute command detected")
                            break
                        
                        if "cancel" in partial or "stop val" in partial:
                            print("\n[❌ CANCELLED]")
                            _play_beep(400, 300)
                            return "" # Return empty to loop again in daemon
                        
                        # Silence timeout
                        if time.time() - silence_start > SILENCE_TIMEOUT:
                            print("\n[🧠 PROCESSING] Silence detected")
                            break

            # End of recording loop
            _play_beep(800, 150)
            
            # Capture any remaining buffer
            final = json.loads(_rec.FinalResult())
            if final.get("text"):
                speech_buffer.append(final["text"])
            
            full_text = " ".join(speech_buffer).lower()
            
            # Clean up
            full_text = full_text.replace("hey val", "").replace("execute", "").strip()
            
            if full_text:
                print(f"[🗣️ COMMAND] {full_text}")
            
            return full_text

    except KeyboardInterrupt:
        return ""
    except Exception as e:
        # don't crash daemon — return empty and let caller handle
        print(f"Error in listener: {e}")
        return ""
