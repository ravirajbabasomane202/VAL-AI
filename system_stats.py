import psutil
import os

def get_system_health():
    try:
        return {
            "cpu": psutil.cpu_percent(interval=None),
            "memory": psutil.virtual_memory().percent,
            "processes": len(psutil.pids())
        }
    except Exception:
        return {
            "cpu": 0,
            "memory": 0,
            "processes": 0
        }