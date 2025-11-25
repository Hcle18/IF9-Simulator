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

# Get manager and simulations
manager = st.session_state.manager
simulations = manager.list_simulations()

# Tabs for different analyses
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Scenario Weighting", 
    "📊 Results Overview", 
    "📈 Visualization", 
    "💾 Export"
])

with tab1:
    st.markdown("### 🎯 Multi-Scenario ECL Calculation")
    
    st.info("""
        **Instructions:** Assign weights to each simulation for multi-scenario ECL calculation.
        The total weight should sum to 100%.
    """)
    
    # Scenario weights
    st.markdown("#### Define Scenario Weights")
    
    weights = {}
    total_weight = 0
    
    for sim_name in simulations:
        col_name, col_weight = st.columns([3, 1])
        
        with col_name:
            st.write(f"**{sim_name}**")
        
        with col_weight:
            weight = st.number_input(
                "Weight (%)",
                min_value=0.0,
                max_value=100.0,
                value=100.0 / len(simulations),
                step=1.0,
                key=f"weight_{sim_name}",
                label_visibility="collapsed"
            )
            weights[sim_name] = weight
            total_weight += weight
    
    # Validation
    col_total1, col_total2 = st.columns([3, 1])
    
    with col_total1:
        st.markdown("**Total Weight:**")
    
    with col_total2:
        status_color = "🟢" if abs(total_weight - 100) < 0.01 else "🔴"
        st.markdown(f"{status_color} **{total_weight:.2f}%**")
    
    if abs(total_weight - 100) > 0.01:
        st.error(f"⚠️ Total weight must equal 100% (current: {total_weight:.2f}%)")
    
    st.markdown("---")
    
    # Calculate weighted ECL
    if st.button("🧮 Calculate Weighted ECL", type="primary", disabled=(abs(total_weight - 100) > 0.01)):
        with st.spinner("Calculating weighted ECL..."):
            try:
                # Get results and calculate weighted average
                weighted_dfs = []
                
                for sim_name in simulations:
                    df = manager.get_results(sim_name)
                    weight_factor = weights[sim_name] / 100
                    
                    # Apply weight to ECL columns (assuming they contain 'ECL' in name)
                    ecl_cols = [col for col in df.columns if 'ECL' in col.upper()]
                    
                    weighted_df = df.copy()
                    for col in ecl_cols:
                        if pd.api.types.is_numeric_dtype(weighted_df[col]):
                            weighted_df[col] = weighted_df[col] * weight_factor
                    
                    weighted_df['scenario'] = sim_name
                    weighted_df['weight'] = weights[sim_name]
                    weighted_dfs.append(weighted_df)
                
                # Combine and aggregate
                combined_df = pd.concat(weighted_dfs, ignore_index=True)
                
                st.session_state.weighted_results = combined_df
                st.session_state.weights = weights
                
                st.success("✅ Weighted ECL calculated successfully!")
                
            except Exception as e:
                st.error(f"❌ Error calculating weighted ECL: {str(e)}")

with tab2:
    st.markdown("### 📊 Results Overview")
    
    # Simulation selector
    selected_sims = st.multiselect(
        "Select simulations to display",
        options=simulations,
        default=simulations[:3] if len(simulations) > 0 else []
    )
    
    if not selected_sims:
        st.info("Please select at least one simulation to display results.")
    else:
        # Display results for each simulation
        for sim_name in selected_sims:
            with st.expander(f"📋 {sim_name}", expanded=True):
                df = manager.get_results(sim_name)
                
                # Summary metrics
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                
                with col_m1:
                    ui.create_metric_card(
                        title="Total Records",
                        value=f"{len(df):,}",
                        status="info"
                    )
                
                # Assuming ECL column exists
                ecl_cols = [col for col in df.columns if 'ECL' in col.upper()]
                
                if ecl_cols:
                    total_ecl = df[ecl_cols[0]].sum() if len(df) > 0 else 0
                    
                    with col_m2:
                        ui.create_metric_card(
                            title=f"Total {ecl_cols[0]}",
                            value=f"{total_ecl:,.2f}",
                            status="success"
                        )
                    
                    avg_ecl = df[ecl_cols[0]].mean() if len(df) > 0 else 0
                    
                    with col_m3:
                        ui.create_metric_card(
                            title=f"Average {ecl_cols[0]}",
                            value=f"{avg_ecl:,.2f}",
                            status="info"
                        )
                    
                    with col_m4:
                        ui.create_metric_card(
                            title="Columns",
                            value=f"{len(df.columns):,}",
                            status="info"
                        )
                
                # Data preview
                st.markdown("##### 📋 Data Preview")
                st.dataframe(df.head(100), use_container_width=True)

