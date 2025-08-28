import logging
import os
from core.app_config import config

LOG_DIR = config.LOGS_DIR
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

def setup_logging():
    """Configures logging to write to a file in data/logs."""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Remove all handlers associated with the root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler() # Also log to console
        ]
    )