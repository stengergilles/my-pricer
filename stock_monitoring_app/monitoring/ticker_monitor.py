import os
import glob
import json
import time
import pandas as pd
from typing import Optional, List, Dict

# You will need to ensure this import path is correct for your project
from stock_monitoring_app.backtest.backtest import BackTest

class TickerMonitor:
    def __init__(
        self,
        ticker,
        monitor_interval_seconds,
        trade_order_queue,
        entry_price,
        process_name="Monitor",
    ):
        self.ticker = ticker
        self.monitor_interval_seconds = monitor_interval_seconds
        self.trade_order_queue = trade_order_queue
        self.entry_price = entry_price
        self.process_name = process_name

        self._running = False
        self._is_active_position = False

    def _resolve_indicator_class(self, module_name: str, class_name: str):
        import importlib
        try:
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except Exception as e:
            print(f"ERROR: Could not resolve class '{class_name}' from module '{module_name}': {e}")
            return None

    def _run_backtest(self):
        print(f"INFO [{self.process_name}]: No optimized config found for {self.ticker}. Running backtest to generate one...")
        try:
            # Adjust period/interval as needed for your use case
            backtester = BackTest(ticker=self.ticker, period="1y", interval="1d")
            results = backtester.run_backtest()
            if results is not None:
                print(f"INFO [{self.process_name}]: Backtest complete for {self.ticker}.")
            else:
                print(f"WARN [{self.process_name}]: Backtest failed for {self.ticker}.")
        except Exception as e:
            print(f"ERROR [{self.process_name}]: Exception during backtest: {e}")

    def _load_optimized_config_from_disk(self) -> Optional[List[Dict]]:
        """
        Loads optimized indicator configurations for this ticker from the latest metrics file.
        If not found, runs a backtest to generate it. Returns a list of {'type': <class>, 'params': {...}} or None on failure.
        """
        import time
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            outputs_dir = os.path.join(project_root, "backtest_outputs")
            pattern = os.path.join(outputs_dir, f"{self.ticker}_*_metrics.json")
            files = glob.glob(pattern)
            if not files:
                print(f"INFO [{self.process_name}]: No optimized config files found for {self.ticker}.")
                self._run_backtest()
                # Wait up to 10 seconds for backtest output to appear (race condition fix)
                max_wait = 10
                waited = 0
                while waited < max_wait:
                    files = glob.glob(pattern)
                    if files:
                        break
                    time.sleep(1)
                    waited += 1
                if not files:
                    print(f"ERROR [{self.process_name}]: Still no config after backtest. Giving up.")
                    return None
            files.sort(key=os.path.getmtime, reverse=True)
            latest_metrics_path = files[0]
            with open(latest_metrics_path, "r") as f:
                metrics_data = json.load(f)
            loaded_raw_configs = metrics_data.get("indicator_configurations", [])
            resolved_configs = []
            for raw_conf in loaded_raw_configs:
                module = raw_conf.get("module")
                class_name = raw_conf.get("class_name")
                params = raw_conf.get("params", {})
                cls = self._resolve_indicator_class(module, class_name)
                if cls:
                    resolved_configs.append({"type": cls, "params": params})
                else:
                    print(f"WARNING [{self.process_name}]: Could not resolve indicator {module}.{class_name}.")
            return resolved_configs if resolved_configs else None
        except Exception as e:
            print(f"ERROR [{self.process_name}]: Failed to load optimized config from disk: {e}")
            return None

    def _fetch_latest_data(self):
        """
        Fetch the latest data for the ticker.
        This is a placeholder; actual logic will depend on your fetcher implementation.
        """
        print(f"INFO [{self.process_name}]: Fetching latest data for {self.ticker}...")
        # Replace with actual fetcher logic.
        return pd.DataFrame()  # Dummy placeholder

    def _process_data_and_decide(self, latest_data_df):
        """
        Process the data and decide what to do.
        Placeholder for actual strategy logic.
        """
        print(f"INFO [{self.process_name}]: Processing data for {self.ticker}...")
        # Example: Simulate a HOLD order
        self.trade_order_queue.put({
            "action": "HOLD",
            "ticker": self.ticker,
            "price": None,
            "timestamp": pd.Timestamp.now(tz='UTC').isoformat()
        })

    def run(self):
        """Main monitoring loop, intended to be run in a subprocess."""
        print(f"INFO [{self.process_name}]: Starting monitor for {self.ticker} with entry price {self.entry_price:.2f}...")
        indicator_configs = self._load_optimized_config_from_disk()
        self._running = True
        print(f"INFO [{self.process_name}]: Monitor loop started. Interval: {self.monitor_interval_seconds}s.")
        while self._running:
            start_time = time.time()
            print(f"INFO [{self.process_name}]: Cycle started at {pd.Timestamp.now(tz='UTC')}.")
            
            try:
                latest_data_df = self._fetch_latest_data()
                if latest_data_df is not None and not latest_data_df.empty:
                    self._process_data_and_decide(latest_data_df)
                    fetch_status = "OK"
                else:
                    print(f"WARN [{self.process_name}]: Skipping processing due to no data from fetch.")
                    fetch_status = "No data"
            except Exception as e:
                print(f"ERROR [{self.process_name}]: Exception during fetch or process: {e}")
                fetch_status = f"Error: {e}"

            elapsed_time = time.time() - start_time
            sleep_duration = self.monitor_interval_seconds - elapsed_time
            
            if sleep_duration > 0:
                print(f"INFO [{self.process_name}]: Cycle finished in {elapsed_time:.2f}s. Sleeping for {sleep_duration:.2f}s...")
                # Check _running flag frequently during sleep for responsiveness to stop()
                for _ in range(int(sleep_duration)):  # Sleep in 1s intervals
                    if not self._running:
                        break
                    time.sleep(1)
                if self._running and sleep_duration % 1 > 0:  # Remainder sleep
                    time.sleep(sleep_duration % 1)
            else:
                print(f"WARN [{self.process_name}]: Cycle took {elapsed_time:.2f}s, exceeding monitor interval of {self.monitor_interval_seconds}s.")
        
        print(f"INFO [{self.process_name}]: Monitor loop stopped for {self.ticker}.")

    def stop(self):
        """Signals the monitoring loop to stop."""
        print(f"INFO [{self.process_name}]: Stop requested for monitor {self.ticker}.")
        self._running = False
