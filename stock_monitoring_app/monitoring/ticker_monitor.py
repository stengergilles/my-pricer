import os
import glob
import json
import time
import pandas as pd
from typing import Optional, List, Dict

from stock_monitoring_app.strategies.base_strategy import BaseStrategy

BACKTEST_SCOPE_PRESETS = {                        "intraday": {"period": "1d", "interval": "1m"},                                             "short": {"period": "1w", "interval": "15m"},                                               "long": {"period": "1mo", "interval": "1d"}                                             }

class TickerMonitor:
    def __init__(
        self,
        ticker,
        monitor_interval_seconds,
        trade_order_queue,
        entry_price,
        process_name="Monitor",
        backtest_scope="intraday"
    ):
        self.ticker = ticker
        self.monitor_interval_seconds = monitor_interval_seconds
        self.trade_order_queue = trade_order_queue
        self.entry_price = entry_price
        self.process_name = process_name

        self._running = False
        self._is_active_position = False
        from stock_monitoring_app.monitoring.ticker_monitor import BACKTEST_SCOPE_PRESETS
        if backtest_scope not in BACKTEST_SCOPE_PRESETS:
            raise ValueError(f"Unknown backtest_scope '{backtest_scope}'. Choose from {list(BACKTEST_SCOPE_PRESETS.keys())}")
        self.backtest_scope = backtest_scope
        self._period = BACKTEST_SCOPE_PRESETS[backtest_scope]["period"]
        self._interval = BACKTEST_SCOPE_PRESETS[backtest_scope]["interval"]
        self._indicator_configs = None

        # For position management in dollars
        self.position_value = 0.0  # USD value of current position
        self._forced_entry_done = False  # Track if forced entry was executed

        # Track opening date for filename
        self.opening_date_str = None  # Will be set when a position is opened

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
            from stock_monitoring_app.backtest.backtest import BackTest
            backtester = BackTest(ticker=self.ticker, period=self._period, interval=self._interval)
            results = backtester.run_backtest()
            if results is not None:
                print(f"INFO [{self.process_name}]: Backtest complete for {self.ticker}.")
            else:
                print(f"WARN [{self.process_name}]: Backtest failed for {self.ticker}.")
        except Exception as e:
            print(f"ERROR [{self.process_name}]: Exception during backtest: {e}")

    def _load_optimized_config_from_disk(self) -> Optional[List[Dict]]:
        import time
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            outputs_dir = os.path.join(project_root, "backtest_outputs")
            pattern = os.path.join(outputs_dir, f"{self.ticker}_*_metrics.json")
            files = glob.glob(pattern)
            if not files:
                print(f"INFO [{self.process_name}]: No optimized config files found for {self.ticker}.")
                self._run_backtest()
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
        print(f"INFO [{self.process_name}]: Fetching latest data for {self.ticker}...")
        try:
            from stock_monitoring_app.backtest.backtest import BackTest
            fetcher = BackTest(ticker=self.ticker, period=self._period, interval=self._interval).fetcher
            data = fetcher.fetch_data(self.ticker, period=self._period, interval=self._interval)
            if data is not None and not data.empty:
                return data
            else:
                print(f"WARN [{self.process_name}]: No data returned for {self.ticker}.")
                return pd.DataFrame()
        except Exception as e:
            print(f"ERROR [{self.process_name}]: Exception in _fetch_latest_data: {e}")
            return pd.DataFrame()

    def _store_forwardtest_result(self, order):
        """
        Store trade order results in a forwardtest_output directory (alongside backtest_outputs).
        The filename includes the opening date (YYYYMMDD_HHMMSS) and the ticker.
        Each order is appended as a new line in JSONL format.
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        output_dir = os.path.join(project_root, "forwardtest_output")
        os.makedirs(output_dir, exist_ok=True)
        # Ensure opening_date_str is set (should be set at the first BUY/forced entry)
        if not self.opening_date_str and order["action"] == "BUY":
            # Use the timestamp of this order
            self.opening_date_str = pd.Timestamp(order["timestamp"]).strftime("%Y%m%d_%H%M%S")
        elif not self.opening_date_str:
            # Fallback: use current time
            self.opening_date_str = pd.Timestamp.now(tz='UTC').strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(
            output_dir,
            f"{self.opening_date_str}_{self.ticker}_forwardtest.json"
        )
        with open(output_file, "a") as f:
            f.write(json.dumps(order) + "\n")

    def _process_data_and_decide(self, latest_data_df):
        print(f"INFO [{self.process_name}]: Processing data for {self.ticker}...")


        if self._indicator_configs is None:
            print(f"WARN [{self.process_name}]: No indicator configs available, skipping decision.")            
            return

        DEFAULT_POSITION_VALUE = 1000.0  # Define unconditionally here
        latest_row = latest_data_df.iloc[[-1]]

        strategy = BaseStrategy(indicator_configs=self._indicator_configs)
        signals_df = strategy.run(latest_row)

        if signals_df is not None and not signals_df.empty:
            signal = signals_df.iloc[0].get('Strategy_Signal', "HOLD")
            price = signals_df.iloc[0].get('Close', None)

            if price is None or price == 0:
                print(f"WARN [{self.process_name}]: No valid price for trade signal; skipping order emission.")
                return
            # DEFAULT_POSITION_VALUE = 1000.0 # Removed from conditional block
            quantity = 0.0
            actioned_signals = {}
            for col in signals_df.columns:
                if col != 'Strategy_Signal' and pd.notna(signals_df.iloc[0][col]):
                    actioned_signals[col] = signals_df.iloc[0][col]
        else:
            signal = "HOLD"
            price = None
            quantity = 0.0
            actioned_signals = {}

        position_before = self.position_value


        if signal == "BUY":
            if price is not None and price > 0:
                if self.position_value == 0:
                    self.position_value = DEFAULT_POSITION_VALUE
                quantity = float(self.position_value) / float(price)
            else:
                quantity = 0.0
                # This case should ideally not be reached due to earlier checks, but good for robustness
                print(f"WARN [{self.process_name}]: Invalid price ({price}) for BUY signal. Setting quantity to 0.")
        elif signal == "SELL":
            if self.position_value > 0:
                if price is not None and price > 0:
                    quantity = float(self.position_value) / float(price)
                else:
                    quantity = 0.0
                    # This case should ideally not be reached
                    print(f"WARN [{self.process_name}]: Invalid price ({price}) for SELL signal. Setting quantity to 0.")
            else:
                quantity = 0.0
            self.position_value = 0.0
        else:
            quantity = float(self.position_value) / float(price) if price else 0.0

        print(f"INFO [{self.process_name}]: Signal for {self.ticker}: {signal} | Price: {price} | Position $ before: {position_before} | after: {self.position_value} | Quantity: {quantity}")

        if signal != "HOLD":
            order = {
                "action": signal,
                "ticker": self.ticker,
                "price": price,
                "quantity": quantity,  # number of shares as float
                "position_value": self.position_value,
                "timestamp": pd.Timestamp.now(tz='UTC').isoformat(),
                "actioned_signals": actioned_signals,
            }
            self.trade_order_queue.put(order)
            self._store_forwardtest_result(order)  # Store in forwardtest_output

    def _force_initial_position(self):
        if self._forced_entry_done or self.entry_price <= 0 or self.position_value > 0:
            return
        latest_data_df = self._fetch_latest_data()
        if latest_data_df is not None and not latest_data_df.empty:
            price = latest_data_df.iloc[-1]["Close"]
            self.position_value = self.entry_price
            quantity = float(self.entry_price) / float(price)
            # Set the opening date string here on first forced entry
            self.opening_date_str = pd.Timestamp.now(tz='UTC').strftime("%Y%m%d_%H%M%S")
            order = {
                "action": "BUY",
                "ticker": self.ticker,
                "price": price,
                "quantity": quantity,  # number of shares as float
                "position_value": self.position_value,
                "timestamp": pd.Timestamp.now(tz='UTC').isoformat(),
                "actioned_signals": {"forced_entry": True}
            }
            self.trade_order_queue.put(order)
            self._store_forwardtest_result(order)  # Store in forwardtest_output
            print(f"INFO [{self.process_name}]: Forced initial BUY at entry price {self.entry_price} (market price {price}) | Quantity: {quantity}")
            self._forced_entry_done = True

    def run(self):
        print(f"DEBUG: TickerMonitor.run() called for {self.ticker}")
        print(f"INFO [{self.process_name}]: Starting monitor for {self.ticker} with entry price {self.entry_price:.2f}...")
        indicator_configs = self._load_optimized_config_from_disk()
        self._indicator_configs = indicator_configs
        self._running = True

        # >>>> FORCE INITIAL POSITION IF NEEDED <<<<
        self._force_initial_position()

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
                for _ in range(int(sleep_duration)):
                    if not self._running:
                        break
                    time.sleep(1)
                if self._running and sleep_duration % 1 > 0:
                    time.sleep(sleep_duration % 1)
            else:
                print(f"WARN [{self.process_name}]: Cycle took {elapsed_time:.2f}s, exceeding monitor interval of {self.monitor_interval_seconds}s.")

        print(f"INFO [{self.process_name}]: Monitor loop stopped for {self.ticker}.")

    def stop(self):
        self._running = False
