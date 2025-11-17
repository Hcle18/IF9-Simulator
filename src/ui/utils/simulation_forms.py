"""
Reusable components for the Simulation Configuration page
Separated into functions for better maintainability
"""

import streamlit as st
from pathlib import Path
from src.core import config as cst
from src.ui.utils.get_directories import get_subdirectories, format_dir_path, get_files_in_directory

def render_step1_simulation_info():
    """Render Step 1: Simulation Information"""
    st.markdown("#### Step 1: Simulation Information")
    
    sim_name = st.text_input(
        "Simulation Name *",
        placeholder="e.g., Baseline_Scenario_2024",
        help="Unique identifier for this simulation",
        key="sim_name_input"
    )
    
    col_type, col_status = st.columns(2)
    
    with col_type:
        operation_type = st.selectbox(
            "Operation Type *",
            options=[t for t in cst.OperationType],
            format_func=lambda x: x.value,
            key="operation_type_select"
        )
    
    with col_status:
        operation_status = st.selectbox(
            "Operation Status *",
            options=[s for s in cst.OperationStatus],
            format_func=lambda x: x.value,
            key="operation_status_select"
        )
    
    return sim_name, operation_type, operation_status


def render_existing_contexts():
    """Display list of existing contexts for current simulation"""
    if len(st.session_state.current_contexts) > 0:
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


