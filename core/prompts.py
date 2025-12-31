from pathlib import Path

def ask_project_location():
    path_str = input("Enter base location (absolute path): ").strip()
    if path_str.startswith('"') and path_str.endswith('"'):
        path_str = path_str[1:-1]
    p = Path(path_str)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ask_project_name():
    return input("Enter project name: ").strip()

def ask_project_type():
    print("\nWhat do you want to create?")
    print("1. Single folder")
    print("2. Custom multi-folder")
    print("3. Flask project")
    print("4. Flutter project")
    return input("Choice: ").strip()

def ask_ai_request():
    print("\nDescribe the project you want (or paste a tree structure).")
    print("Type 'DONE' on a new line to finish:")
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "DONE":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines).strip()
