
import multiprocessing
import time
import pandas as pd
from typing import Optional, Dict, Any, List, Type
import importlib # Added for _resolve_indicator_class

# Assuming these modules are in the parent directory or project is structured accordingly
from ..fetchers.base_fetcher import Fetcher
from ..strategies.base_strategy import BaseStrategy, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from ..backtest.backtest import BackTest # For reusing logic and running setup backtest
from ..indicators.base_indicator import Indicator # For type hints when dealing with configs

# Define TradeOrder type
class TradeOrder:
    def __init__(self, ticker: str, action: str, price: float, quantity: float, timestamp: pd.Timestamp):
        self.ticker = ticker
        self.action = action  # "BUY" or "SELL"
        self.price = price    # Price at which the order should be considered/placed
        self.quantity = quantity
        self.timestamp = timestamp # Timestamp of the data point that triggered the order

    def __repr__(self):
        return (f"TradeOrder(Ticker: {self.ticker}, Action: {self.action}, "
                f"Price: {self.price:.2f}, Qty: {self.quantity}, Signal Time: {self.timestamp})")


class TickerMonitor:
    """
    Monitors a given ticker, fetches live data, applies a strategy,
    and emits trade orders to a queue. Designed to run in a subprocess.
    """
    def __init__(self,
                 ticker: str,
                 entry_price: float,
                 trade_order_queue: multiprocessing.Queue,
                 strategy_config_override: Optional[List[Dict]] = None,
                 monitor_interval_seconds: int = 60,
                 backtest_period_for_setup: str = "6mo", # Period for initial backtest if needed
                 backtest_interval_for_setup: str = "1d" # Interval for initial backtest
                ):
        self.ticker = ticker
        self.entry_price = entry_price # This is the reference entry price of the position being monitored
        self.trade_order_queue = trade_order_queue
        self.monitor_interval_seconds = monitor_interval_seconds
        self.strategy_config_override = strategy_config_override
        self.backtest_period_for_setup = backtest_period_for_setup
        self.backtest_interval_for_setup = backtest_interval_for_setup
        

        # Internal BackTest instance primarily for _get_fetcher and initial strategy setup.
        # It's configured minimally here; specific period/interval for setup backtest is separate.
        # Leverage for the monitor's BackTest reference can be default (1.0) as it's not used for live P&L.
        self._internal_backtest_ref = BackTest(ticker=self.ticker, period="1d", interval="1h")
        self.fetcher: Fetcher = self._internal_backtest_ref._get_fetcher(self.ticker)

        self.strategy: Optional[BaseStrategy] = None
        self.current_indicator_configs: Optional[List[Dict]] = None

        self._is_active_position = False # True if currently holding a position based on entry_price
        self._running = False
        self.process_name = f"TickerMonitor-{self.ticker}"
        self.last_known_price: Optional[float] = None

    def _resolve_indicator_class(self, module_name: str, class_name: str) -> Optional[Type[Indicator]]:
        """Helper to dynamically import an indicator class."""
        try:
            module = importlib.import_module(module_name)
            indicator_class = getattr(module, class_name)
            if not issubclass(indicator_class, Indicator):
                print(f"WARN [{self.process_name}]: {class_name} is not a subclass of Indicator.")
                return None
            return indicator_class
        except ImportError:
            print(f"ERROR [{self.process_name}]: Could not import module {module_name} for indicator {class_name}.")
            return None # Explicitly return None
        except AttributeError:
            print(f"ERROR [{self.process_name}]: Could not find class {class_name} in module {module_name}.")
            return None # Explicitly return None
        except Exception as e:
            print(f"ERROR [{self.process_name}]: Unexpected error resolving indicator {class_name}: {e}")
        return None

    def _load_optimized_config_from_disk(self) -> Optional[List[Dict]]:
        """
        Placeholder: Attempts to load optimized indicator configurations from a file.
        """
        print(f"INFO [{self.process_name}]: Placeholder: Attempting to load optimized config from disk...")
        # In a real implementation, this would involve:
        # 1. Getting project_root (e.g., from BackTest._get_project_root() or similar)
        # 2. Constructing path to 'backtest_outputs' directory.
        # 3. Finding the latest *_metrics.json file for `self.ticker`.
        # 4. Loading the JSON data.
        # 5. Extracting the 'indicator_configurations' list.
        # 6. Iterating through this list and using `_resolve_indicator_class` to convert
        #    module and class name strings back into actual Python class objects.
        # Example of resolving loaded config:
        # loaded_raw_configs = metrics_data.get("indicator_configurations", [])
        # resolved_configs = []
        # for raw_conf in loaded_raw_configs:
        #     cls = self._resolve_indicator_class(raw_conf["module"], raw_conf["class_name"])
        #     if cls:
        #         resolved_configs.append({"type": cls, "params": raw_conf.get("params", {})})
        # return resolved_configs if resolved_configs else None
        return None

    def _initialize_strategy(self):
        """Initializes the strategy, either from override, loaded config, or new backtest."""
        print(f"INFO [{self.process_name}]: Initializing strategy...")
        if self.strategy_config_override:            
            print(f"INFO [{self.process_name}]: Using provided strategy configuration override.")
            self.current_indicator_configs = self.strategy_config_override
        else:
            loaded_configs = self._load_optimized_config_from_disk()
            if loaded_configs:
                print(f"INFO [{self.process_name}]: Loaded existing optimized strategy configuration from disk.")
                self.current_indicator_configs = loaded_configs
            else:
                print(f"INFO [{self.process_name}]: No existing optimized strategy found or loaded. "
                      f"Running a new backtest (period: {self.backtest_period_for_setup}, "
                      f"interval: {self.backtest_interval_for_setup}) "
                      f"to determine strategy for {self.ticker}...")
                setup_bt = BackTest(                    ticker=self.ticker,
                    period=self.backtest_period_for_setup,
                    interval=self.backtest_interval_for_setup
                )
                setup_bt.run_backtest() # This populates setup_bt.current_indicator_configs
                
                if setup_bt.current_indicator_configs:
                    self.current_indicator_configs = setup_bt.current_indicator_configs
                    print(f"INFO [{self.process_name}]: New strategy configured from backtest with "
                          f"{len(self.current_indicator_configs)} indicators.")
                    # Placeholder: self._save_optimized_config_to_disk(self.current_indicator_configs)
                else:
                    print(f"ERROR [{self.process_name}]: Backtest for setup did not yield indicator configurations.")
                    self.current_indicator_configs = []

        if not self.current_indicator_configs: # Ensure it's not None before creating BaseStrategy
            self.current_indicator_configs = []
            print(f"WARN [{self.process_name}]: No indicator configurations available. Strategy will be basic (always HOLD).")
        
        self.strategy = BaseStrategy(indicator_configs=self.current_indicator_configs)
        print(f"INFO [{self.process_name}]: Strategy initialized successfully.")

    def _get_fetch_interval_str(self) -> str:
        """Maps monitor_interval_seconds to a fetcher-compatible interval string."""
        if self.monitor_interval_seconds <= 60: return "1m"
        if self.monitor_interval_seconds <= 300: return "5m"
        if self.monitor_interval_seconds <= 900: return "15m"
        if self.monitor_interval_seconds <= 1800: return "30m"
        if self.monitor_interval_seconds <= 3600: return "1h"
        print(f"WARN [{self.process_name}]: Monitor interval {self.monitor_interval_seconds}s has no direct map to fetch interval, using '1m'. Adjust as needed.")
        return "1m"

    def _fetch_latest_data(self) -> Optional[pd.DataFrame]:
        """Fetches recent historical data for monitoring."""
        fetch_interval = self._get_fetch_interval_str()
        # Fetch a period long enough for indicators to calculate.
        # E.g., "7d" for daily indicators, or a few hours for minutely ones.
        # This needs to be sensible for the chosen fetch_interval.
        # For minutely data, '1d' or '2d' period might be sufficient.
        fetch_period = "3d" if fetch_interval in ["1m", "5m", "15m", "30m"] else "7d"
        
        print(f"INFO [{self.process_name}]: Fetching latest data "
              f"(period: {fetch_period}, interval: {fetch_interval}) "
              f"using {self.fetcher.get_service_name()}...")
        try:
            data = self.fetcher.fetch_data(self.ticker, fetch_period, fetch_interval)
            if data is None or data.empty:
                print(f"WARN [{self.process_name}]: No data fetched for {self.ticker}.")
                return None
            if not isinstance(data.index, pd.DatetimeIndex):
                print(f"ERROR [{self.process_name}]: Fetched data does not have a DatetimeIndex.")
                return None

            # Ensure 'Close' column exists
            if 'Close' not in data.columns:
                print(f"ERROR [{self.process_name}]: Fetched data is missing 'Close' column.")
                return None

            print(f"INFO [{self.process_name}]: Successfully fetched {len(data)} data points.")
            return data
        except Exception as e:
            print(f"ERROR [{self.process_name}]: Exception fetching data for {self.ticker}: {e}")
            return None

    def _process_data_and_decide(self, data: pd.DataFrame):
        """Applies strategy to the latest data and emits trade orders if necessary."""
        if self.strategy is None:
            print(f"ERROR [{self.process_name}]: Strategy not initialized. Cannot process data.")
            return

        print(f"INFO [{self.process_name}]: Processing {len(data)} data points...")
        results_with_signals = self.strategy.run(data.copy()) # strategy.run returns df with 'Strategy_Signal'

        if results_with_signals is None or results_with_signals.empty:
            print(f"WARN [{self.process_name}]: Strategy did not produce signals.")
            return

        if 'Strategy_Signal' not in results_with_signals.columns:
            print(f"ERROR [{self.process_name}]: 'Strategy_Signal' column missing from strategy output.")
            return

        # Get the latest signal and corresponding data point
        latest_signal_data = results_with_signals.iloc[-1]
        latest_signal = latest_signal_data['Strategy_Signal']
        latest_price = latest_signal_data['Close']
        latest_timestamp = results_with_signals.index[-1]

        self.last_known_price = latest_price
        print(f"INFO [{self.process_name}]: Latest signal: {latest_signal} at Price: {latest_price:.2f} on {latest_timestamp}")

        # Simplified trade logic:
        # Assume quantity 1 for now. Could be based on self.entry_price if it represents capital.
        quantity_to_trade = 1.0 

        if latest_signal == SIGNAL_BUY and not self._is_active_position:
            print(f"INFO [{self.process_name}]: BUY signal received. Current state: Not in position.")
            order = TradeOrder(self.ticker, "BUY", latest_price, quantity_to_trade, latest_timestamp)
            self.trade_order_queue.put(order)
            self._is_active_position = True # Assume buy order will be filled
            self.entry_price = latest_price # Update entry price to this new buy
            print(f"EVENT [{self.process_name}]: Emitted BUY order: {order}")

        elif latest_signal == SIGNAL_SELL and self._is_active_position:
            print(f"INFO [{self.process_name}]: SELL signal received. Current state: In position (entry: {self.entry_price:.2f}).")
            order = TradeOrder(self.ticker, "SELL", latest_price, quantity_to_trade, latest_timestamp)
            self.trade_order_queue.put(order)
            self._is_active_position = False # Assume sell order will be filled
            print(f"EVENT [{self.process_name}]: Emitted SELL order: {order}")
        
        elif latest_signal == SIGNAL_HOLD:
            print(f"INFO [{self.process_name}]: HOLD signal received. No action taken.")
        else:
            # E.g., BUY signal while already in position, or SELL signal while not in position
            print(f"INFO [{self.process_name}]: Signal {latest_signal} does not trigger action in current state (Active Position: {self._is_active_position}).")    
    def run(self):
        """Main monitoring loop, intended to be run in a subprocess."""
        print(f"INFO [{self.process_name}]: Starting monitor for {self.ticker} with entry price {self.entry_price:.2f}...")
        try:
            self._initialize_strategy()
        except RuntimeError as e:            
            print(f"FATAL [{self.process_name}]: {e}. Monitor cannot start.")
            return # Exit if strategy initialization fails

        self._running = True
        print(f"INFO [{self.process_name}]: Monitor loop started. Interval: {self.monitor_interval_seconds}s.")
                while self._running:
            start_time = time.time()
            print(f"INFO [{self.process_name}]: Cycle started at {pd.Timestamp.now(tz='UTC')}.")
            
            latest_data_df = self._fetch_latest_data()
            
            if latest_data_df is not None and not latest_data_df.empty:
                self._process_data_and_decide(latest_data_df)
            else:
                print(f"WARN [{self.process_name}]: Skipping processing due to no data from fetch.")

            elapsed_time = time.time() - start_time
            sleep_duration = self.monitor_interval_seconds - elapsed_time
            
            if sleep_duration > 0:
                print(f"INFO [{self.process_name}]: Cycle finished in {elapsed_time:.2f}s. Sleeping for {sleep_duration:.2f}s...")
                # Check _running flag frequently during sleep for responsiveness to stop()
                for _ in range(int(sleep_duration)): # Sleep in 1s intervals
                    if not self._running:
                        break
                    time.sleep(1)
                if self._running and sleep_duration % 1 > 0: # Remainder sleep
                    time.sleep(sleep_duration % 1)
            else:
                print(f"WARN [{self.process_name}]: Cycle took {elapsed_time:.2f}s, exceeding monitor interval of {self.monitor_interval_seconds}s.")
        
        print(f"INFO [{self.process_name}]: Monitor loop stopped for {self.ticker}.")

    def stop(self):
        """Signals the monitoring loop to stop."""
        print(f"INFO [{self.process_name}]: Stop requested for monitor {self.ticker}.")
        self._running = False