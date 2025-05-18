import json
import importlib
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Type
from datetime import datetime
import glob

import pandas as pd

from ..fetchers.base_fetcher import Fetcher
from ..fetchers import CoinGeckoFetcher, PolygonFetcher 
from ..strategies.base_strategy import BaseStrategy, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from ..backtest.backtest import BackTest, NumpyJSONEncoder
from ..indicators.base_indicator import Indicator # For type hinting

# --- Helper function to load indicator configurations ---
def _load_indicator_configs_from_json(metrics_path: Path) -> Optional[List[Dict[str, Any]]]:
    """
    Loads indicator configurations from a saved metrics JSON file.
    Converts module and class name strings back into actual Indicator types.
    """
    try:
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        
        loaded_configs: List[Dict[str, Any]] = []
        serializable_configs = metrics.get("indicator_configurations")


        if not serializable_configs:
            print(f"Warning: No 'indicator_configurations' found in metrics file: {metrics_path}")
            return None
        

        # This loop should only execute if serializable_configs is not None and not empty.
        # The check above handles the None/empty case by returning.
        for s_config in serializable_configs:
            module_name = s_config.get("module")
            class_name = s_config.get("class_name")
            params = s_config.get("params", {})
            
            if not module_name or not class_name:
                print(f"Warning: Invalid indicator config entry (missing module/class name) in {metrics_path}")
                continue
            
            try:
                module = importlib.import_module(module_name)
                IndicatorClass: Type[Indicator] = getattr(module, class_name)
                if not issubclass(IndicatorClass, Indicator):
                    print(f"Warning: Loaded class {class_name} from {module_name} is not a subclass of Indicator.")
                    continue
                loaded_configs.append({'type': IndicatorClass, 'params': params})
            except ImportError:
                print(f"Error: Could not import module {module_name} for indicator {class_name}.")
                return None # Critical error, cannot proceed
            except AttributeError:
                print(f"Error: Could not find class {class_name} in module {module_name}.")
                return None # Critical error
            except Exception as e:
                print(f"Error loading indicator class {module_name}.{class_name}: {e}")                return None
        
        if not loaded_configs: # If all configs failed to load properly
            print(f"Warning: All indicator configurations failed to load from {metrics_path}.")
            return None
            
        return loaded_configs

    except FileNotFoundError:
        print(f"Error: Metrics file not found at {metrics_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from metrics file: {metrics_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading indicator configs from {metrics_path}: {e}")
        return None

