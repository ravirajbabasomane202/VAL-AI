from pathlib import Path

def safe_create_dir(path: Path):
    try:
        if not path.exists():
            path.mkdir(parents=True)
            print(f"[DIR ] {path}")
    except Exception as e:
        print(f"❌ Error creating directory {path}: {e}")

def safe_create_file(path: Path, content=""):
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"[FILE] {path}")
        else:
            print(f"ℹ️ File already exists: {path}")
    except Exception as e:
        print(f"❌ Error creating file {path}: {e}")