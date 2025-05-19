import pandas as pd
from typing import List, Dict, Type, Any, Optional
import importlib # For dynamic import

import inspect   # For inspecting module members

import numpy as np # For calculations like mean, std
from pathlib import Path
import json
from datetime import datetime, timezone # Added timezone

# Assuming fetchers and BaseStrategy are accessible via these relative
# Adjust if your project structure dictates otherwise.

from ..fetchers.base_fetcher import Fetcher

from ..fetchers import CoinGeckoFetcher, PolygonFetcher 
from ..strategies.base_strategy import BaseStrategy, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD

from ..indicators.base_indicator import Indicator # For type hints, and for issubclass check
# Specific indicator imports for type checking and parameter optimization logic
from ..indicators.rsi_indicator import RSIIndicator
from ..indicators.bollinger_bands_indicator import BollingerBandsIndicator
from ..indicators.breakout_indicator import BreakoutIndicator

# from ..indicators.volume_spike_indicator import VolumeSpikeIndicator # Example if adding more
# from ..indicators.atr_indicator import ATRIndicator # Example if adding more


class NumpyJSONEncoder(json.JSONEncoder):
    """ Custom encoder for numpy data types , pandas.NA, and infinity. """

    def default(self, o: Any): # Changed 'obj' to 'o' and added type hint for clarity
        if isinstance(o, np.integer): # Covers all NumPy integer types
            return int(o)
        elif isinstance(o, np.floating): # Covers all NumPy float types
            if np.isnan(o):
                return None  # Serialize np.nan as null in JSON
            elif np.isinf(o):
                return str(o) # Serialize np.inf and -np.inf as "inf" and "-inf"
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist() # Convert ndarrays to lists
        elif isinstance(o, np.bool_):
            return bool(o)
        elif pd.isna(o): # Handle pandas.NA specifically
            return None # Serialize pd.NA as null        return super(NumpyJSONEncoder, self).default(o)

