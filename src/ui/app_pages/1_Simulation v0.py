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

# parent_dir = Path(__file__).parent.parent.parent
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

# Main container
col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("### 📋 Simulations Overview")
    
    # Show current simulation being created (if any contexts exist)
    if len(st.session_state.current_contexts) > 0 and not st.session_state.get('simulation_submitted', False):
        with st.expander("🆕 **Current Simulation (In Progress)**", expanded=True):
            st.warning("⚠️ This simulation is being created. Click 'Submit Simulation' to finalize.")
            st.write(f"**Contexts Added:** {len(st.session_state.current_contexts)}")
            
            # Display each context
            for i, ctx in enumerate(st.session_state.current_contexts):
                st.markdown(f"**Context {i+1}:** {ctx.get('context_name', 'N/A')}")
                data_file = ctx.get('data_file', None)
                template_file = ctx.get('template_file', None)
                jarvis_files = ctx.get('jarvis_files', [])
                
                data_file_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name if data_file else 'N/A'
                template_file_name = template_file.name if hasattr(template_file, 'name') else Path(template_file).name if template_file else 'N/A'
                
                st.write(f"    - Data File: {data_file_name}")
                st.write(f"    - Template File: {template_file_name}")
                if jarvis_files:
                    st.write(f"    - Jarvis Files: {len(jarvis_files)} file(s)")
            
            st.markdown("---")
    
    # Show completed simulations
    if len(st.session_state.simulations_config) == 0:
        st.empty()
        for idx, sim in enumerate(st.session_state.simulations_config):
            with st.expander(f"🔹 {sim['simulation_name']}", expanded=False):
                st.write(f"**Type:** {sim['operation_type'].value}")
                st.write(f"**Status:** {sim['operation_status'].value}")
                # Lister tous les contextes: Context name + data file name + template file name + jarvis files count
                for i, ctx in enumerate(sim.get('contexts', [])):
                    st.markdown(f"**Context {i+1}:** {ctx.get('context_name', 'N/A')}")
                    data_file = ctx.get('data_file', None)
                    template_file = ctx.get('template_file', None)
                    jarvis_files = ctx.get('jarvis_files', [])
                    
                    data_file_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name if data_file else 'N/A'
                    template_file_name = template_file.name if hasattr(template_file, 'name') else Path(template_file).name if template_file else 'N/A'
                    
                    st.write(f"    - Data File: {data_file_name}")
                    st.write(f"    - Template File: {template_file_name}")
                    if jarvis_files:
                        st.write(f"    - Jarvis Files: {len(jarvis_files)} file(s)")
                
                
                if st.button(f"🗑️ Delete", key=f"delete_{idx}"):
                    st.session_state.simulations_config.pop(idx)
                    st.rerun()

