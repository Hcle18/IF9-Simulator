"""
Validation Page Helper Functions
Extracted logic for data validation, template validation, and ECL calculations
"""

import streamlit as st
import pandas as pd
import threading
import time
import warnings
import logging
from typing import Dict, Any, Optional
from src.ui.utils import ui_components as ui


# ============================================================================
# CALCULATION RESULT CONTAINER
# ============================================================================

class CalculationResult:
    """Thread-safe container for sharing calculation results"""
    def __init__(self):
        self.completed = False
        self.results = None
        self.error = None


# ============================================================================
# BACKGROUND CALCULATION THREAD
# ============================================================================

def run_calculation_thread(manager, result_container: CalculationResult):
    """
    Execute ECL calculation in background thread
    
    Args:
        manager: SimulationManager instance
        result_container: Shared CalculationResult object
    """
    # Suppress Streamlit ScriptRunContext warning in thread
    warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')
    streamlit_logger = logging.getLogger('streamlit.runtime.scriptrunner.script_runner')
    streamlit_logger.setLevel(logging.ERROR)
    
    try:
        results = manager.run_all_simulations()
        
        # Store in shared container
        result_container.results = results
        result_container.completed = True
        result_container.error = None
        
    except Exception as e:
        result_container.error = str(e)
        result_container.completed = False


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_validation_state(selected_sim: str, factory=None) -> Dict[str, Any]:
    """
    Initialize validation state for a simulation.
    If validation_complete is True, validations have already been run during 
    prepare_all_simulations(), so we pre-populate the state with results.
    
    Args:
        selected_sim: Simulation name
        factory: Operation factory instance (optional, for pre-loading results)
        
    Returns:
        Validation state dictionary
    """
    validation_key = f"validation_results_{selected_sim}"
    if validation_key not in st.session_state:
        # Check if simulations have already been prepared
        validation_complete = st.session_state.get("validation_complete", False)
        
        if validation_complete and factory:
            # Validations already done during prepare_all_simulations()
            # Pre-populate state with existing results
            
            # Get data validation result
            data_validation_result = factory.ecl_operation_data.data_validation_results
            data_is_valid = False
            if data_validation_result and hasattr(data_validation_result, 'errors'):
                data_is_valid = len(data_validation_result.errors) == 0
            
            # Get template validation result
            template_validation_result = factory.ecl_operation_data.template_validation_results
            template_is_valid = False
            if template_validation_result and hasattr(template_validation_result, 'is_valid'):
                template_is_valid = template_validation_result.is_valid
            
            # Get data and template data
            df = factory.ecl_operation_data.df
            template_data = factory.ecl_operation_data.template_data
            
            st.session_state[validation_key] = {
                "executed": True,
                "data_validation_done": True,
                "template_validation_done": True,
                "data_validation_result": data_validation_result,
                "template_validation_result": template_validation_result,
                "data_is_valid": data_is_valid,
                "template_is_valid": template_is_valid,
                "data_stats": None,
                "quality_df": None,
                "df": df.copy() if df is not None else None,
                "template_data": template_data,
                "auto_validation_passed": data_is_valid and template_is_valid
            }
        else:
            # Fresh state - validations not yet run
            st.session_state[validation_key] = {
                "executed": False,
                "data_validation_done": False,
                "template_validation_done": False,
                "data_validation_result": None,
                "template_validation_result": None,
                "data_is_valid": False,
                "template_is_valid": False,
                "data_stats": None,
                "quality_df": None,
                "df": None,
                "template_data": None,
                "auto_validation_passed": False
            }
    return st.session_state[validation_key]


def initialize_calculation_state(selected_sim: str) -> Dict[str, Any]:
    """
    Initialize ECL calculation state for a simulation
    
    Args:
        selected_sim: Simulation name
        
    Returns:
        Calculation state dictionary
    """
    ecl_calc_key = f"ecl_calculation_{selected_sim}"
    if ecl_calc_key not in st.session_state:
        st.session_state[ecl_calc_key] = {
            "executed": False,
            "running": False,
            "started": False,
            "results": None,
            "error": None,
            "thread": None,
            "result_container": None
        }
    return st.session_state[ecl_calc_key]


# ============================================================================
# DATA VALIDATION
# ============================================================================

