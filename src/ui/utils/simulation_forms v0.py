"""
Reusable components for the Simulation Configuration page
Separated into functions for better maintainability
"""

import logging
import streamlit as st
from pathlib import Path
from src.core import config as cst
from src.templates.template_loader import registry_loader
from src.factory import simulation_manager
from src.ui.utils.get_directories import get_subdirectories, format_dir_path, get_files_in_directory
logger = logging.getLogger(__name__)  

parent_dir = Path(__file__).parent.parent.parent.parent
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
                st.rerun()

    if st.session_state.get("clear_rerun", False):
        del st.session_state["clear_rerun"]
        st.rerun()
    with col2:
        if st.button("Cancel", key="cancel_create_sim", icon=":material/close:", type="secondary"):
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
    # Pré-remplir si on est en mode édition
    # default_context_name = ""
    # if st.session_state.get('editing_mode') and 'editing_context_idx' in st.session_state:
    #     editing_idx = st.session_state['editing_context_idx']
    #     if 'current_contexts' in st.session_state and editing_idx < len(st.session_state.current_contexts):
    #         default_context_name = st.session_state.current_contexts[editing_idx].get('context_name', '')
    
    st.markdown("""
                <h2 style="margin-bottom: 0.5rem; margin-top: -1rem;">
                    Context Name <span style="color: #e74c3c;">*</span>
                </h2>
                """, 
                unsafe_allow_html=True)
    context_name = st.text_input(
        "",  # Label vide
        value="",
        placeholder="e.g., Context Prod",
        help="Unique name for this context within the simulation",
        key="context_name_input",
        label_visibility="collapsed"  # Cache complètement le label vide
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
                type=['zip', 'csv'],
                accept_multiple_files=True,
                key="jarvis_file_uploader"
            )
            
            if uploaded_jarvis_files:
                # Check for duplicates within uploaded files first
                uploaded_names = [f.name for f in uploaded_jarvis_files]
                duplicates = [name for name in uploaded_names if uploaded_names.count(name) > 1]
                
                if duplicates:
                    unique_duplicates = list(set(duplicates))
                    st.error(f"❌ Duplicate files detected in upload: {', '.join(unique_duplicates)}. Please remove duplicates and try again.")
                    return  # Stop processing if duplicates found
                
                # Check for existing files and add new ones
                existing_names = [
                    f.name if hasattr(f, 'name') else Path(f).name 
                    for f in st.session_state.selected_jarvis_files
                ]
                
                files_already_exist = [f.name for f in uploaded_jarvis_files if f.name in existing_names]
                new_files = [f for f in uploaded_jarvis_files if f.name not in existing_names]
                
                if files_already_exist:
                    st.warning(f"⚠️ Files already exist in selection: {', '.join(files_already_exist)}")
                
                # Only add new files
                for new_file in new_files:
                    st.session_state.selected_jarvis_files.append(new_file)
                
                if new_files:
                    st.success(f"✅ {len(new_files)} new file(s) uploaded")
                elif files_already_exist:
                    st.info("ℹ️ No new files were added (all files already exist)")
        
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
    else:
        # Clear Jarvis files if not Non Retail Performing
        if len(st.session_state.selected_jarvis_files) > 0:
            st.session_state.selected_jarvis_files = []
   
    # Context form
    with st.form("context_form", clear_on_submit=True):
        # Use selected files from session state
        context_name = st.session_state.get("context_name_input", "").strip()
        data_file = st.session_state.selected_data_file
        template_file = st.session_state.selected_template_file
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
            elif not data_file or not template_file:
                st.error("❌ Data file and template file are required!")
            elif (operation_type == cst.OperationType.NON_RETAIL and 
                  operation_status == cst.OperationStatus.PERFORMING and
                  (not jarvis_files or len(jarvis_files) == 0)):
                st.error("❌ Jarvis files are required for Non Retail Performing operation!")
            else:
                # Créer l'objet contexte
                context_data = {
                    'context_name': context_name,
                    'data_file': data_file,
                    'template_file': template_file,
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
                st.session_state.selected_template_file = None
                st.session_state.selected_jarvis_files = []
                
                st.rerun()

        if cancelled:
            # # Réinitialiser le mode édition si on annule
            # if 'editing_mode' in st.session_state:
            #     del st.session_state['editing_mode']
            # if 'editing_context_idx' in st.session_state:
            #     del st.session_state['editing_context_idx']
            
            # Nettoyer les fichiers sélectionnés
            st.session_state.selected_data_file = None
            st.session_state.selected_template_file = None
            st.session_state.selected_jarvis_files = []
            st.rerun()        
        
        # return data_file, template_file, jarvis_files, context_name, submitted, cancelled

def callback_submit_button():
    if len(st.session_state.current_contexts) == 0:
        st.error("❌ At least one context is required before submitting the simulation!")
        return
    if st.session_state.validation_complete == True:
        st.warning("Simulation has already been submitted and validated.")
        return
    for key in ["disable_button_modify", 
                "disable_add_context", 
                "disable_submit",
                "hide_context_summary"]:
        if key in st.session_state:
            st.session_state[key] = True
    st.session_state.launch_simulation_submit = True

def render_simulation_submit():

    # Add simulation to config
    simulation_config = {
        'simulation_name': st.session_state.form_sim_name,
        'operation_type': st.session_state.form_operation_type,
        'operation_status': st.session_state.form_operation_status,
        'contexts': st.session_state.current_contexts
    }

    st.session_state.simulations_config.update(simulation_config)
    col_action1, col_action2 = st.columns([1,1])
    with col_action1:
        st.metric(
            label="Total Loaded Contexts",
            value=len(st.session_state.simulations_config['contexts']),
        )
    with col_action2:
        with st.spinner("Submitting simulation..."):
            try:
                sim_name = st.session_state.simulations_config['simulation_name']
                operation_type = st.session_state.simulations_config['operation_type']
                operation_status = st.session_state.simulations_config['operation_status']

                for ctx in st.session_state.simulations_config['contexts']:
                    # Here you would normally call the simulation manager to add and launch the simulation
                    context_name = ctx.get('context_name')
                    st.session_state.manager.add_simulation(
                        simulation_name = context_name,
                        operation_type = operation_type,
                        operation_status = operation_status,
                        data_path = ctx.get('data_file'),
                        template_path = ctx.get('template_file'),
                        list_jarvis_file_path = ctx.get('jarvis_files', [])
                    )

                # Prepare simulations
                st.session_state.manager.prepare_all_simulations()
                st.session_state.validation_complete = True
                st.session_state.launch_simulation_submit = False

                st.success(f"✅ Simulation '{sim_name}' with {len(st.session_state.simulations_config['contexts'])} context(s) submitted successfully!", 
                           icon=":material/check:")
                st.session_state.disable_submit = True
            except Exception as e:
                st.session_state.simulations_config = {}
                #st.session_state.disable_submit = False
                st.session_state.manager.clear()
                logger.error("Error submitting simulation. Please review the configuration.")
                st.error(f"❌ Error submitting simulation: {str(e)}")
                st.warning("Please review your simulation configuration and try again. \n" \
                            "Recommendation: Reset all and start over.", 
                           icon=":material/warning:")
                del st.session_state.manager

                if st.button("Retry Submission", icon=":material/refresh:", type="primary"):
                    logging.info("Retrying simulation submission...")
                    st.rerun()
                if st.button("Cancel Submission", icon=":material/close:", type="secondary"):
                    logging.info("Simulation submission cancelled.")
                    st.session_state.launch_simulation_submit = False
                    st.session_state.disable_submit = False
                    st.session_state.disable_button_modify = False
                    st.session_state.disable_add_context = False
                    st.session_state.hide_context_summary = False
                    st.rerun()
    # with st.expander("View Simulation Configuration"):
    #     st.json(st.session_state.simulations_config)
    # return simulation_config

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
        template_file = ctx.get('template_file')
        jarvis_files = ctx.get('jarvis_files', [])

        # Get file names
        data_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name if data_file else "N/A"
        template_name = template_file.name if hasattr(template_file, 'name') else Path(template_file).name if template_file else "N/A"
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
                st.write(f"- 📁 **Data File**: {data_name}")
                st.write(f"- 📄 **Template File**: {template_name}")
                if operation_type == cst.OperationType.NON_RETAIL and operation_status == cst.OperationStatus.PERFORMING:
                    st.write(f"- 📊 **Jarvis Files** {len(jarvis_items)}: {jarvis_names}")
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
