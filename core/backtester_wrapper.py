"""
Unified backtester wrapper that provides a clean interface to the existing backtester.
Eliminates the need for subprocess calls and provides direct Python access.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from backtester import Backtester
    from config import strategy_configs, DEFAULT_SPREAD_PERCENTAGE, DEFAULT_SLIPPAGE_PERCENTAGE
    from data import get_crypto_data_merged
    from strategy import Strategy
    BACKTESTER_AVAILABLE = True
    logging.info("Backtester modules imported successfully")
except ImportError as e:
    logging.warning(f"Backtester modules not available: {e}")
    BACKTESTER_AVAILABLE = False
    
    # Mock classes for when backtester is not available
    class Backtester:
        def __init__(self, *args, **kwargs):
            pass
        def run_backtest(self, *args, **kwargs):
            return None
    
    class Strategy:
        def __init__(self, *args, **kwargs):
            pass
    
    strategy_configs = {}
    DEFAULT_SPREAD_PERCENTAGE = 0.01
    DEFAULT_SLIPPAGE_PERCENTAGE = 0.001
    def get_crypto_data_merged(*args, **kwargs):
        return None

class BacktestResult:
    """Standardized backtest result container."""
    
    def __init__(self, result_dict=None):
        if result_dict:
            self.total_profit_percentage = result_dict.get('total_profit_percentage', 0.0)
            self.total_trades = result_dict.get('total_trades', 0)
            self.winning_trades = result_dict.get('winning_trades', 0)
            self.losing_trades = result_dict.get('losing_trades', 0)
            self.win_rate = result_dict.get('win_rate', 0.0)
            self.max_drawdown = result_dict.get('max_drawdown', 0.0)
            self.sharpe_ratio = result_dict.get('sharpe_ratio', 0.0)
            self.raw_result = result_dict
        else:
            # Default values
            self.total_profit_percentage = 0.0
            self.total_trades = 0
            self.winning_trades = 0
            self.losing_trades = 0
            self.win_rate = 0.0
            self.max_drawdown = 0.0
            self.sharpe_ratio = 0.0
            self.raw_result = {}

class BacktesterWrapper:
    """
    Wrapper around the existing backtester that provides a clean Python interface.
    Eliminates subprocess calls and provides better error handling.
    """
    
    def __init__(self):
        """Initialize backtester wrapper."""
        self.logger = logging.getLogger(__name__)
        
        if not BACKTESTER_AVAILABLE:
            self.logger.warning("Backtester not available. Results will be mocked.")
    
    def run_single_backtest(self, 
                          crypto: str, 
                          strategy: str, 
                          parameters: Dict[str, Any],
                          timeframe: str = "7d",
                          interval: str = "30m") -> Dict[str, Any]:
        """
        Run a single backtest with specified parameters.
        
        Args:
            crypto: Cryptocurrency identifier
            strategy: Trading strategy name
            parameters: Strategy parameters
            timeframe: Data timeframe (e.g., "7d", "30d")
            interval: Data interval (e.g., "30m", "1h")
            
        Returns:
            Backtest results dictionary
        """
        if not BACKTESTER_AVAILABLE:
            return self._mock_backtest_result(crypto, strategy, parameters)
        
        try:
            # Get crypto data - convert timeframe to days
            timeframe_days = self._timeframe_to_days(timeframe)
            data = get_crypto_data_merged(crypto, timeframe_days)
            if data is None or len(data) == 0:
                self.logger.error(f"No data available for {crypto}")
                return {
                    'crypto': crypto,
                    'strategy': strategy,
                    'parameters': parameters,
                    'success': False,
                    'error': 'No data available',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get strategy configuration
            if strategy not in strategy_configs:
                self.logger.error(f"Unknown strategy: {strategy}")
                return {
                    'crypto': crypto,
                    'strategy': strategy,
                    'parameters': parameters,
                    'success': False,
                    'error': f'Unknown strategy: {strategy}',
                    'timestamp': datetime.now().isoformat()
                }
            
            strategy_config = strategy_configs[strategy]
            
            # Create strategy instance
            strategy_instance = Strategy(strategy, strategy_config)
            
            # Create backtester instance
            backtester = Backtester(data, strategy_instance, strategy_config)
            
            # Add required parameters for backtester
            backtest_params = parameters.copy()
            backtest_params['spread_percentage'] = backtest_params.get('spread_percentage', DEFAULT_SPREAD_PERCENTAGE)
            backtest_params['slippage_percentage'] = backtest_params.get('slippage_percentage', DEFAULT_SLIPPAGE_PERCENTAGE)
            
            # Run the backtest
            result = backtester.run_backtest(backtest_params)
            
            if result is None:
                self.logger.error(f"Backtest returned None for {crypto}/{strategy}")
                return {
                    'crypto': crypto,
                    'strategy': strategy,
                    'parameters': parameters,
                    'success': False,
                    'error': 'Backtest execution failed',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Convert result to standardized format
            return self._format_result(result, crypto, strategy, parameters)
            
        except Exception as e:
            self.logger.error(f"Backtest failed for {crypto}/{strategy}: {e}")
            return {
                'crypto': crypto,
                'strategy': strategy,
                'parameters': parameters,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_batch_backtest(self, 
                         test_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run multiple backtests in batch.
        
        Args:
            test_configs: List of test configuration dictionaries
                         Each should contain: crypto, strategy, parameters
            
        Returns:
            List of backtest results
        """
        results = []
        
        for i, config in enumerate(test_configs):
            self.logger.info(f"Running backtest {i+1}/{len(test_configs)}: "
                           f"{config.get('crypto')}/{config.get('strategy')}")
            
            result = self.run_single_backtest(
                crypto=config.get('crypto'),
                strategy=config.get('strategy'),
                parameters=config.get('parameters', {}),
                timeframe=config.get('timeframe', '7d'),
                interval=config.get('interval', '30m')
            )
            
            results.append(result)
        
        return results
    
    def validate_parameters(self, strategy: str, parameters: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate parameters for a strategy.
        
        Args:
            strategy: Strategy name
            parameters: Parameters to validate
            
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {}
        
        if not BACKTESTER_AVAILABLE:
            return errors
        
        # Check if strategy exists
        if strategy not in strategy_configs:
            errors['strategy'] = f"Unknown strategy: {strategy}"
            return errors
        
        # Get strategy configuration
        strategy_config = strategy_configs.get(strategy, {})
        
        # Basic validation - you can extend this based on your strategy_configs structure
        # For now, just check that parameters are reasonable numbers
        for param_name, value in parameters.items():
            if isinstance(value, (int, float)):
                if value <= 0:
                    errors[param_name] = f"Must be positive"
            elif not isinstance(value, (str, bool)):
                errors[param_name] = f"Invalid parameter type"
        
        return errors
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available trading strategies."""
        if not BACKTESTER_AVAILABLE:
            return ['EMA_Only', 'Strict', 'BB_Breakout', 'BB_RSI', 'Combined_Trigger_Verifier']
        
        return list(strategy_configs.keys())
    
    def get_strategy_info(self, strategy: str) -> Dict[str, Any]:
        """Get information about a specific strategy."""
        if not BACKTESTER_AVAILABLE or strategy not in strategy_configs:
            return {}
        
        return strategy_configs.get(strategy, {})
    
    def test_crypto_data_availability(self, crypto: str, timeframe: str = "7d") -> bool:
        """
        Test if data is available for a cryptocurrency.
        
        Args:
            crypto: Cryptocurrency identifier
            timeframe: Data timeframe to test
            
        Returns:
            True if data is available, False otherwise
        """
        if not BACKTESTER_AVAILABLE:
            return True  # Mock availability
        
        try:
            data = get_crypto_data_merged(crypto, self._timeframe_to_days(timeframe))
            return data is not None and len(data) > 0
        except Exception as e:
            self.logger.warning(f"Data not available for {crypto}: {e}")
            return False
    
    def _timeframe_to_days(self, timeframe: str) -> int:
        """Convert timeframe string to number of days."""
        if timeframe.endswith('d'):
            return int(timeframe[:-1])
        elif timeframe.endswith('w'):
            return int(timeframe[:-1]) * 7
        elif timeframe.endswith('m'):
            return int(timeframe[:-1]) * 30
        else:
            # Default to 7 days
            return 7
    
    def _format_result(self, 
                      result: Any, 
                      crypto: str, 
                      strategy: str, 
                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Format backtest result as dictionary."""
        
        # Handle different result formats
        if isinstance(result, dict):
            # Result is already a dictionary
            formatted_result = {
                'crypto': crypto,
                'strategy': strategy,
                'parameters': parameters,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            formatted_result.update(result)
            return formatted_result
        
        elif hasattr(result, '__dict__'):
            # Result is an object, convert to dict
            result_dict = result.__dict__ if hasattr(result, '__dict__') else {}
            return {
                'crypto': crypto,
                'strategy': strategy,
                'parameters': parameters,
                'success': True,
                'total_profit_percentage': result_dict.get('total_profit_percentage', 0.0),
                'total_trades': result_dict.get('total_trades', 0),
                'winning_trades': result_dict.get('winning_trades', 0),
                'losing_trades': result_dict.get('losing_trades', 0),
                'win_rate': result_dict.get('win_rate', 0.0),
                'max_drawdown': result_dict.get('max_drawdown', 0.0),
                'sharpe_ratio': result_dict.get('sharpe_ratio', 0.0),
                'timestamp': datetime.now().isoformat()
            }
        
        else:
            # Unknown result format, return basic info
            return {
                'crypto': crypto,
                'strategy': strategy,
                'parameters': parameters,
                'success': True,
                'result': str(result),
                'timestamp': datetime.now().isoformat()
            }
    
    def _mock_backtest_result(self, 
                            crypto: str, 
                            strategy: str, 
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock backtest result when backtester is not available."""
        import random
        
        # Generate realistic-looking mock results
        profit = random.uniform(-50, 150)  # -50% to +150% profit
        trades = random.randint(1, 20)
        win_rate = random.uniform(0.2, 0.8)
        winning_trades = int(trades * win_rate)
        losing_trades = trades - winning_trades
        
        return {
            'crypto': crypto,
            'strategy': strategy,
            'parameters': parameters,
            'success': True,
            'total_profit_percentage': profit,
            'total_trades': trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'max_drawdown': random.uniform(0.05, 0.3),
            'sharpe_ratio': random.uniform(-1, 3),
            'timestamp': datetime.now().isoformat(),
            'mock_result': True  # Flag to indicate this is a mock result
        }
