import streamlit as st
from src.factory import simulation_manager
def init_session_state():
    for key, default_value in {
        "manager": simulation_manager.SimulationManager(),
        "simulations_config": {},
        "current_contexts": [],
        "validation_complete": False,
        "calculation_complete": False,
        "disable_add_context": False,
        "disable_submit": False,
        "launch_simulation_submit": False,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default_value