"""
Simulation Configuration Page
Create and configure ECL simulations
"""

import logging
import streamlit as st
from pathlib import Path

from src.core import config as cst
from src.ui.utils import ui_components as ui
from src.ui.utils.session_persistence import save_session_state
from src.ui.utils.get_directories import get_subdirectories, format_dir_path, get_files_in_directory
from src.ui.utils.init_session_state import init_session_state
from src.ui.utils.simulation_forms import (display_context_summary, 
                                           display_simulation_summary,
                                           create_simulation_dialog,
                                           render_context_form,
                                           render_simulation_submit)

st.set_page_config(
    page_title="Simulation Configuration",
    page_icon="🎯",
    layout="wide",
    menu_items={
        'Get Help': 'https://example.com/help',
    }
)

logger = logging.getLogger(__name__)  
parent_dir = Path(__file__).parent.parent.parent.parent

# Custom CSS
st.markdown(ui.get_custom_css(), unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>🎯 Simulation Configuration</h1>
        <p>Create and manage ECL calculation scenarios</p>
    </div>
""", unsafe_allow_html=True)

# Initialize session state with default values
init_session_state()

# ============================== #
# Simulation Configuration Form  #
# ============================== #

if "form_sim_name" not in st.session_state:
    if st.button("Create New Simulation", icon=":material/add_circle:", type="primary"):
        create_simulation_dialog()
else:
    display_simulation_summary(st.session_state.form_sim_name,
                               st.session_state.form_operation_type,
                               st.session_state.form_operation_status,
                               st.session_state.current_contexts)
    
    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.validation_complete:
        # Validation complete - don't show Add Context button or submit form
        pass
    elif st.session_state.launch_simulation_submit:
        # Simulation submitted - show submit form
        render_simulation_submit()
    else:
        # Initial state - show Add Context button
        if st.button("Add Context", icon=":material/add_circle:", 
                     type="primary", use_container_width=False,
                     disabled=st.session_state.disable_add_context):
            render_context_form(st.session_state.form_operation_type,
                                st.session_state.form_operation_status)

        st.markdown("<br>", unsafe_allow_html=True)

        if len(st.session_state.get("current_contexts", [])) > 0:
            st.info("You can add more contexts or submit the simulation for validation.",
                    icon=":material/info:")

    # Contexts Summary
    display_context_summary(st.session_state.current_contexts,
                            st.session_state.form_operation_type,
                            st.session_state.form_operation_status)

# Display results after validation is complete
if st.session_state.validation_complete:
    st.success("✅ Simulation is configured and ready for validation !", 
                icon=":material/check_circle:")
    # Invite user to proceed to calculation page
    st.info("Proceed to the **Validation** page to run ECL computations based on this configuration.",
            icon=":material/info:")
    if st.button("Go to Validation Page", use_container_width=False, type="primary"):
        st.switch_page("app_pages/2_Validation_REFACTORED.py")
