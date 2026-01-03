"""
Enhanced Undo System - Time Travel for Operations
"""
from pathlib import Path
import json
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from core.memory import memory
from core.session import SESSION

UNDO_LOG = Path("logs/undo_stack.json")
TRASH_DIR = Path("logs/trash")
TRASH_DIR.mkdir(exist_ok=True)

class UndoManager:
    """Manage undoable operations with time travel"""
    
    def __init__(self):
        self.stack: List[Dict] = []
        self.load_stack()
    
    def load_stack(self):
        """Load undo stack from file"""
        if UNDO_LOG.exists():
            try:
                with open(UNDO_LOG, 'r') as f:
                    self.stack = json.load(f)
            except:
                self.stack = []
    
    def save_stack(self):
        """Save undo stack to file"""
        with open(UNDO_LOG, 'w') as f:
            json.dump(self.stack, f, indent=2)
    
    def log_operation(self, operation: str, details: Dict, undo_action: str = None):
        """Log an operation for potential undo"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details,
            "undo_action": undo_action or self._infer_undo_action(operation, details)
        }
        
        self.stack.append(entry)
        self.save_stack()
        
        # Keep only last 50 operations
        if len(self.stack) > 50:
            self.stack = self.stack[-50:]
            self.save_stack()
    
    def undo_last(self) -> str:
        """Undo the last operation"""
        if not self.stack:
            return "❌ Nothing to undo"
        
        entry = self.stack.pop()
        self.save_stack()
        
        try:
            result = self._execute_undo(entry)
            memory.log_event("undo_executed", data={"operation": entry["operation"], "success": True})
            return f"↩️ Undone: {entry['operation']}\n{result}"
        except Exception as e:
            # Restore to stack if undo failed
            self.stack.append(entry)
            self.save_stack()
            memory.log_event("undo_failed", data={"operation": entry["operation"], "error": str(e)})
            return f"❌ Undo failed: {e}"
    
    def undo_multiple(self, count: int) -> str:
        """Undo multiple operations"""
        results = []
        for i in range(min(count, len(self.stack))):
            result = self.undo_last()
            results.append(result)
            if "❌" in result:
                break
        return "\n".join(results) if results else "❌ Nothing to undo"
    
    def list_operations(self, limit: int = 10) -> str:
        """List recent operations that can be undone"""
        if not self.stack:
            return "📝 No operations to undo"
        
        ops = self.stack[-limit:]
        output = "📝 Recent Operations (can undo):\n"
        for i, op in enumerate(reversed(ops), 1):
            output += f"{i}. {op['operation']} ({op['timestamp'][:19]})\n"
        return output
    
    def _infer_undo_action(self, operation: str, details: Dict) -> str:
        """Infer undo action based on operation type"""
        if operation == "create_project":
            return "delete_project"
        elif operation == "install_dependency":
            return "uninstall_dependency"
        elif operation == "git_commit":
            return "git_reset_commit"
        elif operation == "delete_file":
            return "restore_file"
        elif operation == "delete_folder":
            return "restore_folder"
        elif operation == "create_file":
            return "delete_file"
        elif operation == "create_folder":
            return "delete_folder"
        return "unknown"
    
    def _execute_undo(self, entry: Dict) -> str:
        """Execute the undo action"""
        operation = entry["operation"]
        details = entry["details"]
        undo_action = entry["undo_action"]
        
        if undo_action == "delete_project":
            project_path = Path(details["path"])
            if project_path.exists():
                # Move to trash instead of delete
                trash_path = TRASH_DIR / f"{project_path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.move(str(project_path), str(trash_path))
                return f"Moved project to trash: {trash_path}"
            return "Project already deleted"
        
        elif undo_action == "uninstall_dependency":
            name = details.get("name", "")
            ptype = details.get("type", "python")
            if ptype == "python":
                result = subprocess.run(["pip", "uninstall", "-y", name], capture_output=True, text=True)
                return f"Uninstalled {name}: {result.stdout.strip()}"
            elif ptype == "node":
                result = subprocess.run(["npm", "uninstall", name], capture_output=True, text=True)
                return f"Uninstalled {name}: {result.stdout.strip()}"
        
        elif undo_action == "git_reset_commit":
            cwd = Path(details.get("cwd", "."))
            result = subprocess.run(["git", "reset", "HEAD~1", "--soft"], cwd=cwd, capture_output=True, text=True)
            return f"Reset last commit: {result.stdout.strip()}"
        
        elif undo_action == "restore_file":
            # For soft deletes, restore from trash
            file_path = Path(details["path"])
            trash_files = list(TRASH_DIR.glob(f"*{file_path.name}*"))
            if trash_files:
                latest_trash = max(trash_files, key=lambda x: x.stat().st_mtime)
                shutil.move(str(latest_trash), str(file_path))
                return f"Restored file: {file_path}"
            return "File not found in trash"
        
        elif undo_action == "restore_folder":
            folder_path = Path(details["path"])
            trash_folders = list(TRASH_DIR.glob(f"*{folder_path.name}*"))
            if trash_folders:
                latest_trash = max(trash_folders, key=lambda x: x.stat().st_mtime)
                shutil.move(str(latest_trash), str(folder_path))
                return f"Restored folder: {folder_path}"
            return "Folder not found in trash"
        
        return f"Unknown undo action: {undo_action}"

# Global undo manager
undo_manager = UndoManager()

# Backward compatibility
def log_action(action: str, path: str):
    """Legacy function for backward compatibility"""
    undo_manager.log_operation(action, {"path": path})

def undo_last():
    """Legacy function for backward compatibility"""
    return undo_manager.undo_last()