class Monitor:
    """
    Monitors a specific ticker, fetches data, applies a strategy derived from
    backtest results, and emits buy/sell signals.
    If a backtest for the ticker doesn't exist, it triggers one.    """
    def __init__(self, ticker: str, period: str, interval: str):
        """
        Initializes the Monitor.

        Args:
            ticker: The stock/crypto ticker symbol.
            period: The historical data period for backtesting and monitoring reference.
            interval: The data interval for backtesting and monitoring reference.        """
        self.ticker = ticker
        self.period = period
        self.interval = interval        self.fetcher: Fetcher = self._get_fetcher(self.ticker)
        self.project_root: Path = self._get_project_root()
        self.backtest_outputs_dir: Path = self.project_root / "backtest_outputs"
        
        self.indicator_configs: Optional[List[Dict[str, Any]]] = None
        self.strategy: Optional[BaseStrategy] = None        self._load_or_run_backtest_and_setup_strategy()

    def _get_project_root(self) -> Path:
        """Determines the project root directory."""
        # Assumes this script (monitor.py) is in .../project_root/stock_monitoring_app/monitor/monitor.py
        return Path(__file__).resolve().parent.parent.parent

    def _get_fetcher(self, ticker: str) -> Fetcher:
        """Initializes the appropriate data fetcher based on the ticker."""
        known_crypto_tickers = [
            "bitcoin", "ethereum", "binancecoin", "cardano", "solana", "ripple", 
            "xrp", "polkadot", "dogecoin", "shiba-inu", "litecoin", "tron", 
            "avalanche-2", "btc", "eth", "sol", "ada", "dot", "ltc", "trx"
        ]
        if ticker.lower() in known_crypto_tickers:
            print(f"INFO (Monitor): Detected '{ticker}' as crypto. Using CoinGeckoFetcher.")            return CoinGeckoFetcher()
        else:
            print(f"INFO (Monitor): Assuming '{ticker}' is stock. Using PolygonFetcher.")
            return PolygonFetcher()

    def _find_latest_backtest_metrics_file(self) -> Optional[Path]:
        """Finds the most recent backtest metrics JSON file for the current ticker, period, and interval."""
        self.backtest_outputs_dir.mkdir(parents=True, exist_ok=True) # Ensure dir exists
        
        pattern = f"{self.ticker}_{self.period}_{self.interval}_*_metrics.json"
        search_path = self.backtest_outputs_dir / pattern
                # glob.glob returns a list of matching file paths
        # The search_path needs to be a string for glob
        matching_files = glob.glob(str(search_path))

        if not matching_files:            return None

        # Sort files by timestamp in filename (descending, so latest is first)
        # Example filename: AAPL_1y_1d_20231027_123045_UTC_metrics.json
        def extract_timestamp_from_filename(filepath_str):
            filename = Path(filepath_str).name
            parts = filename.split('_')
            if len(parts) >= 5: # ticker, period, interval, YYYYMMDD, HHMMSS, ...
                return f"{parts[3]}_{parts[4]}" # "YYYYMMDD_HHMMSS"
            return "00000000_000000" # Default for unparsable names, sorts early

        latest_file = max(matching_files, key=extract_timestamp_from_filename)
        return Path(latest_file)

    def _load_or_run_backtest_and_setup_strategy(self):        """
        Loads indicator configurations from the latest backtest file.
        If no backtest exists or loading fails, runs a new backtest.
        Then, initializes the strategy.
        """
        print(f"INFO (Monitor): Looking for existing backtest for {self.ticker} ({self.period}, {self.interval})...")
        latest_metrics_file = self._find_latest_backtest_metrics_file()

        if latest_metrics_file:
            print(f"INFO (Monitor): Found existing backtest metrics: {latest_metrics_file}")            self.indicator_configs = _load_indicator_configs_from_json(latest_metrics_file)
        
        if not self.indicator_configs:
            if latest_metrics_file: # Found file but loading failed
                print(f"Warning (Monitor): Failed to load indicator configs from {latest_metrics_file}.")
            else: # No file found
                print(f"INFO (Monitor): No existing backtest found for {self.ticker} ({self.period}, {self.interval}).")
            
            print(f"INFO (Monitor): Triggering new backtest for {self.ticker}...")
            backtest_instance = BackTest(ticker=self.ticker, period=self.period, interval=self.interval)
            backtest_results = backtest_instance.run_backtest()

            if backtest_results is not None and not backtest_results.empty:
                print(f"INFO (Monitor): Backtest completed. Attempting to load newly generated configurations...")
                # Retry finding the latest file, which should now be the one just created
                newly_created_metrics_file = self._find_latest_backtest_metrics_file()
                if newly_created_metrics_file:                    self.indicator_configs = _load_indicator_configs_from_json(newly_created_metrics_file)
                else:
                    print(f"Error (Monitor): Backtest ran, but could not find its metrics output file.")
            else:
                print(f"Error (Monitor): Backtest for {self.ticker} failed to produce results. Cannot setup strategy.")
                return # Cannot proceed without a strategy

        if self.indicator_configs:
            print(f"INFO (Monitor): Successfully loaded {len(self.indicator_configs)} indicator configurations.")
            self.strategy = BaseStrategy(indicator_configs=self.indicator_configs)
            print(f"INFO (Monitor): Strategy initialized for {self.ticker}.")
        else:
            print(f"Error (Monitor): Failed to load or generate indicator configurations. Monitor cannot operate.")

    def fetch_monitoring_data(self) -> Optional[pd.DataFrame]:
        """Fetches the latest market data for monitoring."""
        print(f"INFO (Monitor): Fetching latest data for {self.ticker} ({self.period}, {self.interval}) using {self.fetcher.get_service_name()}...")
        # For live monitoring, 'period' and 'interval' might need to be adjusted
        # to fetch only the most recent data points needed for the indicators.
        # For this example, we re-fetch based on the initialized period/interval.
        try:
            data_df = self.fetcher.fetch_data(self.ticker, self.period, self.interval)
            if data_df is None or data_df.empty:
                print(f"Warning (Monitor): No data fetched for {self.ticker}.")
                return None
            print(f"INFO (Monitor): Successfully fetched {len(data_df)} data points for {self.ticker}.")
            return data_df
        except Exception as e:
            print(f"Error (Monitor): Failed to fetch monitoring data for {self.ticker}: {e}")
            return None

    def get_latest_signal(self) -> Optional[str]:
        """        Fetches the latest data, applies the strategy, and returns the latest signal.
        """
        if not self.strategy:
            print("Error (Monitor): Strategy not initialized. Cannot get signal.")
            return None        if not self.indicator_configs:
            print("Error (Monitor): Indicator configurations not loaded. Cannot get signal.")
            return None

        data_df = self.fetch_monitoring_data()
        if data_df is None or data_df.empty:
            print("Error (Monitor): Could not fetch data for signal generation.")
            return None

        print(f"INFO (Monitor): Applying strategy to {len(data_df)} data points for {self.ticker}...")
        results_df = self.strategy.run(data_df.copy()) # Run on a copy

        if results_df is None or results_df.empty:
            print(f"Error (Monitor): Strategy run did not produce results for {self.ticker}.")
            return None
        
        if 'Strategy_Signal' not in results_df.columns:
            print(f"Error (Monitor): 'Strategy_Signal' column missing in strategy results for {self.ticker}.")
            return None
            
        if results_df.empty:
            print(f"Warning (Monitor): Strategy results DataFrame is empty for {self.ticker}. No signal to emit.")
            return SIGNAL_HOLD # Default to HOLD if no data points to make a decision on        latest_signal = results_df['Strategy_Signal'].iloc[-1]
        latest_timestamp = results_df.index[-1]
        
        print(f"--- MONITOR SIGNAL ---")
        print(f"Ticker:    {self.ticker}")
        print(f"Timestamp: {latest_timestamp}")
        print(f"Signal:    {latest_signal}")
        print(f"----------------------")
        return latest_signal

