

 


import pandas as pd
from typing import List, Dict, Type, Any, Optional
import importlib # For dynamic import
import inspect   # For inspecting module members
import numpy as np # For calculations like mean, std

# Assuming fetchers and BaseStrategy are accessible via these relative imports
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
        if results_df is None or results_df.empty:            return -float('inf') # Or 0.0, depending on how failures should be treated

        profit_loss = 0.0
        position = 0
        entry_price = 0.0
        if 'Close' in results_df.columns and 'Strategy_Signal' in results_df.columns:
            for _, row in results_df.iterrows():
                if row['Strategy_Signal'] == SIGNAL_BUY and position == 0:
                    position = 1
                    entry_price = row['Close']
                elif row['Strategy_Signal'] == SIGNAL_SELL and position == 1:
                    if entry_price > 0: # Ensure entry price was set
                        profit_loss += (row['Close'] - entry_price)
                    position = 0
                    entry_price = 0.0
            # Optional: Mark to market if still in position at the end
            # if position == 1 and not results_df.empty and entry_price > 0 and 'Close' in results_df.columns:
            #     profit_loss += (results_df['Close'].iloc[-1] - entry_price)
        return round(profit_loss, 2)

    # Removed duplicate method definition of optimize_thresholds that was here.
    def optimize_thresholds(self, data: pd.DataFrame, initial_discovered_configs: List[Dict]) -> List[Dict]:
        """
        Placeholder implementation for optimizing thresholds (parameters) for discovered indicators.
        It iterates through known indicator types and tries a few parameter combinations.
        The 'placeholder_profit_loss' is used as the optimization target.

        Args:
            data: The historical OHLCV data.
            initial_discovered_configs: The list of indicator configurations from discovery (default params).

        Returns:
            A list of indicator configurations with potentially "optimized" parameters.
        """        
        print(f"INFO: Starting placeholder threshold optimization for {self.ticker}...")
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
            # Baseline PNL for current indicator with its default params, others default
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

            param_search_space_defined = False

            if indicator_class is RSIIndicator:
                param_search_space_defined = True
                # Default RSI params: period=14, oversold=30, overbought=70
                rsi_periods = [10, 14, 20]
                rsi_oversold_levels = [25, 30, 35]
                rsi_overbought_levels = [65, 70, 75]

                for p in rsi_periods:
                    for os_level in rsi_oversold_levels:                        
                        for ob_level in rsi_overbought_levels: # Innermost loop for RSI
                            current_trial_params = {'period': p, 'column': 'Close', 'rsi_oversold': os_level, 'rsi_overbought': ob_level}
                            
                            # This block is now correctly indented and cleaned
                            trial_run_configs = []
                            for i_conf, conf_item in enumerate(initial_discovered_configs): # Renamed loop variables for clarity
                                if i_conf == idx_tuned:
                                    trial_run_configs.append({'type': indicator_class, 'params': current_trial_params})
                                else:                                    
                                    trial_run_configs.append(conf_item) # Use renamed loop variable
                            
                            trial_strategy = BaseStrategy(indicator_configs=trial_run_configs)
                            trial_results = trial_strategy.run(data.copy())
                            current_pnl = self._calculate_placeholder_pnl(trial_results)

                            if current_pnl > best_pnl_for_current_type:
                                best_pnl_for_current_type = current_pnl
                                best_params_for_current_type = current_trial_params
                # End of RSI parameter search
            
            elif indicator_class is BollingerBandsIndicator:
                param_search_space_defined = True
                # Default BBands params: window=20, num_std_dev=2.0


                # Default BBands params: window=20, num_std_dev=2.0
                bb_windows = [15, 20, 25]
                bb_std_devs = [1.5, 2.0, 2.5]
                for w_bb in bb_windows: 
                    for std_bb in bb_std_devs: # Innermost loop for BollingerBands
                        current_trial_params = {'window': w_bb, 'num_std_dev': std_bb, 'column': 'Close'}
                        
                        # This block is now correctly indented and cleaned
                        trial_run_configs = []
                        for i_conf, conf_item in enumerate(initial_discovered_configs): # Renamed loop variables
                            if i_conf == idx_tuned:
                                trial_run_configs.append({'type': indicator_class, 'params': current_trial_params})
                            else:
                                trial_run_configs.append(conf_item) # Use renamed loop variable
                        
                        trial_strategy = BaseStrategy(indicator_configs=trial_run_configs)
                        trial_results = trial_strategy.run(data.copy())
                        current_pnl = self._calculate_placeholder_pnl(trial_results)

                        if current_pnl > best_pnl_for_current_type:
                            best_pnl_for_current_type = current_pnl
                            best_params_for_current_type = current_trial_params

                # End of BollingerBands parameter search

            # Removed duplicate elif for BreakoutIndicator
            elif indicator_class is BreakoutIndicator:

                param_search_space_defined = True
                # Default Breakout params: window=20

                breakout_windows = [10, 20, 30]
                # Assuming default columns ('High', 'Low', 'Close') are used by BreakoutIndicator.
                # Iterating through the breakout_windows to define parameters for each trial.
                for w_bo in breakout_windows:
                    current_trial_params = {'window': w_bo} # Define parameters for the current trial

                    # This line was causing an indentation error due to the missing loop above.
                    trial_run_configs = []
                    for i_conf, conf_item in enumerate(initial_discovered_configs): # Renamed loop variables
                        if i_conf == idx_tuned:
                            trial_run_configs.append({'type': indicator_class, 'params': current_trial_params})
                        else:
                            trial_run_configs.append(conf_item) # Use renamed loop variable

                    trial_strategy = BaseStrategy(indicator_configs=trial_run_configs)
                    trial_results = trial_strategy.run(data.copy())
                    current_pnl = self._calculate_placeholder_pnl(trial_results)

                    if current_pnl > best_pnl_for_current_type:
                        best_pnl_for_current_type = current_pnl
                        best_params_for_current_type = current_trial_params
                # End of BreakoutIndicator parameter search
            
            # Add more 'elif indicator_class is YourOtherIndicator:' blocks here for other specific optimizations

            if not param_search_space_defined:
                print(f"      No specific optimization defined for {indicator_class.__name__}. Using default params.")
            
            print(f"      Selected best PNL for {indicator_class.__name__}: {best_pnl_for_current_type} with params: {best_params_for_current_type}")
            final_optimized_configs.append({'type': indicator_class, 'params': best_params_for_current_type})

        print(f"INFO: Placeholder optimization finished for {self.ticker}.")
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
            
        return self.results    
    
    def evaluate_performance(self) -> Dict[str, Any]:
        """
        Placeholder for calculating and returning performance metrics from backtest results.
        Actual financial metrics (Sharpe Ratio, P&L, Max Drawdown, etc.) would be implemented here.
        """
        if self.results is None or self.results.empty:
            print(f"No backtest results available for {self.ticker} to evaluate.")
            return {}

        print(f"INFO: Evaluating performance for {self.ticker} (placeholder metrics)...")
        


        
        total_data_points = len(self.historical_data) if self.historical_data is not None else 0
        # 'Strategy_Signal' is the key for signals from BaseStrategy
        total_signals_non_hold_df = self.results[self.results['Strategy_Signal'] != SIGNAL_HOLD]
        num_total_signals_non_hold = len(total_signals_non_hold_df)
        num_buy_signals = len(self.results[self.results['Strategy_Signal'] == SIGNAL_BUY])
        num_sell_signals = len(self.results[self.results['Strategy_Signal'] == SIGNAL_SELL])

        trade_pnl_list = [] # Stores P&L for each closed trade
        trade_percentage_returns = [] # Stores % P&L for each closed trade

        position = 0 # 0 = no position, 1 = long
        entry_price = 0.0

        if 'Close' not in self.results.columns or 'Strategy_Signal' not in self.results.columns:
            print("Warning: 'Close' or 'Strategy_Signal' column not found in results. Cannot calculate detailed performance.")
            self.performance_metrics = {
                "ticker": self.ticker, "period_tested": self.period, "interval_tested": self.interval,
                "total_data_points": total_data_points, "num_signals_generated_non_hold": num_total_signals_non_hold,
                "num_buy_signals": num_buy_signals, "num_sell_signals": num_sell_signals,
                "notes": "Results missing 'Close' or 'Strategy_Signal'. Limited metrics."
            }
            return self.performance_metrics
            
        for index, row in self.results.iterrows():
            current_price = row['Close']            
            signal = row['Strategy_Signal']

            if signal == SIGNAL_BUY and position == 0:
                position = 1
                entry_price = current_price
                # print(f"Trade Log: BUY at {current_price} on {index}")
            elif signal == SIGNAL_SELL and position == 1:
                if entry_price > 0: # Ensure there was a valid entry
                    pnl = current_price - entry_price
                    trade_pnl_list.append(pnl)
                    
                    percentage_return = (pnl / entry_price) * 100 if entry_price != 0 else 0
                    trade_percentage_returns.append(percentage_return)
                    
                    # print(f"Trade Log: SELL at {current_price} on {index}. Entry: {entry_price}, P&L: {pnl:.2f} ({percentage_return:.2f}%)")
                position = 0
                entry_price = 0.0 # Reset for next trade
        
        # If still in position at the end of the backtest period, we generally don't count it as a closed trade
        # for these typical backtest summary statistics, unless specified by a particular methodology (e.g., mark-to-market).
        # The _calculate_placeholder_pnl in optimize_thresholds also only counts closed trades.

        # Calculate more detailed metrics
        num_trades = len(trade_pnl_list)
        num_winning_trades = len([pnl for pnl in trade_pnl_list if pnl > 0])
        num_losing_trades = len([pnl for pnl in trade_pnl_list if pnl < 0])

        win_rate = (num_winning_trades / num_trades) * 100 if num_trades > 0 else 0

        gross_profit = sum(pnl for pnl in trade_pnl_list if pnl > 0)
        gross_loss = abs(sum(pnl for pnl in trade_pnl_list if pnl < 0)) # abs to make it positive


        net_profit = gross_profit - gross_loss
        avg_profit_per_winning_trade = gross_profit / num_winning_trades if num_winning_trades > 0 else 0
        avg_loss_per_losing_trade = gross_loss / num_losing_trades if num_losing_trades > 0 else 0 # gross_loss is already positive
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') # If gross_loss is 0

        avg_pnl_per_trade = net_profit / num_trades if num_trades > 0 else 0

        # Max Drawdown Calculation (from equity curve based on trade P&Ls)
        initial_capital = 10000 # Arbitrary starting capital for simulation
        equity_curve = [initial_capital]
        current_equity = initial_capital
        for pnl in trade_pnl_list: # Using P&L per trade to update equity
            current_equity += pnl
            equity_curve.append(current_equity)
        
        peak_equity = equity_curve[0] if equity_curve else 0 # handle empty equity_curve
        max_drawdown_value = 0
        max_drawdown_percentage = 0.0

        for equity_point in equity_curve:
            if equity_point > peak_equity:
                peak_equity = equity_point
            drawdown_val = peak_equity - equity_point
            if drawdown_val > max_drawdown_value:
                max_drawdown_value = drawdown_val
            if peak_equity > 0 : # Avoid division by zero if peak is zero (e.g. all losses from start)
                drawdown_pct = (peak_equity - equity_point) / peak_equity
                if drawdown_pct > max_drawdown_percentage:
                    max_drawdown_percentage = drawdown_pct
        

        # Simplified Sharpe Ratio (based on % returns of trades)
        # This is a very rough estimate. Proper Sharpe uses periodic returns (e.g., daily).
        sharpe_ratio_simplified = "N/A"
        if num_trades > 0 and len(trade_percentage_returns) > 1: # Need at least 2 trades for std dev
            mean_pct_return_per_trade = np.mean(trade_percentage_returns)
            std_dev_pct_return_per_trade = np.std(trade_percentage_returns)


            if std_dev_pct_return_per_trade > 0:
                # Assuming 0 risk-free rate. Annualizing factor (e.g. sqrt(252) for daily) isn't applicable here directly.
                sharpe_ratio_simplified = round(mean_pct_return_per_trade / std_dev_pct_return_per_trade, 3)
            # else: # All trades had same % return, or only one distinct return
                # sharpe_ratio_simplified = float('inf') if mean_pct_return_per_trade > 0 else 0.0 if mean_pct_return_per_trade == 0 else float('-inf')
            # If std_dev is 0, Sharpe is ill-defined or infinite. Let's leave as N/A or specific handling.
            # For simplicity, if std_dev is 0 and mean > 0, it's like "infinite" risk-adjusted return (no volatility).

            # If mean is also 0 or <0, it's 0 or negative infinite. We'll just use N/A for std_dev == 0.

        self.performance_metrics = {
            "ticker": self.ticker,
            "period_tested": self.period,
            "interval_tested": self.interval,
            "total_data_points": total_data_points,            "total_signals_non_hold": num_total_signals_non_hold,
            "num_buy_signals": num_buy_signals,
            "num_sell_signals": num_sell_signals,
            "total_trades": num_trades,
            "winning_trades": num_winning_trades,
            "losing_trades": num_losing_trades,
            "win_rate_pct": round(win_rate, 2),
            "net_profit": round(net_profit, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "avg_profit_per_winning_trade": round(avg_profit_per_winning_trade, 2),
            "avg_loss_per_losing_trade": round(avg_loss_per_losing_trade, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor not in [float('inf'), float('-inf')] else str(profit_factor),
            "avg_pnl_per_trade": round(avg_pnl_per_trade, 2),
            "max_drawdown_value": round(max_drawdown_value, 2),
            "max_drawdown_percentage": round(max_drawdown_percentage * 100, 2), # As percentage
            "sharpe_ratio_simplified_per_trade": str(sharpe_ratio_simplified) if sharpe_ratio_simplified in [float('inf'), float('-inf')] else sharpe_ratio_simplified,
            "notes": "Sharpe Ratio is simplified (per trade % returns, RFR=0). Max Drawdown based on trade P&L equity curve."
        }

        print(f"Performance metrics for {self.ticker}:")
        for k, v in self.performance_metrics.items():            
            print(f"  {k}: {v}")
        return self.performance_metrics


    def get_results(self) -> Optional[pd.DataFrame]:
        """Returns the DataFrame containing the backtest results (data + signals)."""
        return self.results

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Returns the dictionary of calculated performance metrics."""
        return self.performance_metrics

