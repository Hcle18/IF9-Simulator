"""
Simulation Configuration Page
Create and configure ECL simulations
"""

import os
import streamlit as st
from pathlib import Path


from src.core import config as cst
from src.ui.utils import ui_components as ui
from src.ui.utils.session_persistence import save_session_state
from src.ui.utils.get_directories import get_subdirectories, format_dir_path, get_files_in_directory
from src.ui.utils.init_session_state import init_session_state
from src.ui.utils.simulation_forms import render_context_form

parent_dir = Path(__file__).parent.parent.parent.parent

st.set_page_config(
    page_title="Simulation Configuration",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS
st.markdown(ui.get_custom_css(), unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>🎯 Simulation Configuration</h1>
        <p>Create and manage your ECL calculation scenarios</p>
    </div>
""", unsafe_allow_html=True)

# Initialize session state with default values
init_session_state()

@st.dialog(title="Create New Simulation")
def create_simulation_dialog():
    # Show the dialog content to create new simulation
    sim_name = st.text_input(
        "Simulation Name *",
        placeholder="e.g., Non Retail Q2 2025",
        help="Unique identifier for this simulation",
        value=st.session_state.get("form_sim_name", None),
    )
    col_type, col_status = st.columns(2)
    with col_type:
        operation_type = st.selectbox(
            "Operation Type *",
            options=[t for t in cst.OperationType],
            format_func=lambda x: x.value,
            index=[t for t in cst.OperationType].index(st.session_state.get("form_operation_type", cst.OperationType.NON_RETAIL))
    )

    with col_status:
        operation_status = st.selectbox(
            "Operation Status *",
            options=[s for s in cst.OperationStatus],
        format_func=lambda x: x.value,
        index=[s for s in cst.OperationStatus].index(st.session_state.get("form_operation_status", cst.OperationStatus.PERFORMING)),
    )
        
    col1, col2 = st.columns([2,2])
    with col1:
        if st.button("Validate", key="submit_create_sim", icon=":material/check:", type="primary"):
            if not sim_name or sim_name.strip() == "":
                st.error("Simulation Name is required.")
            else:
                st.session_state.form_sim_name = sim_name
                st.session_state.form_operation_type = operation_type
                st.session_state.form_operation_status = operation_status
                st.rerun()
    with col2:
        if st.button("Cancel", key="cancel_create_sim", icon=":material/close:", type="secondary"):
            st.rerun()

col_left, col_right = st.columns([1,1.5])
with col_left:

    if "form_sim_name" in st.session_state:
        ui.display_simulation_summary(
            st.session_state.form_sim_name,
            st.session_state.form_operation_type,
            st.session_state.form_operation_status
        ) 
    else:
        if st.button("Create New Simulation", key="create_sim_btn", icon=":material/add:", type="primary"):
            create_simulation_dialog()      
with col_right:
    if "form_sim_name" in st.session_state:
        col_modify, col_clear = st.columns([1,1], gap='small')
        with col_modify:
            if st.button("Modify Simulation", icon=":material/edit:", type="primary", use_container_width=True):
                create_simulation_dialog()
        with col_clear:
            if st.button("Clear Simulation", icon=":material/delete:", type="secondary", use_container_width=True):
                for key in ["form_sim_name", 
                            "form_operation_type", 
                            "form_operation_status",
                            "current_contexts"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

if "form_sim_name" in st.session_state:
    st.markdown("---")
    # Add Contexts through dialog form and display list of added contexts
    if st.button("Add New Context", key="add_context_btn", icon=":material/add:", type="primary"): 
        render_context_form(st.session_state.form_operation_type, 
                            st.session_state.form_operation_status, 
                            parent_dir)
    if "current_contexts" in st.session_state and len(st.session_state.current_contexts) > 0:
        ui.display_context_summary(st.session_state.current_contexts, 
                                   st.session_state.form_operation_type, 
                                   st.session_state.form_operation_status)
        