def run_data_validation(factory, validation_state: Dict[str, Any]) -> pd.DataFrame:
    """
    Run data validation if not already done
    
    Args:
        factory: Operation factory instance
        validation_state: Validation state dictionary
        
    Returns:
        Validated DataFrame
    """
    if not validation_state["data_validation_done"]:
        with st.spinner("Running data validation..."):
            factory.validate_data()
        
        df = factory.ecl_operation_data.df
        validation_state["data_validation_done"] = True
        validation_state["df"] = df.copy()
        validation_state["executed"] = True
        
        # Get data validation result
        data_validation_result = factory.ecl_operation_data.data_validation_results
        validation_state["data_validation_result"] = data_validation_result
        
        # Check if data is valid (no errors)
        data_is_valid = False
        if data_validation_result and hasattr(data_validation_result, 'errors'):
            data_is_valid = len(data_validation_result.errors) == 0
        
        validation_state["data_is_valid"] = data_is_valid
        
        if data_is_valid:
            st.success("✅ Data validation completed successfully!")
        else:
            st.warning("⚠️ Data validation completed with errors. Review the results below.")
        
        return df
    else:
        st.info("📌 Displaying cached validation results (already executed)")
        return validation_state["df"]


def get_calculation_dataframe(factory, validation_state: Dict[str, Any], selected_sim: str) -> pd.DataFrame:
    """
    Get the DataFrame to use for calculations, applying scope filters if enabled.
    
    Args:
        factory: Operation factory instance
        validation_state: Validation state dictionary
        selected_sim: Simulation name for filter state
        
    Returns:
        DataFrame to use for calculations (filtered or original)
    """
    original_df = validation_state.get("df")
    if original_df is None:
        return factory.ecl_operation_data.df
    
    # Check if filters are applied
    filtered_df = render_data_scope_filter(original_df, selected_sim)
    
    if filtered_df is not None:
        # Update factory with filtered data
        factory.ecl_operation_data.df = filtered_df
        st.info(f"🎯 Using filtered dataset: {len(filtered_df):,} rows (from {len(original_df):,} original)")
        return filtered_df
    else:
        # Use original data
        return original_df


def display_data_quality_metrics(df: pd.DataFrame):
    """
    Display data quality metrics in columns
    
    Args:
        df: DataFrame to analyze
    """
    from src.ui.utils import ui_components as ui
    
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


