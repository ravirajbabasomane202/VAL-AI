# engine/command_executor.py
from pathlib import Path
from engine.undo import log_action

def execute_command(intent: dict):
    action = intent.get("action")
    path_str = intent.get("path") or intent.get("target") or ""
    path = Path(path_str)

    if action == "create_folder":
        path.mkdir(parents=True, exist_ok=True)
        log_action("create_folder", str(path))
        return f"📁 Folder created at {path}"

    if action == "create_file":
        path.parent.mkdir(parents=True, exist_ok=True)
        # create file only if not exists, otherwise leave
        if not path.exists():
            path.write_text("", encoding="utf-8")
            log_action("create_file", str(path))
            return f"📄 File created at {path}"
        else:
            return f"ℹ️ File already exists at {path}"

    if action == "delete_folder":
        if path.exists() and path.is_dir():
            # Safety check - don't delete non-empty without confirmation
            try:
                path.rmdir()  # Only works if empty
                log_action("delete_folder", str(path))
                return f"🗑️ Folder deleted: {path}"
            except OSError:
                return f"⚠️ Folder not empty. Use 'force_delete' to remove recursively."
        else:
            return f"⚠️ Folder does not exist: {path}"

    if action == "delete_file":
        if path.exists() and path.is_file():
            path.unlink()
            log_action("delete_file", str(path))
            return f"🗑️ File deleted: {path}"
        else:
            return f"⚠️ File does not exist: {path}"

    # Add force delete option
    if action == "force_delete":
        if path.exists():
            import shutil
            shutil.rmtree(path) if path.is_dir() else path.unlink()
            log_action("force_delete", str(path))
            return f"🗑️ Force deleted: {path}"

    return "⚠️ Unknown command"
