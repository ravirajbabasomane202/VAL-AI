import subprocess
import json
from pathlib import Path
from core.memory import memory
from core.session import SESSION
from engine.env_manager import detect_project_type

def get_deps(cwd: Path = None) -> str:
    if cwd is None:
        cwd = Path(SESSION.get("last_project", {}).get("path", "."))
    
    ptype = detect_project_type(cwd)
    deps = []
    
    if ptype == "python":
        reqs = cwd / "requirements.txt"
        if reqs.exists():
            with open(reqs) as f:
                deps = [line.strip().split("==")[0] for line in f if line.strip() and not line.startswith("#")]
    elif ptype == "node":
        pkg = cwd / "package.json"
        if pkg.exists():
            with open(pkg) as f:
                data = json.load(f)
                deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
    
    memory.remember(f"deps_{ptype}_{cwd.name}", deps, "project")
    return f"📦 Deps ({ptype}): {', '.join(deps[:10])}{'...' if len(deps) > 10 else ''}"

def check_outdated(cwd: Path = None) -> str:
    ptype = detect_project_type(cwd)
    if ptype == "node":
        result = subprocess.run(["npm", "outdated"], cwd=cwd, capture_output=True, text=True)
        return f"🔄 Outdated (Node): {result.stdout[:200]}..."
    elif ptype == "python":
        result = subprocess.run(["pip", "list", "--outdated"], cwd=cwd, capture_output=True, text=True)
        return f"🔄 Outdated (Python): {result.stdout[:200]}..."
    return "⚠️ Outdated check not supported."

def add_dep(name: str, dev: bool = False, cwd: Path = None) -> str:
    from engine.undo import undo_manager
    ptype = detect_project_type(cwd)
    if ptype == "node":
        cmd = ["npm", "install", name] + (["--save-dev"] if dev else ["--save"])
    elif ptype == "python":
        cmd = ["pip", "install", name]
    else:
        return "❌ Unsupported type."
    
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    memory.log_event("dep_added", data={"name": name, "type": ptype})
    undo_manager.log_operation("install_dependency", {"name": name, "type": ptype, "cwd": str(cwd)})
    return f"➕ Added {name} ({ptype}): {result.stdout.strip()}"

def remove_dep(name: str, cwd: Path = None) -> str:
    from engine.undo import undo_manager
    safety = memory.check_safety({"action": "dep_remove"}, name)
    if safety["action"] == "confirm":
        speak(f"Remove {name}? (May break code)")
        response = listen().strip().lower()
        if not any(word in response for word in ["yes"]):
            return "❌ Cancelled."
    
    ptype = detect_project_type(cwd)
    if ptype == "node":
        cmd = ["npm", "uninstall", name]
    elif ptype == "python":
        cmd = ["pip", "uninstall", "-y", name]
    else:
        return "❌ Unsupported."
    
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    undo_manager.log_operation("uninstall_dependency", {"name": name, "type": ptype, "cwd": str(cwd)})
    return f"➖ Removed {name}: {result.stdout.strip()}"

def audit_dep(name: str, ptype: str) -> str:
    # Static rules (AI stub: later Ollama)
    risky = {"left-pad": "Known risk", "pyjwt": "Secure if configured"}
    return risky.get(name, f"✅ {name} good for {ptype}.")