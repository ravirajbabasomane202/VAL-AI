
"""
Enhanced Intent Extractor with Memory Recall
"""
import json
import re
from ai.ollama_client import ask_ollama
from core.memory import memory
from core.session import SESSION, add_to_context

SYSTEM_PROMPT_WITH_MEMORY = """
You are VAL, a local AI assistant with memory and cognitive capabilities.
You remember past interactions, projects, and user preferences.

MEMORY CONTEXT:
{memory_context}

USER PREFERENCES:
{user_preferences}

USER PROFILE:
{user_profile}

EXTRACT intent as JSON only.

SUPPORTED INTENTS:
- create_flutter_project
- create_flask_project
- create_django_project
- create_react_project
- create_node_project
- create_data_project
- create_web_project
- create_folder
- create_file
- delete_file
- delete_folder
- open_project
- run_project
- install_dependencies
- undo
- undo_multiple
- stop
- help
- status
- remember (store information)
- remember_workflow (store automation rule)
- repeat_last_workflow (repeat last automated workflow)
- pipeline (multi-step command)
- execute_pipeline (run stored macro)
- recall (retrieve information)
- forget (remove information)
- list_projects
- open_last_project
- explain_file
- find_auth
- show_routes
- find_calls
- check_health
- quick_health
- similar_to_last
- start_workflow
- stop_workflow
- replay_workflow
- list_workflows
- delete_workflow
- autonomous_mode (plan and execute complex task)
- open_app (open external application)
- set_voice_mode (whisper/normal)
- set_goal (add a new goal)
- list_goals (show active goals)

RESPONSE FORMAT:
{{
  "intent": "intent_name",
  "name": "project_name",
  "location": "path/location",
  "action": "create_folder/create_file/etc",
  "path": "full/path",
  "parameters": {{"key": "value"}},
  "plan": [{{ "intent": "step1" }}, {{ "intent": "step2" }}],
  "confidence": 0.95,
  "requires_confirmation": false
}}

EXAMPLES:
"create a React app called myapp" -> {{"intent": "create_react_project", "name": "myapp"}}
"delete the config folder" -> {{"intent": "delete_folder", "path": "./config", "requires_confirmation": true}}
"run the project" -> {{"intent": "run_project"}}
"remember that I like blue themes" -> {{"intent": "remember", "parameters": {{"key": "theme_preference", "value": "blue"}}}}
"remember: after creating Flask, add Docker and open VS Code" -> {{"intent": "remember_workflow", "trigger": {{"intent": "create_flask_project", "tech": "flask"}}, "actions": ["add_docker", "open_vscode"]}}
"From now on, after React, run npm install" -> {{"intent": "remember_workflow", "trigger": {{"intent": "create_react_project", "tech": "react"}}, "actions": ["install_dependencies"]}}
"do the usual setup" or "repeat what I did last time" -> {{"intent": "repeat_last_workflow"}}
"Create React app, install deps, run server" -> {{"intent": "pipeline", "steps": ["create_react_project", "install_dependencies", "run_project"]}}
"Do full React setup" -> {{"intent": "execute_pipeline", "name": "react_full_setup"}}
"open last project" -> {{"intent": "open_last_project"}}
"make another like before" -> {{"intent": "similar_to_last"}}
"Initialize git" -> {{"intent": "git_init"}}
"Commit with message 'WIP'" -> {{"intent": "git_commit", "message": "WIP"}}
"Create branch auth" -> {{"intent": "git_branch", "name": "auth"}}
"Push to GitHub" -> {{"intent": "git_push", "remote": "origin"}}
"Undo last commit" -> {{"intent": "git_undo"}}
"Create environment file" -> {{"intent": "env_create"}}
"Load env for this project" -> {{"intent": "env_load"}}
"Switch to dev config" -> {{"intent": "env_switch", "config": "dev"}}
"What dependencies does this project use?" -> {{"intent": "deps_list"}}
"Is anything outdated?" -> {{"intent": "deps_outdated"}}
"Add JWT auth dependency" -> {{"intent": "deps_add", "name": "pyjwt"}}
"Remove unused packages" -> {{"intent": "deps_remove", "name": "unused"}}
"Explain this file app.py" -> {{"intent": "explain_file", "file": "app.py"}}
"Where is authentication handled?" -> {{"intent": "find_auth"}}
"Show me the API routes" -> {{"intent": "show_routes"}}
"Which files call the login function?" -> {{"intent": "find_calls", "function": "login"}}
"Check project health" -> {{"intent": "check_health"}}
"What's missing from this project?" -> {{"intent": "quick_health"}}
"Undo the last 3 operations" -> {{"intent": "undo_multiple", "count": 3}}
"Show undo history" -> {{"intent": "list_undo"}}
"Set up a production Flask API" -> {{"intent": "autonomous_mode", "plan": [{{"intent": "create_flask_project", "name": "api"}}, {{"intent": "deps_add", "name": "docker"}}, {{"intent": "deps_add", "name": "pyjwt"}}]}}
"Open VS Code" -> {{"intent": "open_app", "name": "vscode"}}
"Set a goal to keep dependencies updated" -> {{"intent": "set_goal", "description": "Keep dependencies updated"}}
"What are my goals?" -> {{"intent": "list_goals"}}
"""

