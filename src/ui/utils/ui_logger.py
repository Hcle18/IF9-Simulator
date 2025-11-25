import logging
import re
import streamlit as st
from src.utils.logging_config import setup_logging

class StreamlitLogHandler(logging.Handler):
    # Initializes a custom log handler with a Streamlit container for displaying logs
    def __init__(self, container=None):
        super().__init__()
        # Store the Streamlit container for log output (can be None initially)
        self.container = container
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])') # Regex to remove ANSI codes
        
        # ✅ Buffer pour stocker uniquement le dernier log (pas d'accumulation)
        self.logs_buffer = []
        self.status_container = None  # Pour st.status() updates
        self.is_running = False  # Track if operation is in progress

    def emit(self, record):
        try:
            msg = self.format(record)
            clean_msg = self.ansi_escape.sub('', msg)  # Strip ANSI codes
            
            # ✅ REMPLACER le buffer au lieu d'accumuler
            # Stocke uniquement le nouveau log
            self.logs_buffer = [clean_msg]
            
            # ✅ Déterminer l'état selon le message
            # Messages de fin → complete, autres → running
            if any(keyword in clean_msg.lower() for keyword in ['completed', 'finished', 'success', 'ready', '✅', 
                                                                'failed', 'error', 'cancelled']):
                self.is_running = False
            else:
                self.is_running = True
            
            # ✅ Mise à jour temps réel si status_container disponible
            if self.status_container:
                try:
                    state = "running" if self.is_running else "complete"
                    self.status_container.update(label=clean_msg, state=state)
                except Exception:
                    pass
            
        except Exception:
            # ✅ En cas d'erreur, ignorer silencieusement
            pass

    def display_logs(self):
        """Display logs in the container - call this explicitly when safe"""
        try:
            if self.container and self.logs_buffer:
                # Afficher uniquement le dernier log (pas d'accumulation)
                self.container.text(self.logs_buffer[0])
        except Exception:
            pass

    def clear_logs(self):
        """Clear all logs from buffer and display"""
        self.logs_buffer = []
        try:
            if self.container:
                self.container.empty()
        except Exception:
            pass


def display_ui_logs():
    """
    Display UI logs from the handler buffer.
    Call this function to refresh the log display.
    """
    if 'log_handler' in st.session_state:
        handler = st.session_state.log_handler
        handler.display_logs()


def clear_ui_logs():
    """
    Clear all UI logs from the handler buffer.
    Call this function at the end of module execution.
    """
    if 'log_handler' in st.session_state:
        handler = st.session_state.log_handler
        handler.clear_logs()


# Set up logging to capture all info level logs from the root logger
def ui_setup_logging():
    if "log_handler" not in st.session_state:
        logger = setup_logging(log_level="INFO")
        logger.handlers = [h for h in logger.handlers if not isinstance(h, StreamlitLogHandler)]
        log_container = st.container() # Create a container within which we display logs
        handler = StreamlitLogHandler(log_container)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        st.session_state.log_handler = handler
    return st.session_state.log_handler