# ai/ollama_client.py
import subprocess
import shutil

def ask_ollama(prompt: str, model="mistral", timeout=300):
    """
    Run Ollama CLI with the given prompt and return stdout.
    Raises RuntimeError with helpful message if CLI not found or run fails.
    """
    if shutil.which("ollama") is None:
        raise RuntimeError(
            "ollama CLI not found. Please install Ollama and ensure 'ollama' is on PATH. "
            "See: https://ollama.com/docs"
        )

    command = ["ollama", "run", model]

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        stdout, stderr = process.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("Ollama request timed out.")
    except Exception as e:
        raise RuntimeError(f"Failed to run ollama: {e}")

    if process.returncode != 0:
        raise RuntimeError(stderr.strip() or "ollama returned a non-zero exit code")

    return stdout.strip()
