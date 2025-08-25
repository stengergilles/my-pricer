"""
Unified parameter management for all trading strategies.
Eliminates duplication between CLI scripts and backend API.
"""

import sys
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Add parent directory to path for config imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from config import strategy_configs, indicator_defaults
except ImportError:
    strategy_configs = {}
    indicator_defaults = {}

@dataclass
class ParameterRange:
    """Defines a parameter's optimization range and constraints."""
    min_val: float
    max_val: float
    param_type: str = 'int'  # 'int', 'float', 'categorical'
    constraint_func: Optional[callable] = None
    description: str = ""

class ParameterManager:
    """
    Centralized parameter management for all trading strategies.
    Handles parameter definitions, validation, and Optuna suggestions.
    """
    
    def __init__(self):
        self.max_data_points = 300  # Conservative estimate for 7 days of 30min data
        self._parameter_ranges = self._define_parameter_ranges()
    
    def _define_parameter_ranges(self) -> Dict[str, Dict[str, ParameterRange]]:
        """Define parameter ranges for all strategies."""
        return {
            'EMA_Only': {
                'short_ema_period': ParameterRange(5, 30, 'int', description="Fast EMA period"),
                'long_ema_period': ParameterRange(20, min(100, self.max_data_points // 3), 'int', 
                                                description="Slow EMA period (must be > short_ema_period)"),
                'rsi_oversold': ParameterRange(5, 35, 'int', description="RSI oversold threshold"),
                'rsi_overbought': ParameterRange(65, 95, 'int', description="RSI overbought threshold"),
                'atr_period': ParameterRange(5, min(30, self.max_data_points // 10), 'int', description="ATR calculation period"),
                'atr_multiple': ParameterRange(1.0, 5.0, 'float', description="ATR multiplier for stops"),
                'fixed_stop_loss_percentage': ParameterRange(0.005, 0.05, 'float', description="Fixed stop loss %"),
                'take_profit_multiple': ParameterRange(1.5, 5.0, 'float', description="Take profit multiplier"),
                'macd_fast_period': ParameterRange(5, 25, 'int', description="MACD fast period"),
                'macd_slow_period': ParameterRange(20, min(50, self.max_data_points // 6), 'int', 
                                                 description="MACD slow period"),
                'macd_signal_period': ParameterRange(5, 20, 'int', description="MACD signal period"),
            },
            'Strict': {
                'short_sma_period': ParameterRange(5, 50, 'int', description="Short SMA period"),
                'long_sma_period': ParameterRange(51, min(200, self.max_data_points // 2), 'int', 
                                                description="Long SMA period"),
                'short_ema_period': ParameterRange(5, 30, 'int', description="Short EMA period"),
                'long_ema_period': ParameterRange(31, min(100, self.max_data_points // 3), 'int', 
                                                description="Long EMA period"),
                'rsi_oversold': ParameterRange(5, 35, 'int', description="RSI oversold threshold"),
                'rsi_overbought': ParameterRange(65, 95, 'int', description="RSI overbought threshold"),
                'atr_period': ParameterRange(5, min(30, self.max_data_points // 10), 'int', description="ATR period"),
                'atr_multiple': ParameterRange(1.0, 5.0, 'float', description="ATR multiplier"),
                'fixed_stop_loss_percentage': ParameterRange(0.005, 0.05, 'float', description="Fixed stop loss %"),
                'take_profit_multiple': ParameterRange(1.5, 5.0, 'float', description="Take profit multiplier"),
                'macd_fast_period': ParameterRange(5, 25, 'int', description="MACD fast period"),
                'macd_slow_period': ParameterRange(26, min(50, self.max_data_points // 6), 'int', 
                                                 description="MACD slow period"),
                'macd_signal_period': ParameterRange(5, 20, 'int', description="MACD signal period"),
            },
            'BB_Breakout': {
                'bb_period': ParameterRange(10, min(50, self.max_data_points // 6), 'int', description="Bollinger Band period"),
                'bb_std_dev': ParameterRange(1.5, 3.0, 'float', description="Bollinger Band standard deviation"),
                'rsi_oversold': ParameterRange(5, 35, 'int', description="RSI oversold threshold"),
                'rsi_overbought': ParameterRange(65, 95, 'int', description="RSI overbought threshold"),
                'atr_period': ParameterRange(5, min(30, self.max_data_points // 10), 'int', description="ATR period"),
                'atr_multiple': ParameterRange(1.0, 5.0, 'float', description="ATR multiplier"),
                'fixed_stop_loss_percentage': ParameterRange(0.005, 0.05, 'float', description="Fixed stop loss %"),
                'take_profit_multiple': ParameterRange(1.5, 5.0, 'float', description="Take profit multiplier"),
            },
            'BB_RSI': {
                'bb_period': ParameterRange(10, min(50, self.max_data_points // 6), 'int', description="Bollinger Band period"),
                'bb_std_dev': ParameterRange(1.5, 3.0, 'float', description="Bollinger Band standard deviation"),
                'rsi_period': ParameterRange(5, min(30, self.max_data_points // 10), 'int', description="RSI period"),
                'rsi_oversold': ParameterRange(5, 35, 'int', description="RSI oversold threshold"),
                'rsi_overbought': ParameterRange(65, 95, 'int', description="RSI overbought threshold"),
                'atr_period': ParameterRange(5, min(30, self.max_data_points // 10), 'int', description="ATR period"),
                'atr_multiple': ParameterRange(1.0, 5.0, 'float', description="ATR multiplier"),
                'fixed_stop_loss_percentage': ParameterRange(0.005, 0.05, 'float', description="Fixed stop loss %"),
                'take_profit_multiple': ParameterRange(1.5, 5.0, 'float', description="Take profit multiplier"),
            },
            'Combined_Trigger_Verifier': {
                'short_ema_period': ParameterRange(5, 30, 'int', description="Short EMA period"),
                'long_ema_period': ParameterRange(31, min(100, self.max_data_points // 3), 'int', 
                                                description="Long EMA period"),
                'bb_period': ParameterRange(10, min(50, self.max_data_points // 6), 'int', description="Bollinger Band period"),
                'bb_std_dev': ParameterRange(1.5, 3.0, 'float', description="Bollinger Band standard deviation"),
                'rsi_period': ParameterRange(5, min(30, self.max_data_points // 10), 'int', description="RSI period"),
                'rsi_oversold': ParameterRange(5, 35, 'int', description="RSI oversold threshold"),
                'rsi_overbought': ParameterRange(65, 95, 'int', description="RSI overbought threshold"),
                'atr_period': ParameterRange(5, min(30, self.max_data_points // 10), 'int', description="ATR period"),
                'atr_multiple': ParameterRange(1.0, 5.0, 'float', description="ATR multiplier"),
                'fixed_stop_loss_percentage': ParameterRange(0.005, 0.05, 'float', description="Fixed stop loss %"),
                'take_profit_multiple': ParameterRange(1.5, 5.0, 'float', description="Take profit multiplier"),
                'macd_fast_period': ParameterRange(5, 25, 'int', description="MACD fast period"),
                'macd_slow_period': ParameterRange(26, min(50, self.max_data_points // 6), 'int', 
                                                 description="MACD slow period"),
                'macd_signal_period': ParameterRange(5, 20, 'int', description="MACD signal period"),
            }
        }
    
    def get_strategy_parameters(self, strategy_name: str) -> Dict[str, ParameterRange]:
        """Get parameter definitions for a strategy."""
        return self._parameter_ranges.get(strategy_name, {})
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategies."""
        return list(self._parameter_ranges.keys())
    
    def suggest_parameters(self, trial, strategy_name: str) -> Dict[str, Any]:
        """Generate Optuna parameter suggestions for a strategy."""
        if strategy_name not in self._parameter_ranges:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        params = {}
        param_ranges = self._parameter_ranges[strategy_name]
        
        # Handle interdependent parameters
        if 'short_ema_period' in param_ranges and 'long_ema_period' in param_ranges:
            short_ema = trial.suggest_int('short_ema_period', 
                                        param_ranges['short_ema_period'].min_val,
                                        param_ranges['short_ema_period'].max_val)
            long_ema = trial.suggest_int('long_ema_period', 
                                       max(short_ema + 1, param_ranges['long_ema_period'].min_val),
                                       param_ranges['long_ema_period'].max_val)
            params['short_ema_period'] = short_ema
            params['long_ema_period'] = long_ema
        
        if 'short_sma_period' in param_ranges and 'long_sma_period' in param_ranges:
            short_sma = trial.suggest_int('short_sma_period',
                                        param_ranges['short_sma_period'].min_val,
                                        param_ranges['short_sma_period'].max_val)
            long_sma = trial.suggest_int('long_sma_period',
                                       short_sma + 5,
                                       param_ranges['long_sma_period'].max_val)
            params['short_sma_period'] = short_sma
            params['long_sma_period'] = long_sma
        
        if 'rsi_oversold' in param_ranges and 'rsi_overbought' in param_ranges:
            rsi_oversold = trial.suggest_int('rsi_oversold',
                                           param_ranges['rsi_oversold'].min_val,
                                           param_ranges['rsi_oversold'].max_val)
            rsi_overbought = trial.suggest_int('rsi_overbought',
                                             rsi_oversold + 20,
                                             param_ranges['rsi_overbought'].max_val)
            params['rsi_oversold'] = rsi_oversold
            params['rsi_overbought'] = rsi_overbought
        
        if 'macd_fast_period' in param_ranges and 'macd_slow_period' in param_ranges:
            macd_fast = trial.suggest_int('macd_fast_period',
                                        param_ranges['macd_fast_period'].min_val,
                                        param_ranges['macd_fast_period'].max_val)
            macd_slow = trial.suggest_int('macd_slow_period',
                                        max(macd_fast + 1, param_ranges['macd_slow_period'].min_val),
                                        param_ranges['macd_slow_period'].max_val)
            params['macd_fast_period'] = macd_fast
            params['macd_slow_period'] = macd_slow
        
        # Handle independent parameters
        for param_name, param_range in param_ranges.items():
            if param_name not in params:  # Skip already handled interdependent params
                if param_range.param_type == 'int':
                    params[param_name] = trial.suggest_int(param_name, 
                                                         int(param_range.min_val), 
                                                         int(param_range.max_val))
                elif param_range.param_type == 'float':
                    params[param_name] = trial.suggest_float(param_name, 
                                                           param_range.min_val, 
                                                           param_range.max_val)
        
        return params
    
    def validate_parameters(self, params: Dict[str, Any], strategy_name: str) -> Dict[str, str]:
        """Validate parameter values and return any errors."""
        errors = {}
        
        if strategy_name not in self._parameter_ranges:
            errors['strategy'] = f"Unknown strategy: {strategy_name}"
            return errors
        
        param_ranges = self._parameter_ranges[strategy_name]
        
        for param_name, value in params.items():
            if param_name not in param_ranges:
                errors[param_name] = f"Unknown parameter for strategy {strategy_name}"
                continue
            
            param_range = param_ranges[param_name]
            
            if param_range.param_type == 'int' and not isinstance(value, int):
                errors[param_name] = f"Must be an integer"
                continue
            
            if param_range.param_type == 'float' and not isinstance(value, (int, float)):
                errors[param_name] = f"Must be a number"
                continue
            
            if value < param_range.min_val or value > param_range.max_val:
                errors[param_name] = f"Must be between {param_range.min_val} and {param_range.max_val}"
        
        # Check interdependent constraints
        if 'short_ema_period' in params and 'long_ema_period' in params:
            if params['short_ema_period'] >= params['long_ema_period']:
                errors['long_ema_period'] = "Must be greater than short_ema_period"
        
        if 'short_sma_period' in params and 'long_sma_period' in params:
            if params['short_sma_period'] >= params['long_sma_period']:
                errors['long_sma_period'] = "Must be greater than short_sma_period"
        
        if 'rsi_oversold' in params and 'rsi_overbought' in params:
            if params['rsi_oversold'] >= params['rsi_overbought']:
                errors['rsi_overbought'] = "Must be greater than rsi_oversold"
        
        if 'macd_fast_period' in params and 'macd_slow_period' in params:
            if params['macd_fast_period'] >= params['macd_slow_period']:
                errors['macd_slow_period'] = "Must be greater than macd_fast_period"
        
        return errors
    
    def format_cli_params(self, params: Dict[str, Any]) -> List[str]:
        """Format parameters for CLI backtester execution."""
        cli_args = []
        
        for param_name, value in params.items():
            # Convert parameter names to CLI format
            cli_param = f"--{param_name.replace('_', '-')}"
            cli_args.extend([cli_param, str(value)])
        
        return cli_args
    
    def get_default_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Get default parameter values for a strategy."""
        if strategy_name not in self._parameter_ranges:
            return {}
        
        defaults = {}
        param_ranges = self._parameter_ranges[strategy_name]
        
        for param_name, param_range in param_ranges.items():
            # Use middle value as default
            if param_range.param_type == 'int':
                defaults[param_name] = int((param_range.min_val + param_range.max_val) // 2)
            else:
                defaults[param_name] = (param_range.min_val + param_range.max_val) / 2
        
        # Adjust interdependent defaults
        if 'short_ema_period' in defaults and 'long_ema_period' in defaults:
            defaults['short_ema_period'] = 12
            defaults['long_ema_period'] = 26
        
        if 'short_sma_period' in defaults and 'long_sma_period' in defaults:
            defaults['short_sma_period'] = 20
            defaults['long_sma_period'] = 50
        
        if 'rsi_oversold' in defaults and 'rsi_overbought' in defaults:
            defaults['rsi_oversold'] = 30
            defaults['rsi_overbought'] = 70
        
        if 'macd_fast_period' in defaults and 'macd_slow_period' in defaults:
            defaults['macd_fast_period'] = 12
            defaults['macd_slow_period'] = 26
        
        return defaults
