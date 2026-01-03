"""
SQLite Memory System - Persistent storage for long-term memory
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import hashlib
from typing import Any, Optional, List, Dict
import ast
import re
from core.session import SESSION

# Level 7: Semantic Memory Support
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    _HAS_EMBEDDINGS = True
except ImportError:
    _HAS_EMBEDDINGS = False

DB_PATH = Path("memory/val_memory.db")
DB_PATH.parent.mkdir(exist_ok=True)

# Protected paths (never delete these)
PROTECTED_PATHS = [
    "/",
    "C:/Windows",
    "C:/Program Files",
    "C:/Program Files (x86)",
    "/System",
    "/Library",
    "/usr",
    "/bin",
    "/etc"
]

class Memory:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._load_safety_rules()
    
    def _create_tables(self):
        """Create all necessary tables"""
        # Main memory table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            tags TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 0
        )
        """)
        
        # Events/actions log
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            intent TEXT,
            action TEXT,
            data TEXT,
            result TEXT,
            success BOOLEAN,
            created_at TEXT NOT NULL
        )
        """)
        
        # Projects memory
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            project_type TEXT,
            blueprint TEXT,
            created_at TEXT NOT NULL,
            last_accessed TEXT
        )
        """)
        
        # User preferences
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            category TEXT,
            updated_at TEXT NOT NULL
        )
        """)
        
        # Safety rules
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS safety_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_type TEXT NOT NULL,
            pattern TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
        """)
        
        # Workflows table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            steps TEXT NOT NULL,  -- JSON array of intents
            created_at TEXT NOT NULL,
            last_used TEXT,
            use_count INTEGER DEFAULT 0
        )
        """)
        
        # Error fixes (Level 4)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS error_fixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_pattern TEXT UNIQUE NOT NULL,
            fix_action TEXT NOT NULL,
            confidence REAL DEFAULT 0.8,
            created_at TEXT NOT NULL
        )
        """)
        
        # Level 2: Goals
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            priority INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            success_criteria TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        # Level 3: Triggers
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS triggers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_type TEXT NOT NULL,
            condition TEXT NOT NULL,
            action TEXT NOT NULL,
            confidence REAL DEFAULT 0.9,
            enabled BOOLEAN DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)
        
        # Level 8: Project Digital Twin
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS project_state (
            project_path TEXT PRIMARY KEY,
            state_json TEXT,
            last_updated TEXT
        )
        """)
        
        # Level 6: Self-Reflection Memory
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS self_reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight TEXT,
            action_taken TEXT,
            effectiveness REAL,
            created_at TEXT NOT NULL
        )
        """)
        
        # Level 7: Semantic Memory
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            embedding BLOB,
            memory_type TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
        """)
        
        # Level 7: Feedback
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT,
            signal TEXT,
            weight REAL,
            created_at TEXT NOT NULL
        )
        """)
        
        self.conn.commit()
    
    def _load_safety_rules(self):
        """Load default safety rules"""
        default_rules = [
            ("protected_path", path, "deny", "System protected path") 
            for path in PROTECTED_PATHS
        ]
        default_rules.extend([
            ("dangerous_action", "delete", "confirm", "Destructive operation"),
            ("dangerous_action", "format", "confirm", "Data loss risk"),
            ("dangerous_action", "rm -rf", "confirm", "Recursive delete"),
            ("dangerous_action", "force", "confirm", "Force operation")
        ])
        
        for rule_type, pattern, action, reason in default_rules:
            self.conn.execute("""
            INSERT OR IGNORE INTO safety_rules (rule_type, pattern, action, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (rule_type, pattern, action, reason, datetime.now().isoformat()))
        self.conn.commit()
    
    # Core Memory API
    def remember(self, key: str, value: Any, memory_type: str = "fact", tags: str = ""):
        """Store a memory"""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        now = datetime.now().isoformat()
        
        self.conn.execute("""
        INSERT INTO memory (type, key, value, tags, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            tags=excluded.tags,
            updated_at=excluded.updated_at,
            access_count=access_count + 1
        """, (memory_type, key, value_str, tags, now, now))
        self.conn.commit()
        
        # Auto-embed if text-heavy
        if _HAS_EMBEDDINGS and isinstance(value, str) and len(value) > 20:
            self.remember_semantic(value, memory_type, {"key": key, "tags": tags})
    
    def recall(self, key: str) -> Optional[Any]:
        """Retrieve a memory"""
        cursor = self.conn.execute(
            "SELECT value FROM memory WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        
        if row:
            # Update access count
            self.conn.execute(
                "UPDATE memory SET access_count = access_count + 1, updated_at = ? WHERE key = ?",
                (datetime.now().isoformat(), key)
            )
            self.conn.commit()
            
            try:
                return json.loads(row[0])
            except:
                return row[0]
        return None
    
    def forget(self, key: str) -> bool:
        """Remove a memory"""
        self.conn.execute("DELETE FROM memory WHERE key = ?", (key,))
        self.conn.commit()
        return self.conn.total_changes > 0
    
    def search(self, query: str, memory_type: str = None, limit: int = 10) -> List[Dict]:
        """Search memories by content or tags"""
        sql = """
        SELECT key, value, type, tags FROM memory 
        WHERE value LIKE ? OR tags LIKE ?
        """
        params = [f"%{query}%", f"%{query}%"]
        
        if memory_type:
            sql += " AND type = ?"
            params.append(memory_type)
        
        sql += " ORDER BY access_count DESC, updated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            try:
                value = json.loads(row[1])
            except:
                value = row[1]
            results.append({
                "key": row[0],
                "value": value,
                "type": row[2],
                "tags": row[3]
            })
        return results
    
    def recent(self, n: int = 5, memory_type: str = None) -> List[Dict]:
        """Get recent memories"""
        sql = "SELECT * FROM memory"
        params = []
        
        if memory_type:
            sql += " WHERE type = ?"
            params.append(memory_type)
        
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(n)
        
        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # Project Memory
    def remember_project(self, name: str, path: str, project_type: str = None, blueprint: dict = None):
        """Store project information"""
        blueprint_str = json.dumps(blueprint) if blueprint else ""
        now = datetime.now().isoformat()
        
        self.conn.execute("""
        INSERT INTO projects (name, path, project_type, blueprint, created_at, last_accessed)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            name=excluded.name,
            project_type=excluded.project_type,
            blueprint=excluded.blueprint,
            last_accessed=excluded.last_accessed
        """, (name, str(path), project_type, blueprint_str, now, now))
        self.conn.commit()
        
        # Also remember as last project in session
        SESSION["last_project"] = {"name": name, "path": str(path)}
        self.remember("last_project", {"name": name, "path": str(path)}, "context")
    
    def get_last_project(self):
        """Get the last created/modified project"""
        cursor = self.conn.execute(
            "SELECT * FROM projects ORDER BY last_accessed DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_projects_by_type(self, project_type: str):
        """Get all projects of a specific type"""
        cursor = self.conn.execute(
            "SELECT * FROM projects WHERE project_type = ? ORDER BY last_accessed DESC",
            (project_type,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    # Event Logging
    def log_event(self, event_type: str, intent: dict = None, action: str = None, 
                  data: dict = None, result: str = None, success: bool = True):
        """Log an event for audit trail"""
        intent_str = json.dumps(intent) if intent else ""
        data_str = json.dumps(data) if data else ""
        
        self.conn.execute("""
        INSERT INTO events (event_type, intent, action, data, result, success, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_type, intent_str, action, data_str, result, success, datetime.now().isoformat()))
        self.conn.commit()
        
        # Log clarifications for learning
        if "clarifying" in event_type and data:
            self.remember(f"clarification_{intent.get('intent') if intent else 'unknown'}", {"choice": data.get("choice"), "options": data.get("options")}, "learning")
    
    def get_recent_events(self, n: int = 10):
        """Get recent events"""
        cursor = self.conn.execute(
            "SELECT * FROM events ORDER BY created_at DESC LIMIT ?",
            (n,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    # Preferences
    def set_preference(self, key: str, value: Any, category: str = "general"):
        """Set user preference"""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        self.conn.execute("""
        INSERT INTO preferences (key, value, category, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=excluded.updated_at
        """, (key, value_str, category, datetime.now().isoformat()))
        self.conn.commit()
        
        # Update session
        SESSION["user_preferences"][key] = value
    
    def get_preference(self, key: str, default: Any = None):
        """Get user preference"""
        cursor = self.conn.execute(
            "SELECT value FROM preferences WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except:
                return row[0]
        return default
    
    # Safety Checks
    def check_safety(self, intent: dict, action: str, path: str = None) -> Dict:
        """
        Check if action is safe
        Returns: {"safe": bool, "action": "allow|deny|confirm", "level": "SAFE|NORMAL|DANGEROUS|CRITICAL", "reason": str}
        """
        # Default level
        level = "NORMAL"
        
        # Read-only intents are SAFE
        if intent.get("intent") in ["list_projects", "status", "help", "explain_file", "check_health", "open_app"]:
            level = "SAFE"

        # Check protected paths
        if path:
            for protected in PROTECTED_PATHS:
                if path.startswith(protected):
                    return {
                        "safe": False,
                        "action": "deny",
                        "level": "CRITICAL",
                        "reason": f"Protected system path: {protected}"
                    }
        
        # Check safety rules
        cursor = self.conn.execute(
            "SELECT rule_type, pattern, action, reason FROM safety_rules"
        )
        
        for rule_type, pattern, rule_action, reason in cursor.fetchall():
            if rule_type == "dangerous_action":
                if pattern in action.lower() or pattern in str(intent).lower():
                    # Map to levels
                    if "reset" in pattern or "force" in pattern:
                        level = "CRITICAL"
                    else:
                        level = "DANGEROUS"
                        
                    return {
                        "safe": rule_action == "allow",
                        "action": rule_action,
                        "level": level,
                        "reason": reason
                    }
        
        return {"safe": True, "action": "allow", "level": level, "reason": ""}
    
    def add_safety_rule(self, rule_type: str, pattern: str, action: str, reason: str = ""):
        """Add custom safety rule"""
        # First, try to update existing
        cursor = self.conn.execute("""
        SELECT id FROM safety_rules WHERE rule_type = ? AND pattern = ?
        """, (rule_type, pattern))
        existing = cursor.fetchone()
        if existing:
            self.conn.execute("""
            UPDATE safety_rules SET action = ?, reason = ? WHERE id = ?
            """, (action, reason, existing[0]))
        else:
            self.conn.execute("""
            INSERT INTO safety_rules (rule_type, pattern, action, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (rule_type, pattern, action, reason, datetime.now().isoformat()))
        self.conn.commit()
    
    # Similarity and Recall
    def find_similar_tasks(self, intent: dict, limit: int = 3):
        """Find similar past tasks"""
        intent_str = json.dumps(intent)
        
        # Simple keyword matching for now
        # Can be enhanced with embeddings later
        keywords = []
        if "intent" in intent:
            keywords.append(intent["intent"])
        if "name" in intent:
            keywords.append(intent["name"])
        if "action" in intent:
            keywords.append(intent["action"])
        
        query = " OR ".join(keywords)
        return self.search(query, memory_type="event", limit=limit)
    
    # Workflow Learning
    def save_workflow(self, name: str, steps: List[Dict], description: str = ""):
        """Save a workflow (sequence of intents)"""
        steps_str = json.dumps(steps)
        now = datetime.now().isoformat()
        
        self.conn.execute("""
        INSERT INTO workflows (name, description, steps, created_at, last_used)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            description=excluded.description,
            steps=excluded.steps,
            last_used=excluded.last_used
        """, (name, description, steps_str, now, now))
        self.conn.commit()
    
    def get_workflow(self, name: str) -> Optional[Dict]:
        """Get a workflow by name"""
        cursor = self.conn.execute(
            "SELECT * FROM workflows WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        if row:
            workflow = dict(row)
            workflow["steps"] = json.loads(workflow["steps"])
            return workflow
        return None
    
    def list_workflows(self) -> List[Dict]:
        """List all workflows"""
        cursor = self.conn.execute(
            "SELECT * FROM workflows ORDER BY last_used DESC, use_count DESC"
        )
        workflows = []
        for row in cursor.fetchall():
            workflow = dict(row)
            workflow["steps"] = json.loads(workflow["steps"])
            workflows.append(workflow)
        return workflows
    
    def execute_workflow(self, name: str) -> List[Dict]:
        """Get workflow steps for execution, update usage"""
        cursor = self.conn.execute(
            "SELECT steps FROM workflows WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        if row:
            now = datetime.now().isoformat()
            self.conn.execute("""
            UPDATE workflows SET use_count = use_count + 1, last_used = ? WHERE name = ?
            """, (now, name))
            self.conn.commit()
            return json.loads(row[0])
        return []
    
    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow"""
        self.conn.execute("DELETE FROM workflows WHERE name = ?", (name,))
        self.conn.commit()
        return self.conn.total_changes > 0
    
    # Level 4: Learning From Errors & Profile
    def remember_error_fix(self, error_pattern: str, fix_action: str):
        """Store a fix for a specific error pattern"""
        now = datetime.now().isoformat()
        self.conn.execute("""
        INSERT INTO error_fixes (error_pattern, fix_action, created_at)
        VALUES (?, ?, ?)
        ON CONFLICT(error_pattern) DO UPDATE SET
            fix_action=excluded.fix_action,
            confidence=confidence + 0.1
        """, (error_pattern, fix_action, now))
        self.conn.commit()
        self.log_event("learned_fix", data={"error": error_pattern, "fix": fix_action})

    def get_error_fix(self, error_text: str) -> Optional[str]:
        """Find a fix for an error"""
        cursor = self.conn.execute("SELECT error_pattern, fix_action FROM error_fixes ORDER BY confidence DESC")
        for pattern, fix in cursor.fetchall():
            if pattern in error_text:
                return fix
        return None

    def get_profile(self) -> Dict:
        """Get developer profile"""
        profile = {}
        cursor = self.conn.execute("SELECT key, value FROM preferences WHERE category = 'profile'")
        for key, value in cursor.fetchall():
            try:
                profile[key] = json.loads(value)
            except:
                profile[key] = value
        return profile
    
    # Goal Management
    def add_goal(self, description: str, priority: int = 1, success_criteria: str = ""):
        now = datetime.now().isoformat()
        self.conn.execute("""
        INSERT INTO goals (description, priority, status, success_criteria, created_at, updated_at)
        VALUES (?, ?, 'active', ?, ?, ?)
        """, (description, priority, success_criteria, now, now))
        self.conn.commit()
        self.log_event("goal_added", data={"description": description})

    def get_active_goals(self):
        cursor = self.conn.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY priority DESC")
        return [dict(row) for row in cursor.fetchall()]

    def update_goal_status(self, goal_id: int, status: str):
        now = datetime.now().isoformat()
        self.conn.execute("UPDATE goals SET status = ?, updated_at = ? WHERE id = ?", (status, now, goal_id))
        self.conn.commit()

    # Trigger Management
    def add_trigger(self, trigger_type: str, condition: str, action: str):
        now = datetime.now().isoformat()
        self.conn.execute("""
        INSERT INTO triggers (trigger_type, condition, action, created_at)
        VALUES (?, ?, ?, ?)
        """, (trigger_type, condition, action, now))
        self.conn.commit()

    def get_triggers(self, trigger_type: str = None):
        sql = "SELECT * FROM triggers WHERE enabled = 1"
        params = []
        if trigger_type:
            sql += " AND trigger_type = ?"
            params.append(trigger_type)
        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    # Digital Twin
    def update_project_state(self, path: str, state: dict):
        now = datetime.now().isoformat()
        state_str = json.dumps(state)
        self.conn.execute("""
        INSERT INTO project_state (project_path, state_json, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(project_path) DO UPDATE SET
            state_json=excluded.state_json,
            last_updated=excluded.last_updated
        """, (str(path), state_str, now))
        self.conn.commit()

    # Self-Reflection
    def log_reflection(self, insight: str, action_taken: str, effectiveness: float = 0.0):
        """Log a self-improvement reflection"""
        now = datetime.now().isoformat()
        self.conn.execute("""
        INSERT INTO self_reflections (insight, action_taken, effectiveness, created_at)
        VALUES (?, ?, ?, ?)
        """, (insight, action_taken, effectiveness, now))
        self.conn.commit()

    def remember_workflow(self, trigger: dict, actions: list, scope: str = "global"):
        """Store a workflow pattern"""
        data = {
            "id": hashlib.md5(f"{trigger['intent']}_{trigger.get('tech', 'any')}_{scope}".encode()).hexdigest()[:8],
            "trigger": trigger,
            "actions": actions,
            "scope": scope,
            "confidence": 0.9,  # Starts high; can decay with disuse
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }
        key = f"workflow_{trigger['intent']}_{trigger.get('tech', 'any')}_{scope}"
        self.remember(key, data, memory_type="workflow")
        self.log_event("workflow_learned", data={"trigger": trigger, "actions": actions})
        return key

    def get_workflows_for_trigger(self, intent_name: str, tech: str = None, scope: str = "global") -> List[Dict]:
        """Retrieve enabled workflows matching a trigger"""
        workflows = self.search("", memory_type="workflow", limit=50)  # All workflows
        matched = []
        for wf in workflows:
            data = wf["value"]
            trigger = data["trigger"]
            if (trigger["intent"] == intent_name and
                (tech is None or trigger.get("tech") == tech) and
                data["scope"] == scope and
                data["enabled"]):
                matched.append(data)
        # Sort by confidence (desc)
        matched.sort(key=lambda x: x["confidence"], reverse=True)
        return matched

    def disable_workflow(self, trigger: dict, scope: str = "global"):
        """Disable a workflow (e.g., after user feedback)"""
        key = f"workflow_{trigger['intent']}_{trigger.get('tech', 'any')}_{scope}"
        if self.forget(key):
            self.log_event("workflow_disabled", data={"trigger": trigger})
            return True
        return False
    
    def detect_repeated_pattern(self, min_occurrences: int = 3) -> Optional[Dict]:
        """Analyze recent events for repeatable sequences"""
        events = self.get_recent_events(20)
        sequences = {}
        for i in range(len(events) - 1):
            trigger = events[i]
            follow = events[i + 1]
            if trigger["success"] and follow["success"]:
                key = f"{trigger['intent']}_{follow['intent']}"
                sequences[key] = sequences.get(key, 0) + 1
        
        for seq, count in sequences.items():
            if count >= min_occurrences:
                trigger, action = seq.split("_", 1)
                suggestion = {
                    "trigger": {"intent": trigger},
                    "actions": [action],
                    "confidence": count / len(events)
                }
                return suggestion
        return None
    
    def remember_pipeline(self, name: str, steps: list, description: str = "", scope: str = "global"):
        data = {
            "id": hashlib.md5(f"{name}_{scope}".encode()).hexdigest()[:8],
            "name": name,
            "steps": steps,
            "description": description,
            "scope": scope,
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }
        key = f"pipeline_{name}_{scope}"
        self.remember(key, data, memory_type="pipeline")
        self.log_event("pipeline_learned", data={"name": name, "steps": len(steps)})
        return key

    def get_pipeline(self, name: str, scope: str = "global") -> Optional[Dict]:
        key = f"pipeline_{name}_{scope}"
        data = self.recall(key)
        return data if data and data["enabled"] else None

    def execute_pipeline(self, name: str, context: dict, scope: str = "global"):
        pipeline = self.get_pipeline(name, scope)
        if not pipeline:
            return "❌ Pipeline not found."
        
        from engine.intent_router import route  # Avoid cycle
        results = []
        for step in pipeline["steps"]:
            step_intent = {"intent": step if isinstance(step, str) else step.get("intent"), "context": context, "source": "pipeline"}
            safety = self.check_safety(step_intent, step_intent.get("intent", ""))
            if safety["action"] == "confirm":
                if not self.wait_for_confirmation():
                    results.append("Skipped (cancelled)")
                    continue
            elif safety["action"] == "deny":
                results.append(f"Blocked: {safety['reason']}")
                continue
            
            result = route(step_intent, self)
            results.append(result)
            self.log_event("pipeline_step", intent=step_intent, result=result)
        
        self.log_event("pipeline_executed", data={"name": name, "results": len(results)})
        return "\n".join(results)

    def wait_for_confirmation(self) -> bool:
        from voice.listener import listen
        from voice.speaker import speak
        speak("Confirm?")
        response = listen().strip().lower()
        return any(word in response for word in ["yes", "yep", "confirm", "go"])

    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'conn'):
            self.conn.close()

class CodeAnalyzer:
    """Analyze code for understanding and navigation"""
    
    def __init__(self, project_path=None):
        if project_path is None:
            try:
                from core.session import SESSION
                project_path = Path(SESSION.get("last_project", {}).get("path", "."))
            except:
                project_path = Path(".")
        self.project_path = project_path
        self.cache = {}  # Cache parsed files
    
    def explain_file(self, file_path: str) -> str:
        """Explain what a file does"""
        path = self.project_path / file_path
        if not path.exists():
            return f"❌ File not found: {file_path}"
        
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            ext = path.suffix.lower()
            
            if ext == ".py":
                return self._explain_python_file(content, path.name)
            elif ext in [".js", ".ts"]:
                return self._explain_js_file(content, path.name)
            else:
                return self._explain_generic_file(content, path.name)
        except Exception as e:
            return f"❌ Error reading file: {e}"
    
    def _explain_python_file(self, content: str, filename: str) -> str:
        """Use AST to analyze Python file"""
        try:
            tree = ast.parse(content)
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    imports.extend(f"{module}.{alias.name}" for alias in node.names)
            
            explanation = f"📄 {filename}\n"
            if classes:
                explanation += f"Classes: {', '.join(classes)}\n"
            if functions:
                explanation += f"Functions: {', '.join(functions[:10])}{'...' if len(functions) > 10 else ''}\n"
            if imports:
                explanation += f"Imports: {', '.join(imports[:5])}{'...' if len(imports) > 5 else ''}\n"
            
            # Try to infer purpose
            if "app" in filename.lower() or "main" in filename.lower():
                explanation += "Purpose: Main application entry point\n"
            elif "model" in filename.lower():
                explanation += "Purpose: Data models/ORM\n"
            elif "route" in filename.lower() or "api" in filename.lower():
                explanation += "Purpose: API endpoints/routes\n"
            elif "test" in filename.lower():
                explanation += "Purpose: Unit/integration tests\n"
            
            return explanation
        except:
            return f"📄 {filename}\nCould not parse Python AST. Generic analysis:\n{self._explain_generic_file(content, filename)}"
    
    def _explain_js_file(self, content: str, filename: str) -> str:
        """Basic regex analysis for JS/TS"""
        functions = re.findall(r'(?:function|const|let|var)\s+(\w+)\s*[=:]?\s*(?:function|\([^)]*\)\s*=>)', content)
        classes = re.findall(r'class\s+(\w+)', content)
        imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        
        explanation = f"📄 {filename}\n"
        if classes:
            explanation += f"Classes: {', '.join(classes)}\n"
        if functions:
            explanation += f"Functions/Components: {', '.join(functions[:10])}{'...' if len(functions) > 10 else ''}\n"
        if imports:
            explanation += f"Imports: {', '.join(imports[:5])}{'...' if len(imports) > 5 else ''}\n"
        
        return explanation
    
    def _explain_generic_file(self, content: str, filename: str) -> str:
        """Generic file explanation"""
        lines = content.split('\n')
        explanation = f"📄 {filename}\n"
        explanation += f"Lines: {len(lines)}\n"
        
        # Check for common patterns
        if "# " in content[:200]:
            explanation += "Type: Documentation/Markdown\n"
        elif "function" in content[:200] or "def " in content[:200]:
            explanation += "Type: Code file\n"
        elif "{" in content[:200] and "}" in content[:200]:
            explanation += "Type: Configuration (JSON/YAML)\n"
        
        return explanation
    
    def find_auth_handlers(self) -> str:
        """Find where authentication is handled"""
        results = []
        
        # Search for auth-related keywords
        auth_keywords = ["auth", "login", "authenticate", "token", "jwt", "session", "password"]
        
        for file_path in self._get_code_files():
            try:
                content = file_path.read_text().lower()
                matches = []
                for keyword in auth_keywords:
                    if keyword in content:
                        matches.append(keyword)
                
                if matches:
                    results.append(f"{file_path.name}: {', '.join(matches)}")
            except:
                continue
        
        if results:
            return "🔐 Auth handlers found:\n" + "\n".join(results)
        return "🔐 No obvious auth handlers found"
    
    def show_api_routes(self) -> str:
        """Show API routes/endpoints"""
        routes = []
        
        for file_path in self._get_code_files():
            try:
                content = file_path.read_text()
                ext = file_path.suffix.lower()
                
                if ext == ".py":
                    routes.extend(self._find_python_routes(content, file_path.name))
                elif ext in [".js", ".ts"]:
                    routes.extend(self._find_js_routes(content, file_path.name))
            except:
                continue
        
        if routes:
            return "🛣️ API Routes:\n" + "\n".join(routes)
        return "🛣️ No API routes found"
    
    def _find_python_routes(self, content: str, filename: str) -> List[str]:
        """Find Flask/Django routes in Python"""
        routes = []
        
        # Flask-style routes
        flask_routes = re.findall(r'@app\.route\([\'"]([^\'"]+)[\'"]', content)
        for route in flask_routes:
            routes.append(f"Flask: {route} ({filename})")
        
        # Django URL patterns
        django_routes = re.findall(r'path\([\'"]([^\'"]+)[\'"]', content)
        for route in django_routes:
            routes.append(f"Django: {route} ({filename})")
        
        return routes
    
    def _find_js_routes(self, content: str, filename: str) -> List[str]:
        """Find Express/React Router routes in JS"""
        routes = []
        
        # Express routes
        express_routes = re.findall(r'app\.(get|post|put|delete)\([\'"]([^\'"]+)[\'"]', content)
        for method, route in express_routes:
            routes.append(f"Express {method.upper()}: {route} ({filename})")
        
        # React Router
        react_routes = re.findall(r'<Route[^>]*path=[\'"]([^\'"]+)[\'"]', content)
        for route in react_routes:
            routes.append(f"React Router: {route} ({filename})")
        
        return routes
    
    def find_function_calls(self, function_name: str) -> str:
        """Find where a function is called"""
        results = []
        
        for file_path in self._get_code_files():
            try:
                content = file_path.read_text()
                if function_name in content:
                    # Find lines containing the function call
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if function_name in line and not line.strip().startswith('def ') and not line.strip().startswith('function '):
                            results.append(f"{file_path.name}:{i}: {line.strip()}")
            except:
                continue
        
        if results:
            return f"📞 Function '{function_name}' called in:\n" + "\n".join(results[:20]) + ("\n..." if len(results) > 20 else "")
        return f"📞 Function '{function_name}' not found in calls"
    
    def _get_code_files(self) -> List[Path]:
        """Get all code files in project"""
        extensions = ['.py', '.js', '.ts', '.jsx', '.tsx']
        files = []
        for ext in extensions:
            files.extend(self.project_path.rglob(f"*{ext}"))
        return files

# Global memory instance
memory = Memory()

# Global analyzer instance
analyzer = CodeAnalyzer()