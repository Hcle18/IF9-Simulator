"""
Data & Template Validation Page (REFACTORED)
Review data quality and template validation before ECL calculations
"""

import streamlit as st
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent

from src.ui.utils import ui_components as ui
from src.ui.utils.session_persistence import load_session_state, save_session_state
from src.ui.utils.init_session_state import init_session_state
from src.ui.utils.validation_helpers import (
    initialize_validation_state,
    initialize_calculation_state,
    run_data_validation,
    display_data_quality_metrics,
    create_quality_dataframe,
    run_template_validation,
    display_validation_summary,
    display_template_sheets,
    display_calculation_ui,
    get_calculation_dataframe
)


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Data Validation",
    page_icon="✅",
    layout="wide"
)

# Initialize session state with default values
init_session_state()

# Custom CSS
st.markdown(ui.get_custom_css(), unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>✅ Data & Template Validation</h1>
        <p>Review data quality before running ECL calculations</p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# PRE-CHECKS
# ============================================================================

# Check if simulations are prepared
if not st.session_state.get("validation_complete", False):
    st.warning("⚠️ No simulations prepared yet. Please create simulations first.")
    if st.button("🎯 Go to Simulation Page"):
        st.switch_page("pages/1_🎯_Simulation.py")
    st.stop()

# Get manager and simulations
manager = st.session_state.manager
simulations = manager.list_simulations()

if len(simulations) == 0:
    st.error("No simulations found!")
    st.stop()

# ============================================================================
# SIMULATION SELECTOR
# ============================================================================

col_sel1, col_sel2 = st.columns([3, 1])

with col_sel1:
    selected_sim = st.selectbox(
        "Select Simulation to Review",
        options=simulations,
        key="validation_sim_selector"
    )

with col_sel2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Reset Validation", help="Re-run validation from scratch"):
        validation_key = f"validation_results_{selected_sim}"
        if validation_key in st.session_state:
            del st.session_state[validation_key]
        st.rerun()

factory = manager.get_simulation(selected_sim)

# Initialize states
validation_state = initialize_validation_state(selected_sim)
ecl_state = initialize_calculation_state(selected_sim)

# Show status of cached validations
if validation_state["executed"]:
    st.info("✨ Validation results are cached. Use '🔄 Reset Validation' to re-run.", icon="📌")

# ============================================================================
# VALIDATION TABS
# ============================================================================

tab1, tab2, tab3 = st.tabs(["📊 Data Quality", "📋 Template Validation", "🔍 Detailed Analysis"])

# ----------------------------------------------------------------------------
# TAB 1: DATA QUALITY
# ----------------------------------------------------------------------------
with tab1:
    st.markdown("### 📊 Data Validation Results")
    
    try:
        # Run validation (or use cached results)
        df = run_data_validation(factory, validation_state)
        
        # Display metrics
        display_data_quality_metrics(df)
        
        st.markdown("---")
        
        # Column-level quality
        st.markdown("#### Column-Level Data Quality")
        quality_df = create_quality_dataframe(df)
        
        if not validation_state.get("quality_df") is not None:
            validation_state["quality_df"] = quality_df
        
        st.dataframe(quality_df, use_container_width=True, hide_index=True)
        
        # Data preview
        st.markdown("#### 📋 Data Preview (First 100 rows)")
        st.dataframe(df.head(100), use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error during data validation: {str(e)}")
        st.exception(e)

# ----------------------------------------------------------------------------
# TAB 2: TEMPLATE VALIDATION
# ----------------------------------------------------------------------------
with tab2:
    st.markdown("### 📋 Template Validation Results")
    
    try:
        # Run validation (or use cached results)
        validation_result = run_template_validation(factory, validation_state)
        
        # Display summary
        display_validation_summary(validation_result)
        
        st.markdown("---")
        
        # Get template data
        template_data = validation_state.get("template_data") or factory.ecl_operation_data.template_data
        
        # Display sheets
        display_template_sheets(template_data)
        
    except Exception as e:
        st.error(f"❌ Error during template validation: {str(e)}")
        st.exception(e)

# ----------------------------------------------------------------------------
# TAB 3: DETAILED ANALYSIS
# ----------------------------------------------------------------------------
with tab3:
    st.markdown("### 🔍 Detailed Statistical Analysis")
    
    df_analysis = validation_state.get("df")
    
    if df_analysis is None:
        st.warning("⚠️ Please run data validation first (Tab: Data Quality)")
        st.stop()
    
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        st.markdown("#### 📈 Numeric Columns Statistics")
        numeric_cols = df_analysis.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            st.dataframe(df_analysis[numeric_cols].describe(), use_container_width=True)
        else:
            st.info("No numeric columns found")
    
    with col_stat2:
        st.markdown("#### 📊 Categorical Columns Distribution")
        categorical_cols = df_analysis.select_dtypes(include=['object', 'category']).columns
        if len(categorical_cols) > 0:
            selected_cat = st.selectbox("Select column to analyze", options=categorical_cols)
            value_counts = df_analysis[selected_cat].value_counts().head(10)
            st.bar_chart(value_counts)
        else:
            st.info("No categorical columns found")


# ============================================================================
# ADDITIONAL SCOPE FILTERS TO THE DATA
# ============================================================================
st.markdown("#### 🔍 (Optional) Data Scope Filter")
df_for_calc = get_calculation_dataframe(factory, validation_state, selected_sim)


# ============================================================================
# ECL CALCULATION SECTION
# ============================================================================

st.markdown("---")
st.markdown("### 🚀 Ready to Calculate?")

# Display calculation UI
ecl_calc_key = f"ecl_calculation_{selected_sim}"
display_calculation_ui(ecl_state, manager, ecl_calc_key)
