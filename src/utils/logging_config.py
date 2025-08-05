import logging
import logging.config
from pathlib import Path
import sys

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Setup logging configuration for the IFRS9 application
    
    :param log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :param log_file: Optional log file path
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Default log file if not specified
    if log_file is None:
        log_file = log_dir / "ifrs9_simulation.log"
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'stream': sys.stdout
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filename': str(log_file),
                'mode': 'a',
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False
            },
            'core': {  # Core module logger
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False
            }
        }
    }
    
    logging.config.dictConfig(config)
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration setup complete")