def create_quality_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create column-level quality DataFrame
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Quality analysis DataFrame
    """
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
    
    return pd.DataFrame(quality_data)


# ============================================================================
# TEMPLATE VALIDATION
# ============================================================================

def run_template_validation(factory, validation_state: Dict[str, Any]):
    """
    Run template validation if not already done
    
    Args:
        factory: Operation factory instance
        validation_state: Validation state dictionary
        
    Returns:
        Validation result object
    """
    if not validation_state["template_validation_done"]:
        with st.spinner("Running template validation..."):
            validation_result = factory.validate_templates()
        
        validation_state["template_validation_done"] = True
        validation_state["template_validation_result"] = validation_result
        validation_state["template_data"] = factory.ecl_operation_data.template_data
        validation_state["executed"] = True
        
        # Check if template is valid
        template_is_valid = False
        if validation_result and hasattr(validation_result, 'is_valid'):
            template_is_valid = validation_result.is_valid
        
        validation_state["template_is_valid"] = template_is_valid
        
        return validation_result
    else:
        st.info("📌 Displaying cached validation results (already executed)")
        return validation_state["template_validation_result"]


def display_validation_summary(validation_result):
    """
    Display template validation summary
    
    Args:
        validation_result: Validation result object
    """
    if validation_result and hasattr(validation_result, 'is_valid'):
        if validation_result.is_valid:
            st.success(f"✅ Template validation passed for: {validation_result.template_name}")
        else:
            st.error(f"❌ Template validation failed for: {validation_result.template_name}")
        
        # Display errors
        if validation_result.errors:
            st.markdown("#### ❌ Validation Errors")
            for error in validation_result.errors:
                st.error(f"• {error}")
        
        # Display warnings
        if validation_result.warnings:
            st.markdown("#### ⚠️ Validation Warnings")
            for warning in validation_result.warnings:
                st.warning(f"• {warning}")
    else:
        st.success("✅ Template validation completed")


def display_template_sheets(template_data: Dict[str, pd.DataFrame]):
    """
    Display template sheets in tabs
    
    Args:
        template_data: Dictionary of sheet name -> DataFrame
    """
    
    
    if not template_data:
        st.warning("No template data found for this simulation.")
        return
    
    st.markdown("### 📄 Template Sheets Details")
    
    sheet_tabs = st.tabs([f"📄 {sheet}" for sheet in template_data.keys()])
    
    for idx, (sheet_name, sheet_data) in enumerate(template_data.items()):
        with sheet_tabs[idx]:
            if isinstance(sheet_data, pd.DataFrame):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    ui.create_metric_card(
                        title="Rows",
                        value=f"{len(sheet_data):,}",
                        status="info"
                    )
                
                with col2:
                    ui.create_metric_card(
                        title="Columns",
                        value=f"{len(sheet_data.columns):,}",
                        status="info"
                    )
                
                with col3:
                    missing_pct = (sheet_data.isnull().sum().sum() / 
                                 (len(sheet_data) * len(sheet_data.columns)) * 100)
                    ui.create_metric_card(
                        title="Completeness",
                        value=f"{100-missing_pct:.1f}%",
                        status="success" if missing_pct < 5 else "warning"
                    )
                
                st.markdown("##### Data Preview")
                st.dataframe(sheet_data, use_container_width=True)
            else:
                st.info(f"Sheet '{sheet_name}' contains non-tabular data")

# ============================================================================
# ADDITIONAL SCOPE FILTERS TO THE DATA
# ============================================================================

def render_data_scope_filter(df: pd.DataFrame, selected_sim: str) -> Optional[pd.DataFrame]:
    """
    Render UI for selecting a sub-scope of the DataFrame to reduce memory usage.
    
    Args:
        df: Original DataFrame
        selected_sim: Simulation name for session state key
        
    Returns:
        Filtered DataFrame or None if no filter applied
    """
    filter_key = f"data_filter_{selected_sim}"
    
    # Initialize session state for filters
    if filter_key not in st.session_state:
        st.session_state[filter_key] = {
            "enabled": False,
            "filters": {},
            "filtered_df": None,
            "confirmed": False,  # Track if filters have been confirmed
            "pending_filters": {}  # Temporary filters before confirmation
        }
    
    filter_state = st.session_state[filter_key]
    
    # Backward compatibility: add missing keys if they don't exist
    if "confirmed" not in filter_state:
        filter_state["confirmed"] = False
    if "pending_filters" not in filter_state:
        filter_state["pending_filters"] = {}
    
    with st.container(border=True):
        # Check if filters are already confirmed (locked)
        if filter_state["confirmed"]:
            st.success("✅ **Filters Applied and Locked**")
            st.info("⚠️ Filters have been permanently applied to this simulation. The filter configuration is now locked.")
            
            # Display applied filters summary
            st.markdown("#### 📋 Applied Filters:")
            for col, filter_config in filter_state["filters"].items():
                filter_type = filter_config["type"]
                filter_value = filter_config["value"]
                
                if filter_type == "range":
                    st.write(f"- **{col}**: Range [{filter_value[0]:.2f} - {filter_value[1]:.2f}]")
                elif filter_type == "date":
                    st.write(f"- **{col}**: Date range [{filter_value[0]} to {filter_value[1]}]")
                elif filter_type == "categorical":
                    st.write(f"- **{col}**: {len(filter_value)} values selected")
            
            # Display final statistics
            if filter_state["filtered_df"] is not None:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Original Rows", f"{len(df):,}")
                with col2:
                    st.metric("Filtered Rows", f"{len(filter_state['filtered_df']):,}")
            
            return filter_state["filtered_df"]
        
        # Filters not yet confirmed - allow configuration
        st.markdown("""
        Apply filters to work with a subset of your data.
        """)
        
        # Enable/disable filter
        filter_enabled = st.checkbox(
            "Enable data filtering",
            value=filter_state["enabled"],
            help="Apply filters to reduce the dataset size"
        )
        filter_state["enabled"] = filter_enabled
        
        if filter_enabled:
            st.markdown("---")
            st.markdown("#### Select Filters by Column")
            
            # Select columns to filter on
            available_columns = list(df.columns)
            selected_columns = st.multiselect(
                "Choose columns to filter:",
                options=available_columns,
                default=list(filter_state["filters"].keys()) if filter_state["filters"] else [],
                help="Select columns you want to filter on"
            )
            
            if selected_columns:
                st.markdown("---")
                st.markdown("#### Configure Filters")
                
                new_filters = {}
                
                for col in selected_columns:
                        with st.container(border=True):
                            st.markdown(f"**{col}** ({df[col].dtype})")
                            
                            # Different UI based on data type
                            if pd.api.types.is_numeric_dtype(df[col]):
                                # Numeric column - range filter
                                col_min = float(df[col].min())
                                col_max = float(df[col].max())
                                
                                filter_range = st.slider(
                                    f"Range for {col}:",
                                    min_value=col_min,
                                    max_value=col_max,
                                    value=(col_min, col_max),
                                    key=f"filter_range_{col}"
                                )
                                new_filters[col] = {"type": "range", "value": filter_range}
                            
                            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                                # Date column - date range
                                col_min = df[col].min().date()
                                col_max = df[col].max().date()
                                
                                date_range = st.date_input(
                                    f"Date range for {col}:",
                                    value=(col_min, col_max),
                                    key=f"filter_date_{col}"
                                )
                                new_filters[col] = {"type": "date", "value": date_range}
                            
                            else:
                                # Categorical/text column - multiselect
                                unique_values = df[col].dropna().unique()
                                
                                if len(unique_values) > 50:
                                    st.info(f"ℹ️ Column has {len(unique_values)} unique values. Showing first 50.")
                                    unique_values = sorted(unique_values)[:50]
                                
                                selected_values = st.multiselect(
                                    f"Select values for {col}:",
                                    options=sorted(unique_values),
                                    default=filter_state["filters"].get(col, {}).get("value", []),
                                    key=f"filter_cat_{col}"
                                )
                                
                                if selected_values:
                                    new_filters[col] = {"type": "categorical", "value": selected_values}
                
                filter_state["pending_filters"] = new_filters
                
                # Preview filters button
                st.markdown("---")
                if st.button("👁️ Preview Filtered Data", type="secondary", use_container_width=True):
                    filtered_df = apply_dataframe_filters(df, new_filters)
                    filter_state["filtered_df"] = filtered_df
                    st.rerun()
                
            else:
                st.info("👆 Select columns above to configure filters")
            
            # Display preview and confirmation
            if filter_state["filtered_df"] is not None and not filter_state["confirmed"]:
                st.markdown("---")
                st.markdown("#### 📊 Filtered Data Preview")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Original Rows", f"{len(df):,}")
                with col2:
                    st.metric("Filtered Rows", f"{len(filter_state['filtered_df']):,}")
                
                # Display first 10 rows of filtered data
                st.markdown("##### 📋 First 10 Rows of Filtered Data")
                st.dataframe(filter_state['filtered_df'].head(10), use_container_width=True)
                
                st.markdown("---")
                st.warning("⚠️ **Important Warning**", icon="⚠️")
                st.markdown("""
                **Once confirmed, these filters will be permanently applied to this simulation.**
                
                - ✅ The filtered dataset will be used for all ECL calculations
                - 🔒 Filter configuration will be locked and cannot be modified
                - ⚠️ This action is **IRREVERSIBLE**
                
                Please review the filtered data preview above before confirming.
                """)
                
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ Confirm and Lock Filters", type="primary", use_container_width=True):
                        filter_state["confirmed"] = True
                        filter_state["filters"] = filter_state["pending_filters"].copy()
                        st.success("✅ Filters confirmed and locked!")
                        st.rerun()
                
                with col_cancel:
                    if st.button("❌ Cancel and Modify", use_container_width=True):
                        filter_state["filtered_df"] = None
                        filter_state["pending_filters"] = {}
                        st.rerun()
        
        else:
            # Filter disabled - clear state
            if filter_state["filtered_df"] is not None:
                filter_state["filtered_df"] = None
                filter_state["filters"] = {}
    
    # Return filtered DataFrame if enabled, otherwise None
    return filter_state["filtered_df"] if filter_state["enabled"] else None


def apply_dataframe_filters(df: pd.DataFrame, filters: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """
    Apply multiple filters to a DataFrame.
    
    Args:
        df: Original DataFrame
        filters: Dictionary of column -> filter config
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    for col, filter_config in filters.items():
        if col not in df.columns:
            continue
        
        filter_type = filter_config["type"]
        filter_value = filter_config["value"]
        
        if filter_type == "range":
            # Numeric range filter
            min_val, max_val = filter_value
            filtered_df = filtered_df[
                (filtered_df[col] >= min_val) & (filtered_df[col] <= max_val)
            ]
        
        elif filter_type == "date":
            # Date range filter
            if len(filter_value) == 2:
                start_date, end_date = filter_value
                filtered_df = filtered_df[
                    (filtered_df[col] >= pd.Timestamp(start_date)) & 
                    (filtered_df[col] <= pd.Timestamp(end_date))
                ]
        
        elif filter_type == "categorical":
            # Categorical filter
            if filter_value:  # Only apply if values selected
                filtered_df = filtered_df[filtered_df[col].isin(filter_value)]
    
    return filtered_df


