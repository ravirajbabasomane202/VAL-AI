"""
Session Memory - RAM-based short-term context
"""
SESSION = {
    "state": "idle",  # idle, listening, thinking, confirming, executing
    "last_command": None,
    "last_project": None,
    "last_intent": None,
    "pending_action": None,
    "last_result": None,
    "buffer": [],  # For multi-step commands
    "conversation_context": [],
    "wake_word_detected": False,
    "current_task": None,
    "actions_count": 0,
    "user_preferences": {}
}

def reset_conversation():
    """Reset conversation context while keeping preferences"""
    SESSION["buffer"] = []
    SESSION["conversation_context"] = []
    SESSION["pending_action"] = None
    SESSION["state"] = "idle"

def add_to_context(message, role="user"):
    """Add message to conversation context (max 10 messages)"""
    SESSION["conversation_context"].append({"role": role, "content": message})
    if len(SESSION["conversation_context"]) > 10:
        SESSION["conversation_context"] = SESSION["conversation_context"][-10:]

def get_context():
    """Get current conversation context"""
    return SESSION["conversation_context"]

def set_state(state):
    """Change system state"""
    SESSION["state"] = state

def get_state():
    """Get current state"""
    return SESSION["state"]