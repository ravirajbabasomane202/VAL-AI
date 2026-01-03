import subprocess
from pathlib import Path
from core.memory import memory
from core.session import SESSION
from voice.speaker import speak
from voice.listener import listen

def execute_git_command(args: list, cwd: Path = None, confirm_destructive: bool = True) -> str:
    if cwd is None:
        cwd = Path(SESSION.get("last_project", {}).get("path", "."))
    
    destructive_cmds = ["reset", "rebase", "rm", "--force"]
    if any(cmd in " ".join(args) for cmd in destructive_cmds):
        safety = memory.check_safety({"action": "git_destructive"}, " ".join(args))
        if safety["action"] == "confirm" and confirm_destructive:
            speak(f"Destructive Git: {' '.join(args)}. Confirm?")
            response = listen().strip().lower()
            if not any(word in response for word in ["yes", "confirm"]):
                return "❌ Cancelled: Destructive action."
        elif safety["action"] == "deny":
            return f"❌ Blocked: {safety['reason']}"
    
    try:
        result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=True)
        memory.log_event("git_executed", data={"command": args, "cwd": str(cwd), "success": True})
        return f"✅ Git: {' '.join(args)}\n{result.stdout.strip() if result.stdout else 'Done.'}"
    except subprocess.CalledProcessError as e:
        memory.log_event("git_failed", data={"command": args, "error": e.stderr})
        return f"❌ Git failed: {e.stderr.strip()}"

def init_repo(remote: str = None, cwd: Path = None) -> str:
    result = execute_git_command(["init"], cwd)
    if remote:
        execute_git_command(["remote", "add", "origin", remote], cwd)
    return result + "\n(Repo initialized)"

def commit(message: str, cwd: Path = None) -> str:
    from engine.undo import undo_manager
    result = execute_git_command(["add", "."], cwd) + "\n" + execute_git_command(["commit", "-m", message], cwd)
    undo_manager.log_operation("git_commit", {"message": message, "cwd": str(cwd)})
    return result

def create_branch(name: str, cwd: Path = None) -> str:
    return execute_git_command(["checkout", "-b", name], cwd)

def push(remote: str = "origin", branch: str = "main", force: bool = False, cwd: Path = None) -> str:
    args = ["push", remote, branch]
    if force:
        args += ["--force"]
    return execute_git_command(args, cwd)

def undo_last_commit(cwd: Path = None) -> str:
    return execute_git_command(["reset", "HEAD~1", "--soft"], cwd, confirm_destructive=True)

def get_status(cwd: Path = None) -> str:
    result = subprocess.run(["git", "status"], cwd=cwd, capture_output=True, text=True)
    return f"📊 Git Status:\n{result.stdout}"

def undo_last_commit(cwd: Path = None) -> str:
    # Soft reset for safety
    return execute_git_command(["reset", "HEAD~1", "--soft"], cwd, confirm_destructive=True)

def get_status(cwd: Path = None) -> str:
    result = subprocess.run(["git", "status"], cwd=cwd, capture_output=True, text=True)
    return f"📊 Git Status:\n{result.stdout}"