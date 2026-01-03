from utils.fs import safe_create_dir, safe_create_file
from pathlib import Path
from engine.undo import undo_manager

def apply_blueprint(base: Path, blueprint: dict):
    safe_create_dir(base)
    undo_manager.log_operation("create_project", {"path": str(base), "type": "folder"})

    for folder in blueprint.get("folders", []):
        p = base / folder
        safe_create_dir(p)
        undo_manager.log_operation("create_folder", {"path": str(p)})

    for file_entry in blueprint.get("files", []):
        if isinstance(file_entry, dict):
            # New format: {"path": "...", "content": "..."}
            file_path = file_entry.get("path", "")
            content = file_entry.get("content", "")
        elif ":" in str(file_entry):
            # Old format: "path:content"
            file_path, content = str(file_entry).split(":", 1)
        else:
            # Plain string format
            file_path = str(file_entry)
            content = ""
        
        # Clean up file path
        file_path = file_path.strip()
        if file_path:
            p = base / file_path
            safe_create_file(p, content)
            undo_manager.log_operation("create_file", {"path": str(p)})