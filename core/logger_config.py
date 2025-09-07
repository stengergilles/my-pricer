import logging
import os
from pathlib import Path

# Assuming this file is in core/, so project root is one level up
PROJECT_ROOT = Path(__file__).parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"

def LOG_FILE():
    return LOG_DIR / 'app.log'

def setup_logging(config=None):
    """Configures logging to write to a file in data/logs."""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Remove all handlers associated with the root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE()),
            logging.StreamHandler() # Also log to console
        ]
    )

    # Explicitly set level for auth middleware loggers
    logging.getLogger('auth.middleware').setLevel(logging.DEBUG)
    logging.getLogger('web.backend.auth.middleware').setLevel(logging.DEBUG)

def setup_job_logging(job_id: str):
    """Creates a new logger for a given job ID and adds a file handler to it."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = LOG_DIR / f"job_{job_id}.log"
    logger = logging.getLogger(job_id)
    logger.setLevel(logging.INFO)
    # Remove existing handlers to avoid duplicate logs
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return str(log_path)
