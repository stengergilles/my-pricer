import logging
import os

def LOG_DIR(config):
    return config.LOGS_DIR

def LOG_FILE(config):
    return os.path.join(LOG_DIR(config), 'app.log')

def setup_logging(config):
    """Configures logging to write to a file in data/logs."""
    log_dir = LOG_DIR(config)
    os.makedirs(log_dir, exist_ok=True)
    
    # Remove all handlers associated with the root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE(config)),
            logging.StreamHandler() # Also log to console
        ]
    )
