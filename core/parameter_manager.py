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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config import strategy_configs, indicator_defaults, param_sets
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
    
    def __init__(self, param_set_name: str = 'small'):
        self.max_data_points = 300  # Conservative estimate for 7 days of 30min data
        self.param_set_name = param_set_name
        self._parameter_ranges = self._define_parameter_ranges()
    
    def _define_parameter_ranges(self) -> Dict[str, Dict[str, ParameterRange]]:
        """Define parameter ranges for all strategies based on the selected parameter set."""
        
        # Load the specified parameter set from config.py
        selected_param_set = param_sets['default_sets'].get(self.param_set_name)
        if not selected_param_set:
            raise ValueError(f"Parameter set '{self.param_set_name}' not found in config.py")

        # Initialize a dictionary to hold the strategy-specific parameter ranges
        strategy_param_ranges = {}

        # Iterate through each strategy defined in strategy_configs
        for strategy_name in strategy_configs.keys():
            # Determine which parameter set to use for the current strategy
            # Prioritize strategy-specific sets, then default_sets, then the selected param_set_name
            current_strategy_param_set = param_sets.get(strategy_name, {})
            
            if not current_strategy_param_set:
                current_strategy_param_set = param_sets['default_sets'].get(self.param_set_name)
            
            if not current_strategy_param_set:
                raise ValueError(f"No parameter set found for strategy '{strategy_name}' or default set '{self.param_set_name}'")

            strategy_param_ranges[strategy_name] = {}
            # Apply the ranges from the current_strategy_param_set to the strategy's parameters
            for param_name_with_range, (min_val, max_val, step) in current_strategy_param_set.items():
                # Remove "_range" suffix from parameter name
                clean_param_name = param_name_with_range.replace('_range', '')
                # Determine param_type based on whether min_val/max_val are integers or floats
                param_type = 'int' if isinstance(min_val, int) and isinstance(max_val, int) else 'float'
                strategy_param_ranges[strategy_name][clean_param_name] = ParameterRange(min_val, max_val, param_type)
        
        return strategy_param_ranges

        
    
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
            if param_name in indicator_defaults:
                defaults[param_name] = indicator_defaults[param_name]
            else:
                # Fallback to middle value if not in indicator_defaults
                if param_range.param_type == 'int':
                    defaults[param_name] = int((param_range.min_val + param_range.max_val) // 2)
                else:
                    defaults[param_name] = (param_range.min_val + param_range.max_val) / 2
        
        # Remove hardcoded adjustments as indicator_defaults should handle them
        # if 'short_ema_period' in defaults and 'long_ema_period' in defaults:
        #     defaults['short_ema_period'] = 12
        #     defaults['long_ema_period'] = 26
        
        if 'short_sma_period' in defaults and 'long_sma_period' in defaults:
            defaults['short_sma_period'] = 20
            defaults['long_sma_period'] = 51
        
        # if 'rsi_oversold' in defaults and 'rsi_overbought' in defaults:
        #     defaults['rsi_oversold'] = 30
        #     defaults['rsi_overbought'] = 70
        
        # if 'macd_fast_period' in defaults and 'macd_slow_period' in defaults:
        #     defaults['macd_fast_period'] = 12
        #     defaults['macd_slow_period'] = 26
        
        return defaults