with col_right:
    # Header with Submit button
    col_title, col_submit_btn = st.columns([2, 1])
    
    with col_title:
        st.markdown("### :material/add_circle_outline: Create New Simulation")
    
    with col_submit_btn:
        # Show Submit button only if simulation is not yet submitted
        if not st.session_state.get('simulation_submitted', False):
            # Disable button if no contexts are added or if required fields are missing
            has_contexts = len(st.session_state.current_contexts) > 0
            
            # Store sim_name, operation_type, operation_status for validation
            # These will be defined later in the form
            if st.button(
                "📤 Submit", 
                type="primary", 
                use_container_width=True,
                disabled=not has_contexts,
                key="submit_btn_top",
                help="Add at least one context to submit" if not has_contexts else "Submit simulation and load data"
            ):
                st.session_state.trigger_submit = True
                st.rerun()
    
    # Check if simulation has been submitted
    if st.session_state.get('simulation_submitted', False):
        st.success("✅ Simulation submitted successfully! The form is now locked to prevent accidental modifications.")
        st.info("💡 To create a new simulation, please refresh the page or click the 'Reset' button below.")
        
        if st.button("🔄 Create New Simulation", type="primary", use_container_width=True):
            st.session_state.simulation_submitted = False
            st.session_state.current_contexts = []
            st.session_state.show_context_form = False
            st.session_state.form_sim_name = ""
            st.session_state.form_operation_type = cst.OperationType.RETAIL
            st.session_state.form_operation_status = cst.OperationStatus.PERFORMING
            st.rerun()
        
        st.markdown("---")
    
    # Initialize trigger_submit if not exists
    if "trigger_submit" not in st.session_state:
        st.session_state.trigger_submit = False
    
    # Step 1: Simulation Name - Only show if not submitted
    if not st.session_state.get('simulation_submitted', False):
        st.markdown("#### Step 1: Simulation Information")
        
        # Initialize form values in session state if not exists
        if 'form_sim_name' not in st.session_state:
            st.session_state.form_sim_name = ""
        if 'form_operation_type' not in st.session_state:
            st.session_state.form_operation_type = cst.OperationType.RETAIL
        if 'form_operation_status' not in st.session_state:
            st.session_state.form_operation_status = cst.OperationStatus.PERFORMING
        
        sim_name = st.text_input(
            "Simulation Name *",
            placeholder="e.g., Baseline_Scenario_2024",
            help="Unique identifier for this simulation",
            value=st.session_state.form_sim_name,
            key="sim_name_input"
        )
        # Update session state with current value
        st.session_state.form_sim_name = sim_name
        
        col_type, col_status = st.columns(2)
        
        with col_type:
            operation_type = st.selectbox(
                "Operation Type *",
                options=[t for t in cst.OperationType],
                format_func=lambda x: x.value,
                index=[t for t in cst.OperationType].index(st.session_state.form_operation_type)
            )
            # Update session state with current value
            st.session_state.form_operation_type = operation_type
        
        with col_status:
            operation_status = st.selectbox(
                "Operation Status *",
                options=[s for s in cst.OperationStatus],
                format_func=lambda x: x.value,
                index=[s for s in cst.OperationStatus].index(st.session_state.form_operation_status)
            )
            # Update session state with current value
            st.session_state.form_operation_status = operation_status
        
        st.markdown("---")
        
        # Step 2: Contexts
        st.markdown("#### Step 2: Add Contexts")
    else:
        # Use stored values from session state
        sim_name = st.session_state.get('form_sim_name', None)
        operation_type = st.session_state.get('form_operation_type', None)
        operation_status = st.session_state.get('form_operation_status', None)
    
    # Initialize contexts list for current simulation
    if "current_contexts" not in st.session_state:
        st.session_state.current_contexts = []
    
    # Display existing contexts - Only allow removal if not submitted
    if len(st.session_state.current_contexts) > 0 and not st.session_state.get('simulation_submitted', False):
        st.markdown("**Current Contexts:**")
        for idx, ctx in enumerate(st.session_state.current_contexts):
            col_ctx1, col_ctx2 = st.columns([4, 1])
            with col_ctx1:
                context_name = ctx.get('context_name', f'Context {idx+1}')
                st.markdown(f"🔸 **{context_name}**")
            with col_ctx2:
                if st.button("❌", key=f"remove_ctx_{idx}"):
                    st.session_state.current_contexts.pop(idx)
                    st.rerun()
    
    # Toggle form - Hide button when form is open or when simulation is submitted
    if not st.session_state.show_context_form and not st.session_state.get('simulation_submitted', False):
        if st.button("➕ Add Context", type="primary"):
            st.session_state.show_context_form = True
            st.rerun()
    
    # Context form - Only show if simulation is not submitted
    if st.session_state.show_context_form and not st.session_state.get('simulation_submitted', False):
        # Initialize session state for selected files
        if "selected_data_file" not in st.session_state:
            st.session_state.selected_data_file = None
        if "selected_template_file" not in st.session_state:
            st.session_state.selected_template_file = None
        if "selected_jarvis_files" not in st.session_state:
            st.session_state.selected_jarvis_files = []
        
        # File selection section (OUTSIDE form)
      
        # Data File Selection
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📁 Data File**")
            
            # Radio button to choose between folder selection and upload
            data_mode = st.radio(
                "Choose method:",
                options=["📂 Select from folder", "📤 Upload file"],
                key="data_mode_radio",
                horizontal=True
            )
            
            if data_mode == "📂 Select from folder":
                # Use Sample Data as default base path for data files
                data_base_path = str(parent_dir / "sample" / "data")
                
                # Get directories
                data_dirs = get_subdirectories(data_base_path)
                
                selected_data_dir = st.selectbox(
                    "Select folder:",
                    options=data_dirs,
                    format_func=lambda x: format_dir_path(x, data_base_path),
                    key="data_folder_select"
                )
                
                # Get CSV files in selected directory
                data_files = get_files_in_directory(selected_data_dir, extensions=['.csv', '.xlsx', '.xls', '.zip'])
                
                if data_files:
                    selected_data_file = st.selectbox(
                        "Select file:",
                        options=data_files,
                        format_func=lambda x: Path(x).name,
                        key="data_file_select"
                    )
                    st.session_state.selected_data_file = selected_data_file
                    st.success(f"✅ {Path(selected_data_file).name}")
                else:
                    st.warning("No CSV/Excel files found in this folder")
                    st.session_state.selected_data_file = None
            
            else:  # Upload mode
                uploaded_data_file = st.file_uploader(
                    "Upload data file:",
                    type=['csv', 'xlsx', 'xls', 'zip'],
                    key="data_file_uploader"
                )
                
                if uploaded_data_file is not None:
                    st.session_state.selected_data_file = uploaded_data_file
                    st.success(f"✅ {uploaded_data_file.name}")
                else:
                    st.session_state.selected_data_file = None
        
        with col2:
            st.markdown("**📄 Template File**")
            
            # Radio button to choose between folder selection and upload
            template_mode = st.radio(
                "Choose method:",
                options=["📂 Select from folder", "📤 Upload file"],
                key="template_mode_radio",
                horizontal=True
            )
            
            if template_mode == "📂 Select from folder":
                # Use Templates as default base path for template files
                template_base_path = str(parent_dir / "sample" / "templates")
                
                # Get directories
                template_dirs = get_subdirectories(template_base_path)
                
                selected_template_dir = st.selectbox(
                    "Select folder:",
                    options=template_dirs,
                    format_func=lambda x: format_dir_path(x, template_base_path),
                    key="template_folder_select"
                )
                
                # Get Excel files in selected directory
                template_files = get_files_in_directory(selected_template_dir, extensions=['.xlsx', '.xls'])
                
                if template_files:
                    selected_template_file = st.selectbox(
                        "Select file:",
                        options=template_files,
                        format_func=lambda x: Path(x).name,
                        key="template_file_select"
                    )
                    st.session_state.selected_template_file = selected_template_file
                    st.success(f"✅ {Path(selected_template_file).name}")
                else:
                    st.warning("No template files found in this folder")
                    st.session_state.selected_template_file = None
            
            else:  # Upload mode
                uploaded_template_file = st.file_uploader(
                    "Upload template file:",
                    type=['xlsx', 'xls'],
                    key="template_file_uploader"
                )
                
                if uploaded_template_file is not None:
                    st.session_state.selected_template_file = uploaded_template_file
                    st.success(f"✅ {uploaded_template_file.name}")
                else:
                    st.session_state.selected_template_file = None
        
        # Jarvis files selection - Only for Non Retail
        if operation_type == cst.OperationType.NON_RETAIL:
            st.markdown("**📊 Jarvis Files**")
            
            # Radio button to choose between folder selection and upload
            jarvis_mode = st.radio(
                "Choose method:",
                options=["📂 Select from folder", "📤 Upload file"],
                key="jarvis_mode_radio",
                horizontal=True
            )
            
            if jarvis_mode == "📂 Select from folder":
                # Use Sample Data as default base path for Jarvis files
                jarvis_base_path = str(parent_dir / "sample" / "data")
                
                col_jarvis1, col_jarvis2 = st.columns([2, 2])
                
                with col_jarvis1:
                    jarvis_dirs = get_subdirectories(jarvis_base_path)
                    selected_jarvis_dir = st.selectbox(
                        "Select folder:",
                        options=jarvis_dirs,
                        format_func=lambda x: format_dir_path(x, jarvis_base_path),
                        key="jarvis_folder_select"
                    )
                
                with col_jarvis2:
                    jarvis_files = get_files_in_directory(selected_jarvis_dir, extensions=['.zip'])
                    
                    if jarvis_files:
                        selected_jarvis_file = st.selectbox(
                            "Select file to add:",
                            options=jarvis_files,
                            format_func=lambda x: Path(x).name,
                            key="jarvis_file_select"
                        )
                        
                        if st.button("➕ Add Jarvis File", key="add_jarvis_btn"):
                            if selected_jarvis_file not in st.session_state.selected_jarvis_files:
                                st.session_state.selected_jarvis_files.append(selected_jarvis_file)
                                st.success(f"✅ Added {Path(selected_jarvis_file).name}")
                                st.rerun()
                            else:
                                st.warning("File already added!")
            
            else:  # Upload mode
                uploaded_jarvis_files = st.file_uploader(
                    "Upload Jarvis file(s):",
                    type=['zip'],
                    accept_multiple_files=True,
                    key="jarvis_file_uploader"
                )
                
                if uploaded_jarvis_files:
                    # Add uploaded files to the list
                    for uploaded_file in uploaded_jarvis_files:
                        if uploaded_file not in st.session_state.selected_jarvis_files:
                            st.session_state.selected_jarvis_files.append(uploaded_file)
                    
                    st.success(f"✅ {len(uploaded_jarvis_files)} file(s) uploaded")
            
            # Display selected Jarvis files
            if len(st.session_state.selected_jarvis_files) > 0:
                st.markdown("**Selected Jarvis Files:**")
                for idx, jarvis_item in enumerate(st.session_state.selected_jarvis_files):
                    col_j1, col_j2 = st.columns([4, 1])
                    with col_j1:
                        # Handle both file paths and uploaded files
                        file_name = jarvis_item.name if hasattr(jarvis_item, 'name') else Path(jarvis_item).name
                        st.info(f"{idx+1}. {file_name}")
                    with col_j2:
                        if st.button("❌", key=f"remove_jarvis_{idx}"):
                            st.session_state.selected_jarvis_files.pop(idx)
                            st.rerun()
        else:
            # Clear Jarvis files if operation type is not Non Retail
            if len(st.session_state.selected_jarvis_files) > 0:
                st.session_state.selected_jarvis_files = []
        
        st.markdown("---")
        
        with st.form("context_form", clear_on_submit=True):
            
            # Use selected files from session state
            data_file = st.session_state.selected_data_file
            template_file = st.session_state.selected_template_file
            jarvis_files = st.session_state.selected_jarvis_files.copy() if len(st.session_state.selected_jarvis_files) > 0 else []
            
            # Context name
            st.markdown("**🏷️ Context Name**")
            context_name = st.text_input(
                "Context Name *",
                placeholder="e.g., Context_2024_Q1",
                help="Unique name for this context within the simulation",
                key="context_name_input"
            )
            
            st.markdown("---")
            
            # Display summary
            st.markdown("**📋 Context Summary**")
            
            if data_file:
                # Handle both file paths and uploaded files
                file_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name
                st.success(f"📁 Data: {file_name}")
            else:
                st.error("❌ No data file selected")
            
            if template_file:
                # Handle both file paths and uploaded files
                file_name = template_file.name if hasattr(template_file, 'name') else Path(template_file).name
                st.success(f"📄 Template: {file_name}")
            else:
                st.error("❌ No template file selected")
            
            if operation_type == cst.OperationType.NON_RETAIL and len(jarvis_files) > 0:
                st.info(f"📊 Jarvis: {len(jarvis_files)} file(s)")
            
            data_identifier = st.text_input(
                "Data Identifier (Optional)",
                placeholder="Auto-detected from file name if not provided",
                help="Custom identifier for data sharing between simulations"
            )
            
            # Submit context
            col_submit, col_cancel = st.columns([2, 1])
            
            with col_submit:
                submitted = st.form_submit_button("✅ Add This Context", type="primary", use_container_width=True)
            
            with col_cancel:
                cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
            
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
    
    # Process submit when triggered from top button
    if st.session_state.get('trigger_submit', False):
        st.session_state.trigger_submit = False
        
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
            
            # Mark simulation as submitted to lock the form
            st.session_state.simulation_submitted = True
            st.session_state.show_context_form = False
            
            st.success(f"✅ Simulation '{sim_name}' created successfully!")
            
            # Automatically load and validate data
            with st.spinner("🔄 Loading and validating data..."):
                try:
                    # Add simulation to manager
                    for ctx in simulation_config["contexts"]:
                        context_name = ctx.get("context_name", f"{simulation_config['simulation_name']}_context_{simulation_config['contexts'].index(ctx)}")
                        
                        st.session_state.manager.add_simulation(
                            simulation_name=context_name,
                            operation_type=simulation_config["operation_type"],
                            operation_status=simulation_config["operation_status"],
                            data_path=ctx["data_file"],
                            template_path=ctx["template_file"],
                            list_jarvis_file_path=ctx["jarvis_files"] if ctx["jarvis_files"] else None,
                        )
                    
                    # Prepare simulations
                    st.session_state.manager.prepare_all_simulations()
                    st.session_state.validation_complete = True
                    
                    # Save session state to persist across page refreshes
                    save_session_state(['simulations_config', 'current_contexts', 'validation_complete', 'calculation_complete', 'simulation_submitted', 'manager'])
                    
                    st.success("✅ Data loaded and validated successfully!")
                    st.info("👉 Go to Validation page to review data quality")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Error during loading and validation: {str(e)}")
                    # Rollback: remove the simulation if loading failed
                    st.session_state.simulations_config.pop()
                    st.session_state.simulation_submitted = False
            
            st.rerun()
    
    # Reset button - Show only if not submitted
    if not st.session_state.get('simulation_submitted', False):
        if st.button("🔄 Reset All", use_container_width=True, key="reset_btn_bottom"):
            st.session_state.current_contexts = []
            st.session_state.show_context_form = False
            st.session_state.form_sim_name = ""
            st.session_state.form_operation_type = cst.OperationType.RETAIL
            st.session_state.form_operation_status = cst.OperationStatus.PERFORMING
            st.rerun()

# Footer section
st.markdown("---")

if len(st.session_state.simulations_config) > 0:
    st.markdown("### 🚀 Ready to Process?")
    
    col_action1, col_action2 = st.columns([3, 1])
    
    with col_action1:
        st.metric(
            label="Total Simulations",
            value=len(st.session_state.simulations_config),
            delta=f"{sum(len(s['contexts']) for s in st.session_state.simulations_config)} contexts"
        )
    
    with col_action2:
        if st.session_state.validation_complete:
            if st.button("➡️ Validation", type="primary", use_container_width=True):
                st.switch_page("pages/2_✅_Validation.py")
        else:
            st.info("Submit a simulation to proceed")
