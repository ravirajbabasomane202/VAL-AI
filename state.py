import time
import streamlit as st

class LiveState:
    last_refresh = time.time()
    listening = False
    agent_running = False

STATE = LiveState()

def auto_refresh(interval=2):
    """Auto-refresh the page every `interval` seconds"""
    time.sleep(interval)
    st.rerun()