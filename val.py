"""
VAL Enhanced - Main entry point with cognitive memory system
"""
import sys
from core.prompts import (
    ask_project_location,
    ask_project_name,
    ask_project_type,
    ask_ai_request
)
import argparse
from core.preview import show_preview
from core.validator import validate_blueprint
from engine.scaffold import apply_blueprint

from blueprints.single_folder import blueprint as single_folder
from blueprints.custom_multi import blueprint as custom_multi
from blueprints.flask_basic import blueprint as flask_basic
from blueprints.flutter_basic import blueprint as flutter_basic
from blueprints.react_basic import blueprint as react_basic
from blueprints.node_basic import blueprint as node_basic
from blueprints.web_basic import blueprint as web_basic

from ai.blueprint_generator import generate_blueprint
from core.memory import memory
from core.session import SESSION
from ai.intent_extractor import extract_intent_with_memory

try:
    from ai.flutter_generator import generate_flutter_blueprint
except ImportError:
    generate_flutter_blueprint = None

def main():
    # Debug mode
    debug_mode = "--debug" in sys.argv
    
    # Load memory context
    last_project = memory.get_last_project()
    if last_project:
        print(f"📂 Last project: {last_project['name']} at {last_project['path']}")
    
    base_location = ask_project_location()
    project_name = ask_project_name()
    project_path = base_location / project_name
    
    print("\nChoose creation method:")
    print("1. Manual (predefined)")
    print("2. AI-generated (Ollama)")
    print("3. Similar to last project")
    print("4. Autonomous Task (Level 4)")
    print("5. Configure Profile")
    
    method = input("Choice: ").strip()
    
    if method == "1":
        print("\nWhat do you want to create?")
        print("1. Single folder")
        print("2. Custom multi-folder")
        print("3. Flask project")
        print("4. Flutter project")
        print("5. React project")
        print("6. Node.js project")
        print("7. Web project")
        print("8. Data science project")
        
        choice = input("Choice: ").strip()
        
        if choice == "1":
            bp = single_folder()
            project_type = "folder"
        elif choice == "2":
            bp = custom_multi()
            project_type = "custom"
        elif choice == "3":
            bp = flask_basic()
            project_type = "flask"
        elif choice == "4":
            bp = flutter_basic()
            project_type = "flutter"
        elif choice == "5":
            bp = react_basic()
            project_type = "react"
        elif choice == "6":
            bp = node_basic()
            project_type = "node"
        elif choice == "7":
            bp = web_basic()
            project_type = "web"
        elif choice == "8":
            bp = {
                "folders": ["data", "notebooks", "scripts", "reports"],
                "files": [
                    "README.md:# Data Science Project\n## Description",
                    "requirements.txt:# Python dependencies",
                    "notebooks/analysis.ipynb:# Data analysis notebook",
                    "scripts/process.py:# Data processing script"
                ]
            }
            project_type = "data"
        else:
            print("❌ Invalid choice")
            return
    
    elif method == "2":
        try:
            user_request = ask_ai_request()
            
            # Always try AI generation first
            bp = generate_blueprint(user_request)
            bp = validate_blueprint(bp)
            project_type = "ai_generated"
        except ValueError as e:
            print(f"\n❌ AI Generation failed: {e}")
            
            # Try fallback for Flutter
            if any(word in user_request.lower() for word in ["flutter", "dart"]):
                print("Attempting fallback generation for Flutter...")
                if generate_flutter_blueprint:
                    bp = generate_flutter_blueprint()
                else:
                    bp = flutter_basic()
                bp = validate_blueprint(bp)
                project_type = "flutter"
            else:
                return
    
    elif method == "3":
        # Similar to last project
        last_project = memory.get_last_project()
        if last_project:
            print(f"\n📂 Creating project similar to: {last_project['name']}")
            project_type = last_project.get("project_type", "unknown")
            
            # Try to use the stored blueprint
            try:
                bp = json.loads(last_project.get("blueprint", "{}"))
                if not bp:
                    raise ValueError("No blueprint stored")
            except:
                # Fallback based on project type
                if "flutter" in project_type.lower():
                    bp = flutter_basic()
                elif "flask" in project_type.lower():
                    bp = flask_basic()
                elif "react" in project_type.lower():
                    bp = react_basic()
                elif "node" in project_type.lower():
                    bp = node_basic()
                elif "web" in project_type.lower():
                    bp = web_basic()
                else:
                    bp = custom_multi()
        else:
            print("❌ No previous project found in memory")
            return
    
    elif method == "4":
        # Autonomous Mode
        print("\n🤖 Autonomous Mode (Opt-in)")
        print("Describe your high-level goal (e.g., 'Set up a production Flask API with Docker and Auth')")
        user_request = ask_ai_request()
        
        print("🧠 Planning...")
        intent = extract_intent_with_memory(user_request)
        
        if intent.get("intent") == "autonomous_mode":
            plan = intent.get("plan", [])
            print(f"\n📋 Generated Plan ({len(plan)} steps):")
            
            # Level 7: Critic Check
            from agent.core import CriticAgent
            critic = CriticAgent()
            eval_result = critic.evaluate(plan)
            
            for i, step in enumerate(plan, 1):
                print(f"  {i}. {step.get('intent')} - {step.get('name', '')} {step.get('parameters', '')}")
            
            print(f"\n🕵️ Critic Analysis: {eval_result['reason']}")
            print(f"📊 Predicted Effects: {eval_result['effects']['summary']}")
            
            confirm = input(f"\nExecute plan? (Risk: {eval_result['risk_level']}) (y/n): ").strip().lower()
            if confirm in ["y", "yes"]:
                from engine.intent_router import route
                for step in plan:
                    print(f"\n▶️ Executing: {step.get('intent')}...")
                    result = route(step, memory)
                    print(result)
                print("\n✅ Autonomous task complete!")
                return
            else:
                print("❌ Cancelled.")
                return
        else:
            print("⚠️ Could not generate an autonomous plan. Falling back to blueprint generation.")
            bp = generate_blueprint(user_request)
            bp = validate_blueprint(bp)
            project_type = "ai_generated"

    elif method == "5":
        # Configure Profile
        print("\n👤 Developer Profile Configuration")
        stack = input("Preferred Stack (e.g., Flask, React): ").strip()
        memory.set_preference("preferred_stack", stack, "profile")
        print("✅ Profile updated!")
        return

    elif len(method) > 0 and not method.isdigit():
        try:
            print("\n🤖 Processing as AI request...")
            bp = generate_blueprint(method)
            bp = validate_blueprint(bp)
            project_type = "ai_generated"
        except ValueError as e:
            print(f"\n❌ AI Generation failed: {e}")
            return
    else:
        print("❌ Invalid method")
        return
    
    if debug_mode:
        print("\n🔍 DEBUG: Blueprint structure:")
        print(f"Folders: {bp.get('folders', [])}")
        print(f"Files: {bp.get('files', [])}")
    
    show_preview(project_path, bp)
    
    # Ask for confirmation
    confirm = input("\nCreate project? (y/n): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("❌ Project creation cancelled")
        return
    
    apply_blueprint(project_path, bp)
    
    # Remember project
    memory.remember_project(project_name, str(project_path), project_type, bp)
    SESSION["last_project"] = {"name": project_name, "path": str(project_path)}
    
    print(f"\n✅ Project created successfully at {project_path}")
    print(f"📝 Project saved to memory (type: {project_type})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Raj Enhanced - Cognitive Local AI Assistant")
    parser.add_argument("--daemon", action="store_true", help="Run VAL as background voice daemon")
    parser.add_argument("--enhanced", action="store_true", help="Use enhanced cognitive daemon")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    if args.daemon:
        if args.enhanced:
            # Import enhanced daemon
            try:
                from daemon.service import run as daemon_run_enhanced
                print("🚀 Starting Raj Enhanced Cognitive Daemon...")
                daemon_run_enhanced()
            except ImportError:
                print("❌ Enhanced daemon not available. Falling back to regular daemon.")
                from daemon.service import run as daemon_run
                daemon_run()
        else:
            # Import regular daemon
            from daemon.service import run as daemon_run
            daemon_run()
    else:
        main()