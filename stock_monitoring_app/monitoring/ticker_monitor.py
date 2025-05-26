import os
import glob
import json
import time
import pandas as pd
from typing import Optional, List, Dict

from stock_monitoring_app.strategies.base_strategy import BaseStrategy
from stock_monitoring_app.utils.notification import send_notification

BACKTEST_SCOPE_PRESETS = {
    "intraday": {"period": "1d", "interval": "1m"},
    "short": {"period": "1w", "interval": "15m"},
    "long": {"period": "1mo", "interval": "1d"}
}

time_intervals = {
    '1s': 1, '5s': 5, '10s': 10, '30s': 30,
    '1m': 60, '5m': 300, '15m': 900, '30m': 1800,
    '1h': 3600, '2h': 7200, '1d': 86400, '7d': 604800,
    '30d': 2592000, '1month': 2592000, '1year': 31536000
}

def convert_to_seconds(interval):
    return time_intervals.get(interval, "Invalid interval")

class TickerMonitor:

    def __init__(self, ticker, trade_order_queue, entry_price, process_name="Monitor", backtest_scope="intraday", leverage=1,stop_loss=0.05):
        self.ticker = ticker
        self.trade_order_queue = trade_order_queue
        self.entry_price = entry_price
        self.process_name = process_name
        self.quantity = 0
        self.leverage = leverage
        self._running = False
        self._is_active_position = False

        if backtest_scope not in BACKTEST_SCOPE_PRESETS:
            raise ValueError(f"Unknown backtest_scope '{backtest_scope}'. Choose from {list(BACKTEST_SCOPE_PRESETS.keys())}")
        self.backtest_scope = backtest_scope
        self._period = BACKTEST_SCOPE_PRESETS[backtest_scope]["period"]
        self._interval = BACKTEST_SCOPE_PRESETS[backtest_scope]["interval"]
        self.monitor_interval_seconds = convert_to_seconds(self._interval)

        self._indicator_configs = None
        self.position_value = 0.0
        self._forced_entry_done = False
        self.opening_date_str = None

        self.position_type = "none"
        self.entry_trade_price = None
        self.stop_loss_threshold = 1 - stop_loss

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
            raise

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
#            return pd.DataFrame()
            raise

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

        latest_row = latest_data_df.iloc[[-1]]
        strategy = BaseStrategy(indicator_configs=self._indicator_configs)
        signals_df = strategy.run(latest_row)

        if signals_df is not None and not signals_df.empty:
            signal = signals_df.iloc[0].get('Strategy_Signal', "HOLD")
            price = signals_df.iloc[0].get('Close', None)
            if price is None or price == 0:
                print(f"WARN [{self.process_name}]: No valid price for trade signal; skipping order emission.")
                return
            if self.initial_deposit:
                self.delta = (price - self.current_price)/self.current_price
                price_variation=self.initial_deposit*(self.delta/100)*self.leverage
                self.current_value = self.initial_deposit + price_variation
            self.current_price = price
            actioned_signals = {
                col: signals_df.iloc[0][col]
                for col in signals_df.columns if col != 'Strategy_Signal' and pd.notna(signals_df.iloc[0][col])
            }
        else:
            signal = "HOLD"
            price = None
            actioned_signals = {}
        quantity = self.quantity
        position_before = self.position_value
        position_type_before = self.position_type
        order = None
        timestamp = pd.Timestamp.now(tz='UTC').isoformat()

        # Stop-loss logic
        if self.position_type in ("long", "short") and self.entry_trade_price and price:
            if self.position_type == "long":
                threshold_price = self.entry_trade_price * self.stop_loss_threshold
                stop_loss_triggered = price < threshold_price
            else:
                threshold_price = self.entry_trade_price / self.stop_loss_threshold
                stop_loss_triggered = price > threshold_price

            if stop_loss_triggered:
                print(f"INFO [{self.process_name}]: Stop-loss triggered. Closing {self.position_type} position.")
                action = "SELL" if self.position_type == "long" else "BUY"
                quantity = self.quantity
                order = {
                    "action": action,
                    "ticker": self.ticker,
                    "price": price,
                    "quantity": quantity,
                    "position_value": 0.0,
                    "timestamp": timestamp,
                    "actioned_signals": {**actioned_signals, "stop_loss_triggered": True}
                }
                self.position_value = 0.0
                aelf.quantity = 0
                self.position_type = "none"
                self.entry_trade_price = None
                self.trade_order_queue.put(order)
                self._store_forwardtest_result(order)
                return
        # Signal-based trade logic
        if signal == "BUY":
            if self.position_type == "none":
                quantity = self.quantity
                self.position_value = quantity * price
                self.position_type = "long"
                self.entry_trade_price = price
                order = {
                    "action": "BUY",
                    "ticker": self.ticker,
                    "price": price,
                    "quantity": quantity,
                    "position_value": self.position_value,
                    "timestamp": timestamp,
                    "actioned_signals": actioned_signals
                }
            elif self.position_type == "short":
                quantity = self.quantity
                self.position_value = 0.0
                self.position_type = "none"
                self.entry_trade_price = None
                order = {
                    "action": "BUY",
                    "ticker": self.ticker,
                    "price": price,
                    "quantity": quantity,
                    "position_value": 0.0,
                    "timestamp": timestamp,
                    "actioned_signals": actioned_signals
                }

        elif signal == "SELL":
            if self.position_type == "none":
                quantity = self.quantity
                self.position_value = quantity * price
                self.position_type = "short"
                self.entry_trade_price = price
                order = {
                    "action": "SELL",
                    "ticker": self.ticker,
                    "price": price,
                    "quantity": quantity,
                    "position_value": self.position_value,
                    "timestamp": timestamp,
                    "actioned_signals": actioned_signals
                }
            elif self.position_type == "long":
                quantity = self.quantity
                self.position_value = 0.0
                self.position_type = "none"
                self.entry_trade_price = None
                order = {
                    "action": "SELL",
                    "ticker": self.ticker,
                    "price": price,
                    "quantity": quantity,
                    "position_value": 0.0,
                    "timestamp": timestamp,
                    "actioned_signals": actioned_signals
                }

        if order:
            print(f"INFO [{self.process_name}]: Signal {signal} | Price: {price} | From {position_type_before} to {self.position_type} | Position $: {position_before} -> {self.position_value} | Quantity: {order['quantity']}")
            self.trade_order_queue.put(order)
            self._store_forwardtest_result(order)
        else:
            order = {
                "action": "INFO",
                "ticker": self.ticker,
                "price": self.current_price,
                "quantity": self.quantity,
                "position_value": self.current_value,
                "timestamp": timestamp,
                "actioned_signals": {}
            }
            print(f"INFO [{self.process_name}]: No position change for signal {signal}. Holding current position at ${self.current_value} Market Price ${self.current_price}")
        self.trade_order_queue.put(order)
        self._store_forwardtest_result(order)
        if order["action"]=="SELL" or order["action"]=="BUY":
            send_notification(f"Trade Order {order['action']}:{order['ticker']}",f"${order['price']}, ${order['position_value']}")
            
    def _force_initial_position(self):
        if self._forced_entry_done or self.entry_price <= 0 or self.position_value > 0:
            return
        latest_data_df = self._fetch_latest_data()
        if latest_data_df is not None and not latest_data_df.empty:
            price = latest_data_df.iloc[-1]["Close"]
            quantity = float(self.entry_price) / float(price)
            self.current_value = quantity * price
            self.initial_deposit = self.current_value
            self.current_price = price
            self.quantity = quantity
            self.position_value = quantity * price
            self.position_type = "long"
            self.entry_trade_price = price
            self.opening_date_str = pd.Timestamp.now(tz='UTC').strftime("%Y%m%d_%H%M%S")
            order = {
                "action": "BUY",
                "ticker": self.ticker,
                "price": price,
                "quantity": quantity,
                "position_value": self.position_value,
                "timestamp": pd.Timestamp.now(tz='UTC').isoformat(),
                "actioned_signals": {"forced_entry": True}
            }
            self.trade_order_queue.put(order)
            self._store_forwardtest_result(order)
            send_notification(f"Trade Order {order['action']}:{order['ticker']}",f"${order['price']}, ${order['position_value']}")
            print(f"INFO [{self.process_name}]: Forced initial BUY at entry price {self.entry_price} (market price {price}) | Quantity: {quantity}")
            self._forced_entry_done = True

    def run(self):
        print(f"DEBUG: TickerMonitor.run() called for {self.ticker}")
        print(f"INFO [{self.process_name}]: Starting monitor for {self.ticker} with entry price {self.entry_price:.2f}...")
        self._indicator_configs = self._load_optimized_config_from_disk()
        self._running = True

        self._force_initial_position()

        print(f"INFO [{self.process_name}]: Monitor loop started. Interval: {self.monitor_interval_seconds}s.")
        while self._running:
            start_time = time.time()
            print(f"INFO [{self.process_name}]: Cycle started at {pd.Timestamp.now(tz='UTC')}.")

            try:
                latest_data_df = self._fetch_latest_data()
                if latest_data_df is not None and not latest_data_df.empty:
                    self._process_data_and_decide(latest_data_df)
            except Exception as e:
                print(f"ERROR [{self.process_name}]: Exception during fetch or process: {e}")

            elapsed_time = time.time() - start_time
            sleep_duration = self.monitor_interval_seconds - elapsed_time

            if sleep_duration > 0:
                print(f"INFO [{self.process_name}]: Sleeping for {sleep_duration:.2f}s...")
                time.sleep(sleep_duration)

        print(f"INFO [{self.process_name}]: Monitor loop stopped for {self.ticker}.")

    def stop(self):
        self._running = False

