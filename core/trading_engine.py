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
import pandas as pd
import traceback # ADD THIS IMPORT

# Add CLI directory to path so we can import existing code
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from .result_manager import ResultManager
from .data_manager import DataManager
from .app_config import Config
from .parameter_manager import ParameterManager
from .crypto_discovery import CryptoDiscovery
from .optimizer import BayesianOptimizer
from .backtester_wrapper import BacktesterWrapper
import config # Import the top-level config.py
from .data_fetcher import get_crypto_data_merged
from lines import find_swing_points, find_support_resistance_lines, analyze_line_durations, auto_discover_percentage_change, predict_next_move
from chart import generate_chart
from .scheduler import get_scheduler # Import get_scheduler

class TradingEngine:
    """
    Comprehensive trading engine that provides unified access to all
    trading functionality for both CLI and web interface.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize trading engine with configuration."""
        self.config = config or Config()
        self.result_manager = ResultManager(self.config)
        self.data_manager = DataManager(self.config.CACHE_DIR)
        self.logger = logging.getLogger(__name__)
        
        # Initialize unified components
        self.param_manager = ParameterManager()
        self.crypto_discovery = CryptoDiscovery(self.config.RESULTS_DIR)
        self.optimizer = BayesianOptimizer(self.config.RESULTS_DIR)
        self.backtester = BacktesterWrapper(self.config)
        self._scheduler = None # Initialize scheduler attribute
    
    def set_scheduler(self, scheduler_instance):
        """Set the scheduler instance for the engine."""
        self._scheduler = scheduler_instance

    def get_scheduler(self):
        """Get the scheduler instance."""
        if self._scheduler is None:
            self.logger.warning("Scheduler accessed before being set. Returning global scheduler.")
            return get_scheduler() # Fallback to global if not explicitly set
        return self._scheduler
    
    # ========== Crypto Management ==========
    
    def get_cryptos(self, limit: int = 100, min_volatility: float = 0.1) -> List[Dict[str, Any]]:
        """
        Get list of available cryptocurrencies with market data.
        
        Args:
            limit: Maximum number of cryptos to return
            min_volatility: Minimum volatility threshold
            
        Returns:
            List of cryptocurrency data dictionaries
        """
        try:
            # Use crypto discovery to get crypto list
            cryptos = self.crypto_discovery.get_volatile_cryptos(limit=limit, min_volatility=min_volatility)
            
            return cryptos
        
        except Exception as e:
            self.logger.error(f"Error getting cryptos: {e}")
            return []
    
    def get_volatile_cryptos(self, 
                           min_volatility: float = 5.0, 
                           limit: int = 50,
                           force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get volatile cryptocurrencies for optimization."""
        return self.crypto_discovery.get_volatile_cryptos(
            limit=limit, 
            min_volatility=min_volatility,
            force_refresh=force_refresh
        )
    
    def get_top_movers(self, count: int = 10) -> Dict[str, List[Dict]]:
        """Get top gaining and losing cryptocurrencies."""
        return self.crypto_discovery.get_top_movers(count=count)
    
    def search_cryptos(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for cryptocurrencies by name or symbol."""
        return self.crypto_discovery.search_cryptos(query, limit)
    
    # ========== Strategy Management ==========
    
    def get_strategies(self) -> List[Dict[str, Any]]:
        """Get list of available trading strategies with configurations."""
        strategies = []
        strategy_names = self.param_manager.get_available_strategies()
        
        for name in strategy_names:
            parameters = self.param_manager.get_strategy_parameters(name)
            defaults = self.param_manager.get_default_parameters(name)
            
            # Convert ParameterRange objects to serializable dictionaries
            serializable_parameters = {}
            for param_name, param_range in parameters.items():
                serializable_parameters[param_name] = {
                    'min_val': param_range.min_val,
                    'max_val': param_range.max_val,
                    'param_type': param_range.param_type,
                    'description': param_range.description
                }
            
            strategies.append({
                'name': name,
                'display_name': name.replace('_', ' ').title(),
                'description': self._get_strategy_description(name),
                'parameters': serializable_parameters,
                'defaults': defaults
            })
        
        return strategies
    
    def get_strategy_info(self, strategy_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific strategy."""
        if strategy_name not in self.param_manager.get_available_strategies():
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        parameters = self.param_manager.get_strategy_parameters(strategy_name)
        defaults = self.param_manager.get_default_parameters(strategy_name)
        
        # Convert ParameterRange objects to serializable dictionaries
        serializable_parameters = {}
        for param_name, param_range in parameters.items():
            serializable_parameters[param_name] = {
                'min_val': param_range.min_val,
                'max_val': param_range.max_val,
                'param_type': param_range.param_type,
                'description': param_range.description
            }
        
        return {
            'name': strategy_name,
            'display_name': strategy_name.replace('_', ' ').title(),
            'description': self._get_strategy_description(strategy_name),
            'parameters': serializable_parameters,
            'defaults': defaults,
            'available': True
        }
    
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
    
    # ========== Parameter Management ==========
    
    def validate_parameters(self, strategy_name: str, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Validate strategy parameters and return any errors."""
        return self.param_manager.validate_parameters(parameters, strategy_name)
    
    def get_default_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Get default parameter values for a strategy."""
        return self.param_manager.get_default_parameters(strategy_name)
    
    # ========== Backtesting ==========
    
    def run_backtest(self,
                    crypto_id: str,
                    strategy_name: str,
                    parameters: Dict[str, Any],
                    timeframe: str = "7d",
                    interval: str = "30m",
                    save_result: bool = True) -> Dict[str, Any]:
        """
        Run comprehensive backtest.
        
        Args:
            crypto_id: Cryptocurrency identifier
            strategy_name: Trading strategy name
            parameters: Strategy parameters
            timeframe: Data timeframe (e.g., "7d", "30d")
            interval: Data interval (e.g., "30m", "1h")
            save_result: Whether to save the result
            
        Returns:
            Backtest results dictionary
        """
        self.logger.info(f"Starting backtest for {crypto_id} with {strategy_name}")
        
        try:
            # Validate parameters
            validation_errors = self.validate_parameters(strategy_name, parameters)
            if validation_errors:
                raise ValueError(f"Parameter validation failed: {validation_errors}")
            
            # Run the backtest using the wrapper
            result = self.backtester.run_single_backtest(
                crypto=crypto_id,
                strategy=strategy_name,
                parameters=parameters,
                timeframe=timeframe,
                interval=interval
            )
            
            # Enhance result with metadata
            enhanced_result = {
                **result,
                'backtest_id': self._generate_backtest_id(),
                'timestamp': datetime.now().isoformat(),
                'engine_version': '2.0.0'
            }
            
            # Save result if requested
            if save_result and result.get('success'):
                result_path = self.result_manager.save_backtest_result(
                    crypto_id, strategy_name, enhanced_result
                )
                enhanced_result['result_path'] = result_path
                self.logger.info(f"Backtest result saved to {result_path}")
            
            self.logger.info(f"Backtest completed for {crypto_id}")
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Backtest failed for {crypto_id}: {str(e)}")
            return {
                'crypto': crypto_id,
                'strategy': strategy_name,
                'parameters': parameters,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_batch_backtest(self, test_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run multiple backtests in batch."""
        return self.backtester.run_batch_backtest(test_configs)
    
    # ========== Optimization ==========
    
    def run_optimization(self,
                        crypto_id: str,
                        strategy_name: str,
                        n_trials: int = 50,
                        timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Run Bayesian optimization for a single crypto/strategy pair.
        
        Args:
            crypto_id: Cryptocurrency identifier
            strategy_name: Trading strategy name
            n_trials: Number of optimization trials
            timeout: Timeout in seconds (optional)
            
        Returns:
            Optimization results dictionary
        """
        self.logger.info(f"Starting optimization for {crypto_id} with {strategy_name}")
        
        try:
            result = self.optimizer.optimize_single_crypto(
                crypto=crypto_id,
                strategy=strategy_name,
                n_trials=n_trials,
                timeout=timeout
            )
            
            self.logger.info(f"Optimization completed for {crypto_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Optimization failed for {crypto_id}: {str(e)}")
            return {
                'crypto': crypto_id,
                'strategy': strategy_name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_volatile_optimization(self,
                                strategy_name: str,
                                n_trials: int = 30,
                                top_count: int = 10,
                                min_volatility: float = 5.0) -> Dict[str, Any]:
        """
        Run optimization on multiple volatile cryptocurrencies.
        
        Args:
            strategy_name: Trading strategy name
            n_trials: Number of trials per crypto
            top_count: Number of top volatile cryptos to optimize
            min_volatility: Minimum volatility threshold
            
        Returns:
            Batch optimization results
        """
        self.logger.info(f"Starting volatile crypto optimization with {strategy_name}")
        
        try:
            result = self.optimizer.optimize_volatile_cryptos(
                strategy=strategy_name,
                n_trials=n_trials,
                top_count=top_count,
                min_volatility=min_volatility
            )
            
            self.logger.info(f"Volatile crypto optimization completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Volatile crypto optimization failed: {str(e)}")
            return {
                'strategy': strategy_name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    # ========== Results Management ==========
    
    def get_optimization_results(self, crypto_id: str, strategy_name: str) -> Optional[Dict]:
        """Get optimization results for a specific crypto/strategy pair."""
        return self.optimizer.load_optimization_results(crypto_id, strategy_name)
    
    def get_all_results(self) -> List[Dict]:
        """Get all optimization results."""
        return self.optimizer.get_all_results()
    
    def get_top_results(self, limit: int = 10) -> List[Dict]:
        """Get top optimization results by performance."""
        return self.optimizer.get_top_results(limit)
    
    def get_backtest_history(self,
                           crypto_id: Optional[str] = None,
                           strategy_name: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Get backtest history."""
        return self.result_manager.get_backtest_history(crypto_id, strategy_name, limit)

    def get_analysis_history(self,
                           crypto_id: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Get analysis history."""
        return self.result_manager.get_analysis_history(crypto_id, limit)

    def get_crypto_status(self, crypto_id: str) -> Dict[str, Any]:
        """
        Get status indicators for a specific cryptocurrency.
        """
        all_results = self.optimizer.get_all_results()
        crypto_results = [r for r in all_results if r.get('crypto') == crypto_id]

        if not crypto_results:
            return {
                "has_optimization_results": False,
                "has_valid_optimization_results": False,
                "has_config_params": False
            }

        best_strategy = None
        highest_profit = 0

        for result in crypto_results:
            profit = result.get('backtest_result', {}).get('total_profit_percentage', 0)
            if profit > highest_profit:
                highest_profit = profit
                best_strategy = {
                    'name': result.get('strategy'),
                    'parameters': result.get('best_params'),
                    'profit_percentage': profit
                }

        if best_strategy:
            return {
                "has_optimization_results": True,
                "has_valid_optimization_results": True,
                "best_strategy": best_strategy,
                "has_config_params": False
            }
        else:
            return {
                "has_optimization_results": True,
                "has_valid_optimization_results": False,
                "error": "No profitable strategy found",
                "has_config_params": False
            }

    # ========== Analysis ==========
    
    def analyze_crypto(self, 
                      crypto_id: str, 
                      strategy_name: Optional[str] = None,
                      timeframe: str = "7d",
                      custom_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run comprehensive crypto analysis.
        
        Args:
            crypto_id: Cryptocurrency identifier
            strategy_name: Trading strategy name (optional)
            timeframe: Data timeframe
            custom_params: Custom parameters (optional)
            
        Returns:
            Analysis results dictionary
        """
        self.logger.info(f"Starting analysis for {crypto_id}")
        
        try:
            # If no strategy specified, use best performing strategy for this crypto
            if not strategy_name:
                results = self.get_all_results()
                crypto_results = [r for r in results if r.get('crypto') == crypto_id]
                if crypto_results:
                    best_result = max(crypto_results, key=lambda x: x.get('best_value', -999))
                    strategy_name = best_result.get('strategy') or 'EMA_Only'
                else:
                    strategy_name = 'EMA_Only'  # Default strategy
            
            # Use custom params or load optimized params
            if custom_params:
                parameters = custom_params
            else:
                if not strategy_name:
                    # This path should not be taken given the logic above, but it satisfies the type checker
                    raise ValueError("Strategy name could not be determined.")
                opt_result = self.get_optimization_results(crypto_id, strategy_name)
                if opt_result and opt_result.get('best_params'):
                    parameters = opt_result['best_params']
                else:
                    parameters = self.get_default_parameters(strategy_name)
            
            # Check for existing analysis result (already implemented)
            existing_analyses = self.result_manager.get_analysis_history(crypto_id=crypto_id)
            for existing_analysis in existing_analyses:
                # Convert timeframe to days for comparison
                existing_timeframe_days = existing_analysis.get('timeframe_days')
                requested_timeframe_days = self._timeframe_to_days(timeframe)

                # Compare parameters. Handle cases where parameters_used might be a string (JSON dump)
                existing_params = existing_analysis.get('parameters_used')
                if isinstance(existing_params, str):
                    try:
                        existing_params = json.loads(existing_params)
                    except json.JSONDecodeError:
                        existing_params = {}

                if (existing_analysis.get('strategy_used') == strategy_name and
                    existing_timeframe_days == requested_timeframe_days and
                    existing_params == parameters):
                    self.logger.info(f"Found existing analysis for {crypto_id} with strategy {strategy_name}. Returning existing result.")
                    return existing_analysis

            # If no existing analysis, search for the most profitable backtest result
            optimization_history = self.result_manager.get_optimization_history(crypto_id=crypto_id, strategy_name=strategy_name)
            most_profitable_backtest = None
            highest_profit = -1000 # Initialize with a very low number

            for opt_result in optimization_history:
                backtest_result = opt_result.get('backtest_result')
                if backtest_result:
                    profit = backtest_result.get('total_profit_percentage', -1000)
                    if profit > highest_profit:
                        highest_profit = profit
                        most_profitable_backtest = opt_result

            if not most_profitable_backtest:
                self.logger.warning(f"No existing backtest found for {crypto_id} with strategy {strategy_name}. Cannot perform analysis without running a backtest.")
                return {
                    'success': False,
                    'error': 'No matching backtest found. Please run a backtest first.',
                    'crypto_id': crypto_id,
                    'strategy_used': strategy_name,
                    'parameters_used': parameters,
                    'timeframe_days': self._timeframe_to_days(timeframe),
                    'analysis_timestamp': datetime.now().isoformat()
                }

            # Use the found backtest result to construct the analysis_result
            result = most_profitable_backtest
            self.logger.info(f"Using existing backtest result for analysis: {result}")
            self.logger.info(f"Result from run_backtest: {result}")
            
            # Enhance with analysis metadata
            analysis_result = {
                'analysis_id': self._generate_analysis_id(),
                'crypto_id': crypto_id,  # Explicitly add crypto_id
                'analysis_type': 'backtest_analysis',
                'strategy_used': strategy_name,
                'parameters_source': 'custom' if custom_params else 'optimized',
                'timeframe_days': self._timeframe_to_days(timeframe),
                'analysis_timestamp': datetime.now().isoformat(),
                'backtest_result': result.get('backtest_result', { # Use existing backtest_result if present
                    'total_profit_percentage': result.get('total_profit_percentage'),
                    'total_trades': result.get('total_trades'),
                    'win_rate': result.get('win_rate')
                })
            }

            # Add current price
            crypto_info = self.crypto_discovery.get_crypto_info(crypto_id)
            if crypto_info and crypto_info.get('market_data') and crypto_info['market_data'].get('current_price') and crypto_info['market_data']['current_price'].get('usd'):
                analysis_result['current_price'] = crypto_info['market_data']['current_price']['usd']
            else:
                raise ValueError(f"Could not retrieve current price for {crypto_id} from external service.")

            # Add current signal based on final position from backtest
            final_position = result.get('final_position', 0) # 0: None, 1: Long, -1: Short
            if final_position == 1:
                analysis_result['current_signal'] = 'LONG'
            elif final_position == -1:
                analysis_result['current_signal'] = 'SHORT'
            else:
                analysis_result['current_signal'] = 'HOLD'

            # --- Support/Resistance Analysis ---
            df: Optional[pd.DataFrame] = None
            resistance_lines: List[Dict[str, Any]] = []
            support_lines: List[Dict[str, Any]] = []
            active_resistance: List[Dict[str, Any]] = []
            active_support: List[Dict[str, Any]] = []
            latest_price_point: Optional[pd.Series] = None
            first_timestamp: Optional[datetime] = None
            try:
                timeframe_days = self._timeframe_to_days(timeframe)
                df = get_crypto_data_merged(crypto_id, int(timeframe_days), self.config)
                if df is not None and not df.empty:
                    self.logger.debug(f"DataFrame for S/R analysis: {df.head()}")
                    df['price'] = df['close'] # Add a 'price' column for swing point analysis
                    first_timestamp = df.index[0].to_pydatetime()

                    # Discover optimal percentage change
                    optimal_percentage_change = auto_discover_percentage_change(df, first_timestamp)
                    if optimal_percentage_change is None:
                        self.logger.warning("Optimal percentage change could not be determined. Using default 0.005.")
                        optimal_percentage_change = 0.005

                    swing_highs_df, swing_lows_df = find_swing_points(df, percentage_change=optimal_percentage_change)
                    self.logger.debug(f"Swing highs: {swing_highs_df.head()}")
                    self.logger.debug(f"Swing lows: {swing_lows_df.head()}")
                    
                    resistance_lines = []
                    support_lines = []

                    if not swing_highs_df.empty and first_timestamp:
                        resistance_lines = find_support_resistance_lines(swing_highs_df, 'resistance', first_timestamp)
                        self.logger.debug(f"Resistance lines generated: {resistance_lines}")
                    
                    if not swing_lows_df.empty and first_timestamp:
                        support_lines = find_support_resistance_lines(swing_lows_df, 'support', first_timestamp)
                        self.logger.debug(f"Support lines generated: {support_lines}")

                    # Analyze line durations to find active lines
                    # This function returns a summary of durations, but also finds active lines internally
                    # We need to extract the active lines from the last point of the analysis
                    # For simplicity, we'll re-implement the active line finding based on the last price point
                    
                    active_resistance = []
                    active_support = []

                    if not df.empty:
                        latest_price_point = df.iloc[-1]
                        current_price = latest_price_point['price']
                        if first_timestamp and isinstance(latest_price_point.name, pd.Timestamp):
                            current_relative_timestamp = (latest_price_point.name.timestamp() - first_timestamp.timestamp())
                        else:
                            current_relative_timestamp = 0.0

                        # Find active resistance lines
                        for r_line in resistance_lines:
                            r_y_at_current_time = r_line['slope'] * current_relative_timestamp + r_line['intercept']
                            if current_price <= r_y_at_current_time:
                                r_line['price'] = r_y_at_current_time
                                r_line['strength'] = round(abs(r_line['r_value']) * 10, 2)
                                active_resistance.append(r_line)
                                break # Found the first resistance above

                        # Find active support lines
                        for s_line in support_lines:
                            s_y_at_current_time = s_line['slope'] * current_relative_timestamp + s_line['intercept']
                            if current_price >= s_y_at_current_time:
                                s_line['price'] = s_y_at_current_time
                                s_line['strength'] = round(abs(s_line['r_value']) * 10, 2)
                                active_support.append(s_line)
                                break # Found the first support below

                    analysis_result['active_resistance_lines'] = self._serialize_line_timestamps(active_resistance)
                    analysis_result['active_support_lines'] = self._serialize_line_timestamps(active_support)
                else:
                    self.logger.warning(f"No data for support/resistance analysis for {crypto_id}")
                    analysis_result['active_resistance_lines'] = []
                    analysis_result['active_support_lines'] = []

            except Exception as e:
                self.logger.error(f"Error in support/resistance analysis for {crypto_id}: {e}")
                analysis_result['active_resistance_lines'] = []
                analysis_result['active_support_lines'] = []

            # --- Chart Generation ---
            try:
                if df is not None and not df.empty:
                    chart_data = generate_chart(
                        df,
                        resistance_lines,
                        support_lines,
                        active_resistance,
                        active_support,
                        crypto_id
                    )
                    analysis_result['chart_data'] = chart_data
                    self.logger.info(f"Chart generated for {crypto_id}")
                else:
                    analysis_result['chart_data'] = None
            except Exception as e:
                self.logger.error(f"Error generating chart for {crypto_id}: {e}")
                analysis_result['chart_data'] = None

            # Predict next move using existing function
            try:
                if df is not None and latest_price_point is not None and first_timestamp is not None:
                    next_move_prediction = predict_next_move(df, latest_price_point, active_resistance, active_support, first_timestamp)
                    self.logger.debug(f"Next move prediction: {next_move_prediction}")
                    analysis_result['next_move_prediction'] = next_move_prediction
                else:
                    analysis_result['next_move_prediction'] = None
            except Exception as e:
                self.logger.error(f"Error in next move prediction: {e}")
                analysis_result['next_move_prediction'] = None

            # Make a copy for logging, without the chart data
            log_result = analysis_result.copy()
            log_result.pop('chart_data', None)
            self.logger.info(f"Final analysis_result: {log_result}")
            
            # Save the analysis result
            self.result_manager.save_analysis_result(crypto_id, analysis_result)

            self.logger.info(f"Analysis completed for {crypto_id}")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Analysis failed for {crypto_id}: {str(e)}")
            raise e
    
    # ========== System Health ==========
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        # Check backtester availability
        strategies = self.backtester.get_available_strategies()
        health['checks']['backtester'] = {
            'status': 'ok' if strategies else 'warning',
            'message': f'{len(strategies)} strategies available' if strategies else 'Backtester using mock data',
            'strategies': strategies
        }
        
        # Check crypto discovery
        try:
            cryptos = self.crypto_discovery.get_volatile_cryptos(limit=5, min_volatility=0.1)
            health['checks']['crypto_discovery'] = {
                'status': 'ok' if cryptos else 'error',
                'message': f'{len(cryptos)} cryptos discovered' if cryptos else 'Failed to discover cryptos'
            }
        except Exception as e:
            health['checks']['crypto_discovery'] = {
                'status': 'error',
                'message': f'Crypto discovery failed: {str(e)}'
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
        
        # Check parameter manager
        param_strategies = self.param_manager.get_available_strategies()
        health['checks']['parameter_manager'] = {
            'status': 'ok' if param_strategies else 'error',
            'message': f'{len(param_strategies)} strategies configured',
            'strategies': param_strategies
        }
        
        # Overall status
        error_checks = [check for check in health['checks'].values() if check['status'] == 'error']
        if error_checks:
            health['status'] = 'error'
        elif any(check['status'] == 'warning' for check in health['checks'].values()):
            health['status'] = 'warning'
        
        return health
    
    # ========== Utility Methods ==========
    
    def _timeframe_to_days(self, timeframe: str) -> float:
        """Convert timeframe string to number of days."""
        if isinstance(timeframe, int):
            return float(timeframe)
        if not isinstance(timeframe, str):
            return 0.0
        
        timeframe = timeframe.lower()
        
        if timeframe.endswith('d'):
            return float(timeframe[:-1])
        elif timeframe.endswith('h'):
            # Return as a fraction of a day
            return float(timeframe[:-1]) / 24
        elif timeframe.endswith('m'):
            # Return as a fraction of a day
            return float(timeframe[:-1]) / (24 * 60)
        else:
            try:
                # Assume it's already in days if no suffix
                return float(timeframe)
            except ValueError:
                self.logger.warning(f"Could not parse timeframe: {timeframe}. Defaulting to 0.")
                return 0.0

    def _serialize_line_timestamps(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converts Timestamp objects within line dictionaries to ISO format strings."""
        serialized_lines = []
        for line in lines:
            serialized_line = line.copy()
            if 'points' in serialized_line and isinstance(serialized_line['points'], list):
                serialized_line['points'] = [
                    p.isoformat() if isinstance(p, pd.Timestamp) else p
                    for p in serialized_line['points']
                ]
            serialized_lines.append(serialized_line)
        return serialized_lines

    def get_config(self) -> Dict[str, Any]:
        """Get system configuration for frontend."""
        return {
            'strategies': self.get_strategies(),
            'default_timeframe': config.DEFAULT_TIMEFRAME, # Use value from config.py
            'default_interval': config.DEFAULT_INTERVAL, # Also use this from config.py
            'max_optimization_trials': 100,
            'supported_timeframes': ['1d', '7d', '30d', '90d'],
            'supported_intervals': ['15m', '30m', '1h', '4h', '1d'],
            'version': '2.0.0'
        }

    def _generate_backtest_id(self) -> str:
        """Generate a unique ID for a backtest."""
        import uuid
        return str(uuid.uuid4())

    def _generate_analysis_id(self) -> str:
        """Generate a unique ID for an analysis."""
        import uuid
        return str(uuid.uuid4())
