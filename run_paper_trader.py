
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.paper_trading_engine import run_paper_trader
from core.logger_config import setup_logging
from core.app_config import Config

if __name__ == "__main__":
    # Setup logging
    config = Config()
    setup_logging(config)
    
    # Run the paper trader
    run_paper_trader()
