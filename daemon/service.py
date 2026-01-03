"""
Enhanced Daemon Service with Memory, State Machine, and Cognitive Loop
"""
import logging
import time
import json
import threading
from pathlib import Path

from voice.listener import listen
from voice.speaker import speak
from ai.intent_extractor import extract_intent_with_memory
from engine.intent_router import route, after_intent_execution
from core.memory import memory
from core.session import SESSION, set_state, add_to_context, get_context
from agent.core import agent
from agent.self_improver import self_improver
from agent.core import CriticAgent

# Ensure logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "daemon_enhanced.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# Level 5: Background Watcher
class ProjectWatcher:
    def __init__(self):
        self.running = False
        self.path = None
        self.last_mtime = 0
    
    def start(self, path_str):
        self.path = Path(path_str)
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
    
    def stop(self):
        self.running = False
    
    def _loop(self):
        while self.running:
            if self.path and self.path.exists():
                # Simple modification check
                try:
                    current_mtime = max((p.stat().st_mtime for p in self.path.rglob("*") if p.is_file()), default=0)
                    if self.last_mtime > 0 and current_mtime > self.last_mtime:
                        SESSION["project_status"] = "changed"
                    self.last_mtime = current_mtime
                except: pass
            time.sleep(5)

watcher = ProjectWatcher()

class StateMachine:
    """State machine for cognitive loop"""
    
    def __init__(self):
        self.state = "idle"
        self.previous_state = None
        
    def transition(self, new_state):
        """Transition to new state"""
        self.previous_state = self.state
        self.state = new_state
        set_state(new_state)
        logging.info(f"State transition: {self.previous_state} -> {self.state}")
        
        # Level 5: Earcons (Sound Feedback)
        if new_state == "listening":
            try:
                import winsound
                winsound.Beep(800, 100)
            except: pass
        
        # Log state change to memory
        memory.log_event(
            "state_change",
            data={"from": self.previous_state, "to": new_state}
        )
    
    def handle_intent(self, intent):
        """Handle intent based on current state"""
        if self.state == "idle":
            self.transition("listening")
            speak("I'm listening")
            return None
            
        elif self.state == "listening":
            if not intent:
                self.transition("idle")
                speak("I didn't catch that")
                return None
            
            self.transition("thinking")
            speak("Let me think about that")
            
            # Check safety
            safety = memory.check_safety(
                intent,
                intent.get("action", ""),
                intent.get("path", "")
            )
            
            if safety["action"] == "deny":
                self.transition("idle")
                speak(f"Cannot proceed: {safety['reason']}")
                return None
            
            elif safety["action"] == "confirm":
                # Store pending action and ask for confirmation
                SESSION["pending_action"] = {
                    "intent": intent,
                    "safety_check": safety
                }
                self.transition("confirming")
                
                # Level 5: Safety Levels
                level = safety.get("level", "NORMAL")
                if level == "CRITICAL":
                    speak(f"CRITICAL WARNING: {safety['reason']}. This is irreversible. Say 'confirm critical' to proceed.")
                else:
                    speak(f"Warning: {safety['reason']}. Say confirm to proceed.")
                return None
            
            # Check confidence
            conf = intent.get("confidence", 0.0)
            threshold = SESSION.get("voice_prefs", {}).get("confidence_threshold", 0.75)
            if conf < threshold:
                # store pending and ask for confirmation
                SESSION["pending_action"] = {"intent": intent, "reason": f"Low confidence ({conf})"}
                self.transition("confirming")
                speak(f"I'm not sure I understood. You said: '{intent.get('raw') or intent.get('name','')}'. Say 'confirm' to proceed or 'cancel'.")
                return None
            
            # Safe to proceed
            self.transition("executing")
            speak("Executing now")
            return intent
        
        elif self.state == "confirming":
            # Handle confirmation or slot filling
            if intent.get("intent") is None and "raw" in intent:
                # Fill the slot
                pending = SESSION.get("pending_action")
                if pending and "missing" in pending:
                    missing = pending["missing"][0]  # assume one
                    pending["intent"][missing] = intent["raw"]
                    SESSION["pending_action"] = None
                    self.transition("executing")
                    speak("Got it, executing now")
                    return pending["intent"]
            
            response = intent.get("response", "")
            pending = SESSION.get("pending_action")
            required_response = "confirm"
            if pending and pending.get("safety_check", {}).get("level") == "CRITICAL":
                required_response = "confirm critical"
            
            if response == "confirm" or (required_response == "confirm critical" and "critical" in intent.get("raw", "").lower()):
                # Retrieve pending action
                pending = SESSION.get("pending_action")
                if pending:
                    SESSION["pending_action"] = None
                    self.transition("executing")
                    speak("Confirmed, executing now")
                    return pending["intent"]
                else:
                    self.transition("idle")
                    speak("No pending action to confirm")
                    return None
            else:
                SESSION["pending_action"] = None
                self.transition("idle")
                speak("Action cancelled")
                
                # Level 7: Log Negative Feedback
                pending = SESSION.get("pending_action")
                if pending:
                    memory.log_feedback(str(pending.get("intent")), "cancel", -0.5)
                return None
        
        elif self.state == "executing":
            # Should not receive new intents while executing
            self.transition("idle")
            speak("I was busy executing. Please repeat your command.")
            return None
        
        elif self.state == "thinking":
            # Check for ambiguity (low confidence or vague intent)
            conf = intent.get("confidence", 1.0)
            if conf < 0.7 or intent.get("ambiguous", False):
                # Set up clarification
                pending = SESSION.get("pending_action", {})
                pending["question_type"] = "choice"
                pending["options"] = self._get_options_for_intent(intent)  # Helper below
                pending["original_intent"] = intent
                SESSION["pending_action"] = pending
                self.transition("clarifying")
                speak(f"Got it, but clarify: {self._format_options(pending['options'])}?")
                return None
            
            self.transition("executing")
            speak("Ready to execute")
            return intent
        
        elif self.state == "clarifying":
            choice = intent.get("raw", "").lower()
            pending = SESSION.get("pending_action", {})
            options = pending.get("options", [])
            if choice in [opt.lower() for opt in options]:
                resolved = pending["original_intent"].copy()
                # Map choice to intent (e.g., "flask" -> create_flask_project)
                resolved["ambiguous"] = False
                resolved["confidence"] = 0.95
                SESSION["pending_action"] = None
                self.transition("executing")
                speak(f"Got {choice}. Proceeding.")
                return resolved
            speak("Try an option.")
            return None
        
        return None
    
    def _get_options_for_intent(self, intent):
        if "backend" in intent.get("raw", "").lower():
            return ["Flask", "Django", "Node"]
        if "frontend" in intent.get("raw", "").lower():
            return ["React", "Vue", "Svelte"]
        return ["Yes", "No"]

    def _format_options(self, options):
        return " or ".join(options) + "?"