with tab3:
    st.markdown("### 📈 Visual Analysis")
    
    if not simulations:
        st.info("No simulation results available for visualization.")
    else:
        # Chart type selector
        chart_type = st.selectbox(
            "Select Chart Type",
            options=["ECL Distribution", "Comparison by Scenario", "Time Series", "Custom Analysis"]
        )
        
        if chart_type == "ECL Distribution":
            selected_sim = st.selectbox(
                "Select Simulation",
                options=simulations,
                key="viz_sim_selector"
            )
            
            df = manager.get_results(selected_sim)
            ecl_cols = [col for col in df.columns if 'ECL' in col.upper()]
            
            if ecl_cols:
                selected_col = st.selectbox("Select ECL Column", options=ecl_cols)
                
                fig = px.histogram(
                    df,
                    x=selected_col,
                    title=f"Distribution of {selected_col}",
                    labels={selected_col: selected_col},
                    color_discrete_sequence=['#1f77b4']
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No ECL columns found in the results.")
        
        elif chart_type == "Comparison by Scenario":
            # Aggregate ECL by scenario
            scenario_data = []
            
            for sim_name in simulations:
                df = manager.get_results(sim_name)
                ecl_cols = [col for col in df.columns if 'ECL' in col.upper()]
                
                if ecl_cols:
                    total_ecl = df[ecl_cols[0]].sum()
                    scenario_data.append({
                        "Scenario": sim_name,
                        "Total ECL": total_ecl
                    })
            
            if scenario_data:
                scenario_df = pd.DataFrame(scenario_data)
                
                fig = px.bar(
                    scenario_df,
                    x="Scenario",
                    y="Total ECL",
                    title="Total ECL by Scenario",
                    color="Total ECL",
                    color_continuous_scale="Blues"
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "Custom Analysis":
            st.info("Select simulation and columns for custom analysis")
            
            selected_sim = st.selectbox(
                "Select Simulation",
                options=simulations,
                key="custom_viz_sim"
            )
            
            df = manager.get_results(selected_sim)
            
            col_x, col_y = st.columns(2)
            
            with col_x:
                x_col = st.selectbox("X-axis", options=df.columns, key="x_axis")
            
            with col_y:
                y_col = st.selectbox("Y-axis", options=df.columns, key="y_axis")
            
            chart_style = st.radio("Chart Style", ["Scatter", "Line", "Bar"], horizontal=True)
            
            if chart_style == "Scatter":
                fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
            elif chart_style == "Line":
                fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
            else:
                fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
            
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("### 💾 Export Results")
    
    # Aggregation options
    st.markdown("#### 📊 Data Aggregation")
    
    if not simulations:
        st.info("No simulation results available for export.")
    else:
        # Select simulations to export
        export_sims = st.multiselect(
            "Select Simulations to Export",
            options=simulations,
            default=simulations
        )
        
        if export_sims:
            # Group by options
            sample_df = manager.get_results(export_sims[0])
            
            group_by_cols = st.multiselect(
                "Group By Columns (optional)",
                options=sample_df.columns.tolist(),
                help="Select columns to aggregate by"
            )
            
            if group_by_cols:
                agg_method = st.selectbox(
                    "Aggregation Method",
                    options=["sum", "mean", "count", "min", "max"]
                )
                
                if st.button("📊 Generate Aggregated Results"):
                    with st.spinner("Aggregating data..."):
                        try:
                            aggregated_dfs = []
                            
                            for sim_name in export_sims:
                                df = manager.get_results(sim_name)
                                
                                # Aggregate
                                numeric_cols = df.select_dtypes(include=['number']).columns
                                agg_df = df.groupby(group_by_cols)[numeric_cols].agg(agg_method).reset_index()
                                agg_df['simulation'] = sim_name
                                
                                aggregated_dfs.append(agg_df)
                            
                            final_df = pd.concat(aggregated_dfs, ignore_index=True)
                            st.session_state.export_df = final_df
                            
                            st.success("✅ Aggregation complete!")
                            st.dataframe(final_df, use_container_width=True)
                            
                        except Exception as e:
                            st.error(f"❌ Error during aggregation: {str(e)}")
            
            st.markdown("---")
            st.markdown("#### 📥 Download Options")
            
            # Prepare export data
            if "export_df" in st.session_state:
                export_data = st.session_state.export_df
            else:
                # Combine all selected simulations
                combined_dfs = []
                for sim_name in export_sims:
                    df = manager.get_results(sim_name)
                    df['simulation'] = sim_name
                    combined_dfs.append(df)
                export_data = pd.concat(combined_dfs, ignore_index=True)
            
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                # CSV export
                csv_buffer = BytesIO()
                export_data.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name="ecl_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_exp2:
                # Excel export
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    export_data.to_excel(writer, sheet_name='Results', index=False)
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_buffer.getvalue(),
                    file_name="ecl_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col_exp3:
                # Summary statistics
                if st.button("📈 Download Summary Stats", use_container_width=True):
                    stats_buffer = BytesIO()
                    summary_stats = export_data.describe()
                    summary_stats.to_csv(stats_buffer)
                    stats_buffer.seek(0)
                    
                    st.download_button(
                        label="Download Stats",
                        data=stats_buffer.getvalue(),
                        file_name="ecl_summary_stats.csv",
                        mime="text/csv"
                    )

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>✅ Analysis complete. Results ready for download.</p>
    </div>
""", unsafe_allow_html=True)
