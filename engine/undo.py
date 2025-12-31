from pathlib import Path
import json
from datetime import datetime

LOG_FILE = Path("logs/actions.log")
LOG_FILE.parent.mkdir(exist_ok=True)

def log_action(action: str, path: str):
    entry = {
        "time": datetime.now().isoformat(),
        "action": action,
        "path": path
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def undo_last():
    if not LOG_FILE.exists():
        return "❌ Nothing to undo"

    lines = LOG_FILE.read_text().strip().splitlines()
    if not lines:
        return "❌ Nothing to undo"

    last = json.loads(lines[-1])
    path = Path(last["path"])

    if path.exists():
        if path.is_file():
            path.unlink()
        else:
            for p in reversed(list(path.rglob("*"))):
                if p.is_file():
                    p.unlink()
                else:
                    p.rmdir()
            path.rmdir()

    LOG_FILE.write_text("\n".join(lines[:-1]) + "\n")
    return f"↩️ Undone: {last['action']} {path}"
