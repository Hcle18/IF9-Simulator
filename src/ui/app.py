"""
IFRS9 ECL Simulation - Main Application Entry Point
Multi-page Streamlit application for ECL calculations
"""

import streamlit as st
from pathlib import Path
import logging
from src.factory import simulation_manager
from src.utils.logging_config import setup_logging
from src.ui.utils.ui_logger import StreamlitLogHandler, ui_setup_logging, display_ui_logs
from src.ui.utils.ui_components import get_custom_css
from src.ui.utils.session_persistence import load_session_state, save_session_state
from src.ui.utils.init_session_state import init_session_state

# Page configuration
st.set_page_config(
    page_title="IFRS9 ECL Simulator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Initialize session state with default values
init_session_state()

# if "set_log" not in st.session_state:
#     #logger = setup_logging(log_level="INFO")
#     handler = ui_setup_logging()
#     #logger.addHandler(handler)
#     st.session_state.set_log = True

# Load saved session state if available (survives page refresh)
load_session_state()

# Apply custom CSS - Applied to all pages
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Define custom navigation
def home_page():
    """Home/Welcome page content"""

    # Welcome Page
    st.markdown("""
        <div class="main-header">
            <h1>📊 IFRS9 ECL Simulator</h1>
        </div>
    """, unsafe_allow_html=True)

    # Introduction
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## Welcome to ECL Simulator")
        
        st.markdown("""
            This application allows you to:
            
            - 🎯 **Create Multiple Simulations** with different scenarios
            - 📊 **Validate Data Quality** before calculations
            - 🧮 **Calculate ECL** using advanced models
            - 📈 **Analyze Results** with interactive visualizations
            - 💾 **Export Results** for reporting
        """)
        
        st.markdown("---")
        
        # Quick stats
        st.markdown("### Current Session Status")
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            num_sims = len(st.session_state.manager.simulations)
            st.metric(
                label="Simulations Created",
                value=num_sims,
                delta=None
            )
        
        with col_b:
            num_prepared = len(st.session_state.manager._prepared_simulations)
            st.metric(
                label="Simulations Prepared",
                value=num_prepared,
                delta=None
            )
        
        with col_c:
            status = "✅ Ready" if st.session_state.calculation_complete else "⏳ Pending"
            st.metric(
                label="Calculation Status",
                value=status,
                delta=None
            )
        
        st.markdown("---")
        
        # Navigation guide
        st.markdown("### 📍 Navigation Guide")
        
        st.markdown("""
            1. **Home** - Welcome page and quick overview
            2. **Simulation** - Create and configure your ECL simulations
            3. **Validation** - Review data quality and template validation
            4. **Results** - View, analyze, and export calculation results
        """)
        
        st.info("👈 Use the sidebar to navigate between pages")

        col_btn1,col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Create New Simulation", 
                         use_container_width=True, type="primary", icon=":material/arrow_forward:"):
                st.switch_page("app_pages/1_Simulation.py")
                

# Add logo to sidebar (optional - appears at top left)
st.logo("https://img.icons8.com/fluency/96/000000/financial-analytics.png")


# Navigation setup
pages = {
    "": [
        st.Page(home_page, title="Home", icon=":material/home:", default=True),
    ],
    
    "Operations": [
        st.Page("app_pages/1_Simulation.py", title="Simulation", icon=":material/target:"),
        st.Page("app_pages/2_Validation_REFACTORED.py", title="Validation", icon=":material/check_circle:"),
        st.Page("app_pages/3_Results.py", title="Results", icon=":material/bar_chart:"),
    ]
}
# Sidebar section for logs - must be created EVERY rerun
with st.sidebar:
    st.markdown("#### 📋 Application Logs")
       
    # Utiliser st.status() pour les mises à jour en temps réel
    status_area = st.status("Ready", expanded=False, state="complete")

if "set_log" not in st.session_state:
    # Setup logging configuration (console + file)
    setup_logging(log_level="INFO")
    
    # Get the ROOT logger to capture all module logs
    root_logger = logging.getLogger()
    
    # Remove any existing StreamlitLogHandler to avoid duplicates
    root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, StreamlitLogHandler)]
    
    # Add StreamlitLogHandler to root logger (without container initially)
    handler = StreamlitLogHandler(None)
    handler.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    st.session_state.log_handler = handler
    st.session_state.set_log = True
    
    # Log startup message
    logging.info("✅ Application started")

# Update the handler's status container (every rerun)
if st.session_state.get('log_handler'):
    handler = st.session_state.log_handler
    handler.status_container = status_area  # Update the status container for real-time updates
    
    # Display current log in status with appropriate state
    if handler.logs_buffer:
        state = "running" if handler.is_running else "complete"
        status_area.update(label=handler.logs_buffer[0], state=state)
    else:
        status_area.update(label="Ready", state="complete")

# Check for running calculations across all simulations
with st.sidebar:
    # Show calculation progress indicator if any calculation is running
    calculations_running = []
    for key in st.session_state:
        if key.startswith("ecl_calculation_") and isinstance(st.session_state[key], dict):
            sim_name = key.replace("ecl_calculation_", "")
            calc_state = st.session_state[key]
            if calc_state.get("running", False):
                calculations_running.append(sim_name)
    
    if calculations_running:
        st.markdown("---")
        st.warning(f"⏳ **Calculation in progress**")
        for sim in calculations_running:
            st.caption(f"📊 {sim}")
        st.caption("💡 You can navigate freely - calculations continue in background")

# Footer in sidebar
with st.sidebar:
    st.markdown("---")

    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">
        <div style='text-align: left; color: #24292e; padding: 10px 0; font-size: 12px;'>
            <p style='margin: 0; display: inline-flex; align-items: left; justify-content: left; gap: 5px;'>
                <span class="material-symbols-outlined" style='font-size: 14px;'>info</span>
                <span>IFRS9 ECL Simulator v1.0</span>
            </p>
        </div>
    """, unsafe_allow_html=True)

    # GitHub link with official GitHub logo
    st.markdown("""
        <div style='text-align: left; padding: 10px 0;'>
            <a href='https://github.com/Hcle18/IF9-Simulator' target='_blank' 
               style='text-decoration: none; color: #24292e; display: inline-flex; align-items: left; gap: 8px;'>
                <svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                <span style='font-size: 14px; color: #24292e;'>View on GitHub</span>
            </a>
        </div>
    """, unsafe_allow_html=True)



pg = st.navigation(pages)
pg.run()