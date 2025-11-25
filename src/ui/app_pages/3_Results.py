"""
Results Analysis & Export Page
View, analyze, and export ECL calculation results
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import numpy as np

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
from src.ui.utils import ui_components as ui
from src.ui.utils.session_persistence import load_session_state, save_session_state
from src.ui.utils.init_session_state import init_session_state

st.set_page_config(
    page_title="Results Analysis",
    page_icon="📊",
    layout="wide"
)

# Initialize session state with default values
init_session_state()

# Custom CSS
st.markdown(ui.get_custom_css(), unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>📊 Results Analysis</h1>
        <p>Analyze and export your ECL calculation results</p>
    </div>
""", unsafe_allow_html=True)

# Check if calculations are complete
if not st.session_state.get("calculation_complete", False):
    st.warning("⚠️ No calculation results available yet.")
    if st.button("✅ Go to Validation Page"):
        st.switch_page("app_pages/2_Validation_REFACTORED.py")
    st.stop()



# ============================================== #
# RESULTS                                        #
# ============================================== #

# Get manager and simulations
manager = st.session_state.manager
simulations = manager.list_simulations()

# Create a tab for each simulation context + last tab for overall summary
list_tabs = [sim for sim in simulations]
list_tabs.append("Overall Summary")
tabs = st.tabs(list_tabs)

# Display each simulation context in its own tab
for idx, sim_name in enumerate(simulations):
    with tabs[idx]:
        st.markdown(f"### 📂 Simulation: {sim_name}")

        factory = manager.get_simulation(sim_name)

        # Get results DataFrame and display a preview
        results_df = factory.ecl_operation_data.df
        st.markdown("#### 📋 Results Data Preview")
        st.dataframe(results_df.head(10), use_container_width=True)

        # Toggle to fill scenario weighting and compute weighted ECL
        if "scenario_weighting" not in st.session_state:
            st.session_state.scenario_weighting = {}
        if sim_name not in st.session_state.scenario_weighting:
            st.session_state.scenario_weighting[sim_name] = {}

        # Initialize weight reset trigger
        if "reset_weights_trigger" not in st.session_state:
            st.session_state.reset_weights_trigger = {}
        if sim_name not in st.session_state.reset_weights_trigger:
            st.session_state.reset_weights_trigger[sim_name] = 0

        # Auto-open toggle if weights have been computed
        toggle_default_value = bool(st.session_state.scenario_weighting[sim_name])
        
        st.toggle("⚖️ Show/Hide Scenario Weighting Options", 
                  key=f"toggle_weighting_{sim_name}",
                  value=toggle_default_value)
        if st.session_state.get(f"toggle_weighting_{sim_name}", False):
            st.markdown("#### ⚖️ Scenario Weighting")
            
            scenarios = factory.ecl_operation_data.list_scenarios
            weights = {}
            total_weight = 0.0
            
            # Use reset trigger to force widget value reset
            reset_key = st.session_state.reset_weights_trigger[sim_name]
            
            for scenario in scenarios:
                col_name, col_weight = st.columns(2)
                with col_name:
                    st.write(f"**Scenario:** {scenario}")
                with col_weight:
                    weight = st.number_input(
                        label=f"Weight for {scenario}",
                        placeholder="Enter weight (0.0 - 1.0)",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state.scenario_weighting.get(sim_name, {}).get(scenario, 0.0),
                        step=0.01,
                        key=f"weight_{sim_name}_{scenario}_{reset_key}"
                    )
                    weights[scenario] = weight
                    total_weight += weight
            # Validate total weight
            col_total1, col_total2 = st.columns(2)
            with col_total1:
                st.write("**Total Weight:**")
            with col_total2:
                status_color = "🟢" if np.isclose(total_weight, 1.0) else "🔴"
                st.write(f"{status_color} **{total_weight*100:.2f}%**")
            if not np.isclose(total_weight, 1.0):
                st.error(f"❗ Total scenario weights must sum to 100% (current: {total_weight*100:.2f}%)")

            def trigger_compute_weighted():
                try:
                    factory.calcul_ecl_multi(weights)
                    # Save weights to session state
                    st.session_state.scenario_weighting[sim_name] = weights
                    st.success(f"✅ Weighted ECL computed successfully for {sim_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❗ Error computing weighted ECL: {e}")

            # Compute weighted ECL button available only if weights are valid
            weights_are_valid = np.isclose(total_weight, 1.0)
            
            if weights_are_valid:
                if st.session_state.scenario_weighting[sim_name] == {}:
                    # First computation
                    if st.button("Compute Weighted ECL", type="primary",
                                key=f"btn_compute_weighted_{sim_name}"):
                        with st.spinner("Computing weighted ECL..."):
                            trigger_compute_weighted()
                else:
                    # Check if weights changed
                    weights_changed = any(
                        st.session_state.scenario_weighting[sim_name].get(scen, 0.0) != weights[scen] 
                        for scen in scenarios
                    )
                    
                    if weights_changed:
                        col_retry, col_cancel = st.columns(2)
                        with col_retry:
                            # Retry with new weights
                            if st.button("Retry with New Weights", type="primary",
                                        key=f"btn_recompute_weighted_{sim_name}"):
                                trigger_compute_weighted()
                        with col_cancel:
                            if st.button("Cancel", type="secondary",
                                    key=f"btn_cancel_recompute_{sim_name}"):
                                # Increment reset trigger to recreate widgets with saved weights
                                st.session_state.reset_weights_trigger[sim_name] += 1
                                st.rerun()
                    else:
                        st.info("✅ Weighted ECL has already been computed with the provided weights.")


        