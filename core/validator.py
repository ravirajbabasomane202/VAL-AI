def validate_blueprint(blueprint):
    """Validate and clean a blueprint structure"""
    if not isinstance(blueprint, dict):
        raise ValueError(f"Blueprint must be a dictionary, got {type(blueprint)}")

    blueprint.setdefault("folders", [])
    blueprint.setdefault("files", [])
    
    # Clean folders
    blueprint["folders"] = [str(f).strip() for f in blueprint["folders"] if str(f).strip()]
    
    # Clean files - handle both formats
    cleaned_files = []
    for f in blueprint["files"]:
        if isinstance(f, dict):
            # Ensure path exists
            if "path" in f:
                cleaned_files.append({
                    "path": str(f["path"]).strip(),
                    "content": str(f.get("content", ""))
                })
        elif isinstance(f, str):
            # Handle old format
            cleaned_files.append(f.strip())
    
    blueprint["files"] = cleaned_files
    return blueprint