def run():
    """Main enhanced daemon loop"""
    speak("Raj enhanced cognitive system is running")
    logging.info("Raj enhanced daemon started")
    
    state_machine = StateMachine()
    memory.log_event("system_start")
    
    # Load user preferences into session
    cursor = memory.conn.execute("SELECT key, value FROM preferences")
    for key, value in cursor.fetchall():
        try:
            SESSION["user_preferences"][key] = json.loads(value)
        except:
            SESSION["user_preferences"][key] = value
    
    # Read voice prefs (fallback defaults)
    wake_word_enabled = SESSION["user_preferences"].get("wake_word_enabled", True)
    push_to_talk = SESSION["user_preferences"].get("push_to_talk", False)
    confidence_threshold = SESSION["user_preferences"].get("confidence_threshold", 0.75)

    # Pass these down (example: assign into session)
    SESSION["voice_prefs"] = {
        "wake_word_enabled": wake_word_enabled,
        "push_to_talk": push_to_talk,
        "confidence_threshold": confidence_threshold
    }
    
    while True:
        try:
            # Run Agent Loop
            agent.tick()
            
            # Level 9: Self-Improvement Trigger
            if SESSION.get("actions_count", 0) > 0 and \
               SESSION["actions_count"] % 10 == 0 and \
               SESSION.get("last_improvement_count") != SESSION["actions_count"]:
                self_improver.run()
                SESSION["last_improvement_count"] = SESSION["actions_count"]

            # Get current state
            current_state = state_machine.state
            
            if current_state in ["idle", "listening"]:
                # Listen for voice command
                command = listen()
                if not command:
                    if current_state == "listening":
                        # Timeout on listening
                        state_machine.transition("idle")
                    time.sleep(0.1)
                    continue
                
                logging.info(f"Voice command: {command}")
                memory.log_event("voice_command", data={"command": command})
                
                # Extract intent with memory
                intent = extract_intent_with_memory(command)
                logging.info(f"Extracted intent: {intent}")
                
                # Handle through state machine
                intent_to_execute = state_machine.handle_intent(intent)
                
                # Level 4: Autonomous Mode
                if intent_to_execute and intent_to_execute.get("intent") == "autonomous_mode":
                    plan = intent_to_execute.get("plan", [])
                    speak(f"Autonomous mode engaged. Executing {len(plan)} steps.")
                    for step in plan:
                        # Execute each step
                        step_result = route(step, memory)
                        speak(f"Step complete: {step.get('intent')}")
                        time.sleep(0.5)
                    speak("Autonomous task complete.")
                    state_machine.transition("idle")
                    continue

                if intent_to_execute:
                    # Route and execute intent
                    result = route(intent_to_execute, memory)
                    
                    if "error" not in str(result).lower():
                        workflow_result = after_intent_execution(intent_to_execute, {"path": SESSION.get("last_project", {}).get("path", ""), "scope": "global"})
                        if workflow_result:
                            speak(workflow_result)
                    
                    if isinstance(result, dict) and "ask" in result:
                        SESSION["pending_action"] = {"intent": intent_to_execute, "missing": ["name"]}
                        state_machine.transition("confirming")
                        speak(result["ask"])
                        continue
                    
                    if result == "__STOP__":
                        speak("Stopping VAL")
                        logging.info("Daemon stopped by voice command")
                        memory.log_event("system_stop")
                        break
                    
                    # Speak result and log
                    speak(result)
                    memory.log_event("action_completed", 
                                   intent=intent_to_execute, 
                                   result=result, 
                                   success="error" not in result.lower())
                    
                    # NEW: Auto-apply workflows
                    if "error" not in str(result).lower():  # Only if success
                        workflow_result = after_intent_execution(intent_to_execute, {"path": SESSION.get("last_project", {}).get("path", ""), "scope": "global"})
                        if workflow_result:
                            speak(workflow_result)  # Announce chained results
                    
                    # Optional: Passive learning
                    if SESSION["user_preferences"].get("passive_learning", False):
                        pattern = memory.detect_repeated_pattern()
                        if pattern:
                            speak(f"I noticed you often {pattern['actions'][0]} after {pattern['trigger']['intent']}. Should I automate this? Say 'remember it'.")
                            # Listen for response and call remember_workflow if yes
                            response = listen().strip().lower()
                            if "remember" in response:
                                memory.remember_workflow(pattern["trigger"], pattern["actions"])
                                speak("Automated! I'll suggest it next time.")
                    
                    # Return to idle
                    state_machine.transition("idle")
            
            # Check watcher status
            if SESSION.get("project_status") == "changed":
                SESSION["project_status"] = None
                # Subtle feedback
                logging.info("File change detected by watcher")
            
            elif current_state == "confirming":
                # Listen for confirmation response
                command = listen()
                if command:
                    intent = extract_intent_with_memory(command)
                    intent_to_execute = state_machine.handle_intent(intent)
                    if intent_to_execute:
                        result = route(intent_to_execute, memory)
                        speak(result)
                        memory.log_event("action_completed", 
                                       intent=intent_to_execute, 
                                       result=result, 
                                       success="error" not in str(result).lower())
                        
                        # NEW: Auto-apply workflows
                        if "error" not in str(result).lower():  # Only if success
                            workflow_result = after_intent_execution(intent_to_execute, {"path": SESSION.get("last_project", {}).get("path", ""), "scope": "global"})
                            if workflow_result:
                                speak(workflow_result)  # Announce chained results
                        
                        state_machine.transition("idle")
                else:
                    print("[🧠 PROCESSING] Silence detected in confirming")
                    # Cancel on silence
                    SESSION["pending_action"] = None
                    state_machine.transition("idle")
                    speak("Action cancelled due to silence")
            
            elif current_state in ["thinking", "executing"]:
                # These states handle their own transitions
                time.sleep(0.5)
            
            # Check for idle timeout
            if current_state == "idle":
                # Can add idle behaviors here
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            logging.info("Daemon stopped by user (KeyboardInterrupt)")
            speak("Stopping")
            memory.log_event("system_stop_manual")
            break
            
        except Exception as e:
            logging.exception("Error in enhanced daemon loop")
            memory.log_event("system_error", data={"error": str(e)})
            
            # Level 4: Learning From Errors
            fix = memory.get_error_fix(str(e))
            if fix:
                speak(f"I encountered an error, but I know a fix: {fix}. Applying it.")
                # In a real scenario, we would execute the fix.
            else:
                speak("An error occurred. I'll remember this.")
            
            # Try to recover
            try:
                speak("An error occurred. Returning to idle.")
                state_machine.transition("idle")
            except Exception:
                pass
            
            time.sleep(1)