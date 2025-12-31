# ai/intent_extractor.py
import json
from ai.ollama_client import ask_ollama

SYSTEM = """
Extract intent as JSON only.

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
- stop
- help
- status

RESPONSE FORMAT:
{
  "intent": "intent_name",
  "name": "project_name",
  "location": "path/location",
  "action": "create_folder/create_file/etc",
  "path": "full/path",
  "parameters": {"key": "value"}
}

EXAMPLES:
"create a React app called myapp" -> {"intent": "create_react_project", "name": "myapp"}
"delete the config folder" -> {"intent": "delete_folder", "path": "./config"}
"run the project" -> {"intent": "run_project"}
"""

def _safe_parse_json_from_text(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start:end+1])

def extract_intent(text: str):
    try:
        response = ask_ollama(SYSTEM + "\nUser: " + text)
    except Exception as e:
        # graceful fallback: try to infer minimal intent
        lowered = text.strip().lower()
        if "undo" in lowered:
            return {"intent": "undo"}
        if "stop" in lowered:
            return {"intent": "stop"}
        
        # Project type detection
        if "react" in lowered:
            return {"intent": "create_react_project", "name": "react_app"}
        elif "django" in lowered:
            return {"intent": "create_django_project", "name": "django_project"}
        elif "node" in lowered:
            return {"intent": "create_node_project", "name": "node_app"}
        elif "web" in lowered and "app" in lowered:
            return {"intent": "create_web_project", "name": "web_app"}
        elif "data" in lowered or "analysis" in lowered:
            return {"intent": "create_data_project", "name": "data_project"}
        elif "run" in lowered or "start" in lowered:
            return {"intent": "run_project"}
        elif "install" in lowered or "dependencies" in lowered:
            return {"intent": "install_dependencies"}
        elif "open" in lowered:
            return {"intent": "open_project"}
        elif "help" in lowered:
            return {"intent": "help"}
        elif "status" in lowered or "what's happening" in lowered:
            return {"intent": "status"}

        # rule-based fallback for common commands
        if "create folder" in lowered:
            return {
                "intent": None,
                "action": "create_folder",
                "path": "./new_folder"
            }
        if "create file" in lowered:
            return {
                "intent": None,
                "action": "create_file",
                "path": "./new_file.txt"
            }
        if "are you there" in lowered:
            return {
                "intent": None,
                "action": None,
                "response": "yes"
            }
        
        # default fallback: unknown with error info
        return {"intent": None, "raw": text, "error": str(e)}
    
    try:
        payload = _safe_parse_json_from_text(response)
    except Exception:
        # graceful fallback: try to infer minimal intent
        lowered = text.strip().lower()
        if "undo" in lowered:
            return {"intent": "undo"}
        if "stop" in lowered:
            return {"intent": "stop"}
        
        # Project type detection
        if "react" in lowered:
            return {"intent": "create_react_project", "name": "react_app"}
        elif "django" in lowered:
            return {"intent": "create_django_project", "name": "django_project"}
        elif "node" in lowered:
            return {"intent": "create_node_project", "name": "node_app"}
        elif "web" in lowered and "app" in lowered:
            return {"intent": "create_web_project", "name": "web_app"}
        elif "data" in lowered or "analysis" in lowered:
            return {"intent": "create_data_project", "name": "data_project"}
        elif "run" in lowered or "start" in lowered:
            return {"intent": "run_project"}
        elif "install" in lowered or "dependencies" in lowered:
            return {"intent": "install_dependencies"}
        elif "open" in lowered:
            return {"intent": "open_project"}
        elif "help" in lowered:
            return {"intent": "help"}
        elif "status" in lowered or "what's happening" in lowered:
            return {"intent": "status"}

        # rule-based fallback for common commands
        if "create folder" in lowered:
            return {
                "intent": None,
                "action": "create_folder",
                "path": "./new_folder"
            }
        if "create file" in lowered:
            return {
                "intent": None,
                "action": "create_file",
                "path": "./new_file.txt"
            }
        if "are you there" in lowered:
            return {
                "intent": None,
                "action": None,
                "response": "yes"
            }
        
        # default fallback: unknown
        return {"intent": None, "raw": text}

    # normalize keys
    intent = payload.get("intent")
    name = payload.get("name", "").strip()
    location = payload.get("location", "").strip() or payload.get("path", "").strip() or "."
    action = payload.get("action")
    path = payload.get("path")

    out = {"intent": intent, "name": name, "location": location}
    if action:
        out["action"] = action
    if path:
        out["path"] = path
    return out
