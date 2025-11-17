"""
Simulation Configuration Page - Refactored
Create and configure ECL simulations with a clean, modular structure
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent

# Add utils to path
utils_dir = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(utils_dir))

from src.core import config as cst
import ui_components as ui
from simulation_form_components import (
    render_step1_simulation_info,
    render_existing_contexts,
    render_context_form,
    render_step3_submit
)
from session_persistence import save_session_state

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

# Initialize session state
if "simulations_config" not in st.session_state:
    st.session_state.simulations_config = []

if "show_context_form" not in st.session_state:
    st.session_state.show_context_form = False

if "show_creation_form" not in st.session_state:
    st.session_state.show_creation_form = False

if "current_contexts" not in st.session_state:
    st.session_state.current_contexts = []

# Main container
col_left, col_right = st.columns([1, 2])

# LEFT COLUMN: Simulations Overview
with col_left:
    st.markdown("### 📋 Simulations Overview")
    
    if len(st.session_state.simulations_config) == 0:
        st.info("No simulations created yet. Click 'Create New Simulation' to start.")
    else:
        for idx, sim in enumerate(st.session_state.simulations_config):
            with st.expander(f"🔹 {sim['simulation_name']}", expanded=False):
                st.write(f"**Type:** {sim['operation_type'].value}")
                st.write(f"**Status:** {sim['operation_status'].value}")
                st.write(f"**Contexts:** {len(sim['contexts'])}")
                
                if st.button(f"🗑️ Delete", key=f"delete_{idx}"):
                    st.session_state.simulations_config.pop(idx)
                    save_session_state(['simulations_config'])
                    st.rerun()

# RIGHT COLUMN: Create New Simulation
with col_right:
    st.markdown("### ➕ Create New Simulation")
    
    # Show "Create New Simulation" button if form is not open
    if not st.session_state.show_creation_form:
        if st.button("🆕 Create New Simulation", type="primary", use_container_width=True):
            st.session_state.show_creation_form = True
            st.rerun()
        st.info("👆 Click the button above to start creating a new simulation")

# CREATION FORM: Only show if activated
if st.session_state.show_creation_form:
    with col_right:
        # Step 1: Simulation Information
        sim_name, operation_type, operation_status = render_step1_simulation_info()
        
        st.markdown("---")
        
        # Step 2: Add Contexts
        st.markdown("#### Step 2: Add Contexts")
        
        # Display existing contexts
        render_existing_contexts()
        
        # Toggle form - Hide button when form is open
        if not st.session_state.show_context_form:
            if st.button("➕ Add Context", type="primary"):
                st.session_state.show_context_form = True
                st.rerun()
        
        # Context form
        if st.session_state.show_context_form:
            data_file, template_file, jarvis_files, context_name, data_identifier, submitted, cancelled = render_context_form(
                operation_type, parent_dir
            )
            
            if cancelled:
                st.session_state.show_context_form = False
                st.rerun()
            
            if submitted:
                if not context_name:
                    st.error("❌ Context name is required!")
                elif not data_file or not template_file:
                    st.error("❌ Data file and template file are required!")
                else:
                    context = {
                        "context_name": context_name,
                        "data_file": data_file,
                        "template_file": template_file,
                        "jarvis_files": jarvis_files if jarvis_files else [],
                        "data_identifier": data_identifier if data_identifier else None
                    }
                    st.session_state.current_contexts.append(context)
                    st.session_state.show_context_form = False
                    st.success(f"✅ Context '{context_name}' added successfully!")
                    st.rerun()
        
        st.markdown("---")
        
        # Step 3: Submit Simulation - Only show if not in "add context" mode
        if not st.session_state.show_context_form:
            submitted, reset = render_step3_submit(sim_name, operation_type, operation_status)
            
            if submitted:
                # Validation
                if not sim_name:
                    st.error("❌ Simulation name is required!")
                elif len(st.session_state.current_contexts) == 0:
                    st.error("❌ At least one context is required!")
                else:
                    # Add simulation to config
                    simulation_config = {
                        "simulation_name": sim_name,
                        "operation_type": operation_type,
                        "operation_status": operation_status,
                        "contexts": st.session_state.current_contexts.copy()
                    }
                    
                    st.session_state.simulations_config.append(simulation_config)
                    st.session_state.current_contexts = []
                    st.session_state.show_context_form = False
                    st.session_state.show_creation_form = False
                    
                    # Save session state to persist across page refreshes
                    save_session_state(['simulations_config', 'current_contexts', 'validation_complete', 'calculation_complete'])
                    
                    st.success(f"✅ Simulation '{sim_name}' created successfully!")
                    st.balloons()
                    st.rerun()
            
            if reset:
                st.session_state.current_contexts = []
                st.session_state.show_context_form = False
                st.rerun()
        
        # Cancel button to close the creation form
        st.markdown("---")
        if st.button("❌ Cancel Simulation Creation", use_container_width=True):
            st.session_state.show_creation_form = False
            st.session_state.current_contexts = []
            st.session_state.show_context_form = False
            st.rerun()

# Footer section
st.markdown("---")

if len(st.session_state.simulations_config) > 0:
    st.markdown("### 🚀 Ready to Process?")
    
    col_action1, col_action2, col_action3 = st.columns([2, 2, 1])
    
    with col_action1:
        st.metric(
            label="Total Simulations",
            value=len(st.session_state.simulations_config),
            delta=f"{sum(len(s['contexts']) for s in st.session_state.simulations_config)} contexts"
        )
    
    with col_action2:
        if st.button("🎬 Load & Validate Data", type="primary", use_container_width=True):
            # Add simulations to manager
            with st.spinner("Loading simulations..."):
                try:
                    for sim_config in st.session_state.simulations_config:
                        for ctx in sim_config["contexts"]:
                            # Use the context's own name
                            context_name = ctx.get("context_name", f"{sim_config['simulation_name']}_context_{sim_config['contexts'].index(ctx)}")
                            
                            st.session_state.manager.add_simulation(
                                simulation_name=context_name,
                                operation_type=sim_config["operation_type"],
                                operation_status=sim_config["operation_status"],
                                data_file_path=ctx["data_file"],
                                template_file_path=ctx["template_file"],
                                list_jarvis_file_path=ctx["jarvis_files"] if ctx["jarvis_files"] else None,
                                data_identifier=ctx["data_identifier"]
                            )
                    
                    # Prepare simulations
                    st.session_state.manager.prepare_all_simulations()
                    st.session_state.validation_complete = True
                    
                    # Save session state
                    save_session_state(['simulations_config', 'validation_complete', 'manager'])
                    
                    st.success("✅ All simulations loaded and validated!")
                    st.info("👉 Go to Validation page to review data quality")
                    
                except Exception as e:
                    st.error(f"❌ Error during loading: {str(e)}")
                    st.exception(e)
    
    with col_action3:
        if st.session_state.get("validation_complete", False):
            if st.button("➡️ Validation", use_container_width=True):
                st.switch_page("pages/2_✅_Validation.py")
