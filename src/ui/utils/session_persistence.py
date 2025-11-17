"""
Session persistence utilities for Streamlit
Save and load session state to survive page refreshes
"""

import streamlit as st
import pickle
import json
from pathlib import Path
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

# Default persistence directory
PERSISTENCE_DIR = Path(".streamlit_cache")
PERSISTENCE_DIR.mkdir(exist_ok=True)

def get_session_file() -> Path:
    """Get the session file path based on session ID"""
    # Use Streamlit's session ID if available
    session_id = st.runtime.scriptrunner.get_script_run_ctx().session_id
    return PERSISTENCE_DIR / f"session_{session_id}.pkl"

def save_session_state(keys: list = None):
    """
    Save specified session state keys to disk
    
    Args:
        keys: List of session state keys to save. If None, saves all except internal keys
    """
    try:
        session_file = get_session_file()
        
        # Determine which keys to save
        if keys is None:
            # Save all keys except internal Streamlit keys
            keys_to_save = [k for k in st.session_state.keys() 
                          if not k.startswith('_') and not k.startswith('FormSubmitter')]
        else:
            keys_to_save = keys
        
        # Create dict of data to save
        data_to_save = {k: st.session_state[k] for k in keys_to_save if k in st.session_state}
        
        # Save to file
        with open(session_file, 'wb') as f:
            pickle.dump(data_to_save, f)
        
        logger.info(f"Saved {len(data_to_save)} session keys to {session_file}")
        
    except Exception as e:
        logger.warning(f"Failed to save session state: {e}")

def load_session_state():
    """
    Load session state from disk if available
    """
    try:
        session_file = get_session_file()
        
        if session_file.exists():
            with open(session_file, 'rb') as f:
                saved_data = pickle.load(f)
            
            # Restore data to session state
            for key, value in saved_data.items():
                if key not in st.session_state:
                    st.session_state[key] = value
            
            logger.info(f"Loaded {len(saved_data)} session keys from {session_file}")
            return True
        
    except Exception as e:
        logger.warning(f"Failed to load session state: {e}")
    
    return False

def clear_session_cache():
    """Clear all saved session files"""
    try:
        for file in PERSISTENCE_DIR.glob("session_*.pkl"):
            file.unlink()
        logger.info("Cleared all session cache files")
    except Exception as e:
        logger.warning(f"Failed to clear session cache: {e}")

def auto_save_on_change(keys: list):
    """
    Decorator to automatically save session state when specific keys change
    
    Usage:
        @auto_save_on_change(['simulations_config', 'validation_complete'])
        def my_function():
            # Your code here
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            save_session_state(keys)
            return result
        return wrapper
    return decorator
