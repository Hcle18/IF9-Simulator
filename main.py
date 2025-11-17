import streamlit as st
import os
import pandas as pd

# st.title("📁 Multi-level Folder Browser")

# --- Set base directory (server-side) ---
BASE_DIR = os.path.abspath(".")  # Start from the project root

# Keep track of current path using Streamlit session state
if "current_path" not in st.session_state:
    st.session_state.current_path = BASE_DIR


def go_to_folder(subfolder):
    """Navigate into a subfolder."""
    st.session_state.current_path = os.path.join(st.session_state.current_path, subfolder)
    st.rerun()


def go_up():
    """Navigate one level up."""
    if st.session_state.current_path != BASE_DIR:
        st.session_state.current_path = os.path.dirname(st.session_state.current_path)
        st.rerun()

def go_to_root():
    """Navigate to root."""
    if st.session_state.current_path != BASE_DIR:
        st.session_state.current_path = BASE_DIR
        st.rerun()


# --- Display current path ---
st.write(f"📂 **Current directory:** `{st.session_state.current_path}`")

# --- Get directories and files ---
try:
    items = os.listdir(st.session_state.current_path)
except FileNotFoundError:
    st.error("Folder not found.")
    st.stop()

dirs = [d for d in items if os.path.isdir(os.path.join(st.session_state.current_path, d))]
files = [f for f in items if os.path.isfile(os.path.join(st.session_state.current_path, f))]

# --- Navigation buttons ---
col1, col2 = st.columns([2, 1])
with col1:
    if st.button("🏠 Go to Root"):
        go_to_root()
    if st.button("⬆️ Go Up"):
        go_up()

# --- Folder navigation ---
st.subheader("📁 Folders")
for d in dirs:
    if st.button(f"📂 {d}"):
        go_to_folder(d)

# --- File selection ---
st.subheader("📄 Files")
selected_file = st.selectbox("Select a file", files)

if selected_file:
    file_path = os.path.join(st.session_state.current_path, selected_file)
    st.write(f"**Selected file:** `{file_path}`")
