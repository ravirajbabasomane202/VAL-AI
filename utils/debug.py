import sys

def debug_print(*args, **kwargs):
    if "--debug" in sys.argv:
        print("[DEBUG]", *args, **kwargs)