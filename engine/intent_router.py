# engine/intent_router.py
from blueprints.flutter_basic import blueprint as flutter
from blueprints.flask_basic import blueprint as flask
from engine.scaffold import apply_blueprint
from engine.undo import undo_last
from engine.command_executor import execute_command
from pathlib import Path
import subprocess
import os

def route(intent: dict):
    # guard
    if not isinstance(intent, dict):
        return "⚠️ Invalid intent"

    # handle simple responses
    if intent.get("response") == "yes":
        return "Yes, I am here."

    i = intent.get("intent")
    if i == "stop":
        return "__STOP__"

    if not i:
        # maybe it's a low-level action
        if "action" in intent and "path" in intent:
            return execute_command({"action": intent["action"], "path": intent["path"]})
        return "⚠️ No intent detected"

    if i == "undo":
        return undo_last()

    # create project intents
    if i in ("create_flutter_project", "create_flask_project"):
        base = Path(intent.get("location", "."))
        name = intent.get("name") or "unnamed_project"
        project = base / name

        if i == "create_flutter_project":
            apply_blueprint(project, flutter())
            return f"✅ Flutter project created at {project}"

        if i == "create_flask_project":
            apply_blueprint(project, flask())
            return f"✅ Flask project created at {project}"

    if i == "create_react_project":
        base = Path(intent.get("location", "."))
        name = intent.get("name") or "react_app"
        project = base / name
        
        # Create React-like structure
        bp = {
            "folders": [
                "src", "src/components", "src/pages", "src/hooks",
                "public", "assets", "styles"
            ],
            "files": [
                "package.json:{\"name\": \"" + name + "\", \"version\": \"1.0.0\"}",
                "README.md:# " + name + "\\nReact Application",
                "src/index.js:// React entry point",
                "public/index.html:<!DOCTYPE html>\\n<html>\\n<head>\\n  <title>" + name + "</title>\\n</head>\\n<body>\\n  <div id=\"root\"></div>\\n</body>\\n</html>"
            ]
        }
        apply_blueprint(project, bp)
        return f"✅ React project created at {project}"
    
    if i == "create_node_project":
        base = Path(intent.get("location", "."))
        name = intent.get("name") or "node_app"
        project = base / name
        
        bp = {
            "folders": ["src", "routes", "models", "config", "tests"],
            "files": [
                "package.json:{\"name\": \"" + name + "\", \"main\": \"src/index.js\"}",
                "src/index.js:console.log('Hello Node!')",
                ".gitignore:node_modules\\n.env",
                "README.md:# " + name + "\\nNode.js Application"
            ]
        }
        apply_blueprint(project, bp)
        return f"✅ Node.js project created at {project}"
    
    if i == "create_web_project":
        base = Path(intent.get("location", "."))
        name = intent.get("name") or "website"
        project = base / name
        
        bp = {
            "folders": ["css", "js", "images"],
            "files": [
                "index.html:<!DOCTYPE html>\\n<html>\\n<head>\\n  <title>" + name + "</title>\\n  <link rel=\"stylesheet\" href=\"css/style.css\">\\n</head>\\n<body>\\n  <h1>Welcome to " + name + "</h1>\\n  <script src=\"js/app.js\"></script>\\n</body>\\n</html>",
                "css/style.css:body { font-family: Arial; margin: 40px; }",
                "js/app.js:console.log('Website loaded');",
                "README.md:# " + name + "\\nStatic Website"
            ]
        }
        apply_blueprint(project, bp)
        return f"✅ Web project created at {project}"
    
    # Add action handlers
    if i == "run_project":
        # Try to detect project type and run
        cwd = intent.get("location", ".")
        try:
            if os.path.exists(os.path.join(cwd, "package.json")):
                subprocess.run(["npm", "start"], cwd=cwd)
                return "🚀 Node project started"
            elif os.path.exists(os.path.join(cwd, "app.py")):
                subprocess.run(["python", "app.py"], cwd=cwd)
                return "🚀 Python app started"
            else:
                return "⚠️ No runnable project detected"
        except Exception as e:
            return f"❌ Failed to run project: {e}"
    
    if i == "install_dependencies":
        cwd = intent.get("location", ".")
        if os.path.exists(os.path.join(cwd, "package.json")):
            subprocess.run(["npm", "install"], cwd=cwd)
            return "📦 Node dependencies installed"
        elif os.path.exists(os.path.join(cwd, "requirements.txt")):
            subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=cwd)
            return "📦 Python dependencies installed"
        else:
            return "⚠️ No dependency file found"
    
    if i == "help":
        return """Available commands:
• Create projects: React, Node, Flask, Flutter, Django, Web
• File operations: create folder/file, delete folder/file
• Project actions: run project, install dependencies
• System: undo, stop, help, status"""
    
    if i == "status":
        return "✅ VAL is running and ready"

    # low-level filesystem intents
    if "action" in intent and "path" in intent:
        return execute_command({"action": intent["action"], "path": intent["path"]})

    return "⚠️ Unknown intent"
