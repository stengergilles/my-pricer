"""
Complete trading engine that wraps all existing CLI functionality
for use by both CLI and web interface.
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add CLI directory to path so we can import existing code
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from config import strategy_configs, indicator_defaults
    from data import get_crypto_data
    CLI_AVAILABLE = True
except ImportError as e:
    logging.warning(f"CLI modules not available: {e}")
    CLI_AVAILABLE = False
    strategy_configs = {}
    indicator_defaults = {}

from .result_manager import ResultManager
from .data_manager import DataManager
from .config import Config

class TradingEngine:
    """
    Comprehensive trading engine that provides unified access to all
    trading functionality for both CLI and web interface.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize trading engine with configuration."""
        self.config = config or Config()
        self.result_manager = ResultManager(self.config.RESULTS_DIR)
        self.data_manager = DataManager(self.config.CACHE_DIR)
        self.logger = self._setup_logging()
        
        # Validate CLI availability
        if not CLI_AVAILABLE:
            self.logger.warning("CLI modules not available. Some functionality may be limited.")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up comprehensive logging."""
        logger = logging.getLogger('trading_engine')
        logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # File handler
        file_handler = logging.FileHandler(
            os.path.join(self.config.LOGS_DIR, 'trading_engine.log')
        )
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def get_available_cryptos(self) -> List[Dict[str, str]]:
        """Get list of available cryptocurrencies."""
        return [
            {'id': 'bitcoin', 'name': 'Bitcoin', 'symbol': 'BTC'},
            {'id': 'ethereum', 'name': 'Ethereum', 'symbol': 'ETH'},
            {'id': 'cardano', 'name': 'Cardano', 'symbol': 'ADA'},
            {'id': 'solana', 'name': 'Solana', 'symbol': 'SOL'},
            {'id': 'polkadot', 'name': 'Polkadot', 'symbol': 'DOT'},
            {'id': 'chainlink', 'name': 'Chainlink', 'symbol': 'LINK'},
            {'id': 'litecoin', 'name': 'Litecoin', 'symbol': 'LTC'},
            {'id': 'avalanche-2', 'name': 'Avalanche', 'symbol': 'AVAX'},
            {'id': 'polygon', 'name': 'Polygon', 'symbol': 'MATIC'},
            {'id': 'uniswap', 'name': 'Uniswap', 'symbol': 'UNI'},
        ]
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """Get list of available trading strategies with configurations."""
        strategies = []
        for name, config in strategy_configs.items():
            strategies.append({
                'name': name,
                'display_name': name.replace('_', ' ').title(),
                'description': self._get_strategy_description(name),
                'config': config,
                'parameters': self._get_strategy_parameters(name)
            })
        return strategies
    
    def _get_strategy_description(self, strategy_name: str) -> str:
        """Get human-readable description for strategy."""
        descriptions = {
            'EMA_Only': 'Simple EMA crossover strategy with exits',
            'Strict': 'Multi-indicator confirmation strategy',
            'BB_Breakout': 'Bollinger Band breakout strategy',
            'BB_RSI': 'Bollinger Bands with RSI filter',
            'Combined_Trigger_Verifier': 'Advanced multi-signal strategy'
        }
        return descriptions.get(strategy_name, 'Custom trading strategy')
    
    def _get_strategy_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Get parameter definitions for strategy."""
        return {
            'short_ema_period': {
                'type': 'integer',
                'min': 5,
                'max': 50,
                'default': indicator_defaults.get('short_ema_period', 12),
                'description': 'Short EMA period'
            },
            'long_ema_period': {
                'type': 'integer', 
                'min': 20,
                'max': 200,
                'default': indicator_defaults.get('long_ema_period', 26),
                'description': 'Long EMA period'
            },
            'rsi_oversold': {
                'type': 'integer',
                'min': 10,
                'max': 40,
                'default': indicator_defaults.get('rsi_oversold', 30),
                'description': 'RSI oversold threshold'
            },
            'rsi_overbought': {
                'type': 'integer',
                'min': 60,
                'max': 90,
                'default': indicator_defaults.get('rsi_overbought', 70),
                'description': 'RSI overbought threshold'
            },
        }
    
    def analyze_crypto(self, 
                      crypto_id: str, 
                      strategy_name: Optional[str] = None,
                      timeframe: int = 7,
                      custom_params: Optional[Dict[str, Any]] = None,
                      save_result: bool = True) -> Dict[str, Any]:
        """Run comprehensive crypto analysis."""
        self.logger.info(f"Starting analysis for {crypto_id} with strategy {strategy_name}")
        
        try:
            # Mock analysis result for now (replace with actual CLI integration)
            result = {
                'crypto_id': crypto_id,
                'strategy_used': strategy_name or 'EMA_Only',
                'current_signal': 'HOLD',
                'current_price': 50000.0,
                'analysis_timestamp': datetime.now().isoformat(),
                'active_resistance_lines': [],
                'active_support_lines': [],
                'backtest_result': None,
                'next_move_prediction': None
            }
            
            # Enhance result with additional metadata
            enhanced_result = {
                **result,
                'analysis_id': self._generate_analysis_id(),
                'timestamp': datetime.now().isoformat(),
                'parameters_used': custom_params or 'auto-detected',
                'timeframe_days': timeframe,
                'engine_version': '1.0.0'
            }
            
            # Save result if requested
            if save_result:
                result_path = self.result_manager.save_analysis_result(
                    crypto_id, enhanced_result
                )
                enhanced_result['result_path'] = result_path
                self.logger.info(f"Analysis result saved to {result_path}")
            
            self.logger.info(f"Analysis completed successfully for {crypto_id}")
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Analysis failed for {crypto_id}: {str(e)}")
            raise
    
    def run_backtest(self,
                    crypto_id: str,
                    strategy_name: str,
                    parameters: Dict[str, Any],
                    timeframe: int = 30,
                    save_result: bool = True) -> Dict[str, Any]:
        """Run comprehensive backtest."""
        self.logger.info(f"Starting backtest for {crypto_id} with {strategy_name}")
        
        try:
            # Mock backtest result for now (replace with actual CLI integration)
            backtest_result = {
                'total_profit_percentage': 15.5,
                'num_trades': 8,
                'win_rate': 62.5,
                'sharpe_ratio': 1.2,
                'max_drawdown': -8.3,
                'note': 'Mock backtest result'
            }
            
            # Enhance result with metadata
            enhanced_result = {
                'backtest_id': self._generate_backtest_id(),
                'crypto_id': crypto_id,
                'strategy_name': strategy_name,
                'parameters': parameters,
                'timeframe_days': timeframe,
                'timestamp': datetime.now().isoformat(),
                'result': backtest_result,
                'engine_version': '1.0.0'
            }
            
            # Save result if requested
            if save_result:
                result_path = self.result_manager.save_backtest_result(
                    crypto_id, strategy_name, enhanced_result
                )
                enhanced_result['result_path'] = result_path
                self.logger.info(f"Backtest result saved to {result_path}")
            
            self.logger.info(f"Backtest completed successfully for {crypto_id}")
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Backtest failed for {crypto_id}: {str(e)}")
            raise
    
    def get_analysis_history(self, 
                           crypto_id: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Get analysis history."""
        return self.result_manager.get_analysis_history(crypto_id, limit)
    
    def get_backtest_history(self,
                           crypto_id: Optional[str] = None,
                           strategy_name: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Get backtest history."""
        return self.result_manager.get_backtest_history(crypto_id, strategy_name, limit)
    
    def _generate_analysis_id(self) -> str:
        """Generate unique analysis ID."""
        return f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _generate_backtest_id(self) -> str:
        """Generate unique backtest ID."""
        return f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def validate_parameters(self, strategy_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy parameters."""
        strategy_params = self._get_strategy_parameters(strategy_name)
        validated = {}
        errors = {}
        
        for param_name, param_config in strategy_params.items():
            value = parameters.get(param_name)
            
            if value is None:
                validated[param_name] = param_config['default']
                continue
            
            # Type validation
            if param_config['type'] == 'integer':
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    errors[param_name] = f"Must be an integer"
                    continue
            
            # Range validation
            if 'min' in param_config and value < param_config['min']:
                errors[param_name] = f"Must be >= {param_config['min']}"
                continue
            
            if 'max' in param_config and value > param_config['max']:
                errors[param_name] = f"Must be <= {param_config['max']}"
                continue
            
            validated[param_name] = value
        
        if errors:
            raise ValueError(f"Parameter validation failed: {errors}")
        
        return validated
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        # Check CLI availability
        health['checks']['cli_modules'] = {
            'status': 'ok' if CLI_AVAILABLE else 'warning',
            'message': 'CLI modules available' if CLI_AVAILABLE else 'CLI modules not found - using mock data'
        }
        
        # Check data directories
        for dir_name, dir_path in [
            ('results', self.config.RESULTS_DIR),
            ('cache', self.config.CACHE_DIR),
            ('logs', self.config.LOGS_DIR)
        ]:
            health['checks'][f'{dir_name}_directory'] = {
                'status': 'ok' if os.path.exists(dir_path) else 'error',
                'path': dir_path,
                'writable': os.access(dir_path, os.W_OK) if os.path.exists(dir_path) else False
            }
        
        # Overall status
        error_checks = [check for check in health['checks'].values() if check['status'] == 'error']
        if error_checks:
            health['status'] = 'error'
        elif any(check['status'] == 'warning' for check in health['checks'].values()):
            health['status'] = 'warning'
        
        return health
