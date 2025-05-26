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

                 interval: str,
                 initial_capital: float = 10000.0,
                 leverage: float = 1.0,
                 take_profit_pct: Optional[float] = None,
                 stop_loss_pct: Optional[float] = None): # Added leverage
        """
        Initializes the BackTest instance.
        Fetcher type is now inferred from the ticker.
        Leverage is applied to P&L calculations for non-crypto assets.

        Args:
            ticker: The stock/crypto ticker symbol (e.g., "AAPL", "bitcoin").
            period: The historical data period (e.g., "1y", "6mo").
            interval: The data interval (e.g., "1d", "1h").
            initial_capital: The starting capital for the backtest.
            leverage: The leverage to apply (1.0 to 20.0 for non-crypto, 1.0 for crypto).
        """


        self.ticker = ticker        
        self.period = period
        self.interval = interval        
        self.initial_capital = initial_capital
        self.leverage = float(leverage) # Ensure it's a float
        self._is_crypto = False # Will be set by _get_fetcher
        
        self.fetcher = self._get_fetcher(self.ticker) # Fetcher type inferred from ticker

        if self._is_crypto:
            if self.leverage != 1.0:
                print(f"INFO: Leverage for crypto asset '{self.ticker}' is always 1.0. Overriding provided leverage {self.leverage}.")
            self.leverage = 1.0
        else:
            if self.leverage < 1.0:
                print(f"WARNING: Leverage {self.leverage} for '{self.ticker}' is below minimum 1.0. Clamping to 1.0.")
                self.leverage = 1.0
            elif self.leverage > 20.0:

                print(f"WARNING: Leverage {self.leverage} for '{self.ticker}' exceeds maximum 20.0. Clamping to 20.0.")
                self.leverage = 20.0

        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct

        if self.take_profit_pct is not None and self.take_profit_pct <= 0:
            raise ValueError("Take profit percentage, if provided, must be positive and greater than 0.")
        if self.stop_loss_pct is not None and self.stop_loss_pct <= 0:
            raise ValueError("Stop loss percentage, if provided, must be positive and greater than 0.")
        
        self.historical_data: Optional[pd.DataFrame] = None
        # Indicator configurations will be populated by determine_relevant_indicators
        self.current_indicator_configs: List[Dict] = [] 
        
        self.strategy: Optional[BaseStrategy] = None        
        self.results: Optional[pd.DataFrame] = None # Will be populated with portfolio data
        self.performance_metrics: Dict[str, Any] = {}
        
        # Portfolio tracking attributes
        self.current_balance = self.initial_capital
        self.shares_held = 0
        self.trade_log: List[Dict] = []

    def _get_fetcher(self, ticker: str) -> Fetcher:
        """
        Initializes and returns the appropriate data fetcher based on the ticker.
        Uses CoinGecko for known crypto tickers, Polygon for others.
        Sets self._is_crypto attribute.
        """
        # Simple heuristic: list of known crypto identifiers (lowercase)
        known_crypto_tickers = [
            "bitcoin", "ethereum", "binancecoin", "cardano", "solana", 
            "ripple", "xrp", "polkadot", "dogecoin", "shiba-inu", "litecoin", 

            "tron", "avalanche-2", "btc", "eth", "sol", "ada", "dot", "ltc", "trx"
        ]
        ticker_lower = ticker.lower()
        if ticker_lower in known_crypto_tickers:
            self._is_crypto = True
            print(f"INFO: Detected '{ticker}' as a cryptocurrency. Using CoinGeckoFetcher.")
            return CoinGeckoFetcher()        
        else:
            self._is_crypto = False
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
                    profit_loss += (current_price - entry_price) * self.leverage
                    position = 0  # Go flat
                    entry_price = 0 # Reset entry price
                # If signal is BUY or HOLD while long, no PNL action for this simple calculator
            elif position == -1:  # Currently short
                if signal == SIGNAL_BUY:  # Closing short
                    profit_loss += (entry_price - current_price) * self.leverage
                    position = 0  # Go flat
                    entry_price = 0 # Reset entry price                # If signal is SELL or HOLD while short, no PNL action for this simple calculator
        
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

            if hasattr(indicator_class, 'get_search_space') and callable(getattr(indicator_class, 'get_search_space')):
                search_space = indicator_class.get_search_space()
                if search_space and isinstance(search_space, dict):
                    param_search_space_defined = True
                else:
                    print(f"      INFO: get_search_space() for {indicator_class.__name__} returned an empty or non-dict search space. Using default params.")
                    search_space = {} 
                    param_search_space_defined = False
            else:
                print(f"      INFO: No get_search_space() method found or callable for {indicator_class.__name__}. Using default params.")
                search_space = {}
                param_search_space_defined = False

            if param_search_space_defined and search_space: # Proceed only if search space is valid
                import itertools
                param_names = list(search_space.keys())
                
                all_param_lists_valid = True
                param_value_lists = []

                for p_name in param_names:
                    # Ensure the value for the parameter key is a non-empty list
                    param_values = search_space.get(p_name)
                    if not param_values or not isinstance(param_values, list):
                        print(f"      WARNING: Invalid or empty parameter list for '{p_name}' in {indicator_class.__name__}'s search space. Skipping detailed optimization for this indicator.")
                        all_param_lists_valid = False
                        break 
                    param_value_lists.append(param_values)

                if all_param_lists_valid and param_names: # Ensure param_names is not empty
                    for combination in itertools.product(*param_value_lists):
                        current_trial_params = dict(zip(param_names, combination))
                        
                        # Ensure 'column': 'Close' is added if not defined, this is a common default
                        # However, it's better if get_search_space() explicitly includes 'column': ['Close'] or other relevant columns
                        # if 'column' not in current_trial_params and 'Close' in data.columns: # Example specific handling
                        #    current_trial_params['column'] = 'Close'


                        trial_run_configs = []
                        for i_conf, conf_item in enumerate(initial_discovered_configs):
                            if i_conf == idx_tuned:
                                trial_run_configs.append({'type': indicator_class, 'params': current_trial_params})

                            else:                                trial_run_configs.append(conf_item)
                        


                        print(f"        TRIAL: Testing {indicator_class.__name__} with params: {current_trial_params}...", end="")
                        try:
                            trial_strategy = BaseStrategy(indicator_configs=trial_run_configs)
                            trial_results = trial_strategy.run(data.copy())

                            # --- START DEBUG BLOCK for printing raw signal counts from tuned indicator ---
                            print_debug_raw_signals = True # Define the flag here
                            if print_debug_raw_signals and trial_results is not None and not trial_results.empty:
                                try:
                                    # Instantiate the tuned indicator with current trial params to get its signal column names

                                    # This relies on the indicator populating self.signal_orientations correctly in its __init__
                                    temp_indicator_for_debug = indicator_class(data.copy(), **current_trial_params)
                                    tuned_indicator_signal_cols = list(temp_indicator_for_debug.get_signal_orientations().keys())
                                    
                                    if tuned_indicator_signal_cols:
                                        print(" (RawSigCounts: ", end="")
                                        for sig_col_idx, sig_col_name in enumerate(tuned_indicator_signal_cols):
                                            if sig_col_name in trial_results.columns:
                                                true_count = trial_results[sig_col_name].sum()
                                                # Use a more robust way to get a short name, or just use full name
                                                short_sig_name = sig_col_name.replace(f"_{temp_indicator_for_debug.window}", "") if hasattr(temp_indicator_for_debug, 'window') else sig_col_name
                                                short_sig_name = short_sig_name.replace(f"_{temp_indicator_for_debug.spike_multiplier}", "") if hasattr(temp_indicator_for_debug, 'spike_multiplier') else short_sig_name

                                                print(f"{short_sig_name.split('_')[0]}={true_count}", end="")

                                                # Specific debug for VolumeSpikeIndicator if counts are zero
                                                if indicator_class.__name__ == "VolumeSpikeIndicator" and true_count == 0:
                                                    try:
                                                        # Re-calculate to inspect intermediate values for VolumeSpike
                                                        # This is a bit redundant but helps debug this specific case
                                                        # Ensure VolumeSpikeIndicator uses self.df and self.volume_col
                                                        # The actual indicator calculation happens in strategy.run(), trial_results has the output
                                                        # We need to inspect what led to the all-false signal column
                                                        # Let's check a few values of the threshold and volume if possible
                                                        # This assumes 'Volume' column exists in original 'data'
                                                        if temp_indicator_for_debug.volume_col in data.columns:
                                                            vol_series = data[temp_indicator_for_debug.volume_col]
                                                            roll_avg = vol_series.rolling(window=temp_indicator_for_debug.window, min_periods=temp_indicator_for_debug.window).mean()
                                                            threshold = roll_avg * temp_indicator_for_debug.spike_multiplier
                                                            
                                                            # Print some non-NaN threshold values if they exist
                                                            valid_thresholds = threshold.dropna()
                                                            if not valid_thresholds.empty:
                                                                print(f" [VSI_Thresh_Sample: {valid_thresholds.iloc[0]:.2f}]", end="")
                                                            else:
                                                                print(" [VSI_Thresh_All_NaN]", end="")
                                                        else:
                                                            print(" [VSI_VolCol_Missing_In_Data]", end="")

                                                    except Exception as vsi_debug_e:
                                                        print(f" [VSI_Debug_Err: {vsi_debug_e}]", end="")
                                            else:
                                                print(f"{sig_col_name.split('_')[0]}=MISSING", end="")
                                            if sig_col_idx < len(tuned_indicator_signal_cols) - 1:
                                                print(", ", end="")
                                        print(")", end="")
                                except Exception as debug_e:
                                    print(f" (RawSigCounts_ERR: {debug_e})", end="")
                            # --- END DEBUG BLOCK ---


                            current_pnl = self._calculate_placeholder_pnl(trial_results)
                            print(f" PNL: {current_pnl:.2f}")

                            # Changed > to >= to favor non-empty params if PNL is equal to baseline
                            if current_pnl >= best_pnl_for_current_type: 
                                if current_pnl > best_pnl_for_current_type:
                                    print(f"          NEW BEST for {indicator_class.__name__}: PNL {current_pnl:.2f} with params {current_trial_params} (was {best_pnl_for_current_type:.2f})")
                                elif current_pnl == best_pnl_for_current_type and not best_params_for_current_type : # If PNL is same as baseline and baseline params were empty
                                    print(f"          MATCHING BASELINE PNL for {indicator_class.__name__}: PNL {current_pnl:.2f} with params {current_trial_params} (baseline had empty params)")
                                # else: # PNL is same but baseline already had non-empty params, so we don't necessarily overwrite unless it's a true improvement.
                                #     pass # Or add a log if you want to see these cases.
                                best_pnl_for_current_type = current_pnl
                                best_params_for_current_type = current_trial_params
                        except Exception as e:
                            print(f" EXCEPTION: {e}")
                            # This parameter combination failed, log error but continue optimization
                            pass 
                elif not param_names and search_space: # Search space was provided but had no valid param names
                     print(f"      INFO: No valid parameter names to iterate over in search space for {indicator_class.__name__}. Using default params.")
                # If all_param_lists_valid became False, the warning about specific param list was already printed.

            # If param_search_space_defined was false or search_space was empty initially, or all_param_lists_valid became false,
            # best_params_for_current_type remains the initial (default) one. This is logged next.
            print(f"      Selected best PNL for {indicator_class.__name__}: {best_pnl_for_current_type:.2f} with params: {best_params_for_current_type}")
            final_optimized_configs.append({'type': indicator_class, 'params': best_params_for_current_type})

        print(f"INFO: Generalized threshold optimization finished for {self.ticker}.")


        print(f"INFO: Generalized threshold optimization finished for {self.ticker}.")

        self.current_indicator_configs = final_optimized_configs
        # This return should be at the same indentation level as the main loop and initial checks in this method
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
        
        try:
            # Generate signals using the strategy
            print(f"INFO: Running strategy for {self.ticker} with indicators: "
                  f"{[f'{c["type"].__name__}({c.get("params")})' for c in self.current_indicator_configs]}")
            signal_generation_results = self.strategy.run(self.historical_data.copy())
        except Exception as e:
            print(f"ERROR: Strategy execution failed for {self.ticker} during backtest. "
                  "This may be due to an error in one of the configured indicators.")
            print(f"       Final indicator configurations attempted: {self.current_indicator_configs}")
            print(f"       Original error: {type(e).__name__}: {e}")
            # Re-raise the exception to halt the backtest as the main strategy run failed.
            raise

        if signal_generation_results is None or signal_generation_results.empty:
            print(f"Backtest for {self.ticker} did not produce signals. Check strategy and indicator logic.")
            self.results = pd.DataFrame() # Ensure self.results is an empty DataFrame
            return self.results

        # --- Simulate Trades and Track Portfolio ---
        self.results = signal_generation_results.copy()
        
        # Initialize portfolio tracking columns
        # Default to initial capital, no shares, and portfolio value equals cash
        self.results['Shares_Held'] = 0.0  # Use float for shares to handle potential fractional shares if ever needed
        self.results['Cash_Balance'] = self.initial_capital
        self.results['Portfolio_Value'] = self.initial_capital
        self.results['Trade_Action'] = "" # Records BUY, SELL, or ""

        # Reset instance state for this specific run
        current_balance_iter = self.initial_capital
        shares_held_iter = 0.0
        self.trade_log = [] # Clear trade log for this run

        print(f"Simulating trades for {self.ticker} with initial capital: {self.initial_capital:.2f}")        
        for index, row in self.results.iterrows():
            current_price = row['Close'] # Assume transactions occur at closing price
            signal = row['Strategy_Signal']
            trade_action_this_step = ""



            if pd.isna(current_price): # Skip if price is NaN

                self.results.at[index, 'Shares_Held'] = shares_held_iter
                self.results.at[index, 'Cash_Balance'] = current_balance_iter
                # Portfolio value remains cash balance + value of shares held (which is 0 if price is NaN for current calc)
                # Or, more robustly, carry forward previous portfolio value if current price is unusable.

                # For now, if current_price is NaN, asset value part is 0.
                self.results.at[index, 'Portfolio_Value'] = current_balance_iter # Or previous row's portfolio value
                self.results.at[index, 'Trade_Action'] = "SKIP_NAN_PRICE"
                continue

            # Buy Logic
            if signal == SIGNAL_BUY:
                if current_balance_iter > 0 and current_price > 0: # Can only buy if cash available and price is valid
                    # Buy as many whole shares as possible with available cash
                    # Consider a buffer or percentage of capital to invest later
                    num_shares_to_buy = np.floor(current_balance_iter / current_price) 
                    if num_shares_to_buy > 0:
                        cost = num_shares_to_buy * current_price
                        current_balance_iter -= cost
                        shares_held_iter += num_shares_to_buy
                        self.trade_log.append({
                            'timestamp': index, 
                            'type': 'BUY', 
                            'price': current_price, 
                            'quantity': num_shares_to_buy, 
                            'cost': cost,
                            'balance_after_trade': current_balance_iter
                        })
                        trade_action_this_step = "BUY"
                # If already holding, typically a BUY signal might mean "hold" or "add more"
                # Current simple logic: only buys if completely flat or to add to existing if logic expanded.
                # For now, if shares_held_iter > 0, a BUY signal implies HOLD.
            
            # Sell Logic
            elif signal == SIGNAL_SELL:
                if shares_held_iter > 0 and current_price > 0: # Can only sell if shares are held and price is valid
                    proceeds = shares_held_iter * current_price
                    current_balance_iter += proceeds
                    self.trade_log.append({
                        'timestamp': index, 
                        'type': 'SELL', 
                        'price': current_price, 
                        'quantity': shares_held_iter, 
                        'proceeds': proceeds,
                        'balance_after_trade': current_balance_iter
                    })
                    shares_held_iter = 0 # Sell all shares
                    trade_action_this_step = "SELL"



            # Update DataFrame for the current time step
            self.results.at[index, 'Shares_Held'] = shares_held_iter
            self.results.at[index, 'Cash_Balance'] = current_balance_iter
            self.results.at[index, 'Portfolio_Value'] = current_balance_iter + (shares_held_iter * current_price)
            self.results.at[index, 'Trade_Action'] = trade_action_this_step
        
        
        # Update final state of the BackTest instance (optional, as results DF has the history)
        self.current_balance = current_balance_iter 
        self.shares_held = shares_held_iter

        if self.results.empty: # Should have been caught earlier, but as a safeguard
            print(f"Backtest for {self.ticker} did not produce results after trade simulation.")
        else:
            print(f"Trade simulation completed for {self.ticker}. Results DataFrame augmented with portfolio data.")
            # Step 3: Evaluate performance (will need significant update later)
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
            current_price = row['Close'] # This is the Close price of the bar
            signal = row['Strategy_Signal'] # Strategy signal for this bar
            exit_trade = False # Initialize exit_trade flag for each iteration

            # 1. Check for SL/TP on existing positions or exit by signal
            if position == 1: # Currently Long
                exit_price_for_pnl = current_price # Default if closed by signal
                reason_for_exit = "Signal" # Default reason

                # Check Stop Loss
                if self.stop_loss_pct is not None:
                    sl_price = entry_price * (1 - self.stop_loss_pct / 100.0)
                    if current_price <= sl_price: # SL Hit
                        exit_price_for_pnl = sl_price # Exit at SL price
                        reason_for_exit = "SL"
                        exit_trade = True
                
                # Check Take Profit (only if SL not already hit)
                if not exit_trade and self.take_profit_pct is not None:
                    tp_price = entry_price * (1 + self.take_profit_pct / 100.0)
                    if current_price >= tp_price: # TP Hit
                        exit_price_for_pnl = tp_price # Exit at TP price
                        reason_for_exit = "TP"
                        exit_trade = True
                
                # Check Strategy Signal for exit (only if SL/TP not already hit)
                if not exit_trade and signal == SIGNAL_SELL:
                    # exit_price_for_pnl is already current_price (Close of the bar)
                    reason_for_exit = "Signal"
                    exit_trade = True
                
                if exit_trade:
                    pnl = (exit_price_for_pnl - entry_price) * self.leverage
                    trades_details.append({
                        'pnl': pnl, 
                        'entry_price': entry_price,                         'exit_price': exit_price_for_pnl, 
                        'type': 'long', 
                        'exit_reason': reason_for_exit
                    })
                    position = 0
                    entry_price = 0.0

            elif position == -1: # Currently Short
                exit_price_for_pnl = current_price # Default if closed by signal
                reason_for_exit = "Signal" # Default reason


                # Check Stop Loss
                if self.stop_loss_pct is not None:
                    sl_price = entry_price * (1 + self.stop_loss_pct / 100.0)
                    if current_price >= sl_price: # SL Hit
                        exit_price_for_pnl = sl_price # Exit at SL price
                        reason_for_exit = "SL"
                        exit_trade = True
                
                # Check Take Profit (only if SL not already hit)
                if not exit_trade and self.take_profit_pct is not None:
                    tp_price = entry_price * (1 - self.take_profit_pct / 100.0)
                    if current_price <= tp_price: # TP Hit
                        exit_price_for_pnl = tp_price # Exit at TP price
                        reason_for_exit = "TP"
                        exit_trade = True
                                # Check Strategy Signal for exit (only if SL/TP not already hit)
                if not exit_trade and signal == SIGNAL_BUY:
                    # exit_price_for_pnl is already current_price (Close of the bar)
                    reason_for_exit = "Signal"
                    exit_trade = True                
                if exit_trade:
                    pnl = (entry_price - exit_price_for_pnl) * self.leverage 
                    trades_details.append({
                        'pnl': pnl, 
                        'entry_price': entry_price, 
                        'exit_price': exit_price_for_pnl, 
                        'type': 'short', 
                        'exit_reason': reason_for_exit
                    })
                    position = 0
                    entry_price = 0.0
            
            # 2. Check for new entries if flat (and no exit happened in this step that made us flat)
            if position == 0 and not exit_trade: # Only enter if we didn't just exit
                if signal == SIGNAL_BUY:
                    position = 1
                    entry_price = current_price # Entry at current bar's Close
                elif signal == SIGNAL_SELL:
                    position = -1
                    entry_price = current_price # Entry at current bar's Close

        trade_pnl_list = [td['pnl'] for td in trades_details] # PNLs are now leveraged
        num_trades = len(trade_pnl_list)

        trade_pnl_list = [td['pnl'] for td in trades_details] # PNLs are now leveraged
        num_trades = len(trade_pnl_list)
        
        net_profit = sum(trade_pnl_list) # Net profit is now leveraged
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
            "period_tested": self.period,            "interval_tested": self.interval,
            "leverage_applied": self.leverage, # Added leverage
            "total_data_points": len(self.historical_data) if self.historical_data is not None else 0,
            "total_signals_non_hold": len(self.results[self.results['Strategy_Signal'] != SIGNAL_HOLD]),
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
            "profit_factor": profit_factor, # Store with full precision for pytest.approx
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


