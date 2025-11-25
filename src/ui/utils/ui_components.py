"""
Reusable UI components for Streamlit app
"""

import streamlit as st


def get_custom_css():
    """Return custom CSS styling for the application"""
    return """
        <style>
        /* Main theme colors */
        :root {
            --primary-color: #1f77b4;
            --secondary-color: #ff7f0e;
            --success-color: #2ca02c;
            --warning-color: #ff9800;
            --error-color: #d62728;
            --info-color: #17a2b8;
        }
        
        /* Sidebar styling */
        # [data-testid="stSidebar"] {
        #     background-color: #f8f9fa;
        # }
        
        /* Card styling */
        .metric-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 10px 0;
            border-left: 4px solid;
        }
        
        .metric-card.success {
            border-left-color: #2ca02c;
        }
        
        .metric-card.warning {
            border-left-color: #ff9800;
        }
        
        .metric-card.error {
            border-left-color: #d62728;
        }
        
        .metric-card.info {
            border-left-color: #17a2b8;
        }
        
        /* Button styling */
        .stButton>button {
            border-radius: 5px;
            font-weight: 500;
            transition: all 0.3s;
        }
        
        /* Status badges */
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 500;
            font-size: 14px;
        }
        
        .status-success {
            background-color: #d4edda;
            color: #155724;
        }
        
        .status-warning {
            background-color: #fff3cd;
            color: #856404;
        }
        
        .status-error {
            background-color: #f8d7da;
            color: #721c24;
        }
        
        .status-info {
            background-color: #d1ecf1;
            color: #0c5460;
        }
        
        /* Header styling */
        .main-header {
            text-align: center;
            padding: 20px 0;
            background: linear-gradient(90deg, #1f77b4 0%, #17a2b8 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        
        /* Hide Streamlit branding */
        MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
               
        /* Status container in sidebar - smaller font for st.status() */
        [data-testid="stSidebar"] [data-testid="stExpander"],
        [data-testid="stSidebar"] [data-testid="stExpander"] *,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary,
        [data-testid="stSidebar"] [data-testid="stExpander"] div,
        [data-testid="stSidebar"] [data-testid="stExpander"] p,
        [data-testid="stSidebar"] [data-testid="stExpander"] span {
            font-size: 0.9rem !important;
            line-height: 1.3 !important;
        }
        
        /* Remove border from status area in sidebar */
        [data-testid="stSidebar"] [data-testid="stExpander"] {
            border: none !important;
        }
        
        [data-testid="stSidebar"] [data-testid="stExpander"] details {
            border: none !important;
        }
        </style>
    """


def create_metric_card(title, value, status="info"):
    """
    Create a styled metric card
    
    Args:
        title: Card title
        value: Value to display
        status: Card status (success, warning, error, info)
    """
    st.markdown(f"""
        <div class="metric-card {status}">
            <div style="color: #666; font-size: 14px; margin-bottom: 5px;">{title}</div>
            <div style="font-size: 24px; font-weight: bold;">{value}</div>
        </div>
    """, unsafe_allow_html=True)


def create_status_badge(text, status="info"):
    """
    Create a status badge
    
    Args:
        text: Badge text
        status: Badge status (success, warning, error, info)
    """
    return f'<span class="status-badge status-{status}">{text}</span>'

