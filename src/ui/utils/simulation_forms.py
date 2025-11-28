def reset_context_indices_and_paths(operation_type, operation_status):
    """Reset default indices and base paths when operation type/status changes"""
    st.session_state.base_path = str(cst.CONFIG_DATA_DIR.get((operation_type, operation_status)))
    st.session_state.default_index = 0
    st.session_state.jarvis_base_path = str(cst.CONFIG_DATA_DIR.get((operation_type, operation_status)))
    st.session_state.default_jarvis_index = 0
    st.session_state.template_base_path = str(cst.CONFIG_TEMPLATES_DIR.get((operation_type, operation_status)))
    st.session_state.default_template_index = 0
    for tpl_key, tpl_config in TEMPLATE_TYPES.items():
        base_key = tpl_config.get('base_key', tpl_key)
        st.session_state[f"default_template_index_{base_key}"] = 0
    if "folder_selection_version" not in st.session_state:
        st.session_state.folder_selection_version = 0
    st.session_state.folder_selection_version += 1
"""
Reusable components for the Simulation Configuration page
Separated into functions for better maintainability
"""

import logging
import streamlit as st
from pathlib import Path
import threading
import time
import warnings
from src.core import config as cst
from src.templates.template_loader import registry_loader
from src.factory import simulation_manager
from src.ui.utils.get_directories import get_subdirectories, format_dir_path, get_files_in_directory
logger = logging.getLogger(__name__)  

parent_dir = Path(__file__).parent.parent.parent.parent
sample_dir = Path(__file__).parent.parent.parent.parent / "sample"  