class BackTest:
    """
    A class to perform backtesting for a given ticker.
    It handles data fetching, strategy execution.
    It automatically discovers and uses available indicators from the 'stock_monitoring_app.indicators' module.
    Threshold optimization remains a placeholder.
    """


    def __init__(self,
                 ticker: str,
                 period: str,
                 interval: str): # Removed fetcher_type
        """
        Initializes the BackTest instance.
        Fetcher type is now inferred from the ticker.

        Args:
            ticker: The stock/crypto ticker symbol (e.g., "AAPL", "bitcoin").
            period: The historical data period (e.g., "1y", "6mo").
            interval: The data interval (e.g., "1d", "1h").
        """


        self.ticker = ticker        
        self.period = period

        self.interval = interval
        self.fetcher = self._get_fetcher(self.ticker) # Fetcher type inferred from ticker
        self.historical_data: Optional[pd.DataFrame] = None
        # Indicator configurations will be populated by determine_relevant_indicators
        self.current_indicator_configs: List[Dict] = [] 
        
        self.strategy: Optional[BaseStrategy] = None        
        self.results: Optional[pd.DataFrame] = None
        self.performance_metrics: Dict[str, Any] = {}

    def _get_fetcher(self, ticker: str) -> Fetcher:
        """
        Initializes and returns the appropriate data fetcher based on the ticker.        Uses CoinGecko for known crypto tickers, Polygon for others.
        """
        # Simple heuristic: list of known crypto identifiers (lowercase)
        # This list can be expanded or managed externally in a more complex system.
        known_crypto_tickers = [
            "bitcoin", "ethereum", "binancecoin", "cardano", "solana", 
            "ripple", "xrp", "polkadot", "dogecoin", "shiba-inu", "litecoin", 
            "tron", "avalanche-2", "btc", "eth", "sol", "ada", "dot", "ltc", "trx"
            # Add more common crypto IDs as needed
        ]
        # Common crypto pair suffixes (often not needed for CoinGecko ID but good for pattern)
        # crypto_suffixes = ["-usd", "-usdt", "-btc", "-eur"]

        ticker_lower = ticker.lower()

        is_crypto = False
        if ticker_lower in known_crypto_tickers:
            is_crypto = True
        # Optionally, check for suffixes if the above list isn't comprehensive enough,
        # though CoinGecko usually prefers the base coin ID.
        # for suffix in crypto_suffixes:
        #     if ticker_lower.endswith(suffix):
        #         is_crypto = True
        #         break
        
        if is_crypto:
            print(f"INFO: Detected '{ticker}' as a cryptocurrency. Using CoinGeckoFetcher.")
            return CoinGeckoFetcher()
        else:
            print(f"INFO: Assuming '{ticker}' is a stock ticker. Using PolygonFetcher.")
            return PolygonFetcher()


    def fetch_historical_data(self) -> Optional[pd.DataFrame]: # Corrected return type hint
        """Fetches historical data for the configured ticker, period, and interval."""
        print(f"Fetching historical data for {self.ticker} using {self.fetcher.get_service_name()} for period {self.period}, interval {self.interval}...")
        try:
            self.historical_data = self.fetcher.fetch_data(self.ticker, self.period, self.interval)
            if self.historical_data is None or self.historical_data.empty:
                print(f"Warning: No data fetched for {self.ticker}. Please check ticker, period, interval, and fetcher configuration.")
            else:
                print(f"Successfully fetched {len(self.historical_data)} data points for {self.ticker}.")
        except Exception as e:
            print(f"Error fetching data for {self.ticker}: {e}")
            self.historical_data = pd.DataFrame() # Ensure it's an empty DataFrame on error
        return self.historical_data

    def determine_relevant_indicators(self, data: pd.DataFrame) -> List[Dict]:
        """

        Placeholder for determining relevant indicators and their initial parameters
        for the given ticker and historical data.
        This method now automatically discovers indicators.

        Args:
            data: The historical OHLCV data for the ticker. (Currently unused for discovery but kept for future relevance logic)

        Returns:
            A list of indicator configurations.
        """

        print(f"INFO: Automatically discovering relevant indicators for {self.ticker}...")
        discovered_configs: List[Dict] = []
        indicators_module_path = "stock_monitoring_app.indicators" # Define path before try block
        
        try:
            # The path is relative to the project root if stock_monitoring_app is in PYTHONPATH
            indicators_module = importlib.import_module(indicators_module_path)

            for name, member_type in inspect.getmembers(indicators_module):
                if inspect.isclass(member_type) and \
                   issubclass(member_type, Indicator) and \
                   member_type is not Indicator:  # Exclude the base Indicator class itself
                    
                    print(f"      Discovered indicator: {member_type.__name__}")
                    # Use default parameters for now.
                    discovered_configs.append({'type': member_type, 'params': {}})
            
            if not discovered_configs:
                print("      Warning: No indicators derived from BaseIndicator found in the 'stock_monitoring_app.indicators' module.")
            else:
                print(f"      Successfully discovered {len(discovered_configs)} indicator(s).")

        except ImportError as e:
            print(f"      Error: Could not import indicators module at '{indicators_module_path}': {e}")
        except Exception as e:
            print(f"      An unexpected error occurred during indicator discovery: {e}")
            

        self.current_indicator_configs = discovered_configs

        return self.current_indicator_configs

    def _calculate_placeholder_pnl(self, results_df: Optional[pd.DataFrame]) -> float:
        """Helper to calculate placeholder P&L for optimization runs."""
        if results_df is None or results_df.empty:
            return -float('inf')

        profit_loss = 0.0
        position = 0  # 0 = no position, 1 = long, -1 = short
        entry_price = 0.0


        for _, row in results_df.iterrows():
            current_price = row['Close']
            signal = row['Strategy_Signal']

            if position == 0:  # Currently flat
                if signal == SIGNAL_BUY:
                    position = 1
                    entry_price = current_price
                elif signal == SIGNAL_SELL:
                    position = -1
                    entry_price = current_price
            elif position == 1:  # Currently long
                if signal == SIGNAL_SELL:  # Closing long
                    profit_loss += (current_price - entry_price)
                    position = 0  # Go flat
                    entry_price = 0 # Reset entry price
                # If signal is BUY or HOLD while long, no PNL action for this simple calculator
            elif position == -1:  # Currently short
                if signal == SIGNAL_BUY:  # Closing short
                    profit_loss += (entry_price - current_price)
                    position = 0  # Go flat
                    entry_price = 0 # Reset entry price
                # If signal is SELL or HOLD while short, no PNL action for this simple calculator
        
        return round(profit_loss, 2)

    def optimize_thresholds(self, data: pd.DataFrame, initial_discovered_configs: List[Dict]) -> List[Dict]:
        """
        Generalized implementation for optimizing thresholds (parameters) for discovered indicators.
        Each indicator must provide a 'get_search_space' static method that returns a dict of param_name: list_of_values.
        """
        print(f"INFO: Starting generalized threshold optimization for {self.ticker}...")

        if data is None or data.empty:
            print("      Warning: Historical data is empty. Cannot perform optimization.")
            self.current_indicator_configs = initial_discovered_configs
            return initial_discovered_configs

        if not initial_discovered_configs:
            print("      No indicators discovered. Skipping optimization.")
            self.current_indicator_configs = []
            return []

        final_optimized_configs: List[Dict] = []

        for idx_tuned, config_to_optimize in enumerate(initial_discovered_configs):
            indicator_class = config_to_optimize['type']
            best_params_for_current_type = config_to_optimize['params'].copy()
            baseline_eval_configs = []
            for i, conf in enumerate(initial_discovered_configs):
                if i == idx_tuned:
                    baseline_eval_configs.append({'type': indicator_class, 'params': best_params_for_current_type})
                else:
                    baseline_eval_configs.append(conf)

            strategy_baseline = BaseStrategy(indicator_configs=baseline_eval_configs)
            results_baseline = strategy_baseline.run(data.copy())
            best_pnl_for_current_type = self._calculate_placeholder_pnl(results_baseline)

            print(f"      Optimizing {indicator_class.__name__}: Initial PNL with default params = {best_pnl_for_current_type}")

            # --- Generalized grid search ---
            param_search_space_defined = False
            search_space = {}

            # The indicator class must define a staticmethod get_search_space() returning {param: [values]}
            if hasattr(indicator_class, 'get_search_space') and callable(getattr(indicator_class, 'get_search_space')):
                search_space = indicator_class.get_search_space()
                param_search_space_defined = True

            if param_search_space_defined and search_space:
                import itertools
                param_names = list(search_space.keys())
                param_value_lists = [search_space[k] for k in param_names]

                for combination in itertools.product(*param_value_lists):
                    current_trial_params = dict(zip(param_names, combination))
                    # Always add 'column': 'Close' if not set and 'Close' is expected
                    if 'column' in param_names and 'column' not in current_trial_params:
                        current_trial_params['column'] = 'Close'

                    trial_run_configs = []
                    for i_conf, conf_item in enumerate(initial_discovered_configs):
                        if i_conf == idx_tuned:
                            trial_run_configs.append({'type': indicator_class, 'params': current_trial_params})
                        else:
                            trial_run_configs.append(conf_item)
                    trial_strategy = BaseStrategy(indicator_configs=trial_run_configs)
                    trial_results = trial_strategy.run(data.copy())
                    current_pnl = self._calculate_placeholder_pnl(trial_results)
                    if current_pnl > best_pnl_for_current_type:
                        best_pnl_for_current_type = current_pnl
                        best_params_for_current_type = current_trial_params
            else:
                print(f"      No get_search_space() defined for {indicator_class.__name__}. Using default params.")

            print(f"      Selected best PNL for {indicator_class.__name__}: {best_pnl_for_current_type} with params: {best_params_for_current_type}")
            final_optimized_configs.append({'type': indicator_class, 'params': best_params_for_current_type})

        print(f"INFO: Generalized threshold optimization finished for {self.ticker}.")
        self.current_indicator_configs = final_optimized_configs
        return final_optimized_configs

    def run_backtest(self) -> Optional[pd.DataFrame]:
        """
        Executes the backtest:
        1. Fetches data (if not already fetched).
        2. (Placeholder) Determines relevant indicators.
        3. (Placeholder) Optimizes thresholds.
        4. Runs the strategy using BaseStrategy.
        5. (Placeholder) Evaluates performance.
        """
        if self.historical_data is None or self.historical_data.empty:
            print(f"Historical data for {self.ticker} is not yet fetched or is empty. Fetching now...")
            self.fetch_historical_data()
            if self.historical_data is None or self.historical_data.empty:
                print(f"Cannot run backtest for {self.ticker}: historical data fetching failed or yielded no data.")                
                return None


        # Step 1: Determine relevant indicators (auto-discovery)
        # This populates self.current_indicator_configs
        print("Determining relevant indicators (auto-discovery)...")
        # Pass self.historical_data, as the method signature expects it, even if not used by current discovery logic
        self.current_indicator_configs = self.determine_relevant_indicators(self.historical_data) 
        
        if not self.current_indicator_configs:
            print(f"Error: No indicator configurations discovered for {self.ticker}. Cannot run backtest.")
            return None

        # Step 2: Optimize thresholds (placeholder - uses the discovered configs)
        print("Applying (or skipping) threshold optimization (placeholder)...")
        # The current_indicator_configs from discovery are passed for (placeholder) optimization
        self.current_indicator_configs = self.optimize_thresholds(self.historical_data, self.current_indicator_configs)

        print(f"Running backtest for {self.ticker} with {len(self.current_indicator_configs)} configured indicator(s).")
        self.strategy = BaseStrategy(indicator_configs=self.current_indicator_configs)
        
        # Run strategy on a copy of the historical data
        self.results = self.strategy.run(self.historical_data.copy()) 

        if self.results is None or self.results.empty:
            print(f"Backtest for {self.ticker} did not produce results. Check strategy and indicator logic.")
        else:

            print(f"Backtest completed for {self.ticker}. Results DataFrame generated.")
            # Step 3: Evaluate performance
            self.evaluate_performance()
            # Step 4: Save results if they were generated
            self.save_results()
            
        return self.results
    
    def evaluate_performance(self) -> Dict[str, Any]:
        """Calculates and returns performance metrics from backtest results."""
        if self.results is None or self.results.empty:
            print(f"No backtest results available for {self.ticker} to evaluate.")
            return {}

        required_columns = ['Close', 'Strategy_Signal']
        for col in required_columns:
            if col not in self.results.columns:
                raise KeyError(f"'{col}' column is missing in the results DataFrame.")



        trades_details = [] # Store dicts: {'pnl': float, 'entry_price': float, 'type': str}
        position = 0  # 0 = no position, 1 = long, -1 = short
        entry_price = 0.0  # Initialize entry_price

        for _, row in self.results.iterrows():
            current_price = row['Close']
            signal = row['Strategy_Signal']

            if position == 0: # Currently flat
                if signal == SIGNAL_BUY:
                    position = 1
                    entry_price = current_price
                elif signal == SIGNAL_SELL:
                    position = -1
                    entry_price = current_price
            elif position == 1: # Currently long
                if signal == SIGNAL_SELL: # Signal to sell while long
                    pnl = current_price - entry_price
                    trades_details.append({'pnl': pnl, 'entry_price': entry_price, 'type': 'long'})
                    position = 0 # Go flat
                    entry_price = 0 # Reset entry price
            elif position == -1: # Currently short
                if signal == SIGNAL_BUY: # Signal to buy while short
                    pnl = entry_price - current_price
                    trades_details.append({'pnl': pnl, 'entry_price': entry_price, 'type': 'short'})
                    position = 0 # Go flat
                    entry_price = 0 # Reset entry price

        trade_pnl_list = [td['pnl'] for td in trades_details]
        num_trades = len(trade_pnl_list)
        
        net_profit = sum(trade_pnl_list)
        num_winning_trades = len([pnl for pnl in trade_pnl_list if pnl > 0])
        num_losing_trades = len([pnl for pnl in trade_pnl_list if pnl < 0])

        gross_profit = sum([pnl for pnl in trade_pnl_list if pnl > 0])
        gross_loss = abs(sum([pnl for pnl in trade_pnl_list if pnl < 0]))

        win_rate_pct = (num_winning_trades / num_trades) * 100 if num_trades > 0 else 0.0
        avg_profit_per_winning_trade = gross_profit / num_winning_trades if num_winning_trades > 0 else 0.0
        avg_loss_per_losing_trade = gross_loss / num_losing_trades if num_losing_trades > 0 else 0.0
        
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0: # gross_loss is 0 but gross_profit > 0
            profit_factor = float('inf') 
        else: # both gross_profit and gross_loss are 0
            profit_factor = 0.0 
            
        avg_pnl_per_trade = net_profit / num_trades if num_trades > 0 else 0.0

        # Max Drawdown Calculation
        initial_capital = 10000.0         
        equity = initial_capital
        current_peak_equity = initial_capital
        max_drawdown_value = 0.0
        peak_at_max_drawdown = initial_capital

        for pnl_val in trade_pnl_list:
            equity += pnl_val
            if equity > current_peak_equity:
                current_peak_equity = equity
            
            drawdown = current_peak_equity - equity
            if drawdown > max_drawdown_value:
                max_drawdown_value = drawdown
                peak_at_max_drawdown = current_peak_equity
        
        max_drawdown_percentage = (max_drawdown_value / peak_at_max_drawdown) * 100 if peak_at_max_drawdown > 0 and max_drawdown_value > 0 else 0.0

        # Simplified Sharpe Ratio per trade
        trade_returns_pct_list = []
        if num_trades > 0:
            for td in trades_details:
                if td['entry_price'] != 0: 
                    trade_return_pct = (td['pnl'] / td['entry_price']) * 100
                    trade_returns_pct_list.append(trade_return_pct)
        
        sharpe_ratio_simplified_per_trade: Any = "N/A"
        if len(trade_returns_pct_list) >= 2: # Needs at least 2 data points for standard deviation
            mean_trade_return_pct = np.mean(trade_returns_pct_list)
            std_dev_trade_return_pct = np.std(trade_returns_pct_list)
            if std_dev_trade_return_pct > 0:
                sharpe_ratio_simplified_per_trade = round(mean_trade_return_pct / std_dev_trade_return_pct, 3)        
        self.performance_metrics = {
            "ticker": self.ticker,
            "period_tested": self.period,
            "interval_tested": self.interval,
            "total_data_points": len(self.historical_data) if self.historical_data is not None else 0,            "total_signals_non_hold": len(self.results[self.results['Strategy_Signal'] != SIGNAL_HOLD]),
            "num_buy_signals": len(self.results[self.results['Strategy_Signal'] == SIGNAL_BUY]),
            "num_sell_signals": len(self.results[self.results['Strategy_Signal'] == SIGNAL_SELL]),
            "total_trades": num_trades,
            "winning_trades": num_winning_trades,
            "losing_trades": num_losing_trades,
            "net_profit": round(net_profit, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "win_rate_pct": round(win_rate_pct, 2),
            "avg_profit_per_winning_trade": round(avg_profit_per_winning_trade, 2),
            "avg_loss_per_losing_trade": round(avg_loss_per_losing_trade, 2),
            "profit_factor": round(profit_factor, 2) if isinstance(profit_factor, (int, float)) and profit_factor not in [float('inf'), float('-inf')] else profit_factor,
            "avg_pnl_per_trade": round(avg_pnl_per_trade, 2),
            "max_drawdown_value": round(max_drawdown_value, 2),

            "max_drawdown_percentage": round(max_drawdown_percentage, 2),
            "sharpe_ratio_simplified_per_trade": sharpe_ratio_simplified_per_trade
        }

        return self.performance_metrics

    def get_results(self) -> Optional[pd.DataFrame]:
        """Returns the DataFrame containing the backtest results (data + signals)."""
        return self.results


    def get_performance_metrics(self) -> Dict[str, Any]:
        """Returns the dictionary of calculated performance metrics."""
        return self.performance_metrics

    def _get_project_root(self) -> Path:
        """
        Determines the project root directory.
        Assumes this script (backtest.py) is located at a path like:        .../project_root/stock_monitoring_app/backtest/backtest.py
        The project root is then three levels up from this file's directory.
        """
        # Path to the current file (backtest.py)
        current_file_path = Path(__file__).resolve()
        # .../stock_monitoring_app/backtest/ -> .../stock_monitoring_app/ -> .../project_root/
        project_root = current_file_path.parent.parent.parent
        return project_root

    def save_results(self):
        """
        Saves the backtest results DataFrame to a CSV file and performance_metrics        dictionary to a JSON file in a 'backtest_outputs' directory at the project root.
        Filenames are timestamped.
        """
        if (self.results is None or self.results.empty) and \
           (not self.performance_metrics): # Check if metrics dict is empty
            print("INFO: No results DataFrame or performance metrics to save.")
            return

        project_root = self._get_project_root()
        output_dir = project_root / "backtest_outputs"
        

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            # Use timezone-aware UTC datetime
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
            base_filename = f"{self.ticker}_{self.period}_{self.interval}_{timestamp_str}"

            # Save results DataFrame if it exists and is not empty
            if self.results is not None and not self.results.empty:
                results_filepath = output_dir / f"{base_filename}_results.csv"
                self.results.to_csv(results_filepath)
                print(f"Backtest results DataFrame saved to: {results_filepath}")
            else:
                if self.results is None:
                    print("INFO: Results DataFrame is None. Not saving CSV.")
                else: # self.results is an empty DataFrame
                    print("INFO: Results DataFrame is empty. Not saving CSV.")
            

            # Save performance metrics if the dictionary is not empty
            if self.performance_metrics:
                # Serialize indicator configurations
                serializable_indicator_configs = []
                if self.current_indicator_configs: # Ensure it's not None or empty                    
                    for config in self.current_indicator_configs:
                        indicator_class = config['type']
                        # Ensure params are serializable; NumpyJSONEncoder helps with numpy types
                        serializable_indicator_configs.append({
                            "module": indicator_class.__module__,

                            "class_name": indicator_class.__name__,
                            "params": config.get('params', {}) 
                        })
                if serializable_indicator_configs: # Only add if not empty
                    self.performance_metrics["indicator_configurations"] = serializable_indicator_configs

                metrics_filepath = output_dir / f"{base_filename}_metrics.json"
                with open(metrics_filepath, 'w') as f:
                    json.dump(self.performance_metrics, f, cls=NumpyJSONEncoder, indent=4)
                print(f"Performance metrics saved to: {metrics_filepath}")
            else:
                print("INFO: Performance metrics dictionary is empty. Not saving JSON.")

        except Exception as e:
            print(f"Error saving backtest results: {e}")


