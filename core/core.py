import time
import json
import logging
from datetime import datetime
from pathlib import Path
from core.memory import memory
from core.session import SESSION
from engine.intent_router import route

class AgentGovernor:
    """Safety Governor for Autonomous Actions"""
    def __init__(self):
        self.limits = {
            "max_actions_per_hour": 20,
            "max_deletions_per_hour": 2,
            "max_git_resets": 1
        }
        self.usage = {
            "actions": [],
            "deletions": [],
            "resets": []
        }
    
    def check(self, action_type: str) -> bool:
        now = time.time()
        # Clean old usage logs (older than 1 hour)
        for key in self.usage:
            self.usage[key] = [t for t in self.usage[key] if now - t < 3600]
            
        if action_type == "delete":
            if len(self.usage["deletions"]) >= self.limits["max_deletions_per_hour"]:
                return False
            self.usage["deletions"].append(now)
        elif action_type == "reset":
            if len(self.usage["resets"]) >= self.limits["max_git_resets"]:
                return False
            self.usage["resets"].append(now)
        
        if len(self.usage["actions"]) >= self.limits["max_actions_per_hour"]:
            return False
        self.usage["actions"].append(now)
        return True

class AutonomousAgent:
    """
    Level 1-9: Autonomous Developer Agent
    Loop: Observe -> Decide -> Act -> Evaluate -> Learn
    """
    def __init__(self):
        self.governor = AgentGovernor()
        self.last_tick = 0
        self.tick_rate = 5  # Seconds
        
    def tick(self):
        """Main agent loop step"""
        now = time.time()
        if now - self.last_tick < self.tick_rate:
            return
        self.last_tick = now
        
        # 1. Observe
        context = self.observe()
        
        # 2. Decide
        plan = self.decide(context)
        
        # 3. Act
        if plan:
            self.execute_plan(plan)
            
    def observe(self):
        """Observe environment state"""
        context = {
            "time": datetime.now(),
            "project_status": SESSION.get("project_status"),
            "last_project": memory.get_last_project(),
            "active_goals": memory.get_active_goals()
        }
        # Reset transient flags
        if SESSION.get("project_status") == "changed":
            SESSION["project_status"] = None
            context["file_changed"] = True
        return context

    def decide(self, context):
        """Decide on actions based on triggers and goals"""
        actions = []
        
        # Check Triggers
        if context.get("file_changed"):
            triggers = memory.get_triggers("event")
            for t in triggers:
                if t["condition"] == "file_changed":
                    actions.append(t)
        
        return actions

    def execute_plan(self, actions):
        """Execute decided actions safely"""
        for action_def in actions:
            action_str = action_def["action"]
            
            # Determine intent
            intent = None
            if action_str.startswith("{"):
                try:
                    intent = json.loads(action_str)
                except: pass
            else:
                # Assume workflow name
                intent = {"intent": "execute_pipeline", "name": action_str}
            
            if not intent:
                continue
            
            # Safety Check (Governor)
            action_type = "normal"
            if "delete" in str(intent): action_type = "delete"
            if "reset" in str(intent): action_type = "reset"
            
            if not self.governor.check(action_type):
                logging.warning(f"Governor blocked action: {intent}")
                memory.log_event("governor_block", data={"intent": intent})
                continue
            
            # Execute
            logging.info(f"Agent executing: {intent}")
            result = route(intent, memory)
            
            # 4. Evaluate & 5. Learn
            if "error" in str(result).lower():
                memory.log_event("agent_failure", data={"intent": intent, "result": result})
            else:
                memory.log_event("agent_success", data={"intent": intent})

# Global Agent Instance
agent = AutonomousAgent()