def _extract_memory_context():
    """Extract relevant memories for context"""
    # Get last 3 events
    recent_events = memory.get_recent_events(3)
    last_project = memory.get_last_project()
    
    context = []
    
    if last_project:
        context.append(f"Last project: {last_project['name']} at {last_project['path']}")
    
    if recent_events:
        context.append("Recent actions:")
        for event in recent_events[:2]:
            if event['intent']:
                try:
                    intent_data = json.loads(event['intent'])
                    context.append(f"- {intent_data.get('intent', 'action')}: {event['result']}")
                except:
                    pass
    
    return "\n".join(context)

def _extract_user_preferences():
    """Extract user preferences"""
    preferences = []
    cursor = memory.conn.execute(
        "SELECT key, value FROM preferences ORDER BY updated_at DESC LIMIT 5"
    )
    
    for key, value in cursor.fetchall():
        try:
            val = json.loads(value)
            preferences.append(f"{key}: {val}")
        except:
            preferences.append(f"{key}: {value}")
    
    return "\n".join(preferences) if preferences else "No preferences stored yet"

def _extract_user_profile():
    """Extract developer profile"""
    profile = memory.get_profile()
    if not profile:
        return "Standard User"
    
    lines = []
    for k, v in profile.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)

def _safe_parse_json_from_text(text: str):
    """Safely parse JSON from text response"""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start:end+1])

