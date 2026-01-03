"""
Code Understanding Module - Selective IDE-like Analysis
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Optional
from core.memory import memory
from core.session import SESSION

class CodeAnalyzer:
    """Analyze code for understanding and navigation"""
    
    def __init__(self, project_path: Path = None):
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

# Global analyzer instance
analyzer = CodeAnalyzer()