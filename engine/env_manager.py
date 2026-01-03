import os
from pathlib import Path
from core.memory import memory
from core.session import SESSION

ENV_TEMPLATES = {
    "python": {"DATABASE_URL": "sqlite:///app.db", "SECRET_KEY": "dev-secret"},
    "node": {"PORT": "3000", "JWT_SECRET": "dev-jwt"},
    "flutter": {"API_BASE": "http://localhost:8000"},
    "general": {"APP_NAME": "My App"}
}

def detect_project_type(cwd: Path) -> str:
    if (cwd / "pubspec.yaml").exists():
        return "flutter"
    if (cwd / "package.json").exists():
        return "node"
    if (cwd / "requirements.txt").exists() or any(f.suffix == ".py" for f in cwd.glob("*.py")):
        return "python"
    return "general"

def create_env(cwd: Path = None, template: str = None) -> str:
    if cwd is None:
        cwd = Path(SESSION.get("last_project", {}).get("path", "."))
    
    ptype = detect_project_type(cwd) if not template else template
    env_data = ENV_TEMPLATES.get(ptype, ENV_TEMPLATES["general"])
    
    env_path = cwd / ".env"
    env_path.write_text("\n".join(f"{k}={v}" for k, v in env_data.items()))
    
    example_path = cwd / ".env.example"
    example_path.write_text("\n".join(f"{k}={k.lower()}_example" for k in env_data.keys()))
    
    memory.remember(f"env_template_{ptype}", env_data, "project")
    memory.log_event("env_created", data={"type": ptype, "path": str(cwd)})
    
    os.environ.update(env_data)
    return f"✅ .env created for {ptype} at {cwd}\nLoaded: {env_data}"

def load_env(cwd: Path = None, config: str = "dev") -> str:
    if cwd is None:
        cwd = Path(SESSION.get("last_project", {}).get("path", "."))
    
    env_path = cwd / ".env"
    if not env_path.exists():
        return create_env(cwd)
    
    with open(env_path) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ[k] = v
    
    if config == "prod":
        os.environ["DEBUG"] = "false"
    
    memory.log_event("env_loaded", data={"config": config, "path": str(cwd)})
    return f"📂 .env loaded ({config}) from {cwd}. Vars: {list(os.environ.keys())[:3]}..."

def switch_config(config: str, cwd: Path = None) -> str:
    return load_env(cwd, config)