def extract_intent_with_memory(text: str):
    """
    Extract intent with memory context
    Returns enriched intent with memory recall
    """
    # Add to conversation context
    add_to_context(text, role="user")
    SESSION["last_command"] = text
    
    # Check for memory-related commands first
    lowered = text.strip().lower()
    
    # Memory commands
    if lowered.startswith(("remember that", "remember this", "store that")):
        # Extract key-value pair
        match = re.search(r"remember (?:that|this)?\s+(.+?)\s+is\s+(.+)", lowered)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            return {
                "intent": "remember",
                "action": "store_memory",
                "parameters": {"key": key, "value": value},
                "confidence": 0.9
            }
    
    elif lowered.startswith(("recall", "what did i say about", "tell me about")):
        key = lowered.replace("recall", "").replace("what did i say about", "").replace("tell me about", "").strip()
        return {
            "intent": "recall",
            "action": "retrieve_memory",
            "parameters": {"key": key},
            "confidence": 0.8
        }
    
    elif lowered.startswith(("forget about", "delete memory of")):
        key = lowered.replace("forget about", "").replace("delete memory of", "").strip()
        return {
            "intent": "forget",
            "action": "remove_memory",
            "parameters": {"key": key},
            "confidence": 0.8
        }
    
    elif lowered in ("confirm", "yes", "proceed", "go ahead", "sure"):
        return {"response": "confirm", "confidence": 0.9}
    
    elif lowered in ("cancel", "no", "stop", "abort", "never mind"):
        return {"response": "cancel", "confidence": 0.9}
    
    elif lowered in ("list projects", "show projects", "what projects have i made"):
        return {"intent": "list_projects", "confidence": 0.9}
    
    elif lowered in ("open last project", "go to last project", "where was my last project"):
        return {"intent": "open_last_project", "confidence": 0.9}
    
    elif "like before" in lowered or "similar to last" in lowered:
        return {"intent": "similar_to_last", "confidence": 0.8}
    
    elif "explain this file" in lowered or "explain file" in lowered:
        # Extract file name
        file_match = re.search(r'explain(?: this)? file (.+)', lowered)
        if file_match:
            return {"intent": "explain_file", "file": file_match.group(1).strip(), "confidence": 0.9}
    
    elif "where is auth" in lowered or "find auth" in lowered or "authentication handled" in lowered:
        return {"intent": "find_auth", "confidence": 0.8}
    
    elif "show api routes" in lowered or "show routes" in lowered or "api endpoints" in lowered:
        return {"intent": "show_routes", "confidence": 0.8}
    
    elif "which file" in lowered and "call" in lowered:
        func_match = re.search(r'call(?:s)? (?:the )?(\w+) function', lowered)
        if func_match:
            return {"intent": "find_calls", "function": func_match.group(1), "confidence": 0.8}
    
    elif "check health" in lowered or "project health" in lowered:
        return {"intent": "check_health", "confidence": 0.9}
    
    elif "what's missing" in lowered or "quick health" in lowered:
        return {"intent": "quick_health", "confidence": 0.8}
    
    elif "undo" in lowered and ("last" in lowered or "multiple" in lowered or "operations" in lowered):
        count_match = re.search(r'undo (?:the )?last (\d+)', lowered)
        if count_match:
            return {"intent": "undo_multiple", "count": int(count_match.group(1)), "confidence": 0.9}
        elif "undo" in lowered:
            return {"intent": "undo", "confidence": 0.9}
    
    elif "undo history" in lowered or "list undo" in lowered:
        return {"intent": "list_undo", "confidence": 0.8}
    
    # App Control (Level 5)
    elif lowered.startswith("open ") and any(app in lowered for app in ["code", "browser", "postman", "terminal", "docker"]):
        app_name = lowered.replace("open ", "").strip()
        return {"intent": "open_app", "name": app_name, "confidence": 0.9}
    
    # Voice Mode (Level 5)
    elif "whisper mode" in lowered:
        return {"intent": "set_voice_mode", "mode": "whisper", "confidence": 0.9}
    elif "normal mode" in lowered:
        return {"intent": "set_voice_mode", "mode": "normal", "confidence": 0.9}
    
    # Goals (Level 2)
    elif lowered.startswith("set goal"):
        desc = lowered.replace("set goal", "").strip()
        return {"intent": "set_goal", "description": desc, "confidence": 0.9}
    
    elif "my goals" in lowered or "list goals" in lowered:
        return {"intent": "list_goals", "confidence": 0.9}
    
    # Chain/ambiguous fallback (Level 1.2/3)
    chain_phrases = [" and then ", " then ", ","]
    if any(phrase in lowered for phrase in chain_phrases):
        steps = [s.strip() for s in re.split(r' and then | then |,', lowered) if s.strip()]
        steps = [f"{'create_' if 'create' in s else ''}{step}_project" if step in ["react", "flask"] else step for step in steps]
        return {"intent": "pipeline", "steps": steps, "confidence": 0.8}
    if "create backend" in lowered or "create project" in lowered:
        return {"intent": "create_project", "ambiguous": True, "confidence": 0.6}
    
    elif "undo" in lowered:
        return {"intent": "undo", "confidence": 0.9}
    
    elif "stop" in lowered:
        return {"intent": "stop", "confidence": 0.9}
    
    # Use AI for complex intent extraction
    memory_context = _extract_memory_context()
    user_preferences = _extract_user_preferences()
    user_profile = _extract_user_profile()
    
    prompt = SYSTEM_PROMPT_WITH_MEMORY.format(
        memory_context=memory_context,
        user_preferences=user_preferences,
        user_profile=user_profile
    ) + f"\n\nUser command: {text}\n\nExtracted intent (JSON only, use autonomous_mode for complex tasks):"
    
    try:
        response = ask_ollama(prompt, model="mistral", timeout=30)
        intent_data = _safe_parse_json_from_text(response)
        
        # Ensure confidence exists:
        if "confidence" not in intent_data:
            # Try to infer from keywords / presence of name/path etc.
            c = 0.9 if intent_data.get("intent") else 0.5
            if intent_data.get("parameters"):
                c = min(0.98, c + 0.05)
        intent_data["confidence"] = round(intent_data.get("confidence", c), 2)
        
        # Flag ambiguity for clarification (Level 1.3)
        conf = intent_data.get("confidence", 1.0)
        if conf < 0.7 or ("create" in lowered and not any(tech in lowered for tech in ["flask", "react", "node"])):
            intent_data["ambiguous"] = True
            add_to_context(f"Clarify: ambiguous {intent_data.get('intent')}", role="system")
        
        # Add memory context to intent
        intent_data["_memory"] = {
            "has_context": bool(memory_context),
            "last_project": memory.get_last_project(),
            "session_state": SESSION.get("state", "idle")
        }
        
        # Log intent extraction
        memory.log_event("intent_extracted", intent=intent_data, action="extract")
        
        # Update session
        SESSION["last_intent"] = intent_data
        
        # Add to conversation context
        add_to_context(f"Extracted intent: {intent_data.get('intent', 'unknown')}", role="assistant")
        
        return intent_data
        
    except Exception as e:
        # Fallback to rule-based extraction
        return _fallback_intent_extraction(text)

