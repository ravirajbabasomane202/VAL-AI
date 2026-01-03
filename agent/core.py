"""
Agent Core Module - Critic Agent for Plan Evaluation
"""
import re
from typing import Dict, List, Any
import time
from core.memory import memory
from core.session import SESSION

class CriticAgent:
    """AI Agent that evaluates and criticizes plans for potential issues"""

    def __init__(self):
        self.risk_patterns = {
            "high": [
                r"delete.*all", r"drop.*database", r"format.*drive",
                r"rm.*-rf.*\/", r"sudo.*rm", r"overwrite.*system"
            ],
            "medium": [
                r"install.*unknown", r"download.*untrusted", r"run.*script",
                r"chmod.*777", r"pip install.*--force"
            ],
            "low": [
                r"create.*file", r"mkdir", r"git.*commit", r"echo"
            ]
        }

    def evaluate(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate a plan for risks and effectiveness

        Args:
            plan: List of plan steps

        Returns:
            Dict with evaluation results
        """
        if not plan:
            return {
                "risk_level": "low",
                "reason": "Empty plan - no actions to evaluate",
                "effects": {"summary": "No actions planned"},
                "recommendations": ["Add specific actions to the plan"]
            }

        # Analyze each step
        risks = []
        effects = []
        recommendations = []

        for step in plan:
            intent = step.get("intent", "").lower()
            name = step.get("name", "").lower()
            params = step.get("parameters", "").lower()

            # Check for risky patterns
            step_text = f"{intent} {name} {params}"
            for risk_level, patterns in self.risk_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, step_text, re.IGNORECASE):
                        risks.append({
                            "level": risk_level,
                            "pattern": pattern,
                            "step": step_text
                        })

        # Determine overall risk level
        if any(r["level"] == "high" for r in risks):
            risk_level = "high"
            reason = "Plan contains high-risk operations that could cause data loss or system damage"
        elif any(r["level"] == "medium" for r in risks):
            risk_level = "medium"
            reason = "Plan contains potentially risky operations that should be reviewed"
        else:
            risk_level = "low"
            reason = "Plan appears safe with standard operations"

        # Analyze effects
        effect_summary = self._analyze_effects(plan)

        # Generate recommendations
        if risk_level == "high":
            recommendations.extend([
                "Consider breaking down high-risk operations into smaller, reversible steps",
                "Create backups before executing destructive operations",
                "Test operations in a safe environment first"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "Review operations with unknown sources",
                "Verify download URLs and package sources",
                "Consider using virtual environments for installations"
            ])

        return {
            "risk_level": risk_level,
            "reason": reason,
            "effects": {"summary": effect_summary},
            "recommendations": recommendations,
            "details": risks if risks else None
        }

    def _analyze_effects(self, plan: List[Dict[str, Any]]) -> str:
        """Analyze the overall effects of a plan"""
        effects = []

        # Count different types of operations
        create_count = sum(1 for step in plan if "create" in step.get("intent", "").lower())
        modify_count = sum(1 for step in plan if any(word in step.get("intent", "").lower() for word in ["modify", "update", "edit"]))
        delete_count = sum(1 for step in plan if "delete" in step.get("intent", "").lower())

        if create_count > 0:
            effects.append(f"Creates {create_count} new items")
        if modify_count > 0:
            effects.append(f"Modifies {modify_count} existing items")
        if delete_count > 0:
            effects.append(f"Deletes {delete_count} items")

        if not effects:
            effects.append("Performs various operations")

        return "; ".join(effects)


class MainAgent:
    """Main agent controller for the daemon loop"""

    def __init__(self):
        self.last_tick = time.time()
        self.tick_count = 0

    def tick(self):
        """Main agent tick - called in the daemon loop"""
        current_time = time.time()
        self.tick_count += 1

        # Simple heartbeat - could be expanded with more logic
        if self.tick_count % 100 == 0:  # Every 100 ticks
            # Update session with tick info
            SESSION["agent_ticks"] = self.tick_count
            SESSION["last_agent_tick"] = current_time

        self.last_tick = current_time


# Global instances
critic_agent = CriticAgent()
agent = MainAgent()