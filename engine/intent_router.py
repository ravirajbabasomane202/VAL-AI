from pathlib import Path
import subprocess
import os
import json
from engine.scaffold import apply_blueprint
from engine.undo import undo_last
from engine.command_executor import execute_command, open_application
from engine.git_executor import (init_repo, commit, create_branch, push, undo_last_commit, get_status)
from engine.env_manager import (create_env, load_env, switch_config, detect_project_type)
from engine.dep_intelligence import (get_deps, check_outdated, add_dep, remove_dep, audit_dep)
from blueprints.flask_basic import blueprint as flask
from blueprints.flutter_basic import blueprint as flutter
# ... existing ...

def route(intent: dict, memory_instance=None):
    if not isinstance(intent, dict):
        return "⚠️ Invalid intent"
    
    intent_type = intent.get("intent")
    
    # Stop/undo/help/status (existing, unchanged)
    if intent_type == "stop":
        return "__STOP__"
    if intent_type == "undo":
        return undo_last()
    if intent_type == "help":
        return """🧠 Raj Enhanced Commands: ..."""  # Existing help_text
    if intent_type == "status":
        return f"""✅ Raj Status: ..."""  # Existing
    
    # Memory/Workflow (Level 1.1)
    if intent_type == "remember":
        # Existing
        pass
    elif intent_type == "remember_workflow":
        trigger = intent.get("trigger", {})
        actions = intent.get("actions", [])
        if not trigger or not actions:
            return "⚠️ Incomplete workflow."
        key = memory_instance.remember_workflow(trigger, actions)
        return f"✅ Workflow remembered! Key: {key}."
    elif intent_type == "repeat_last_workflow":
        wf = SESSION.get("last_workflow")
        if not wf:
            return "❌ No workflow to repeat."
        context = {"path": SESSION.get("last_project", {}).get("path", ""), "scope": "global"}
        return execute_workflow(wf["actions"], context)
    
    # Pipeline/Chaining (Level 1.2)
    if intent_type == "pipeline":
        steps = intent.get("steps", [])
        context = {"path": SESSION.get("last_project", {}).get("path", ""), "scope": "global"}
        result = memory_instance.execute_pipeline("ad-hoc", steps, context)
        if len(steps) > 1:
            memory_instance.remember_pipeline(f"{intent_type}_auto", steps, f"From: {intent.get('raw', '')}")
        return f"🔗 Pipeline: {result}"
    elif intent_type == "execute_pipeline":
        name = intent.get("name", "")
        context = {"path": SESSION.get("last_project", {}).get("path", ""), "scope": "global"}
        return memory_instance.execute_pipeline(name, context)
    
    # Clarification (Level 1.3) - Defer to state machine, but handle here if text
    if intent.get("ambiguous"):
        pending = SESSION.get("pending_action", {})
        if pending.get("question_type") == "choice":
            choice = intent.get("raw", "").lower()
            options = pending.get("options", [])
            if choice in [opt.lower() for opt in options]:
                resolved = pending["original_intent"].copy()
                if "flask" in choice:
                    resolved["intent"] = "create_flask_project"
                # Map others: django -> create_django_project, etc.
                resolved["ambiguous"] = False
                resolved["confidence"] = 0.95
                SESSION["pending_action"] = None
                return route(resolved, memory_instance)
            return {"ask": f"Not clear. Options: {', '.join(options)}?"}
    
    # Project creation (existing, with tech extract)
    if intent_type in ("create_flutter_project", "create_flask_project", "create_react_project", "create_node_project", "create_web_project", "create_data_project"):
        # Existing blueprint/apply logic...
        pass  # Keep as-is, but add after apply_blueprint:
        after_intent_execution(intent, {"path": str(project), "scope": "global"})
    
    # Run/install (existing)
    if intent_type == "run_project":
        # Existing
        pass
    elif intent_type == "install_dependencies":
        # Existing
        pass
    
    # Git (Level 2.4)
    if intent_type in ["git_init", "git_commit", "git_branch", "git_push", "git_undo"]:
        cwd = Path(intent.get("location", SESSION.get("last_project", {}).get("path", ".")))
        if intent_type == "git_init":
            result = init_repo(intent.get("remote"))
        elif intent_type == "git_commit":
            result = commit(intent.get("message", "No msg"))
        elif intent_type == "git_branch":
            result = create_branch(intent.get("name", "feature"))
        elif intent_type == "git_push":
            result = push(intent.get("remote", "origin"), intent.get("branch", "main"), intent.get("force", False))
        elif intent_type == "git_undo":
            result = undo_last_commit()
        memory_instance.remember("git_remote", intent.get("remote", ""), "project")
        return result + f"\n(CWD: {cwd})"
    
    # Env (Level 2.5)
    if intent_type in ["env_create", "env_load", "env_switch"]:
        cwd = Path(intent.get("location", SESSION.get("last_project", {}).get("path", ".")))
        if intent_type == "env_create":
            result = create_env(template=intent.get("template"))
        elif intent_type == "env_load":
            result = load_env(config=intent.get("config", "dev"))
        else:
            result = switch_config(intent.get("config", "dev"))
        return result + f"\n(CWD: {cwd})"
    
    # Deps (Level 2.6)
    if intent_type in ["deps_list", "deps_outdated", "deps_add", "deps_remove"]:
        cwd = Path(intent.get("location", SESSION.get("last_project", {}).get("path", ".")))
        if intent_type == "deps_list":
            result = get_deps(cwd)
        elif intent_type == "deps_outdated":
            result = check_outdated(cwd)
        elif intent_type == "deps_add":
            result = add_dep(intent.get("name", ""), intent.get("dev", False), cwd)
            audit = audit_dep(intent.get("name", ""), detect_project_type(cwd))
            result += f"\nAudit: {audit}"
        else:
            result = remove_dep(intent.get("name", ""), cwd)
        return result
    
    # Code Understanding (Level 3)
    if intent_type == "explain_file":
        from engine.code_analyzer import analyzer
        file_path = intent.get("file", "")
        return analyzer.explain_file(file_path)
    
    elif intent_type == "find_auth":
        from engine.code_analyzer import analyzer
        return analyzer.find_auth_handlers()
    
    elif intent_type == "show_routes":
        from engine.code_analyzer import analyzer
        return analyzer.show_api_routes()
    
    elif intent_type == "find_calls":
        from engine.code_analyzer import analyzer
        function = intent.get("function", "")
        return analyzer.find_function_calls(function)
    
    # Health Scanner (Level 3)
    elif intent_type == "check_health":
        from engine.health_scanner import scanner
        report = scanner.scan_health()
        memory.log_event("health_scan", result=report)
        return scanner.format_report(report)
    
    elif intent_type == "quick_health":
        from engine.health_scanner import scanner
        return scanner.quick_check()
    
    # Enhanced Undo (Level 3)
    elif intent_type == "undo_multiple":
        from engine.undo import undo_manager
        count = intent.get("count", 1)
        return undo_manager.undo_multiple(count)
    
    elif intent_type == "list_undo":
        from engine.undo import undo_manager
        return undo_manager.list_operations()
    
    # App Control (Level 5)
    elif intent_type == "open_app":
        cwd = Path(SESSION.get("last_project", {}).get("path", "."))
        return open_application(intent.get("name", ""), cwd)

    elif intent_type == "set_voice_mode":
        mode = intent.get("mode")
        SESSION.setdefault("voice_prefs", {})["whisper_mode"] = (mode == "whisper")
        return f"🎙️ Switched to {mode} mode."
    
    # Goals (Level 2)
    elif intent_type == "set_goal":
        desc = intent.get("description", "Unknown goal")
        memory_instance.add_goal(desc)
        return f"🎯 Goal set: {desc}"
    
    elif intent_type == "list_goals":
        goals = memory_instance.get_active_goals()
        if not goals:
            return "🎯 No active goals."
        return "🎯 Active Goals:\n" + "\n".join([f"- {g['description']} (Priority: {g['priority']})" for g in goals])
    
    # Filesystem (existing)
    if "action" in intent and "path" in intent:
        # Existing
        pass
    
    return "⚠️ Unknown intent"


