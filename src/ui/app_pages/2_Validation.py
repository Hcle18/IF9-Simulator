"""
Data & Template Validation Page
Review data quality and template validation before ECL calculations
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent

from src.ui.utils import ui_components as ui
from src.ui.utils.session_persistence import load_session_state, save_session_state
from src.ui.utils.init_session_state import init_session_state

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

# Check if simulations are prepared
if not st.session_state.get("validation_complete", False):
    st.warning("⚠️ No simulations prepared yet. Please create simulations first.")
    if st.button("🎯 Go to Simulation Page"):
        st.switch_page("pages/1_🎯_Simulation.py")
    st.stop()

# Get manager
manager = st.session_state.manager
simulations = manager.list_simulations()

if len(simulations) == 0:
    st.error("No simulations found!")
    st.stop()

# Simulation selector
selected_sim = st.selectbox(
    "Select Simulation to Review",
    options=simulations,
    key="validation_sim_selector"
)

factory = manager.get_simulation(selected_sim)

# Tabs for different validation aspects
tab1, tab2, tab3 = st.tabs(["📊 Data Quality", "📋 Template Validation", "🔍 Detailed Analysis"])

with tab1:
    st.markdown("### 📊 Data Validation Results")
    
    # Run data validation using OperationFactory method
    try:
        with st.spinner("Running data validation..."):
            factory.validate_data()
        
        st.success("✅ Data validation completed successfully!")
        
        # Get data statistics
        df = factory.ecl_operation_data.df
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            ui.create_metric_card(
                title="Total Records",
                value=f"{len(df):,}",
                status="success" if len(df) > 0 else "error"
            )
        
        with col2:
            missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100)
            ui.create_metric_card(
                title="Missing Values",
                value=f"{missing_pct:.2f}%",
                status="success" if missing_pct < 5 else ("warning" if missing_pct < 15 else "error")
            )
        
        with col3:
            duplicate_count = df.duplicated().sum()
            ui.create_metric_card(
                title="Duplicates",
                value=f"{duplicate_count:,}",
                status="success" if duplicate_count == 0 else "warning"
            )
        
        with col4:
            ui.create_metric_card(
                title="Columns",
                value=f"{len(df.columns):,}",
                status="info"
            )
        
        st.markdown("---")
        
        # Column-level quality
        st.markdown("#### Column-Level Data Quality")
        
        quality_data = []
        for col in df.columns:
            missing = df[col].isnull().sum()
            missing_pct = (missing / len(df)) * 100
            dtype = str(df[col].dtype)
            unique = df[col].nunique()
            
            quality_data.append({
                "Column": col,
                "Type": dtype,
                "Missing": missing,
                "Missing %": f"{missing_pct:.2f}%",
                "Unique Values": unique,
                "Status": "✅" if missing_pct < 5 else ("⚠️" if missing_pct < 15 else "❌")
            })
        
        quality_df = pd.DataFrame(quality_data)
        
        st.dataframe(
            quality_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Data preview
        st.markdown("#### 📋 Data Preview (First 100 rows)")
        st.dataframe(df.head(100), use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Data validation failed: {str(e)}")
        st.exception(e)

with tab2:
    st.markdown("### 📋 Template Validation Results")
    
    # Run template validation using OperationFactory method
    try:
        with st.spinner("Running template validation..."):
            validation_result = factory.validate_templates()
        
        # Display validation summary
        if validation_result and hasattr(validation_result, 'is_valid'):
            if validation_result.is_valid:
                st.success(f"✅ Template validation passed for: {validation_result.template_name}")
            else:
                st.error(f"❌ Template validation failed for: {validation_result.template_name}")
            
            # Display errors if any
            if validation_result.errors:
                st.markdown("#### ❌ Validation Errors")
                for error in validation_result.errors:
                    st.error(f"• {error}")
            
            # Display warnings if any
            if validation_result.warnings:
                st.markdown("#### ⚠️ Validation Warnings")
                for warning in validation_result.warnings:
                    st.warning(f"• {warning}")
        else:
            st.success("✅ Template validation completed")
        
        st.markdown("---")
        
        # Get template data
        template_data = factory.ecl_operation_data.template_data
        
        if not template_data:
            st.warning("No template data found for this simulation.")
        else:
            st.markdown("### 📄 Template Sheets Details")
            
            # Create tabs for each sheet
            sheet_tabs = st.tabs([f"📄 {sheet}" for sheet in template_data.keys()])
            
            for idx, (sheet_name, sheet_data) in enumerate(template_data.items()):
                with sheet_tabs[idx]:
                    col_sheet1, col_sheet2, col_sheet3 = st.columns(3)
                    
                    # Sheet metrics
                    if isinstance(sheet_data, pd.DataFrame):
                        with col_sheet1:
                            ui.create_metric_card(
                                title="Rows",
                                value=f"{len(sheet_data):,}",
                                status="info"
                            )
                        
                        with col_sheet2:
                            ui.create_metric_card(
                                title="Columns",
                                value=f"{len(sheet_data.columns):,}",
                                status="info"
                            )
                        
                        with col_sheet3:
                            missing_pct = (sheet_data.isnull().sum().sum() / 
                                         (len(sheet_data) * len(sheet_data.columns)) * 100)
                            ui.create_metric_card(
                                title="Completeness",
                                value=f"{100-missing_pct:.1f}%",
                                status="success" if missing_pct < 5 else "warning"
                            )
                        
                        # Display data
                        st.markdown("##### Data Preview")
                        st.dataframe(sheet_data, use_container_width=True)
                    else:
                        st.info(f"Sheet '{sheet_name}' contains non-tabular data")
        
    except Exception as e:
        st.error(f"❌ Template validation failed: {str(e)}")
        st.exception(e)

with tab3:
    st.markdown("### 🔍 Detailed Statistical Analysis")
    
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        # Numeric columns analysis
        st.markdown("#### 📈 Numeric Columns Statistics")
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            st.dataframe(
                df[numeric_cols].describe(),
                use_container_width=True
            )
        else:
            st.info("No numeric columns found")
    
    with col_stat2:
        # Categorical columns analysis
        st.markdown("#### 📊 Categorical Columns Distribution")
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        if len(categorical_cols) > 0:
            selected_cat = st.selectbox(
                "Select column to analyze",
                options=categorical_cols
            )
            
            value_counts = df[selected_cat].value_counts().head(10)
            st.bar_chart(value_counts)
        else:
            st.info("No categorical columns found")

# Action buttons
st.markdown("---")
st.markdown("### 🚀 Ready to Calculate?")

col_calc1, col_calc2, col_calc3 = st.columns([2, 2, 1])

with col_calc1:
    st.info("📝 Data validation complete. Review the quality metrics above before proceeding.")

with col_calc2:
    if st.button("🧮 Run ECL Calculations", type="primary", use_container_width=True):
        with st.spinner("Running ECL calculations..."):
            try:
                # Run calculations
                results = manager.run_all_simulations()
                st.session_state.calculation_complete = True
                st.session_state.results = results
                
                st.success("✅ Calculations completed successfully!")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Error during calculation: {str(e)}")

with col_calc3:
    if st.session_state.get("calculation_complete", False):
        if st.button("📊 View Results", use_container_width=True):
            st.switch_page("pages/3_📊_Results.py")
