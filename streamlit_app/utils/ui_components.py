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
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
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
