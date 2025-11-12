# IFRS9 ECL Simulator - Streamlit Application

## 🎯 Overview

Professional multi-page Streamlit application for IFRS9 Expected Credit Loss (ECL) calculations with data validation, scenario management, and result visualization.

## 📁 Project Structure

```
streamlit_app/
├── app.py                      # Main entry point (Home page)
├── pages/
│   ├── 1_🎯_Simulation.py     # Simulation configuration
│   ├── 2_✅_Validation.py     # Data & template validation
│   └── 3_📊_Results.py        # Results analysis & export
├── utils/
│   ├── __init__.py
│   └── ui_components.py       # Reusable UI components
└── README.md
```

## 🚀 Features

### 1. **Home Page** (`app.py`)
- Welcome dashboard with session status
- Quick navigation to all pages
- Overview of current simulations
- Professional gradient header design

### 2. **Simulation Page** (`1_🎯_Simulation.py`)
- ➕ Create new simulations with custom names
- 📁 Upload data files (ZIP), templates (Excel), and Jarvis parameters
- 🔄 Add multiple contexts per simulation
- 📤 Submit and load simulations into SimulationManager
- 🎬 Trigger data loading and validation

### 3. **Validation Page** (`2_✅_Validation.py`)
- 📊 **Global Data Quality Metrics**:
  - Total records, missing values, duplicates
  - Column-level quality analysis
  - Data preview
  
- 📋 **Template Validation**:
  - Sheet-by-sheet validation
  - Completeness metrics
  - Data preview per sheet
  
- 🔍 **Detailed Analysis**:
  - Statistical summaries for numeric columns
  - Distribution analysis for categorical columns
  - Interactive column selection

- 🧮 **Run ECL Calculations** button to trigger computations

### 4. **Results Page** (`3_📊_Results.py`)
- 🎯 **Multi-Scenario ECL**:
  - Assign weights to each simulation (must sum to 100%)
  - Calculate weighted average ECL
  
- 📊 **Results Overview**:
  - Summary metrics per simulation
  - Data preview with key statistics
  
- 📈 **Visualization**:
  - ECL distribution histograms
  - Scenario comparison bar charts
  - Time series analysis
  - Custom scatter/line/bar charts
  
- 💾 **Export Options**:
  - Aggregate by custom columns
  - Download as CSV, Excel
  - Export summary statistics

## 🎨 Design Features

### Professional UI Components
- **Gradient Headers**: Eye-catching blue gradient headers
- **Metric Cards**: Color-coded cards for status (success/warning/error/info)
- **Status Badges**: Visual indicators for validation states
- **Consistent Color Scheme**:
  - 🟢 Success: Green (#2ca02c)
  - 🟡 Warning: Orange (#ff9800)
  - 🔴 Error: Red (#d62728)
  - 🔵 Info: Blue (#17a2b8)

### Responsive Layout
- Wide layout for better data visualization
- Multi-column layouts for efficient space usage
- Collapsible expanders for detailed information
- Tabs for organizing complex content

## 🔧 Installation & Setup

### Prerequisites
```bash
pip install streamlit pandas plotly openpyxl
```

### Running the Application

```bash
# From the project root directory
cd streamlit_app
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 📊 Usage Workflow

### Step 1: Create Simulations
1. Navigate to **🎯 Simulation** page
2. Enter simulation name
3. Select operation type and status
4. Add contexts:
   - Upload data file (ZIP)
   - Upload template file (Excel)
   - Optionally upload Jarvis parameter files
5. Click **Submit Simulation**
6. Click **Load & Validate Data**

### Step 2: Review Validation
1. Navigate to **✅ Validation** page
2. Review data quality metrics
3. Check template validation by sheet
4. Analyze detailed statistics
5. Click **Run ECL Calculations** when ready

### Step 3: Analyze Results
1. Navigate to **📊 Results** page
2. **Scenario Weighting** tab:
   - Assign weights to each scenario (total = 100%)
   - Calculate weighted ECL
3. **Results Overview** tab:
   - View summary metrics
   - Preview data
4. **Visualization** tab:
   - Create charts for analysis
5. **Export** tab:
   - Aggregate data by columns
   - Download as CSV or Excel

## 🛠️ Customization

### Adding New Validation Metrics
Edit `pages/2_✅_Validation.py`:
```python
# Add custom validation logic
def custom_validation(df):
    # Your validation code
    return validation_results
```

### Adding New Chart Types
Edit `pages/3_📊_Results.py`:
```python
# Add to chart_type options
chart_type = st.selectbox(
    "Select Chart Type",
    options=["...", "Your Custom Chart"]
)
```

### Modifying UI Colors
Edit `streamlit_app/utils/ui_components.py`:
```python
# Modify CSS variables
:root {
    --primary-color: #your_color;
    --success-color: #your_color;
}
```

## 📝 Session State Management

The app uses Streamlit session state to maintain:
- `manager`: SimulationManager instance
- `simulations_config`: List of simulation configurations
- `validation_complete`: Boolean flag for validation status
- `calculation_complete`: Boolean flag for calculation status
- `results`: Dictionary of calculation results
- `weighted_results`: Weighted ECL results

## 🔒 Best Practices

1. **Data Validation**: Always review validation results before calculations
2. **Scenario Weights**: Ensure weights sum to 100% before weighted ECL calculation
3. **Memory Management**: Clear session state when starting new analysis
4. **Export**: Aggregate data before export for large datasets

## 🐛 Troubleshooting

### Issue: "No simulations found"
**Solution**: Go back to Simulation page and create at least one simulation

### Issue: "Total weight must equal 100%"
**Solution**: Adjust scenario weights in the Results page until they sum to 100%

### Issue: Slow performance with large datasets
**Solution**: Use data aggregation before visualization/export

## 📈 Future Enhancements

- [ ] Add user authentication
- [ ] Save/load simulation configurations
- [ ] Advanced filtering options
- [ ] More chart types (heatmaps, treemaps)
- [ ] PDF report generation
- [ ] Real-time calculation progress bars
- [ ] Database integration for result storage

## 📞 Support

For issues or questions, please refer to the main project documentation.

---

**Version**: 1.0  
**Last Updated**: November 2025