def _fallback_intent_extraction(text: str):
    """Rule-based fallback intent extraction"""
    lowered = text.strip().lower()
    
    # Project type detection
    project_types = {
        "react": "create_react_project",
        "django": "create_django_project",
        "flask": "create_flask_project",
        "flutter": "create_flutter_project",
        "node": "create_node_project",
        "web": "create_web_project",
        "data": "create_data_project"
    }
    
    for keyword, intent in project_types.items():
        if keyword in lowered:
            # Extract project name
            name_match = re.search(rf"{keyword}\s+(?:project|app)?\s+(\w+)", lowered)
            name = name_match.group(1) if name_match else f"{keyword}_project"
            
            return {
                "intent": intent,
                "name": name,
                "requires_confirmation": False,
                "confidence": 0.8
            }
    
    # In fallback, set ambiguous for partial matches
    if "create" in lowered and "project" in lowered and not any(k in lowered for k in project_types):
        return {
            "intent": "create_project",
            "ambiguous": True,
            "confidence": 0.6
        }
    
    # Action-based detection
    if "create" in lowered and "folder" in lowered:
        folder_match = re.search(r"create.*folder\s+(.+)", lowered)
        path = folder_match.group(1) if folder_match else "./new_folder"
        return {"intent": None, "action": "create_folder", "path": path, "confidence": 0.8}
    
    elif "create" in lowered and "file" in lowered:
        file_match = re.search(r"create.*file\s+(.+)", lowered)
        path = file_match.group(1) if file_match else "./new_file.txt"
        return {"intent": None, "action": "create_file", "path": path, "confidence": 0.7}
    
    elif "delete" in lowered:
        # This always requires confirmation
        path = lowered.replace("delete", "").replace("folder", "").replace("file", "").strip()
        return {
            "intent": "delete_folder" if "folder" in lowered else "delete_file",
            "path": path,
            "requires_confirmation": True,
            "confidence": 0.7
        }
    
    elif "run" in lowered or "start" in lowered:
        return {"intent": "run_project", "confidence": 0.7}
    
    elif "install" in lowered:
        return {"intent": "install_dependencies", "confidence": 0.7}
    
    elif "open" in lowered:
        return {"intent": "open_project", "confidence": 0.7}
    
    elif "help" in lowered:
        return {"intent": "help", "confidence": 0.8}
    
    elif "status" in lowered or "what's happening" in lowered:
        return {"intent": "status", "confidence": 0.8}
    
    elif "are you there" in lowered:
        return {"intent": None, "response": "yes", "confidence": 0.9}
    
    # Workflow learning fallback
    if any(phrase in lowered for phrase in ["remember:", "always do", "from now on", "automate"]):
        # Parse trigger and actions (simple regex)
        trigger_match = re.search(r"(?:after|when)\s+(create|making)\s+([a-z]+)\s+(project|app)", lowered)
        actions_match = re.search(r"(?:add|do|run)\s+(.+?)(?:\s+(?:and|then)\s+(.+?))?", lowered)
        if trigger_match:
            intent_name = f"create_{trigger_match.group(2)}_project"
            tech = trigger_match.group(2)
            actions = [a.strip() for a in (actions_match.groups() if actions_match else ["default_setup"])]
            return {
                "intent": "remember_workflow",
                "trigger": {"intent": intent_name, "tech": tech},
                "actions": actions,
                "confidence": 0.85
            }
    
    # Chain detection fallback
    chain_phrases = [" and then ", " then ", ","]
    if any(phrase in lowered for phrase in chain_phrases) or "full setup" in lowered:
        # Split into steps (simple)
        steps_str = lowered.replace("create ", "").replace(" and then ", " ").replace(",", " ").strip()
        steps = [s.strip() for s in steps_str.split() if s in ["install", "run", "open"]]  # Map to intents
        steps = [f"{'create_' if 'create' in lowered else ''}{step}_project" if step in ["react", "flask"] else f"{step}_dependencies" for step in steps]
        return {
            "intent": "pipeline",
            "steps": steps,
            "confidence": 0.8
        }
    
    # Default fallback
    return {"intent": None, "raw": text, "requires_confirmation": False, "confidence": 0.5}