"""
Core module for shared trading functionality.
"""

from .config import Config
from .trading_engine import TradingEngine
from .result_manager import ResultManager
from .data_manager import DataManager

__all__ = ['Config', 'TradingEngine', 'ResultManager', 'DataManager']
