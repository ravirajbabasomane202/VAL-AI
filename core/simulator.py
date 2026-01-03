import json

class DryRunSimulator:
    """
    Level 7: Simulates execution plans to predict effects and risks.
    """
    def simulate(self, plan: list):
        effects = {
            "creates": [],
            "modifies": [],
            "deletes": [],
            "risk": "low",
            "summary": ""
        }
        
        for step in plan:
            self._simulate_step(step, effects)
            
        # Calculate summary
        effects["summary"] = f"Creates {len(effects['creates'])}, Modifies {len(effects['modifies'])}, Deletes {len(effects['deletes'])}"
        
        # Determine risk
        if effects["deletes"]:
            effects["risk"] = "high"
        elif len(effects["modifies"]) > 5:
            effects["risk"] = "medium"
            
        return effects

    def _simulate_step(self, step: dict, effects: dict):
        intent = step.get("intent", "")
        
        # File Operations
        if intent == "create_file":
            effects["creates"].append(step.get("path", "unknown_file"))
        elif intent == "create_folder":
            effects["creates"].append(step.get("path", "unknown_folder") + "/")
        elif intent in ["delete_file", "delete_folder"]:
            effects["deletes"].append(step.get("path", "unknown"))
            
        # Project Creation
        elif intent.startswith("create_") and "_project" in intent:
            effects["creates"].append(f"Project: {step.get('name', 'new_project')}")
            effects["creates"].append("Config files")
            
        # Git
        elif intent.startswith("git_"):
            effects["modifies"].append("Git History")
            if intent == "git_reset":
                effects["deletes"].append("Recent Commits")
                
        # Dependencies
        elif intent in ["deps_add", "install_dependencies"]:
            effects["modifies"].append("dependencies")
            effects["creates"].append("lock files")