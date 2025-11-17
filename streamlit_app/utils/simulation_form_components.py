"""
Reusable components for the Simulation Configuration page
Separated into functions for better maintainability
"""

import streamlit as st
from pathlib import Path
from src.core import config as cst


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


def get_subdirectories(base_path):
    """Get all subdirectories from a base path with relative paths"""
    try:
        path = Path(base_path)
        if not path.exists():
            return []
        
        # Folders to exclude
        exclude_folders = {'__pycache__', '.git', '.vscode', '.idea',
                          'node_modules', '.pytest_cache', '__MACOSX',
                          '.venv'}
        
        dirs = [str(base_path)]  # Include base path itself
        for item in path.rglob("*"):
            if item.is_dir():
                # Skip if any part of the path is in exclude list
                if not any(excluded in item.parts for excluded in exclude_folders):
                    dirs.append(str(item))
        return sorted(dirs)
    except Exception:
        return [str(base_path)]


def format_dir_path(dir_path, base_path):
    """Format directory path to show hierarchy"""
    try:
        rel_path = Path(dir_path).relative_to(Path(base_path))
        if str(rel_path) == ".":
            return f"📂 {Path(base_path).name}"
        else:
            # Show relative path with hierarchy
            return f"📂 {Path(base_path).name}/{rel_path}"
    except ValueError:
        # If not relative, just show the name
        return f"📂 {Path(dir_path).name}"


def get_files_in_directory(directory, extensions=None):
    """Get all files in a directory with optional extension filter"""
    try:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            return []
        files = []
        for item in path.iterdir():
            if item.is_file():
                if extensions is None or item.suffix.lower() in extensions:
                    files.append(str(item))
        return sorted(files)
    except Exception:
        return []


def render_file_selector(label, file_type, extensions, base_path_suffix, key_prefix):
    """
    Render a file selector with folder browsing or upload options
    
    Args:
        label: Display label for the file selector
        file_type: Type of file (for display)
        extensions: List of allowed extensions (e.g., ['.csv', '.xlsx'])
        base_path_suffix: Path suffix to append to parent_dir (e.g., "sample/data")
        key_prefix: Unique prefix for widget keys
    
    Returns:
        Selected file (path or uploaded file object)
    """
    parent_dir = Path(__file__).parent.parent.parent
    
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
            key=f"{key_prefix}_folder_select"
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
            st.success(f"✅ {uploaded_file.name}")
            return uploaded_file
        else:
            return None


def render_context_form(operation_type, parent_dir):
    """
    Render the context creation form
    
    Args:
        operation_type: Current operation type
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
    
    # Data and Template File Selection
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.selected_data_file = render_file_selector(
            label="📁 Data File",
            file_type="CSV/Excel",
            extensions=['.csv', '.xlsx', '.xls'],
            base_path_suffix="sample/data",
            key_prefix="data"
        )
    
    with col2:
        st.session_state.selected_template_file = render_file_selector(
            label="📄 Template File",
            file_type="Excel/YAML",
            extensions=['.xlsx', '.xls', '.yaml', '.yml'],
            base_path_suffix="sample/templates",
            key_prefix="template"
        )
    
    # Jarvis files selection - Only for Non Retail
    if operation_type == cst.OperationType.NON_RETAIL:
        st.markdown("**📊 Jarvis Files (Optional)**")
        
        # Simple file uploader for Jarvis files
        uploaded_jarvis_files = st.file_uploader(
            "Upload Jarvis file(s):",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="jarvis_file_uploader"
        )
        
        if uploaded_jarvis_files:
            st.session_state.selected_jarvis_files = list(uploaded_jarvis_files)
            st.success(f"✅ {len(uploaded_jarvis_files)} file(s) uploaded")
        else:
            st.session_state.selected_jarvis_files = []
    else:
        st.session_state.selected_jarvis_files = []
    
    st.markdown("---")
    
    # Context form
    with st.form("context_form", clear_on_submit=True):
        # Use selected files from session state
        data_file = st.session_state.selected_data_file
        template_file = st.session_state.selected_template_file
        jarvis_files = st.session_state.selected_jarvis_files.copy()
        
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
            file_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name
            st.success(f"📁 Data: {file_name}")
        else:
            st.error("❌ No data file selected")
        
        if template_file:
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
        
        return data_file, template_file, jarvis_files, context_name, data_identifier, submitted, cancelled


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
