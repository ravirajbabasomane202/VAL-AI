import json
import logging
from core.memory import memory
from core.session import SESSION

class SelfImprover:
    """
    Level 6: Meta-Agent for Self-Improvement
    Loop: Observe -> Analyze -> Plan -> Apply
    """
    def run(self):
        logging.info("🧠 Running Self-Improver...")
        observations = self.observe()
        insights = self.analyze(observations)
        plans = self.plan(insights)
        self.apply(plans)
        self.tune_confidence(observations)

    def observe(self):
        """Gather data about recent performance"""
        return {
            "recent_events": memory.get_recent_events(50),
            "preferences": memory.get_profile()
        }

    def analyze(self, obs):
        """Analyze observations for patterns and issues"""
        insights = []
        events = obs["recent_events"]
        
        # 1. Frequent undo detection
        undo_count = 0
        for e in events[:20]: # Check last 20
            try:
                intent = json.loads(e["intent"] or "{}")
                if intent.get("intent") in ["undo", "undo_multiple"]:
                    undo_count += 1
            except: pass
            
        if undo_count >= 3:
            insights.append({
                "issue": "frequent_undo",
                "suggestion": "increase_confirmation"
            })

        # 2. Repeated patterns detection
        pattern = memory.detect_repeated_pattern()
        if pattern:
            insights.append({
                "issue": "repeated_pattern",
                "pattern": pattern
            })

        return insights

    def plan(self, insights):
        """Generate improvement plans"""
        plans = []
        for i in insights:
            if i["issue"] == "repeated_pattern":
                plans.append({
                    "action": "create_workflow",
                    "data": i["pattern"],
                    "reason": "Detected repeated manual sequence"
                })
            elif i["issue"] == "frequent_undo":
                current_conf = SESSION.get("voice_prefs", {}).get("confidence_threshold", 0.75)
                plans.append({
                    "action": "adjust_preference",
                    "key": "confidence_threshold",
                    "value": min(0.95, current_conf + 0.05),
                    "reason": "High undo rate detected"
                })
        return plans

    def apply(self, plans):
        """Apply improvements safely"""
        for plan in plans:
            if plan["action"] == "create_workflow":
                trigger = plan["data"]["trigger"]
                actions = plan["data"]["actions"]
                memory.remember_workflow(trigger, actions)
                memory.log_reflection("Created workflow from pattern", f"Automated {trigger['intent']} -> {actions}", 0.8)
                logging.info(f"🧠 Self-Improvement: Created workflow {trigger['intent']} -> {actions}")
                
            elif plan["action"] == "adjust_preference":
                memory.set_preference(plan["key"], plan["value"], "adaptive")
                memory.log_reflection("Adjusted preference", f"Set {plan['key']} to {plan['value']}", 0.9)
                logging.info(f"🧠 Self-Improvement: Adjusted {plan['key']} to {plan['value']}")

    def tune_confidence(self, obs):
        """Auto-tune confidence threshold based on success rate"""
        events = obs["recent_events"]
        if not events: return
        
        success_count = sum(1 for e in events[:20] if e["success"])
        success_rate = success_count / min(len(events), 20)
        
        current_conf = memory.get_preference("confidence_threshold", 0.75)
        new_conf = current_conf
        
        if success_rate > 0.9 and current_conf > 0.6:
            new_conf = round(current_conf - 0.01, 2)
        elif success_rate < 0.7 and current_conf < 0.95:
            new_conf = round(current_conf + 0.02, 2)
            
        if new_conf != current_conf:
            memory.set_preference("confidence_threshold", new_conf, "adaptive")
            memory.log_reflection("Confidence Auto-Tune", f"Changed from {current_conf} to {new_conf}", 1.0)

self_improver = SelfImprover()