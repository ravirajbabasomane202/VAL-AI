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

# Add new imports
from blueprints.react_basic import blueprint as react_basic
from blueprints.node_basic import blueprint as node_basic
from blueprints.web_basic import blueprint as web_basic

from ai.blueprint_generator import generate_blueprint

try:
    from ai.flutter_generator import generate_flutter_blueprint
except ImportError:
    generate_flutter_blueprint = None

def main():
    # Debug mode
    debug_mode = "--debug" in sys.argv

    base_location = ask_project_location()
    project_name = ask_project_name()
    project_path = base_location / project_name

    print("\nChoose creation method:")
    print("1. Manual (predefined)")
    print("2. AI-generated (Ollama)")

    method = input("Choice: ").strip()

    if method == "1":
        choice = ask_project_type()

        if choice == "1":
            bp = single_folder()
        elif choice == "2":
            bp = custom_multi()
        elif choice == "3":
            bp = flask_basic()
        elif choice == "4":
            bp = flutter_basic()
        elif choice == "5":
            bp = react_basic()
        elif choice == "6":
            bp = node_basic()
        elif choice == "7":
            bp = web_basic()
        elif choice == "8":
            # Data science blueprint
            bp = {
                "folders": ["data", "notebooks", "scripts", "reports"],
                "files": [
                    "README.md:# Data Science Project\n## Description",
                    "requirements.txt:# Python dependencies",
                    "notebooks/analysis.ipynb:# Data analysis notebook",
                    "scripts/process.py:# Data processing script"
                ]
            }
        else:
            print("❌ Invalid choice")
            return

    elif method == "2":
        try:
            user_request = ask_ai_request()
            
            # Always try AI generation first
            bp = generate_blueprint(user_request)
            bp = validate_blueprint(bp)
        except ValueError as e:
            print(f"\n❌ AI Generation failed: {e}")
            
            # Try fallback for Flutter
            if any(word in user_request.lower() for word in ["flutter", "dart"]):
                print("Attempting fallback generation for Flutter...")
                if generate_flutter_blueprint:
                    bp = generate_flutter_blueprint()
                else:
                    from blueprints.flutter_basic import blueprint as flutter_basic
                    bp = flutter_basic()
                bp = validate_blueprint(bp)
            else:
                return

    elif len(method) > 0 and not method.isdigit():
        try:
            print("\n🤖 Processing as AI request...")
            bp = generate_blueprint(method)
            bp = validate_blueprint(bp)
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
        print(f"First file entry type: {type(bp.get('files', [])[0]) if bp.get('files') else 'No files'}")

    show_preview(project_path, bp)
    apply_blueprint(project_path, bp)
    print(f"\n✅ Project created successfully at {project_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VAL - Local Automated Coding Assistant")
    parser.add_argument("--daemon", action="store_true", help="Run VAL as background voice daemon")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    if args.daemon:
        # import here to avoid importing daemon during normal interactive runs
        from daemon.service import run as daemon_run
        daemon_run()
    else:
        main()
