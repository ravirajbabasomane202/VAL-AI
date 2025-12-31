def blueprint():
    print("Enter folders (comma separated):")
    folders = input().strip().split(",")

    print("Enter files (comma separated):")
    files = input().strip().split(",")

    return {
        "folders": [f.strip() for f in folders if f.strip()],
        "files": [f.strip() for f in files if f.strip()]
    }
