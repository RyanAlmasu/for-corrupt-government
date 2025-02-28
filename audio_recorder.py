# audio_recorder.py (file baru)
import streamlit.components.v1 as components

def audio_recorder():
    return components.declare_component(
        "audio_recorder",
        path="./frontend"
    )