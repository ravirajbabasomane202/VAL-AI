# engine/command_executor.py
from pathlib import Path
from engine.undo import undo_manager
import shutil
import subprocess
import platform

def execute_command(intent: dict):
    action = intent.get("action")
    path_str = intent.get("path") or intent.get("target") or ""
    path = Path(path_str)

    if action == "create_folder":
        path.mkdir(parents=True, exist_ok=True)
        undo_manager.log_operation("create_folder", {"path": str(path)})
        return f"📁 Folder created at {path}"

    if action == "create_file":
        path.parent.mkdir(parents=True, exist_ok=True)
        # create file only if not exists, otherwise leave
        if not path.exists():
            path.write_text("", encoding="utf-8")
            undo_manager.log_operation("create_file", {"path": str(path)})
            return f"📄 File created at {path}"
        else:
            return f"ℹ️ File already exists at {path}"

    if action == "delete_folder":
        if path.exists() and path.is_dir():
            # Soft delete: move to trash
            from engine.undo import TRASH_DIR
            trash_path = TRASH_DIR / f"{path.name}_{path.stat().st_mtime}"
            shutil.move(str(path), str(trash_path))
            undo_manager.log_operation("delete_folder", {"path": str(path), "trash_path": str(trash_path)})
            return f"🗑️ Folder moved to trash: {trash_path}"
        else:
            return f"⚠️ Folder does not exist: {path}"

    if action == "delete_file":
        if path.exists() and path.is_file():
            # Soft delete: move to trash
            from engine.undo import TRASH_DIR
            trash_path = TRASH_DIR / f"{path.name}_{path.stat().st_mtime}"
            shutil.move(str(path), str(trash_path))
            undo_manager.log_operation("delete_file", {"path": str(path), "trash_path": str(trash_path)})
            return f"🗑️ File moved to trash: {trash_path}"
        else:
            return f"⚠️ File does not exist: {path}"

    # Add force delete option (hard delete)
    if action == "force_delete":
        if path.exists():
            shutil.rmtree(path) if path.is_dir() else path.unlink()
            undo_manager.log_operation("force_delete", {"path": str(path)})
            return f"💥 Force deleted: {path}"
        else:
            return f"⚠️ Path does not exist: {path}"
            return f"🗑️ Force deleted: {path}"

    return "⚠️ Unknown command"

def open_application(app_name: str, path: Path = None):
    """Open external applications (Level 5)"""
    system = platform.system()
    path_str = str(path) if path else "."
    
    # Normalize app name
    name = app_name.lower().replace(" ", "").replace("vs", "")
    
    cmds = {
        "code": ["code", path_str],
        "vscode": ["code", path_str],
        "browser": ["start", "http://localhost:3000"] if system == "Windows" else ["open", "http://localhost:3000"],
        "postman": ["postman"],
        "terminal": ["start", "cmd", "/k", f"cd /d {path_str}"] if system == "Windows" else ["gnome-terminal", "--working-directory", path_str],
        "docker": ["start", "Docker Desktop"] if system == "Windows" else ["open", "-a", "Docker"],
        "dockerdesktop": ["start", "Docker Desktop"] if system == "Windows" else ["open", "-a", "Docker"]
    }
    
    cmd = cmds.get(name)
    if not cmd:
        return f"⚠️ Unknown app: {app_name}"
        
    try:
        if system == "Windows":
            # Use shell=True for Windows start commands as they require shell interpretation
            subprocess.Popen(cmd, shell=True)
        else:
            # Use shell=False for Unix-like systems for better security
            subprocess.Popen(cmd, shell=False)
        return f"🚀 Opened {app_name}"
    except Exception as e:
        return f"❌ Failed to open {app_name}: {e}"