@st.dialog(title="Create New Simulation")
def create_simulation_dialog():
    st.markdown(
        """
        <style>
        div[data-testid="stDialog"] div[role="dialog"] {
        width: 50%; /* Adjust width as a percentage of the page */
        }
        
        /* Style pour les boutons primary (rouge) */
        div[data-testid="stDialog"] button[kind="primary"] {
            background-color: #e74c3c !important;
            border-color: #e74c3c !important;
            color: white !important;
        }
        
        div[data-testid="stDialog"] button[kind="primary"]:hover {
            background-color: #d62c1a !important;
            border-color: #d62c1a !important;
        }
        
        /* Style pour les boutons secondary (bleu) */
        div[data-testid="stDialog"] button[kind="secondary"] {
            background-color: #007bff !important;
            border-color: #007bff !important;
            color: white !important;
        }
        
        div[data-testid="stDialog"] button[kind="secondary"]:hover {
            background-color: #0056b3 !important;
            border-color: #004085 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

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
            
            # Check whether operation type/status is supported 
            # in templates registry loader
            if (operation_type, operation_status) not in registry_loader:
                st.error(f"❌ Operation Type '{operation_type.value}' with Status '{operation_status.value}' is not supported yet.")
            elif not sim_name or sim_name.strip() == "":
                st.error("❌ Simulation name is required!")
            elif (
                ("form_operation_type" in st.session_state and operation_type != st.session_state["form_operation_type"])
                or ("form_operation_status" in st.session_state and operation_status != st.session_state["form_operation_status"])
                ) and len(st.session_state.get("current_contexts", [])) > 0:
                    
                    st.warning("Changing operation type/status will reset existing contexts.", icon=":material/warning:")

                    def clear_contexts():
                        st.session_state.current_contexts = []
                        st.session_state.form_operation_type = operation_type
                        st.session_state.form_operation_status = operation_status
                        st.session_state.form_sim_name = sim_name
                        # Added success message here
                        st.success("✅ Existing contexts cleared.", icon=":material/check:")
                        # Define the function above where it is used
                        st.session_state.clear_rerun = True  # Set flag to rerun after clearing
                    
                    col_clear_yes, col_clear_no = st.columns(2)
                    with col_clear_yes:
                        st.button("Yes, clear contexts", icon=":material/check:", 
                                  on_click=clear_contexts, type="primary")
                    with col_clear_no:
                        st.button("No, keep contexts", icon=":material/close:", 
                                 type="secondary", on_click=lambda: setattr(st.session_state, 'clear_rerun', True))
            else:
                st.session_state.form_operation_type = operation_type
                st.session_state.form_operation_status = operation_status
                st.session_state.form_sim_name = sim_name
                # Reset indices and paths for new operation type/status
                reset_context_indices_and_paths(operation_type, operation_status)
                st.rerun()

    if st.session_state.get("clear_rerun", False):
        del st.session_state["clear_rerun"]
        st.rerun()
    with col2:
        if st.button("Cancel", key="cancel_create_sim", icon=":material/close:", type="secondary"):
            st.rerun()


# Template types configuration (shared across functions)
TEMPLATE_TYPES = {
    'PD *': {'label': '📊 PD (Probability of Default)', 'required': True, 'base_key': 'PD'},
    'LGD *': {'label': '💰 LGD (Loss Given Default)', 'required': True, 'base_key': 'LGD'},
    'CCF': {'label': '🔄 CCF (Credit Conversion Factor)', 'required': False, 'base_key': 'CCF'},
    'Staging': {'label': '🎯 Staging Rules', 'required': False, 'base_key': 'Staging'},
    'Segmentation': {'label': '📦 Segmentation Rules', 'required': False, 'base_key': 'Segmentation'},
    'Mapping Time Steps': {'label': '⏳ Mapping Time Steps', 'required': False, 'base_key': 'Mapping Time Steps'}
}

# Example template paths - Chemins complets des fichiers d'exemple à télécharger
# Ces fichiers sont dans un répertoire complètement différent des templates à charger
EXAMPLE_TEMPLATE_PATHS = {
    'PD': sample_dir / 'templates' / 'Template_outil_V1.xlsx',
    'LGD': sample_dir / 'sample' / 'templates' / 'example_LGD_template.xlsx',
    'CCF': sample_dir / 'sample' / 'templates' / 'example_CCF_template.xlsx',
    'Staging': sample_dir / 'sample' / 'templates' / 'example_Staging_template.xlsx',
    'Segmentation': sample_dir / 'sample' / 'templates' / 'example_Segmentation_template.xlsx',
    'Mapping Time Steps': sample_dir / 'sample' / 'templates' / 'example_Mapping_Time_Steps_template.xlsx'
}


def _initialize_context_session_state(operation_type, operation_status):
    # Initialiser les index pour chaque template type (base_key)
    for tpl_key, tpl_config in TEMPLATE_TYPES.items():
        base_key = tpl_config.get('base_key', tpl_key)
        key_name = f"default_template_index_{base_key}"
        if key_name not in st.session_state:
            st.session_state[key_name] = 0


    """Initialize session state for context form"""

    if "base_path" not in st.session_state:
        st.session_state.base_path = str(cst.CONFIG_DATA_DIR.get((operation_type, operation_status)))

    if "sub_dirs" not in st.session_state:
        st.session_state.sub_dirs = get_subdirectories(st.session_state.base_path)

    if "default_index" not in st.session_state:
        st.session_state.default_index = 0
    
    # Initialize jarvis base path and default index
    if "jarvis_base_path" not in st.session_state:
        st.session_state.jarvis_base_path = str(cst.CONFIG_DATA_DIR.get((operation_type, operation_status)))
    
    if "default_jarvis_index" not in st.session_state:
        st.session_state.default_jarvis_index = 0
    
    # Initialize template base path and default index
    if "template_base_path" not in st.session_state:
        st.session_state.template_base_path = str(cst.CONFIG_TEMPLATES_DIR.get((operation_type, operation_status)))
    
    if "default_template_index" not in st.session_state:
        st.session_state.default_template_index = 0
    
    # Version counter to force widget refresh without rerun
    if "folder_selection_version" not in st.session_state:
        st.session_state.folder_selection_version = 0

    if "selected_data_file" not in st.session_state:
        st.session_state.selected_data_file = None
    
    # Template mode: 'single' or 'multiple'
    if "template_mode" not in st.session_state:
        st.session_state.template_mode = 'single'
    
    # Single template file (classic mode)
    if "selected_single_template_file" not in st.session_state:
        st.session_state.selected_single_template_file = None
    
    # Multiple template files (new mode)
    if "selected_template_files" not in st.session_state:
        st.session_state.selected_template_files = {key: [] for key in TEMPLATE_TYPES.keys()}
    
    if "selected_jarvis_files" not in st.session_state:
        st.session_state.selected_jarvis_files = []


def update_scope_folder():
    """Update folder indexes based on selected scope"""
    selected_scope = st.session_state.get("selected_scope", "")
    
    # Don't update if empty option is selected
    if not selected_scope or selected_scope == "":
        return
    
    if st.session_state.get("base_path"):
        # === Update Data Folder Index ===
        base_path = st.session_state.base_path
        sub_dirs = get_subdirectories(base_path)
        keywords = str(Path(base_path) / selected_scope / "PROD")
        select_dirs = [d for d in sub_dirs if keywords in d]
        sorted_dirs = sorted(select_dirs, reverse=True)
        
        if sorted_dirs:
            st.session_state.default_index = sub_dirs.index(sorted_dirs[0])
        else:
            st.session_state.default_index = 0
        
        # === Update Jarvis Folder Index ===
        if "jarvis_base_path" in st.session_state:
            jarvis_base_path = st.session_state.jarvis_base_path
            jarvis_sub_dirs = get_subdirectories(jarvis_base_path)
            jarvis_keywords = str(Path(jarvis_base_path) / selected_scope / "PROD")
            jarvis_select_dirs = [d for d in jarvis_sub_dirs if jarvis_keywords in d]
            jarvis_sorted_dirs = sorted(jarvis_select_dirs, reverse=True)
            
            if jarvis_sorted_dirs:
                st.session_state.default_jarvis_index = jarvis_sub_dirs.index(jarvis_sorted_dirs[0])
            else:
                st.session_state.default_jarvis_index = 0
        
        # === Update Template Folder Index for each base_key ===
        if "template_base_path" in st.session_state:
            template_base_path = st.session_state.template_base_path
            template_sub_dirs = get_subdirectories(template_base_path)
            template_keywords = str(Path(template_base_path) / selected_scope / "PROD")
            
            if st.session_state.get("template_mode", "single") == "single":
                print("Yes, single")
                # Single template mode : on prend le dossier le plus récent qui finit par 'Single template'
                single_template_dirs = [d for d in template_sub_dirs if template_keywords in d and d.endswith("Single template")]
                single_template_dirs = sorted(single_template_dirs, reverse=True)
                if single_template_dirs:
                    st.session_state.default_template_index = template_sub_dirs.index(single_template_dirs[0])
                else:
                    st.session_state.default_template_index = 0
            else:
                # Multiple template mode
                print("Yes, Multiple mode")
                for tpl_key, tpl_config in TEMPLATE_TYPES.items():
                    base_key = tpl_config.get('base_key', tpl_key)
                    template_select_dirs = [d for d in template_sub_dirs if template_keywords in d and d.endswith(str(base_key))]
                    template_sorted_dirs = sorted(template_select_dirs, reverse=True)
                    key_name = f"default_template_index_{base_key}"
                    if template_sorted_dirs:
                        st.session_state[key_name] = template_sub_dirs.index(template_sorted_dirs[0])
                    else:
                        st.session_state[key_name] = 0
        
        # Increment version to force widget refresh without closing dialog
        st.session_state.folder_selection_version += 1

def _render_sub_scope(operation_type, operation_status):
    """Render sub-scope selection to autofill select folder"""
    
    st.markdown("""
        <h2 style="margin-bottom: 0.5rem; margin-top: -1rem;">
            🎯 Quick Folder Selection
        </h2>
        """, unsafe_allow_html=True)

    # Get dir from data_dir config
    data_dir_suffix = str(cst.CONFIG_DATA_DIR.get((operation_type, operation_status)))

    # Get list of scopes = first level subdirectories
    try:
        path = Path(data_dir_suffix)
        if not path.exists():
            st.session_state.list_scopes = [""]
        else:
            list_scopes = [d.name for d in path.iterdir() if d.is_dir()]
            # Add empty option at the beginning
            st.session_state.list_scopes = [""] + sorted(list_scopes)
    except Exception as e:
        st.session_state.list_scopes = [""]

    # Render selectbox for scopes
    if len(st.session_state.list_scopes) > 1 or (len(st.session_state.list_scopes) == 1 and st.session_state.list_scopes[0] != ""):
        selected_scope = st.selectbox(
            "Select Sub-Scope (auto-selects most recent PROD folder):",
            options=st.session_state.list_scopes,
            index=0,
            format_func=lambda x: "-- Select a scope --" if x == "" else x,
            key="selected_scope",
            on_change=update_scope_folder,
            help="Selecting a scope will automatically choose the most recent PROD folder for Data, Jarvis, and Templates"
        )
        
        if selected_scope and selected_scope != "":
            st.info(f"📂 Auto-selecting most recent folder in **{selected_scope}/PROD**")
    else:
        st.warning("No sub-scopes found in the data directory")

def _render_context_name_input():
    """Render context name input field"""
    st.markdown("""
        <h2 style="margin-bottom: 0.5rem; margin-top: -1rem;">
            Context Name <span style="color: #e74c3c;">*</span>
        </h2>
        """, unsafe_allow_html=True)
    
    return st.text_input(
        "",
        value="",
        placeholder="e.g., Context Prod",
        help="Unique name for this context within the simulation",
        key="context_name_input",
        label_visibility="collapsed"
    )


def _render_jarvis_file_selector(operation_type, operation_status):
    """Render Jarvis file selector (for Non Retail Performing only)"""
    st.markdown("**📊 Jarvis Files**")
    
    jarvis_base_path = str(cst.CONFIG_DATA_DIR.get((operation_type, operation_status)))
    jarvis_dirs = get_subdirectories(jarvis_base_path)
    
    jarvis_search_input = st.text_input(
        "Search folders:",
        value="",
        placeholder="Type to filter folders. Example: 2025Q3, SIMU",
        key="jarvis_search_input",
        icon=":material/search:"
    )
    
    if jarvis_search_input:
        jarvis_dirs = [d for d in jarvis_dirs if jarvis_search_input.lower() in d.lower()]
    
    # Get default index for jarvis from session state
    default_jarvis_index = st.session_state.get("default_jarvis_index", 0)
    # Ensure index is within bounds
    if default_jarvis_index >= len(jarvis_dirs):
        default_jarvis_index = 0
    
    # Include version in key to force refresh when scope changes
    version = st.session_state.get("folder_selection_version", 0)
    
    selected_jarvis_dir = st.selectbox(
        "Select folder:",
        options=jarvis_dirs,
        index=default_jarvis_index,
        format_func=lambda x: format_dir_path(x, jarvis_base_path),
        key=f"jarvis_folder_select_v{version}"
    )
    
    jarvis_files = get_files_in_directory(selected_jarvis_dir, extensions=['.zip', '.csv'])
    
    if jarvis_files:
        selected_jarvis_file = st.selectbox(
            "Select file to add:",
            options=jarvis_files,
            format_func=lambda x: Path(x).name,
            key="jarvis_file_select"
        )
        
        if st.button("Add this Jarvis File", key="add_jarvis_btn", 
                    icon=":material/add:", type="primary"):
            if selected_jarvis_file not in st.session_state.selected_jarvis_files:
                st.session_state.selected_jarvis_files.append(selected_jarvis_file)
                st.success(f"Added {Path(selected_jarvis_file).name}", icon=":material/check:")
            else:
                st.warning("File already added!")
    
    # Display selected Jarvis files
    if len(st.session_state.selected_jarvis_files) > 0:
        st.markdown("**Selected Jarvis Files:**")
        for idx, jarvis_item in enumerate(st.session_state.selected_jarvis_files):
            col_j1, col_j2 = st.columns([4, 1])
            with col_j1:
                file_name = jarvis_item.name if hasattr(jarvis_item, 'name') else Path(jarvis_item).name
                st.info(f"{idx+1}. {file_name}")
            with col_j2:
                def remove_jarvis_files(idx):
                    st.session_state.selected_jarvis_files = [
                        item for i, item in enumerate(st.session_state.selected_jarvis_files) if i != idx
                    ]
                st.button("❌", key=f"remove_jarvis_{idx}", 
                         on_click=lambda idx=idx: remove_jarvis_files(idx))


def _render_template_tab(tpl_key, tpl_config, parent_dir, operation_type, operation_status, example_templates):
    """Render a single template tab content"""
    # Get base key for example templates (without *)
    base_key = tpl_config.get('base_key', tpl_key)
    
    # Header with download link
    col_header, col_download = st.columns([3, 1])
    with col_header:
        required_marker = " (Required)" if tpl_config['required'] else " (Optional)"
        st.markdown(f"**{tpl_config['label']}**{required_marker}")
    
    with col_download:
        # Utiliser le chemin complet du fichier d'exemple (répertoire différent)
        example_path = example_templates.get(base_key, None)
        if example_path and example_path.exists() and example_path.is_file():
            with open(example_path, 'rb') as f:
                st.download_button(
                    label="📥 Example",
                    data=f.read(),
                    file_name=f"example_{base_key}_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_example_{tpl_key}",
                    use_container_width=True
                )
        else:
            st.caption("ℹ️ No example available")
    
    # Initialize template files list
    if tpl_key not in st.session_state.selected_template_files or \
       st.session_state.selected_template_files[tpl_key] is None:
        st.session_state.selected_template_files[tpl_key] = []
    
    # File selector and add button
    col_select, col_add = st.columns([3, 1])
    
    with col_select:
        selected_file = render_file_selector(
            label=f"Select {tpl_key} template",
            file_type="Excel",
            extensions=['.xlsx', '.xls'],
            base_path_suffix=cst.CONFIG_TEMPLATES_DIR.get((operation_type, operation_status)),
            key_prefix=f"template_{base_key.lower()}",
            parent_dir=parent_dir
        )
    
    with col_add:
        if st.button("Add File", key=f"add_template_{tpl_key}", 
                    type="primary", use_container_width=True,
                    disabled=not selected_file):
            if selected_file:
                file_path_str = str(selected_file) if not hasattr(selected_file, 'name') else selected_file.name
                current_files = st.session_state.selected_template_files[tpl_key] or []
                existing_paths = [str(f) if not hasattr(f, 'name') else f.name for f in current_files]
                
                if file_path_str not in existing_paths:
                    st.session_state.selected_template_files[tpl_key].append(selected_file)
                else:
                    st.warning("⚠️ File already added!")
    
    # Display list of added files
    files_list = st.session_state.selected_template_files[tpl_key] or []
    if files_list and len(files_list) > 0:
        st.markdown(f"**Selected Files ({len(files_list)}):**")
        for file_idx, file in enumerate(files_list):
            file_name = file.name if hasattr(file, 'name') else Path(file).name
            col_file, col_remove = st.columns([5, 1])
            with col_file:
                st.success(f"✅ {file_name}")
            with col_remove:
                st.button("🗑️", key=f"remove_{tpl_key}_{file_idx}",
                         help="Remove this file",
                         use_container_width=True,
                         on_click=lambda tpl_key=tpl_key, file_idx=file_idx: 
                                  st.session_state.selected_template_files[tpl_key].pop(file_idx))
    elif tpl_config['required']:
        st.warning(f"⚠️ At least one {tpl_key} template is required")
    else:
        st.info(f"ℹ️ No files selected (optional)")


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
    
    # Use base path for files
    base_path = str(parent_dir / base_path_suffix)
    
    # Get directories
    dirs = get_subdirectories(base_path)
    
    # # Text input for search subdirectories
    # search_input = st.text_input(
    #     "Search folders:",
    #     value="",
    #     placeholder="Type to filter folders. Example: 2025Q3, SIMU",
    #     key=f"{key_prefix}_search_input",
    #     icon=":material/search:"
    # )

    # # Filter directories based on search input
    # if search_input:
    #     dirs = [d for d in dirs if search_input.lower() in d.lower()]

    # Determine which default index to use based on key_prefix
    version = st.session_state.get("folder_selection_version", 0)
    default_index = 0
    if key_prefix.startswith("template_single"):
        default_index = st.session_state.get("default_template_index", 0)
    elif key_prefix.startswith("template_") and key_prefix != "template_single":
        # key_prefix = template_{base_key}
        base_key = key_prefix.replace("template_", "")
        index_key = f"default_template_index_{base_key.upper()}" if base_key else "default_template_index"
        default_index = st.session_state.get(index_key, 0)
    else:
        default_index = st.session_state.get("default_index", 0)

    # Ensure index is within bounds
    if default_index >= len(dirs):
        default_index = 0
    selected_dir = st.selectbox(
        "Select folder:",
        options=dirs,
        index=default_index,
        format_func=lambda x: format_dir_path(x, base_path),
        key=f"{key_prefix}_folder_select_v{version}",
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
        
@st.dialog(title="Create New Context")
def render_context_form(operation_type, operation_status):
    """Render the context creation form"""
    
    # Initialize session state
    _initialize_context_session_state(operation_type, operation_status)
    
    # Dialog styling
    st.markdown("""
        <style>
        div[data-testid="stDialog"] div[role="dialog"] {
            width: 80%;
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Sub-scope selection
    _render_sub_scope(operation_type, operation_status)

    # Context name input
    context_name = _render_context_name_input()
    
    # Get parent directory
    parent_dir = Path(cst.CONFIG_PARENT_DIR)

    # Data and Jarvis File Selection
    if operation_type == cst.OperationType.NON_RETAIL and operation_status == cst.OperationStatus.PERFORMING:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.selected_data_file = render_file_selector(
                label="📁 Data File", file_type="CSV/Excel/Zip", extensions=['.zip'],
                base_path_suffix=cst.CONFIG_DATA_DIR.get((operation_type, operation_status)),
                key_prefix="data", parent_dir=parent_dir
            )
        with col2:
            _render_jarvis_file_selector(operation_type, operation_status)
    else:
        st.session_state.selected_data_file = render_file_selector(
            label="📁 Data File", file_type="CSV/Excel/Zip", extensions=['.zip'],
            base_path_suffix=cst.CONFIG_DATA_DIR.get((operation_type, operation_status)),
            key_prefix="data", parent_dir=parent_dir
        )
        if len(st.session_state.selected_jarvis_files) > 0:
            st.session_state.selected_jarvis_files = []
    
    # Template Files Section
    st.markdown("""
        <h2 style="margin-bottom: 0.5rem; margin-top: 0;">
            📄 Template Files <span style="color: #e74c3c;">*</span>
        </h2>
        """, unsafe_allow_html=True)
    
    # Radio button to choose template mode
    template_mode = st.radio(
        "Choose template mode:",
        options=["📄 Single Template File", "📁 Multiple Template Files (by type)"],
        index= 1,
        key="template_mode_radio",
        horizontal=True,
        help="Single: One file with all sheets | Multiple: Separate files for PD, LGD, CCF, etc.",
        on_change=update_scope_folder
    )
    
    # Update session state based on selection
    st.session_state.template_mode = 'single' if template_mode.startswith("📄") else 'multiple'
    
    if st.session_state.template_mode == 'single':
        # Single template file mode (classic)
        st.session_state.selected_single_template_file = render_file_selector(
            label="Select Template File",
            file_type="Excel",
            extensions=['.xlsx', '.xls'],
            base_path_suffix=cst.CONFIG_TEMPLATES_DIR.get((operation_type, operation_status)),
            key_prefix="template_single",
            parent_dir=parent_dir
        )
        # Clear multiple mode data
        st.session_state.selected_template_files = {key: [] for key in TEMPLATE_TYPES.keys()}
        
    else:
        # Multiple template files mode (new)
        tabs = st.tabs(list(TEMPLATE_TYPES.keys()))
        for idx, (tpl_key, tpl_config) in enumerate(TEMPLATE_TYPES.items()):
            with tabs[idx]:
                _render_template_tab(tpl_key, tpl_config, parent_dir, operation_type, 
                                     operation_status, EXAMPLE_TEMPLATE_PATHS)
        # Clear single mode data
        st.session_state.selected_single_template_file = None

    # Context form summary and submission
    with st.form("context_form", clear_on_submit=True):
        # Use selected files from session state
        context_name = st.session_state.get("context_name_input", "").strip()
        data_file = st.session_state.selected_data_file
        template_mode = st.session_state.template_mode
        single_template_file = st.session_state.selected_single_template_file
        template_files = st.session_state.selected_template_files
        jarvis_files = st.session_state.selected_jarvis_files
        
        # Display summary
        st.markdown("**📋 Context Summary**")

        if context_name:
            st.success(f"📛 Context Name: {context_name}")
        else:
            st.error("❌ Context name is required!")
        
        if data_file:
            file_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name
            st.success(f"📁 Data: {file_name}")
        else:
            st.error("❌ No data file selected")
        
        # Display template files summary based on mode
        missing_required_templates = []
        
        if template_mode == 'single':
            # Single template mode
            if single_template_file:
                file_name = single_template_file.name if hasattr(single_template_file, 'name') else Path(single_template_file).name
                st.success(f"📄 Template File (Single): {file_name}")
            else:
                st.error("❌ Template file is required!")
                missing_required_templates.append('Template')
        else:
            # Multiple templates mode
            for tpl_key, tpl_config in TEMPLATE_TYPES.items():
                tpl_files_list = template_files.get(tpl_key, [])
                file_count = len(tpl_files_list) if tpl_files_list else 0
                
                if file_count > 0:
                    file_names = [f.name if hasattr(f, 'name') else Path(f).name for f in tpl_files_list]
                    if file_count == 1:
                        st.success(f"📄 {tpl_config['label']}: {file_names[0]}")
                    else:
                        st.success(f"📄 {tpl_config['label']} ({file_count} files): {', '.join(file_names)}")
                elif tpl_config['required']:
                    st.error(f"❌ {tpl_config['label']}: Required but not selected")
                    missing_required_templates.append(tpl_key)
                else:
                    st.info(f"⚪ {tpl_config['label']}: Not selected (optional)")
        
        if (operation_type == cst.OperationType.NON_RETAIL and 
            operation_status == cst.OperationStatus.PERFORMING):
            if jarvis_files and len(jarvis_files) > 0:
                
                file_names = [f.name if hasattr(f, 'name') else Path(f).name for f in jarvis_files]
                st.success(f"📊 Jarvis files: {', '.join(file_names)}")
            else:
                st.error("❌ No Jarvis files selected")
        
        # Submit context
        col_submit, col_cancel = st.columns([2, 1])
        
        # Vérifier si on est en mode édition
        # is_editing = st.session_state.get('editing_mode', False)
        # editing_idx = st.session_state.get('editing_context_idx')
        
        with col_submit:
            #button_label = "💾 Update Context" if is_editing else "✅ Add This Context"
            button_label = "✅ Add This Context"
            submitted = st.form_submit_button(button_label, type="primary", use_container_width=True)
        
        with col_cancel:
            cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submitted:
            # Récupérer les noms de contextes existants (en excluant celui en cours d'édition)
            # if is_editing and editing_idx is not None:
            #     submitted_contexts = [ctx['context_name'] for i, ctx in enumerate(st.session_state.current_contexts) if i != editing_idx]
            # else:
            #     submitted_contexts = [ctx['context_name'] for ctx in st.session_state.current_contexts]
            submitted_contexts = [ctx['context_name'] for ctx in st.session_state.current_contexts]
            if not context_name:
                st.error("❌ Context name is required!")
            elif context_name in submitted_contexts:
                st.error("❌ Context name must be unique!")
            elif not data_file:
                st.error("❌ Data file is required!")
            elif missing_required_templates:
                st.error(f"❌ Required template(s) missing: {', '.join(missing_required_templates)}")
            elif (operation_type == cst.OperationType.NON_RETAIL and 
                  operation_status == cst.OperationStatus.PERFORMING and
                  (not jarvis_files or len(jarvis_files) == 0)):
                st.error("❌ Jarvis files are required for Non Retail Performing operation!")
            else:
                # Créer l'objet contexte avec format unifié
                context_data = {
                    'context_name': context_name,
                    'data_file': data_file,
                    'template_mode': template_mode,
                    'template_files': {
                        'single': single_template_file if template_mode == 'single' else None,
                        'multiple': template_files.copy() if template_mode == 'multiple' else None
                    },
                    'jarvis_files': jarvis_files
                }
                
                # Ajouter ou mettre à jour le contexte
                # if is_editing and editing_idx is not None and editing_idx < len(st.session_state.current_contexts):
                #     # Mode édition: mettre à jour le contexte existant
                #     st.session_state.current_contexts[editing_idx] = context_data
                #     st.success(f"✅ Context '{context_name}' updated successfully!", icon=":material/check:")
                    
                #     # Réinitialiser le mode édition
                #     del st.session_state['editing_mode']
                #     del st.session_state['editing_context_idx']
                # else:
                #     # Mode ajout: ajouter un nouveau contexte
                #     st.session_state.current_contexts.append(context_data)
                #     st.success(f"✅ Context '{context_name}' added successfully!", icon=":material/check:")
                

                st.session_state.current_contexts.append(context_data)
                st.success(f"✅ Context '{context_name}' added successfully!", icon=":material/check:")
                
                # Nettoyer les fichiers sélectionnés
                st.session_state.selected_data_file = None
                st.session_state.selected_template_files = {key: [] for key in TEMPLATE_TYPES.keys()}
                st.session_state.selected_jarvis_files = []
                st.rerun()

        if cancelled:
            # Nettoyer les fichiers sélectionnés
            _initialize_context_session_state(operation_type, operation_status)
            st.rerun()        
        
        # return data_file, template_file, jarvis_files, context_name, submitted, cancelled

def callback_submit_button():
    if len(st.session_state.current_contexts) == 0:
        st.error("❌ At least one context is required before submitting the simulation!")
        return
    if st.session_state.validation_complete == True:
        st.warning("Simulation has already been submitted and validated.")
        return
    
    # Initialize submission state
    if "submission_state" not in st.session_state:
        st.session_state.submission_state = {
            "running": False,
            "started": False,
            "completed": False,
            "error": None,
            "result_container": None,
            "thread": None
        }
    
    # Mark as running
    st.session_state.submission_state["running"] = True
    st.session_state.submission_state["started"] = False
    
    for key in ["disable_button_modify", 
                "disable_add_context", 
                "disable_submit",
                "hide_context_summary"]:
        if key in st.session_state:
            st.session_state[key] = True
    st.session_state.launch_simulation_submit = True

# Shared result container for thread-safe communication
class SubmissionResult:
    def __init__(self):
        self.completed = False
        self.success = False
        self.error = None
        self.sim_name = None

def run_submission_thread(manager, simulation_config, result_container):
    """Execute simulation submission and preparation in background thread"""
    
    # Suppress Streamlit ScriptRunContext warning in thread
    warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')
    
    # Suppress in logger if it appears there
    streamlit_logger = logging.getLogger('streamlit.runtime.scriptrunner.script_runner')
    streamlit_logger.setLevel(logging.ERROR)
    
    try:
        sim_name = simulation_config['simulation_name']
        operation_type = simulation_config['operation_type']
        operation_status = simulation_config['operation_status']
        
        # Add simulations
        for ctx in simulation_config['contexts']:
            # Extract template path based on mode
            template_mode = ctx.get('template_mode', 'single')
            template_files_data = ctx.get('template_files', {})
            
            # Determine template_path based on mode
            if template_mode == 'single':
                template_path = template_files_data.get('single') or ctx.get('template_file')  # Backward compatibility
            else:  # multiple mode
                template_path = template_files_data.get('multiple', {})
            
            context_name = ctx.get('context_name')
            manager.add_simulation(
                simulation_name = context_name,
                operation_type = operation_type,
                operation_status = operation_status,
                data_path = ctx.get('data_file'),
                template_path = template_path,  # Can be single file or dict of files
                list_jarvis_file_path = ctx.get('jarvis_files', [])
            )
        
        # Prepare simulations (potentially long operation)
        manager.prepare_all_simulations()
        
        # Mark success
        result_container.success = True
        result_container.sim_name = sim_name
        result_container.completed = True
        
    except Exception as e:
        result_container.error = str(e)
        result_container.completed = True
        result_container.success = False
        logger.error(f"Error in submission thread: {e}")

def render_simulation_submit():
    """Render simulation submission with background thread processing"""
    
    # Add simulation to config
    simulation_config = {
        'simulation_name': st.session_state.form_sim_name,
        'operation_type': st.session_state.form_operation_type,
        'operation_status': st.session_state.form_operation_status,
        'contexts': st.session_state.current_contexts
    }

    st.session_state.simulations_config.update(simulation_config)
    
    # Initialize submission state if needed
    if "submission_state" not in st.session_state:
        st.session_state.submission_state = {
            "running": False,
            "started": False,
            "completed": False,
            "error": None,
            "result_container": None,
            "thread": None
        }
    
    submission_state = st.session_state.submission_state
    
    col_action1, col_action2 = st.columns([1,1])
    with col_action1:
        st.metric(
            label="Total Loaded Contexts",
            value=len(st.session_state.simulations_config['contexts']),
        )
    
    with col_action2:
        # Show different UI based on submission state
        if submission_state["running"]:
            # Submission in progress
            st.warning("⏳ Preparing simulations... Please wait.")
            st.info("💡 You can navigate to other pages. The preparation will continue in background.")
            
            # Start thread ONLY if not yet started
            if not submission_state["started"]:
                submission_state["started"] = True
                
                # Create result container
                result_container = SubmissionResult()
                submission_state["result_container"] = result_container
                
                # Launch submission in background thread
                submit_thread = threading.Thread(
                    target=run_submission_thread,
                    args=(st.session_state.manager, simulation_config, result_container),
                    daemon=True
                )
                submit_thread.start()
                submission_state["thread"] = submit_thread
            
            # Check thread status
            result_container = submission_state.get("result_container")
            submit_thread = submission_state.get("thread")
            
            if submit_thread and submit_thread.is_alive():
                # Still running - show progress
                st.caption(f"⏱️ Preparing {len(simulation_config['contexts'])} context(s)...")
                with st.spinner("Loading data and templates..."):
                    time.sleep(0.5)
                st.rerun()
                
            elif result_container and result_container.completed:
                # Finished - check result
                if result_container.success:
                    # Success!
                    submission_state["running"] = False
                    submission_state["completed"] = True
                    st.session_state.validation_complete = True
                    st.session_state.launch_simulation_submit = False
                    st.session_state.disable_submit = True
                    
                    st.success(f"✅ Simulation '{result_container.sim_name}' with {len(simulation_config['contexts'])} context(s) submitted successfully!", 
                               icon=":material/check:")
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    # Error occurred
                    submission_state["running"] = False
                    submission_state["error"] = result_container.error
                    st.error(f"❌ Error submitting simulation: {result_container.error}")
                    st.warning("Please review your simulation configuration and try again.", 
                               icon=":material/warning:")
                    
                    # Cleanup on error
                    st.session_state.simulations_config = {}
                    if hasattr(st.session_state, 'manager'):
                        st.session_state.manager.clear()
                    
                    col_retry, col_cancel = st.columns(2)
                    with col_retry:
                        if st.button("Retry Submission", icon=":material/refresh:", type="primary"):
                            # Reset state for retry
                            submission_state["running"] = False
                            submission_state["started"] = False
                            submission_state["completed"] = False
                            submission_state["error"] = None
                            st.rerun()
                    with col_cancel:
                        if st.button("Cancel Submission", icon=":material/close:", type="secondary"):
                            # Cancel and reset
                            st.session_state.launch_simulation_submit = False
                            st.session_state.disable_submit = False
                            st.session_state.disable_button_modify = False
                            st.session_state.disable_add_context = False
                            st.session_state.hide_context_summary = False
                            submission_state["running"] = False
                            submission_state["started"] = False
                            st.rerun()
        
        elif submission_state["completed"] and not submission_state["error"]:
            # Already completed successfully
            st.success("✅ Submission completed!", icon="📌")
        
        else:
            # Initial state - should not reach here as button triggers callback
            st.info("Click 'Submit Simulation' to start preparation")

def display_simulation_summary(sim_name, operation_type, operation_status, current_contexts):
    """
    Display a summary of the current simulation configuration
    """
    if "disable_button_modify" not in st.session_state:
        st.session_state.disable_button_modify = False

    with st.container(border=True):
        col_desc, col_modify, col_clear, col_submit = st.columns([2,1,1,1])
        with col_desc:
            st.markdown("### 📋 Simulation Summary")
            st.info(f"**Simulation Name:** {sim_name}  \n"
                    f"**Operation Type:** {operation_type.value}  \n"
                    f"**Operation Status:** {operation_status.value}  \n"
                    f"**Total Contexts:** {len(current_contexts)}"
            )
        with col_modify:
            if st.button("Modify Simulation", icon=":material/edit:", type="secondary", 
                         use_container_width=True,
                         disabled=st.session_state.disable_button_modify):
                # Reset indices and paths before opening dialog
                reset_context_indices_and_paths(st.session_state.form_operation_type, st.session_state.form_operation_status)
                create_simulation_dialog()
        with col_clear:
            if st.button("Clear Simulation", icon=":material/delete:", 
                         type="secondary", use_container_width=True):
                # Stop any running calculation threads
                for key in list(st.session_state.keys()):
                    if key.startswith("ecl_calculation_"):
                        calc_state = st.session_state.get(key)
                        if calc_state and isinstance(calc_state, dict):
                            # Mark thread as invalid to discard results
                            calc_state["running"] = False
                            calc_state["started"] = False
                            calc_state["invalidated"] = True
                
                # Delete all cache files
                try:
                    from pathlib import Path
                    cache_dir = Path(__file__).parent.parent.parent.parent / "cache"
                    if cache_dir.exists():
                        for cache_file in cache_dir.glob("ecl_results_*.pkl"):
                            cache_file.unlink()
                except Exception:
                    pass  # Ignore errors during cleanup
                
                # Clear manager and session state
                st.session_state.manager.clear()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        with col_submit:
            # Active callback on submit button to update session state
            # Will trigger rendering of submission section in main page
            st.button("Submit Simulation", icon=":material/send:", 
                      type="primary", use_container_width=True,
                      on_click=callback_submit_button,
                      disabled=st.session_state.disable_submit)
            
def display_context_summary(contexts: list, operation_type, operation_status):
    """
    Display a summary of a context configuration
    """

    if "hide_context_summary" not in st.session_state:
        st.session_state.hide_context_summary = False
    
    if not contexts or len(contexts) == 0:
        st.info("No contexts added yet.")
        return
    st.markdown(f"### 📂 Contexts Summary ({len(contexts)})")

    for idx, ctx in enumerate(contexts):
        context_name = ctx.get('context_name')
        data_file = ctx.get('data_file')
        
        # Handle different template formats
        template_mode = ctx.get('template_mode', 'single')  # Default to single for backward compatibility
        template_files_data = ctx.get('template_files', {})
        
        # Old format support (for backward compatibility)
        old_template_file = ctx.get('template_file')
        
        jarvis_files = ctx.get('jarvis_files', [])

        # Get file names
        data_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name if data_file else "N/A"
        
        jarvis_items = []
        if jarvis_files and len(jarvis_files) > 0:
            jarvis_items = [
                f.name if hasattr(f, 'name') else Path(f).name for f in jarvis_files
            ]
        jarvis_names = ", ".join(jarvis_items) if jarvis_items else "N/A"

        with st.container(border=True):
            st.markdown(f":material/folder: **Context {idx+1}: {context_name}**")
            col_1, col_2 = st.columns([12, 1])

            # Context details
            with col_1:
                st.write(f"📁 **Data File**: {data_name}")
                
                
                # Display templates based on mode
                if template_mode == 'single':
                    # Single template mode
                    single_file = template_files_data.get('single') if isinstance(template_files_data, dict) else old_template_file
                    if single_file:
                        file_name = single_file.name if hasattr(single_file, 'name') else Path(single_file).name
                        st.write(f"- 📄 **Template File**: {file_name}")
                    else:
                        st.write(f"- 📄 **Template File**: Not provided")
                        
                elif template_mode == 'multiple':
                    st.write("📄 **Template Files**")
                    # Multiple templates mode
                    with st.expander("Details"):
                        multiple_files = template_files_data.get('multiple', {})
                        if multiple_files:
                            for tpl_key, tpl_config in TEMPLATE_TYPES.items():
                                #tpl_label = tpl_config['label'].replace('📊 ', '').replace('💰 ', '').replace('🔄 ', '').replace('🎯 ', '').replace('📦 ', '').replace('⏳ ', '')
                                tpl_label = tpl_config['label']
                                tpl_files_list = multiple_files.get(tpl_key, [])
                                if tpl_files_list and len(tpl_files_list) > 0:
                                    file_names = [f.name if hasattr(f, 'name') else Path(f).name for f in tpl_files_list]
                                    if len(file_names) == 1:
                                        st.write(f"  - {tpl_label}: {file_names[0]}")
                                    else:
                                        st.write(f"  - {tpl_label} ({len(file_names)}): {', '.join(file_names)}")
                                else:
                                    st.write(f"  - {tpl_label}: Not provided, using default")
                
                # Fallback for very old format
                # elif old_template_file:
                #     template_name = old_template_file.name if hasattr(old_template_file, 'name') else Path(old_template_file).name
                #     st.write(f"- 📄 **Template File**: {template_name}")
                
                if operation_type == cst.OperationType.NON_RETAIL and operation_status == cst.OperationStatus.PERFORMING:
                    st.write(f"📊 **Jarvis Files** ({len(jarvis_items)}): {jarvis_names}")
            with col_2:
                with st.popover("",
                                type="tertiary", use_container_width=True,
                                disabled=st.session_state.hide_context_summary):
                    if st.session_state.get(f"confirm_delete_{idx}"):
                        st.warning(f"Confirm deletion of context '{context_name}'?", 
                                   icon=":material/warning:")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Yes", key=f"yes_delete_{idx}", type="primary", 
                                        use_container_width=True, icon=":material/check:"):
                                # Delete context
                                st.session_state.current_contexts.pop(idx)
                                # Reset confirmation state
                                del st.session_state[f"confirm_delete_{idx}"]
                                st.success(f"✅ Context '{context_name}' deleted.", icon=":material/check:")
                                st.rerun()
                        with col_no:
                            if st.button("No", key=f"no_delete_{idx}", type="secondary", 
                                            use_container_width=True, icon=":material/close:"):
                                # Cancel deletion
                                del st.session_state[f"confirm_delete_{idx}"]
                                st.rerun()
                    else:
                        if st.button("Delete Context", key=f"delete_{idx}", type="secondary", 
                                        use_container_width=True, icon=":material/delete:"):
                            st.session_state[f"confirm_delete_{idx}"] = True
                            st.rerun()
