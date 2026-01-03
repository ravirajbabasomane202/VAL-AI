"""
Initialize VAL memory system
"""
from core.memory import memory
import json
from pathlib import Path

def initialize_memory():
    """Initialize memory with default data"""
    print("🧠 Initializing VAL Memory System...")
    
    # Create memory directory
    Path("memory").mkdir(exist_ok=True)
    
    # Set default preferences
    memory.set_preference("default_project_location", str(Path.home() / "Projects"), "path")
    memory.set_preference("preferred_theme", "dark", "ui")
    memory.set_preference("ask_confirmation", True, "safety")
    memory.set_preference("auto_open_project", False, "behavior")
    memory.set_preference("wake_word_enabled", True, "voice")
    memory.set_preference("push_to_talk", False, "voice")
    memory.set_preference("confidence_threshold", 0.75, "voice")
    memory.set_preference("log_audio", False, "voice")
    memory.set_preference("vad_aggressiveness", 1, "voice")
    memory.set_preference("auto_apply_workflows", True, "workflow")
    memory.set_preference("passive_learning", False, "workflow")
    
    # Workflow safety
    memory.add_safety_rule("workflow_action", "git reset", "confirm", "Git history change")
    memory.add_safety_rule("workflow_action", "delete", "confirm", "Destructive file op")
    memory.add_safety_rule("workflow_action", "docker build", "allow", "Container automation")
    
    # Git safety
    memory.add_safety_rule("git_destructive", "reset --hard", "confirm", "Irreversible history loss")
    memory.add_safety_rule("git_destructive", "push --force", "confirm", "Overwrites remote history")
    memory.add_safety_rule("git_destructive", "rm --cached", "allow", "Safe untrack")
    
    # Add some example memories
    memory.remember("val_purpose", "VAL is a Local Autonomous AI Operator that helps with project creation and file management.", "fact")
    memory.remember("user_role", "developer/creator", "fact", tags="user,role")
    
    # Add helpful tips
    memory.remember("tip_voice_commands", "Say 'Hey Raj' to wake me up, then give commands like 'create a Flask project' or 'open last project'.", "tip")
    memory.remember("tip_memory", "I remember your projects and preferences. Ask me to 'list projects' or 'recall my default path'.", "tip")
    
    print("✅ Memory system initialized!")
    print("📊 Stats:")
    print(f"  - Memory entries: {memory.conn.execute('SELECT COUNT(*) FROM memory').fetchone()[0]}")
    print(f"  - Safety rules: {memory.conn.execute('SELECT COUNT(*) FROM safety_rules').fetchone()[0]}")
    print(f"  - Preferences: {memory.conn.execute('SELECT COUNT(*) FROM preferences').fetchone()[0]}")
    
    return memory

if __name__ == "__main__":
    initialize_memory()