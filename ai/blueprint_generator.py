import json
import re
import time
from ai.ollama_client import ask_ollama

ENHANCED_SYSTEM_PROMPT = """
You are an expert project scaffolding generator with deep knowledge of software architecture.

RULES:
CRITICAL RULES:
- Output ONLY valid JSON
- Use relative paths only
- "folders" and "files" must be lists
- For files, you can specify content templates using: "path:content" format
- Support nested structures up to 5 levels
- Include necessary configuration files
- Add README.md with project description
- Include .gitignore when applicable
- For files, use format: {"path": "filename", "content": "file content"}
- DO NOT use single quotes, only double quotes for JSON
- Escape all backslashes and special characters
- Keep it simple - no complex nesting in response

COMMON PATTERNS:
- Web: index.html, style.css, script.js
- Python: requirements.txt, main.py, setup.py
- Node: package.json, src/, public/
- Data: data/, notebooks/, scripts/
- Config: config/, .env.example

JSON format:
SIMPLE JSON format (use this exactly):
{
  "folders": ["src", "tests", "docs"],
  "folders": ["folder1", "folder2"],
  "files": [
    {"path": "README.md", "content": "# Project\n## Description"},
    {"path": "src/main.py", "content": "# Main application"},
    {"path": ".gitignore", "content": "*.pyc\n__pycache__/"}
    {"path": "file1.txt", "content": "Content here"},
    {"path": "folder/file2.py", "content": "# Python code"}
  ]
}
"""

def generate_blueprint(user_request: str):
    # Check for specific keywords
    if any(word in user_request.lower() for word in ["web", "website", "html", "css"]):
        task_instruction = "Generate a web project blueprint with HTML, CSS, JS."
    elif any(word in user_request.lower() for word in ["api", "rest", "backend"]):
        task_instruction = "Generate a backend API project blueprint."
    elif any(word in user_request.lower() for word in ["data", "analysis", "notebook"]):
        task_instruction = "Generate a data analysis project blueprint."
    # Check if it's a tree structure
    is_tree_structure = any(char in user_request for char in ["├", "└", "│", "└──", "├──", "└", "│"])
    
    if is_tree_structure:
        task_instruction = """
        Convert this tree structure to SIMPLE JSON format.
        - Extract all folders and files
        - Use simple paths
        - For files, provide empty content or basic template
        - Output must be valid JSON with double quotes only
        """
    else:
        task_instruction = "Generate the most appropriate project blueprint."
        # Check for specific keywords
        if any(word in user_request.lower() for word in ["web", "website", "html", "css"]):
            task_instruction = "Generate a simple web project blueprint with HTML, CSS, JS."
        elif any(word in user_request.lower() for word in ["api", "rest", "backend"]):
            task_instruction = "Generate a simple backend API project blueprint."
        elif any(word in user_request.lower() for word in ["data", "analysis", "notebook"]):
            task_instruction = "Generate a simple data analysis project blueprint."
        elif any(word in user_request.lower() for word in ["flutter", "dart"]):
            task_instruction = "Generate a simple Flutter/Dart project blueprint."
        else:
            task_instruction = "Generate a simple project blueprint."
    
    prompt = f"""
{ENHANCED_SYSTEM_PROMPT}

USER REQUEST:
{user_request}

ADDITIONAL INSTRUCTIONS:
{task_instruction}
- Include essential configuration files
- Add sample/starter code in main files
- Ensure project is runnable/executable
- Add documentation where needed

Generate blueprint now:
"""

    start_time = time.time()
    response = ask_ollama(prompt)
    end_time = time.time()
    duration = end_time - start_time
    print(f"AI response time: {duration:.2f} seconds")

    # Clean up response (handle Markdown code blocks)
    json_str = response
    match = re.search(r"```(?:json)?\s*(.*?)```", response, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            json_str = response[start:end+1]

    # Remove invalid control characters
    json_str = ''.join(c for c in json_str if ord(c) >= 32 or c in '\n\r\t')

    try:
        blueprint = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Attempting to fix JSON...")
        
        # Try to fix common JSON issues
        # 1. Fix escape sequences
        json_str = json_str.replace('\\', '\\\\')
        
        # 2. Fix invalid control characters
        json_str = ''.join(c for c in json_str if c == '\n' or c == '\t' or c == '\r' or (32 <= ord(c) <= 126))
        
        # 3. Try to find valid JSON object
        try:
            start = json_str.find('{')
            end = json_str.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = json_str[start:end+1]
                blueprint = json.loads(json_str)
            else:
                raise ValueError(f"Could not find valid JSON in response")
        except json.JSONDecodeError as e2:
            print(f"Second JSON parse attempt failed: {e2}")
            
            # Try to extract as simple format if complex JSON fails
            print("Attempting fallback to simple structure...")
            blueprint = _extract_simple_structure(response)

    return blueprint


def _extract_simple_structure(response: str):
    """Fallback method to extract structure from text when JSON fails"""
    lines = response.split('\n')
    folders = []
    files = []
    
    for line in lines:
        line = line.strip()
        # Look for directory indicators
        if any(indicator in line for indicator in ['/', '├', '└', '│', '└──', '├──']):
            # Extract potential path
            clean_line = line.replace('├──', '').replace('└──', '').replace('│', '').strip()
            
            # Check if it's a folder (ends with / or contains / but no file extension)
            if '/' in clean_line:
                path_parts = clean_line.split('/')
                # If ends with empty or looks like folder
                if len(path_parts) > 1 and ('.' not in path_parts[-1] or path_parts[-1] == ''):
                    folder_path = '/'.join(path_parts[:-1]) if path_parts[-1] == '' else clean_line
                    if folder_path and folder_path not in folders:
                        folders.append(folder_path)
                # Could be a file
                elif '.' in path_parts[-1]:
                    if clean_line and clean_line not in files:
                        files.append({"path": clean_line, "content": ""})
            elif clean_line and '.' not in clean_line and clean_line not in ['', 'flutter_app']:
                # Might be a folder
                folders.append(clean_line)
    
    # If we didn't find anything, return a basic structure
    if not folders and not files:
        return {
            "folders": ["lib", "assets"],
            "files": [
                {"path": "README.md", "content": "# Flutter App"},
                {"path": "pubspec.yaml", "content": "name: flutter_app"}
            ]
        }
    
    return {
        "folders": list(set(folders)),
        "files": files if files else [{"path": "README.md", "content": "# Generated App"}]
    }
