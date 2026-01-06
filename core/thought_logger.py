"""
Thought Logger for AI Cognitive Process
"""
import json
from datetime import datetime
from core.memory import memory
from core.session import SESSION

class ThoughtLogger:
    """Log AI thoughts for visualization"""
    
    def __init__(self):
        self.thoughts = []
    
    def log_thought(self, thought_type: str, content: str, confidence: float = 1.0, 
                   alternatives: list = None, metadata: dict = None):
        """Log a thought"""
        thought = {
            "timestamp": datetime.now().isoformat(),
            "type": thought_type,
            "content": content,
            "confidence": confidence,
            "alternatives": alternatives or [],
            "metadata": metadata or {},
            "session_id": id(SESSION)
        }
        
        self.thoughts.append(thought)
        
        # Also save to memory
        memory.remember(
            key=f"thought_{datetime.now().timestamp()}",
            value=thought,
            memory_type="cognition"
        )
        
        # Broadcast via WebSocket if available
        try:
            from ui.websocket_handler import ws_server
            asyncio.create_task(ws_server.broadcast("thought", thought))
        except:
            pass
        
        return thought
    
    def log_decision(self, decision: str, reasoning: str, 
                    options: list, chosen_index: int):
        """Log a decision with reasoning"""
        return self.log_thought(
            thought_type="decision",
            content=decision,
            metadata={
                "reasoning": reasoning,
                "options": options,
                "chosen": chosen_index
            }
        )
    
    def log_criticism(self, warning: str, severity: str, 
                     suggestion: str = None):
        """Log critic's warning"""
        return self.log_thought(
            thought_type="criticism",
            content=warning,
            metadata={
                "severity": severity,
                "suggestion": suggestion
            }
        )

# Global thought logger
thought_logger = ThoughtLogger()