def render_file_selector(label, file_type, extensions, 
                         base_path_suffix, key_prefix, parent_dir):
    """
    Render a file selector with folder browsing or upload options
    
    Args:
        label: Display label for the file selector
        file_type: Type of file (for display)
        extensions: List of allowed extensions (e.g., ['.csv', '.xlsx'])
        base_path_suffix: Path suffix to append to parent_dir (e.g., "sample/data")
        key_prefix: Unique prefix for widget keys
        parent_dir: Parent directory path
    Returns:
        Selected file (path or uploaded file object)
    """
    
    st.markdown(f"**{label}**")
    
    # Radio button to choose between folder selection and upload
    mode = st.radio(
        "Choose method:",
        options=["📂 Select from folder", "📤 Upload file"],
        key=f"{key_prefix}_mode_radio",
        horizontal=True
    )
    
    if mode == "📂 Select from folder":
        # Use base path for files
        base_path = str(parent_dir / base_path_suffix)
        
        # Get directories
        dirs = get_subdirectories(base_path)
        
        selected_dir = st.selectbox(
            "Select folder:",
            options=dirs,
            format_func=lambda x: format_dir_path(x, base_path),
            key=f"{key_prefix}_folder_select",
            width="stretch"
        )
        
        # Get files in selected directory
        files = get_files_in_directory(selected_dir, extensions=extensions)
        
        if files:
            selected_file = st.selectbox(
                "Select file:",
                options=files,
                format_func=lambda x: Path(x).name,
                key=f"{key_prefix}_file_select"
            )
            st.success(f"✅ {Path(selected_file).name}")
            return selected_file
        else:
            st.warning(f"No {file_type} files found in this folder")
            return None
    
    else:  # Upload mode
        uploaded_file = st.file_uploader(
            f"Upload {file_type} file:",
            type=[ext.replace('.', '') for ext in extensions],
            key=f"{key_prefix}_file_uploader"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ {Path(uploaded_file.name).name} uploaded")
            return uploaded_file
        else:
            return None
        
@st.dialog(title="Create New Context")
def render_context_form(operation_type, operation_status, parent_dir):
    """
    Render the context creation form
    
    Args:
        operation_type: Current operation type
        operation_status: Current operation status
        parent_dir: Parent directory path
    
    Returns:
        Tuple of (data_file, template_file, jarvis_files, context_name, data_identifier, submitted, cancelled)
    """
    # Initialize session state for selected files
    if "selected_data_file" not in st.session_state:
        st.session_state.selected_data_file = None
    if "selected_template_file" not in st.session_state:
        st.session_state.selected_template_file = None
    if "selected_jarvis_files" not in st.session_state:
        st.session_state.selected_jarvis_files = []
    st.markdown(
        """
        <style>
        div[data-testid="stDialog"] div[role="dialog"] {
        width: 80%; /* Adjust width as a percentage of the page */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Add Context name
    context_name = st.text_input(
        "**Context Name** *",
        placeholder="e.g., Context Prod",
        help="Unique name for this context within the simulation",
        key="context_name_input"
    )
    
    # Data and Template File Selection
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.selected_data_file = render_file_selector(
            label="📁 Data File",
            file_type="CSV/Excel/Zip",
            extensions=['.csv', '.xlsx', '.xls', '.zip'],
            base_path_suffix="sample/data",
            key_prefix="data",
            parent_dir=parent_dir,
        )
    
    with col2:
        st.session_state.selected_template_file = render_file_selector(
            label="📄 Template File",
            file_type="Excel",
            extensions=['.xlsx', '.xls'],
            base_path_suffix="sample/templates",
            key_prefix="template",
            parent_dir=parent_dir
        )
    
    # Jarvis files selection - Only for Non Retail
    if operation_type == cst.OperationType.NON_RETAIL and operation_status == cst.OperationStatus.PERFORMING:
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
                jarvis_files = get_files_in_directory(selected_jarvis_dir, extensions=['.zip', '.csv'])
                
                if jarvis_files:
                    selected_jarvis_file = st.selectbox(
                        "Select file to add:",
                        options=jarvis_files,
                        format_func=lambda x: Path(x).name,
                        key="jarvis_file_select"
                    )
                    
                    if st.button("Add this Jarvis File", key="add_jarvis_btn", icon=":material/add:", type="secondary"):
                        if selected_jarvis_file not in st.session_state.selected_jarvis_files:
                            st.session_state.selected_jarvis_files.append(selected_jarvis_file)
                            st.success(f"Added {Path(selected_jarvis_file).name}", icon=":material/check:")
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
                    def remove_jarvis_files(idx):
                        st.session_state.selected_jarvis_files = [
                            item for i, item in enumerate(st.session_state.selected_jarvis_files) if i != idx
                        ]
                    st.button("❌", key=f"remove_jarvis_{idx}", on_click=lambda idx=idx: remove_jarvis_files(idx))
                    # if st.button("❌", key=f"remove_jarvis_{idx}"):
                    #     st.session_state.selected_jarvis_files.pop(idx)
                        #st.rerun()
    else:
        # Clear Jarvis files if not Non Retail Performing
        if len(st.session_state.selected_jarvis_files) > 0:
            st.session_state.selected_jarvis_files = []
   
    # Context form
    with st.form("context_form", clear_on_submit=True):
        # Use selected files from session state
        data_file = st.session_state.selected_data_file
        template_file = st.session_state.selected_template_file
        jarvis_files = st.session_state.selected_jarvis_files
        
        # Display summary
        st.markdown("**📋 Context Summary**")
        
        if data_file:
            file_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name
            st.success(f"📁 Data: {file_name}")
        else:
            st.error("❌ No data file selected")
        
        if template_file:
            file_name = template_file.name if hasattr(template_file, 'name') else Path(template_file).name
            st.success(f"📄 Template: {file_name}")
        else:
            st.error("❌ No template file selected")
        
        if (operation_type == cst.OperationType.NON_RETAIL and 
            operation_status == cst.OperationStatus.PERFORMING):
            if jarvis_files and len(jarvis_files) > 0:
                
                file_names = [f.name if hasattr(f, 'name') else Path(f).name for f in jarvis_files]
                st.success(f"📊 Jarvis files: {', '.join(file_names)}")
            else:
                st.error("❌ No Jarvis files selected")
        
        # Submit context
        col_submit, col_cancel = st.columns([2, 1])
        
        with col_submit:
            submitted = st.form_submit_button("✅ Add This Context", type="primary", use_container_width=True)
        
        with col_cancel:
            cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submitted:
            submitted_contexts = [ctx['context_name'] for ctx in st.session_state.current_contexts]
            if not context_name:
                st.error("❌ Context name is required!")
            elif context_name in submitted_contexts:
                st.error("❌ Context name must be unique!")
            elif not data_file or not template_file:
                st.error("❌ Data file and template file are required!")
            elif (operation_type == cst.OperationType.NON_RETAIL and 
                  operation_status == cst.OperationStatus.PERFORMING and
                  (not jarvis_files or len(jarvis_files) == 0)):
                st.error("❌ Jarvis files are required for Non Retail Performing operation!")
            else:
                # Add context to session state and display in main page
                new_context = {
                    'context_name': context_name,
                    'data_file': data_file,
                    'template_file': template_file,
                    'jarvis_files': jarvis_files
                }
                st.session_state.current_contexts.append(new_context)
                st.success(f"✅ Context '{context_name}' added successfully!", icon=":material/check:")
                st.rerun()

        if cancelled:
            st.rerun()        
        
        # return data_file, template_file, jarvis_files, context_name, submitted, cancelled

def display_context_details(context):
    pass

def render_step3_submit(sim_name, operation_type, operation_status):
    """
    Render Step 3: Submit Simulation
    
    Args:
        sim_name: Simulation name
        operation_type: Operation type
        operation_status: Operation status
    
    Returns:
        Tuple of (submitted, reset)
    """
    st.markdown("#### Step 3: Submit Simulation")
    
    col_submit1, col_submit2 = st.columns([3, 1])
    
    with col_submit1:
        submitted = st.button("📤 Submit Simulation", type="primary", use_container_width=True, key="submit_simulation_btn")
    
    with col_submit2:
        reset = st.button("🔄 Reset", use_container_width=True, key="reset_simulation_btn")
    
    return submitted, reset
