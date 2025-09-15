
import sys
import os
import time

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.scheduler import init_scheduler
from core.logger_config import setup_logging
from core.app_config import Config

if __name__ == "__main__":
    # Setup logging
    config = Config()
    setup_logging(config, component_name='scheduler')
    
    # Initialize and start the scheduler
    init_scheduler(config)

    # Keep the script running
    while True:
        time.sleep(60)