def display_simulation_summary(sim_name: str, operation_type, operation_status):
    """
    Display a summary card of the current simulation configuration
    
    Args:
        sim_name: Name of the simulation
        operation_type: Type of operation (OperationType enum)
        operation_status: Status of operation (OperationStatus enum)
    """
    st.markdown("""
        <style>
        .summary-card {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            color: #333;
            margin: 0 0 1rem 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border: 1px solid #e0e0e0;
            display: block;
        }
        .summary-card h3 {
            margin: 0 0 0.5rem 0;
            font-size: 1.2rem;
            font-weight: 600;
        }
        .summary-item {
            display: flex;
            justify-content: space-between;
            margin: 0.25rem 0;
            padding: 0.25rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        .summary-item:last-child {
            border-bottom: none;
        }
        .summary-label {
            font-weight: 500;
            opacity: 0.9;
        }
        .summary-value {
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="summary-card">
            <h3>📋 Current Simulation</h3>
            <div class="summary-item">
                <span class="summary-label">Name:</span>
                <span class="summary-value">{sim_name}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Operation Type:</span>
                <span class="summary-value">{operation_type.value}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Operation Status:</span>
                <span class="summary-value">{operation_status.value}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

def display_context_summary(contexts: list, operation_type, operation_status):
    """
    Display a summary of all contexts with their details
    
    Args:
        contexts: List of context dictionaries
        operation_type: Type of operation (OperationType enum)
        operation_status: Status of operation (OperationStatus enum)
    """
    from pathlib import Path
    from src.core import config as cst
    
    if not contexts or len(contexts) == 0:
        st.info("No contexts added yet.")
        return
    
    st.markdown("""
        <style>
        .context-card {
            background: #ffffff;
            padding: 1.2rem;
            border-radius: 8px;
            margin: 0.8rem 0;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
        }
        .context-header {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 0.8rem;
            display: flex;
            align-items: center;
        }
        .context-detail {
            display: flex;
            margin: 0.4rem 0;
            font-size: 0.9rem;
        }
        .context-label {
            font-weight: 500;
            color: #666;
            min-width: 120px;
        }
        .context-value {
            color: #333;
            flex: 1;
        }
        .jarvis-list {
            margin-left: 120px;
            color: #333;
        }
        .jarvis-item {
            margin: 0.2rem 0;
            padding-left: 1rem;
            position: relative;
        }
        .jarvis-item:before {
            content: "•";
            position: absolute;
            left: 0;
            color: #667eea;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 📋 Contexts Summary ({len(contexts)})")
    
    for idx, ctx in enumerate(contexts):
        context_name = ctx.get('context_name', f'Context {idx+1}')
        data_file = ctx.get('data_file')
        template_file = ctx.get('template_file')
        jarvis_files = ctx.get('jarvis_files', [])
        
        # Get file names
        data_name = data_file.name if hasattr(data_file, 'name') else Path(data_file).name if data_file else "N/A"
        template_name = template_file.name if hasattr(template_file, 'name') else Path(template_file).name if template_file else "N/A"
        
        jarvis_names = []
        if jarvis_files and len(jarvis_files) > 0:
            for f in jarvis_files:
                if hasattr(f, 'name'):
                    jarvis_names.append(f.name)
                else:
                    jarvis_names.append(Path(f).name)
        # Créer une carte avec colonnes
        with st.container(border=True):
            st.markdown(f"#### 🔸 {context_name}")
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.write(f"📁 **Data:** {data_name}")
                st.write(f"📄 **Template:** {template_name}")
                
                if jarvis_names:
                    st.write(f"📊 **Jarvis Files ({len(jarvis_names)}):**")
                    for name in jarvis_names:
                        st.write(f"  • {name}")
                else:
                    st.write("📊 **Jarvis Files:** None")
            
            with col2:
                # Menu déroulant avec bouton "..."
                with st.popover("⋮", use_container_width=True):
                    st.markdown("**Actions**")
                    
                    # Bouton Edit
                    if st.button("✏️ Edit", key=f"edit_ctx_{idx}", use_container_width=True, type="secondary"):
                        # Charger le contexte à éditer
                        st.session_state['editing_context_idx'] = idx
                        st.session_state['editing_mode'] = True
                        
                        # Pré-remplir les champs avec les données du contexte
                        ctx_to_edit = contexts[idx]
                        st.session_state.selected_data_file = ctx_to_edit.get('data_file')
                        st.session_state.selected_template_file = ctx_to_edit.get('template_file')
                        st.session_state.selected_jarvis_files = ctx_to_edit.get('jarvis_files', [])
                        
                        # Ouvrir le dialog en déclenchant un rerun
                        st.rerun()
                    
                    # Bouton Delete avec confirmation
                    if st.session_state.get(f'confirm_delete_{idx}'):
                        st.warning("⚠️ Confirm deletion?", icon="⚠️")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅ Yes", key=f"confirm_yes_{idx}", use_container_width=True):
                                st.session_state.contexts.pop(idx)
                                del st.session_state[f'confirm_delete_{idx}']
                                st.success("Context deleted!")
                                st.rerun()
                        with col_no:
                            if st.button("❌ No", key=f"confirm_no_{idx}", use_container_width=True):
                                del st.session_state[f'confirm_delete_{idx}']
                                st.rerun()
                    else:
                        if st.button("🗑️ Delete", key=f"delete_ctx_{idx}", use_container_width=True, type="secondary"):
                            st.session_state[f'confirm_delete_{idx}'] = True
                            st.rerun()
            
        #st.divider()
        
        
        
def display_validation_result(title, passed, total, status="success"):
    """
    Display validation results in a consistent format
    
    Args:
        title: Validation title
        passed: Number of passed validations
        total: Total number of validations
        status: Overall status
    """
    percentage = (passed / total * 100) if total > 0 else 0
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"**{title}**")
        st.progress(percentage / 100)
    
    with col2:
        badge_html = create_status_badge(f"{passed}/{total}", status)
        st.markdown(badge_html, unsafe_allow_html=True)
