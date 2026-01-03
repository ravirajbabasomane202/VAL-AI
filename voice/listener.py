# voice/listener.py
import sounddevice as sd
import queue
import json
import time
import sys
from vosk import Model, KaldiRecognizer
from pathlib import Path
import audioop
import wave
from core.session import SESSION
from core.memory import memory

AUDIO_LOG_DIR = Path("logs/audio")
AUDIO_LOG_DIR.mkdir(parents=True, exist_ok=True)

def save_wav(frames, filename):
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

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

def _callback(indata, frames, time, status):
    _q.put(bytes(indata))

def _play_beep(freq=1000, duration=200):
    if winsound:
        try:
            winsound.Beep(freq, duration)
        except:
            pass

MAX_SILENCE = 1.2   # base seconds
MIN_SILENCE = 0.5
RMS_THRESHOLD = 200  # tune this per mic

def _frame_rms(frame_bytes):
    # 16-bit samples
    try:
        return audioop.rms(frame_bytes, 2)
    except:
        return 0

def listen():
    """
    Blocks until a final recognition result is available and returns text.
    Uses a state machine: IDLE -> LISTENING -> PROCESSING.
    """
    state = "IDLE"
    speech_buffer = []
    silence_start = time.time()
    adaptive_silence = MAX_SILENCE
    collected_frames = []

    # Initialize RMS threshold (can be overridden by whisper mode)
    rms_threshold = RMS_THRESHOLD

    # Settings
    WAKE_WORDS = ["hey raj", "hey ray", "hey rage", "hey rajj", "hay raj", "hey rajah", "hey rajj", "he raj", "raj"]
    EXECUTE_WORDS = ["execute", "run", "do it", "go", "start"]
    
    vad_aggressiveness = SESSION.get("user_preferences", {}).get("vad_aggressiveness", 1)
    vad = webrtcvad.Vad(vad_aggressiveness) if webrtcvad else None
    EXECUTE_WORDS = ["execute", "run", "do it", "go", "start"]
    
    wake_word_enabled = SESSION.get("voice_prefs", {}).get("wake_word_enabled", True)
    if not wake_word_enabled:
        # Level 5: Whisper Mode check
        if SESSION.get("voice_prefs", {}).get("whisper_mode"):
            rms_threshold = 50
            
        state = "LISTENING"
        print("\n[🎤 LISTENING] Wake word disabled")
        _play_beep(1000, 200)
    else:
        print("\n[💤 IDLE] Waiting for 'Hey Raj'...")
    
    # pre-clear
    with _q.mutex:
        _q.queue.clear()
    _rec.Reset()

    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                               dtype="int16", channels=1, callback=_callback):
            while True:
                data = _q.get()
                collected_frames.append(data)
                is_speech_vad = False
                if vad:
                    try:
                        is_speech_vad = vad.is_speech(data, SAMPLE_RATE)
                    except:
                        is_speech_vad = False

                rms = _frame_rms(data)
                is_speech_energy = rms > rms_threshold

                # treat as speech if either VAD or energy says so
                is_speech = is_speech_vad or is_speech_energy

                # adapt silence timeout: if user speaking louder, shorten timeout
                if is_speech:
                    silence_start = time.time()
                    adaptive_silence = max(MIN_SILENCE, MAX_SILENCE * (200.0 / max(rms, 200.0)))
                    if state == "LISTENING":
                        sys.stdout.write("·")
                        sys.stdout.flush()

                # Vosk accept/partial handling (keep your existing logic)
                if _rec.AcceptWaveform(data):
                    res = json.loads(_rec.Result())
                    text = res.get("text", "")
                    if text:
                        silence_start = time.time()
                        if state == "IDLE":
                            if any(w in text for w in WAKE_WORDS):
                                state = "LISTENING"
                                print("\n[🎤 LISTENING] Wake word detected!")
                                _play_beep(1000, 200)
                                speech_buffer.append(text)
                                silence_start = time.time()
                        elif state == "LISTENING":
                            if text:
                                speech_buffer.append(text)
                else:
                    partial = json.loads(_rec.PartialResult()).get("partial", "")
                    # detect wake word in partials too (quicker)
                    if state == "IDLE":
                        if partial:
                            sys.stdout.write(f"\r[👂 Hearing]: {partial[:40].ljust(40)}")
                            sys.stdout.flush()
                        if partial and any(w in partial for w in WAKE_WORDS):
                            state = "LISTENING"
                            print("\n[🎤 LISTENING] Wake word detected!")
                            _play_beep(1000, 200)
                            silence_start = time.time()
                    # early execute/cancel detection (keep your existing keywords)
                    if state == "LISTENING":
                        if any(f" {w} " in f" {partial} " for w in EXECUTE_WORDS):
                            print("\n[⚙️ EXECUTING] Execute command detected")
                            break
                        if "cancel" in partial or "stop val" in partial:
                            print("\n[❌ CANCELLED]")
                            _play_beep(400, 300)
                            return ""
                        # endpoint on adaptive silence
                        if time.time() - silence_start > adaptive_silence:
                            print("\n[🧠 PROCESSING] Silence detected")
                            break

            # finishing
            _play_beep(800, 150)
            final = json.loads(_rec.FinalResult())
            if final.get("text"):
                speech_buffer.append(final["text"])
            full_text = " ".join(speech_buffer).lower()
            for w in WAKE_WORDS:
                full_text = full_text.replace(w, "")
            full_text = full_text.replace("execute", "").strip()
            if full_text:
                print(f"[🗣️ COMMAND] {full_text}")
            
            if SESSION.get("user_preferences", {}).get("log_audio", False):
                fname = AUDIO_LOG_DIR / f"{int(time.time())}_command.wav"
                save_wav(collected_frames, fname)
                memory.log_event("voice_record", data={"file": str(fname)})
            
            return full_text
    except KeyboardInterrupt:
        return ""
    except Exception as e:
        print(f"Error in listener: {e}")
        return ""
