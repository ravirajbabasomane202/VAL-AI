def show_preview(base, blueprint):
    print("\n📁 PREVIEW:")
    for d in blueprint.get("folders", []):
        print(f"  [DIR ] {base / d}")
    for f in blueprint.get("files", []):
        if isinstance(f, dict):
            # Handle new format: {"path": "...", "content": "..."}
            file_path = f.get("path", "")
        elif ":" in str(f):
            # Handle old format: "path:content"
            file_path = str(f).split(":", 1)[0]
        else:
            # Handle plain string format
            file_path = str(f)
        print(f"  [FILE] {base / file_path}")