def confirm_workflow(wf: dict, context: dict) -> bool:
    """Ask for confirmation if not auto-enabled"""
    if SESSION["user_preferences"].get("auto_apply_workflows", True):
        return True
    actions_str = ", ".join(wf["actions"])
    speak(f"Smart suggestion: After {context.get('intent', 'this'), actions_str}? Say yes or no.")
    # Listen for simple yes/no (use existing listener)
    response = listen().strip().lower()
    return any(word in response for word in ["yes", "yep", "sure"])

def execute_workflow(actions: list, context: dict):
    """Execute a list of actions as chained intents"""
    results = []
    for action in actions:
        # Map action to intent (e.g., "add_docker" -> {"intent": "add_docker", "context": context})
        sub_intent = {
            "intent": action if "_" in action else f"perform_{action}",
            "context": context,
            "source": "workflow"  # For logging
        }
        # Safety check per action
        safety = memory.check_safety(sub_intent, action, context.get("path", ""))
        if safety["action"] == "confirm":
            if not confirm_workflow({"actions": [action]}, context):
                results.append(f"Skipped: {action} (cancelled)")
                continue
        elif safety["action"] == "deny":
            results.append(f"Blocked: {action} ({safety['reason']})")
            continue
        
        result = route(sub_intent, memory)
        results.append(result)
        # Log each sub-action
        memory.log_event("workflow_action", intent=sub_intent, result=result)
    return "\n".join(results)

def after_intent_execution(intent: dict, context: dict):
    """Hook: Auto-apply workflows after successful execution"""
    if intent.get("source") == "workflow":  # Avoid recursion
        return
    
    # Extract tech from intent (e.g., "create_flask_project" -> "flask")
    tech = None
    if "create_" in intent.get("intent", "") and "_project" in intent.get("intent", ""):
        tech = intent["intent"].split("_")[1]
    
    workflows = memory.get_workflows_for_trigger(
        intent_name=intent["intent"],
        tech=tech,
        scope=context.get("scope", "global")
    )
    
    if not workflows:
        return  # No matches
    
    # Prioritize highest-confidence workflow
    wf = workflows[0]
    context["intent"] = intent["intent"]  # For confirmation phrasing
    
    if confirm_workflow(wf, context):
        result = execute_workflow(wf["actions"], context)
        memory.log_event("workflow_applied", data={"workflow": wf["id"], "results": result})
        SESSION["last_workflow"] = wf  # For repeat
        return result
    else:
        memory.log_event("workflow_declined", data={"workflow": wf["id"]})
    
    # Auto-deps after project create
    if "create_" in intent["intent"]:
        tech = intent["intent"].split("_")[1]
        # Chain deps and env
        from engine.dep_intelligence import add_dep
        from engine.env_manager import create_env
        add_dep(f"{tech}_defaults", cwd=Path(context.get("path", ".")))
        create_env(cwd=Path(context.get("path", ".")))