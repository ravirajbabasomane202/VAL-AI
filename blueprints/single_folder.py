def blueprint():
    name = input("Folder name: ").strip()
    return {
        "folders": [name],
        "files": []
    }