# ============================================================================
# ECL CALCULATION MANAGEMENT
# ============================================================================

def start_calculation_thread(manager, ecl_state: Dict[str, Any], ecl_calc_key: str):
    """
    Start ECL calculation in background thread
    
    Args:
        manager: SimulationManager instance
        ecl_state: Calculation state dictionary
        ecl_calc_key: Session state key for this calculation
    """
    if not ecl_state["started"] and not ecl_state["executed"]:
        ecl_state["started"] = True
        
        # Create result container
        result_container = CalculationResult()
        ecl_state["result_container"] = result_container
        
        # Launch thread
        calc_thread = threading.Thread(
            target=run_calculation_thread,
            args=(manager, result_container),
            daemon=True
        )
        calc_thread.start()
        ecl_state["thread"] = calc_thread


def check_calculation_status(ecl_state: Dict[str, Any], ecl_calc_key: str) -> str:
    """
    Check calculation status and update session state
    
    Args:
        ecl_state: Calculation state dictionary
        ecl_calc_key: Session state key for this calculation
        
    Returns:
        Status string: "running", "completed", "error", or "not_started"
    """
    result_container = ecl_state.get("result_container")
    calc_thread = ecl_state.get("thread")
    
    if calc_thread and calc_thread.is_alive():
        return "running"
    elif result_container and result_container.completed:
        # Update session state
        ecl_state["executed"] = True
        ecl_state["running"] = False
        ecl_state["results"] = result_container.results
        ecl_state["error"] = None
        st.session_state.calculation_complete = True
        st.session_state.results = result_container.results
        return "completed"
    elif result_container and result_container.error:
        # Error occurred
        ecl_state["running"] = False
        ecl_state["started"] = False
        ecl_state["error"] = result_container.error
        return "error"
    else:
        return "not_started"


