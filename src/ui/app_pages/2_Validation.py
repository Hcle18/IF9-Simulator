"""
Data & Template Validation Page
Review data quality and template validation before ECL calculations
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import threading
import time
import warnings
import logging

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

# Simulation selector with reset button
col_sel1, col_sel2 = st.columns([3, 1])

# Simulation selection
with col_sel1:
    selected_sim = st.selectbox(
        "Select Simulation to Review",
        options=simulations,
        key="validation_sim_selector"
    )

# Reset button
with col_sel2:
    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
    if st.button("🔄 Reset Validation", help="Re-run validation from scratch"):
        # Clear cached validation results for this simulation
        validation_key = f"validation_results_{selected_sim}"
        if validation_key in st.session_state:
            del st.session_state[validation_key]
        st.rerun()

# Get factory for selected simulation
factory = manager.get_simulation(selected_sim)

# Initialize validation results storage for this simulation if first time
validation_key = f"validation_results_{selected_sim}"
if validation_key not in st.session_state:
    st.session_state[validation_key] = {
        "executed": False,
        "data_validation_done": False,
        "template_validation_done": False,
        "data_validation_result": None,
        "template_validation_result": None,
        "data_stats": None,
        "quality_df": None,
        "df": None,
        "template_data": None
    }

# Show status of cached validations
validation_state = st.session_state[validation_key]
if validation_state["executed"]:
    st.info("✨ Validation results are cached. Use '🔄 Reset Validation' to re-run.", icon="📌")

# Tabs for different validation aspects
tab1, tab2, tab3 = st.tabs(["📊 Data Quality", "📋 Template Validation", "🔍 Detailed Analysis"])

with tab1:
    st.markdown("### 📊 Data Validation Results")
    
    # Run data validation ONLY if not already done
    validation_state = st.session_state[validation_key]
    
    if not validation_state["data_validation_done"]:
        try:
            with st.spinner("Running data validation..."):
                factory.validate_data()
            
            # Store results
            df = factory.ecl_operation_data.df
            validation_state["data_validation_done"] = True
            validation_state["df"] = df.copy()  # Store a copy
            validation_state["executed"] = True
            
            st.success("✅ Data validation completed successfully!")
        except Exception as e:
            st.error(f"❌ Data validation failed: {str(e)}")
            st.exception(e)
            st.stop()
    else:
        # Use stored results
        df = validation_state["df"]
        st.info("📌 Displaying cached validation results (already executed)")
    
    try:
        # Get data statistics (same code, but using stored df)
        
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
        
        # Store quality_df for reuse
        if not validation_state.get("quality_df") is not None:
            validation_state["quality_df"] = quality_df
        
        st.dataframe(
            quality_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Data preview
        st.markdown("#### 📋 Data Preview (First 100 rows)")
        st.dataframe(df.head(100), use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error displaying data validation: {str(e)}")
        st.exception(e)

with tab2:
    st.markdown("### 📋 Template Validation Results")
    
    # Run template validation ONLY if not already done
    if not validation_state["template_validation_done"]:
        try:
            with st.spinner("Running template validation..."):
                validation_result = factory.validate_templates()
            
            # Store results
            validation_state["template_validation_done"] = True
            validation_state["template_validation_result"] = validation_result
            validation_state["template_data"] = factory.ecl_operation_data.template_data
            validation_state["executed"] = True
            
        except Exception as e:
            st.error(f"❌ Template validation failed: {str(e)}")
            st.exception(e)
            st.stop()
    else:
        # Use stored results
        validation_result = validation_state["template_validation_result"]
        st.info("📌 Displaying cached validation results (already executed)")
    
    try:
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
        
        # Get template data (from cache or factory)
        template_data = validation_state.get("template_data") or factory.ecl_operation_data.template_data
        
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
        st.error(f"❌ Error displaying template validation: {str(e)}")
        st.exception(e)

with tab3:
    st.markdown("### 🔍 Detailed Statistical Analysis")
    
    # Use cached df if available
    df_analysis = validation_state.get("df")
    
    if df_analysis is None:
        st.warning("⚠️ Please run data validation first (Tab: Data Quality)")
        st.stop()
    
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        # Numeric columns analysis
        st.markdown("#### 📈 Numeric Columns Statistics")
        numeric_cols = df_analysis.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            st.dataframe(
                df_analysis[numeric_cols].describe(),
                use_container_width=True
            )
        else:
            st.info("No numeric columns found")
    
    with col_stat2:
        # Categorical columns analysis
        st.markdown("#### 📊 Categorical Columns Distribution")
        categorical_cols = df_analysis.select_dtypes(include=['object', 'category']).columns
        if len(categorical_cols) > 0:
            selected_cat = st.selectbox(
                "Select column to analyze",
                options=categorical_cols
            )
            
            value_counts = df_analysis[selected_cat].value_counts().head(10)
            st.bar_chart(value_counts)
        else:
            st.info("No categorical columns found")

# Action buttons
st.markdown("---")
st.markdown("### 🚀 Ready to Calculate?")

# Initialize ECL calculation state for this simulation
ecl_calc_key = f"ecl_calculation_{selected_sim}"
if ecl_calc_key not in st.session_state:
    st.session_state[ecl_calc_key] = {
        "executed": False,
        "running": False,
        "started": False,  # Verrou pour éviter les relances multiples
        "results": None,
        "error": None,
        "thread": None,
        "sim_name": selected_sim  # Store sim name for cache
    }

ecl_state = st.session_state[ecl_calc_key]

# Helper function to compute configuration hash
def compute_config_hash(factory):
    """Create unique hash based on data files and templates to detect config changes"""
    import hashlib
    
    try:
        # Get simulation configuration
        config_str = ""
        
        # Add operation type and status
        config_str += str(factory.operation_type.value)
        config_str += str(factory.operation_status.value)
        
        # Add data file info (size + modification time)
        if hasattr(factory, 'ecl_operation_data') and factory.ecl_operation_data:
            data = factory.ecl_operation_data
            if hasattr(data, 'df') and data.df is not None:
                # Use dataframe shape and column names as signature
                config_str += str(data.df.shape)
                config_str += str(list(data.df.columns))
            
            # Add template info
            if hasattr(data, 'template_data') and data.template_data:
                for sheet_name, sheet_df in data.template_data.items():
                    if isinstance(sheet_df, pd.DataFrame):
                        config_str += sheet_name
                        config_str += str(sheet_df.shape)
        
        # Generate hash
        return hashlib.md5(config_str.encode()).hexdigest()
    except:
        # If we can't compute hash, return timestamp-based value
        return str(int(time.time()))

# Try to load cached results if page was refreshed during calculation
if not ecl_state["executed"] and not ecl_state["running"]:
    try:
        import pickle
        cache_dir = Path(__file__).parent.parent.parent.parent / "cache"
        cache_file = cache_dir / f"ecl_results_{selected_sim}.pkl"
        
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
            
            # Compute current configuration hash
            current_hash = compute_config_hash(factory)
            cached_hash = cached_data.get('config_hash', None)
            
            # Check if cache is recent AND configuration matches
            cache_age = time.time() - cached_data.get('timestamp', 0)
            config_matches = (current_hash == cached_hash)
            
            if cache_age < 3600 and config_matches:  # 1 hour and same config
                ecl_state["results"] = cached_data['results']
                ecl_state["executed"] = True
                st.session_state.calculation_complete = True
                st.session_state.results = cached_data['results']
                st.info("✨ Loaded cached calculation results (from previous session)")
            elif not config_matches:
                # Configuration changed - delete old cache
                cache_file.unlink()
                st.info("🔄 Configuration changed - cache invalidated")
    except Exception as e:
        # Loading cache is optional, don't fail if it doesn't work
        pass

# Shared result container (thread-safe)
class CalculationResult:
    def __init__(self):
        self.completed = False
        self.results = None
        self.error = None

# Function to run calculations in background thread
def run_calculation_thread(manager, result_container, ecl_state, config_hash):
    """Execute ECL calculation in background thread"""
    import pickle
    from pathlib import Path
    
    # Suppress Streamlit ScriptRunContext warning in thread
    warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')
    
    # Also suppress in logger if it appears there
    streamlit_logger = logging.getLogger('streamlit.runtime.scriptrunner.script_runner')
    streamlit_logger.setLevel(logging.ERROR)
    
    try:
        results = manager.run_all_simulations()
        
        # Check if calculation was invalidated during execution (e.g., Clear Simulation)
        if ecl_state.get("invalidated", False):
            # Don't store results - calculation was cancelled
            result_container.completed = False
            result_container.error = "Calculation cancelled (simulation cleared)"
            return
        
        # Store in shared container
        result_container.results = results
        result_container.completed = True
        result_container.error = None
        
        # BONUS: Persist to file to survive page refresh
        try:
            cache_dir = Path(__file__).parent.parent.parent.parent / "cache"
            cache_dir.mkdir(exist_ok=True)
            cache_file = cache_dir / f"ecl_results_{ecl_state.get('sim_name', 'default')}.pkl"
            
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'results': results,
                    'completed': True,
                    'timestamp': time.time(),
                    'config_hash': config_hash  # Save hash to validate later
                }, f)
        except Exception as e:
            # Persisting is optional, don't fail if it doesn't work
            logging.warning(f"Failed to persist results to cache: {e}")
        
    except Exception as e:
        result_container.error = str(e)
        result_container.completed = False

col_calc1, col_calc2, col_calc3 = st.columns([2, 2, 1])

with col_calc1:
    st.info("📝 Data validation complete. Review the quality metrics above before proceeding.")

with col_calc2:
    # Show different UI based on execution state
    if ecl_state["running"]:
        # Calculation in progress
        st.warning("⏳ ECL Calculations in progress... Please wait.")
        st.info("💡 You can navigate to other pages. The calculation will continue in background.")
        st.error("⚠️ **WARNING:** Do NOT refresh the page (F5) during calculation or results will be lost!")
        
        # Start thread ONLY if not yet started
        if not ecl_state["started"] and not ecl_state["executed"]:
            ecl_state["started"] = True  # Marquer comme démarré IMMÉDIATEMENT
            
            # Compute configuration hash BEFORE starting thread
            config_hash = compute_config_hash(factory)
            ecl_state["config_hash"] = config_hash
            
            # Create result container
            result_container = CalculationResult()
            ecl_state["result_container"] = result_container
            
            # Launch calculation in background thread
            calc_thread = threading.Thread(
                target=run_calculation_thread,
                args=(manager, result_container, ecl_state, config_hash),
                daemon=True
            )
            calc_thread.start()
            ecl_state["thread"] = calc_thread
        
        # Check thread status and result container
        result_container = ecl_state.get("result_container")
        calc_thread = ecl_state.get("thread")
        
        # Check if calculation was invalidated (e.g., Clear Simulation clicked)
        if ecl_state.get("invalidated", False):
            st.warning("⚠️ Calculation was cancelled (simulation cleared)")
            ecl_state["running"] = False
            ecl_state["started"] = False
            time.sleep(1)
            st.rerun()
        elif calc_thread and calc_thread.is_alive():
            # Still running - show progress and schedule refresh
            st.caption(f"⏱️ Calculation running in background...")
            placeholder = st.empty()
            with placeholder:
                st.info("🔄 Page will auto-refresh to check progress...")
            time.sleep(0.5)
            st.rerun()
        elif result_container and result_container.error:
            # Error occurred (including cancellation)
            ecl_state["running"] = False
            ecl_state["started"] = False
            ecl_state["error"] = result_container.error
            st.error(f"❌ Error during calculation: {result_container.error}")
            time.sleep(0.5)
            st.rerun()
        elif result_container and result_container.completed:
            # Calculation finished! Update session_state
            ecl_state["executed"] = True
            ecl_state["running"] = False
            ecl_state["results"] = result_container.results
            ecl_state["error"] = None
            st.session_state.calculation_complete = True
            st.session_state.results = result_container.results
            
            st.success("✅ Calculations completed successfully!")
            st.balloons()
            time.sleep(0.5)
            st.rerun()
    
    elif not ecl_state["executed"]:
        # First time - show button to run
        if st.button("🧮 Run ECL Calculations", type="primary", use_container_width=True):
            # Mark as running (le thread sera lancé au prochain rerun)
            ecl_state["running"] = True
            ecl_state["started"] = False  # Reset pour le prochain cycle
            st.rerun()  # Rerun to start execution
    else:
        # Already executed - show status
        if ecl_state["error"]:
            st.error(f"❌ Calculation failed: {ecl_state['error']}")
            if st.button("🔄 Retry Calculation", type="primary", use_container_width=True):
                ecl_state["executed"] = False
                ecl_state["running"] = False
                ecl_state["started"] = False
                ecl_state["error"] = None
                st.rerun()
        else:
            st.success("✅ ECL Calculations already completed!", icon="📌")
            if st.button("🔄 Re-run Calculations", use_container_width=True):
                ecl_state["executed"] = False
                ecl_state["running"] = False
                ecl_state["started"] = False
                ecl_state["results"] = None
                st.rerun()

with col_calc3:
    if ecl_state["executed"] and ecl_state["results"] is not None:
        if st.button("📊 View Results", use_container_width=True):
            st.switch_page("app_pages/3_Results.py")