# Example Usage (Illustrative - typically run from a main script or scheduler)
if __name__ == '__main__':
    print("--- Monitor Example ---")
    # Ensure your .env file is in the project root (parent of stock_monitoring_app)
    # and POLYGON_API_KEY (or COINGECKO_API_KEY if using crypto) is set.
    
    # Example: Monitor AAPL stock with 1-year data at 1-day interval for backtest strategy
    # monitor_aapl = Monitor(ticker="AAPL", period="1y", interval="1d")
    # signal_aapl = monitor_aapl.get_latest_signal()
    # print(f"Final AAPL Signal Received: {signal_aapl}")

    # print("\n---")

    # Example: Monitor Bitcoin with 90-day data at daily interval for backtest strategy
    # monitor_btc = Monitor(ticker="bitcoin", period="3mo", interval="1d") # CoinGecko uses daily for '1d' interval
    # signal_btc = monitor_btc.get_latest_signal()
    # print(f"Final Bitcoin Signal Received: {signal_btc}")
    
    # To run this example:
    # 1. Make sure your project root has a .env file with necessary API keys.
    #    (e.g., POLYGON_API_KEY=your_key)
    # 2. The 'stock_monitoring_app' should be runnable. You might need to adjust PYTHONPATH
    #    or run from the project root directory:
    #    python -m stock_monitoring_app.monitor.monitor
    pass