def check_all_contexts_validated(manager) -> tuple[bool, list, list]:
    """
    Check if all simulation contexts have been automatically validated.
    
    Validation is automatic: context passes if both data and template validations
    complete successfully (template.is_valid == True).
    
    Args:
        manager: SimulationManager instance
        
    Returns:
        Tuple of (all_validated: bool, validated_contexts: list, missing_contexts: list)
    """
    simulations = manager.list_simulations()
    validated_contexts = []
    missing_contexts = []
    
    for sim_name in simulations:
        validation_key = f"validation_results_{sim_name}"
        
        # Check if validation state exists
        if validation_key not in st.session_state:
            missing_contexts.append(sim_name)
            continue
        
        validation_state = st.session_state[validation_key]
        
        # Check automatic validation status
        auto_validation_passed = validation_state.get("auto_validation_passed", False)
        
        if auto_validation_passed:
            validated_contexts.append(sim_name)
        else:
            missing_contexts.append(sim_name)
    
    all_validated = len(missing_contexts) == 0
    return all_validated, validated_contexts, missing_contexts


def display_calculation_ui(ecl_state: Dict[str, Any], manager, ecl_calc_key: str):
    """
    Display ECL calculation UI based on current state
    
    Args:
        ecl_state: Calculation state dictionary
        manager: SimulationManager instance
        ecl_calc_key: Session state key for this calculation
    """
    # Check if all contexts are validated
    all_validated, validated_contexts, missing_contexts = check_all_contexts_validated(manager)
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        if all_validated:
            st.success(f"✅ All {len(validated_contexts)} context(s) validated and confirmed!")
            st.info("🚀 You can now proceed with ECL calculations for all contexts.")
        else:
            st.warning(f"⚠️ {len(missing_contexts)} context(s) still need validation before running ECL calculations.")
            
            # Display missing contexts with detailed status
            with st.expander("📋 Show detailed validation status", expanded=False):
                st.markdown("### ✅ Validated Contexts:")
                if validated_contexts:
                    for ctx in validated_contexts:
                        st.success(f"✓ **{ctx}** - All validations passed, ready for calculation")
                else:
                    st.info("None yet")
                
                st.markdown("---")
                st.markdown("### ⚠️ Contexts Pending Validation:")
                if missing_contexts:
                    for ctx in missing_contexts:
                        validation_key = f"validation_results_{ctx}"
                        if validation_key in st.session_state:
                            val_state = st.session_state[validation_key]
                            data_done = val_state.get("data_validation_done", False)
                            template_done = val_state.get("template_validation_done", False)
                            
                            # Get data validation result
                            data_valid = val_state.get("data_is_valid", False)
                            
                            # Get template validation result
                            template_result = val_state.get("template_validation_result")
                            template_valid = False
                            if template_result and hasattr(template_result, 'is_valid'):
                                template_valid = template_result.is_valid
                            
                            status_parts = []
                            if not data_done:
                                status_parts.append("❌ Data validation pending")
                            elif data_valid:
                                status_parts.append("✅ Data validation passed")
                            else:
                                status_parts.append("❌ Data validation failed")
                            
                            if not template_done:
                                status_parts.append("❌ Template validation pending")
                            elif template_valid:
                                status_parts.append("✅ Template validation passed")
                            else:
                                status_parts.append("❌ Template validation failed")
                            
                            # Determine overall status
                            if data_done and template_done and data_valid and template_valid:
                                st.success(f"**{ctx}**")
                            elif data_done and template_done and (not data_valid or not template_valid):
                                error_msg = f"**{ctx}** - "
                                errors = []
                                if not data_valid:
                                    errors.append("Data errors")
                                if not template_valid:
                                    errors.append("Template errors")
                                error_msg += " & ".join(errors) + " found"
                                st.error(error_msg)
                            else:
                                st.warning(f"**{ctx}**")
                            
                            st.caption(" | ".join(status_parts))
                        else:
                            st.error(f"• **{ctx}** - Not started")
                else:
                    st.info("All validated!")
                
                st.markdown("---")
                st.info("💡 **Next steps:**\n1. Select a context from the dropdown above\n2. Run data validation (Tab 1)\n3. Run template validation (Tab 2)\n4. Validation is automatic - context passes if no errors found\n5. Repeat for all contexts")
    
    with col2:
        if ecl_state["running"]:
            # Calculation in progress
            st.warning("⏳ ECL Calculations in progress... Please wait.")
            st.info("💡 You can navigate to other pages. The calculation will continue in background.")
            
            # Start thread if needed
            start_calculation_thread(manager, ecl_state, ecl_calc_key)
            
            # Check status
            status = check_calculation_status(ecl_state, ecl_calc_key)
            
            if status == "running":
                st.caption("⏱️ Calculation running in background...")
                placeholder = st.empty()
                with placeholder:
                    st.info("🔄 Page will auto-refresh to check progress...")
                time.sleep(0.5)
                st.rerun()
            elif status == "completed":
                st.success("✅ Calculations completed successfully!")
                st.balloons()
                time.sleep(0.5)
                st.rerun()
            elif status == "error":
                st.error(f"❌ Error during calculation: {ecl_state['error']}")
                time.sleep(0.5)
                st.rerun()
        
        elif not ecl_state["executed"]:
            # Show button to start (only if all contexts validated)
            if all_validated:
                if st.button("🧮 Run ECL Calculations", type="primary", use_container_width=True):
                    ecl_state["running"] = True
                    ecl_state["started"] = False
                    st.rerun()
            else:
                # Button disabled with explanation
                st.button(
                    "🧮 Run ECL Calculations", 
                    type="primary", 
                    use_container_width=True,
                    disabled=True,
                    help=f"Complete validation for all {len(missing_contexts)} remaining context(s) first"
                )
                st.caption(f"⚠️ Validate all contexts first ({len(validated_contexts)}/{len(validated_contexts) + len(missing_contexts)} done)")
        
        else:
            # Already executed
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
    
    with col3:
        if ecl_state["executed"] and ecl_state["results"] is not None:
            if st.button("📊 View Results", use_container_width=True):
                st.switch_page("app_pages/3_Results.py")
