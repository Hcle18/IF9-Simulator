"""
IFRS9 ECL Simulation - Main Application Entry Point
Multi-page Streamlit application for ECL calculations
"""

import streamlit as st
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="IFRS9 ECL Simulator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
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
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    
    /* Card styling */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
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
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "manager" not in st.session_state:
    from src.factory import simulation_manager
    st.session_state.manager = simulation_manager.SimulationManager()

if "simulations_config" not in st.session_state:
    st.session_state.simulations_config = []

if "validation_complete" not in st.session_state:
    st.session_state.validation_complete = False

if "calculation_complete" not in st.session_state:
    st.session_state.calculation_complete = False

# Welcome Page
st.markdown("""
    <div class="main-header">
        <h1>📊 IFRS9 ECL Simulator</h1>
        <p>Professional Expected Credit Loss Calculation Platform</p>
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
        1. **🎯 Simulation** - Create and configure your ECL simulations
        2. **✅ Validation** - Review data quality and template validation
        3. **📊 Results** - View, analyze, and export calculation results
    """)
    
    st.info("👈 Use the sidebar to navigate between pages")
    
    # Quick actions
    st.markdown("### 🚀 Quick Actions")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("➕ Create New Simulation", use_container_width=True, type="primary"):
            st.switch_page("pages/1_🎯_Simulation.py")
    
    with col_btn2:
        if num_sims > 0:
            if st.button("📊 View Results", use_container_width=True):
                st.switch_page("pages/3_📊_Results.py")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>IFRS9 ECL Simulator v1.0 | Professional Credit Risk Management Platform</p>
    </div>
""", unsafe_allow_html=True)
