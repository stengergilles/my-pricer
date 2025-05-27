
import os
import glob
import json
import time
import pandas as pd
import numpy as np # Import numpy
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
        
        monitor_interval_value = convert_to_seconds(self._interval)
        if not isinstance(monitor_interval_value, int):
            # This should not happen if _interval from BACKTEST_SCOPE_PRESETS is always valid.
            # Adding this check for type safety and to inform the type checker.
            raise TypeError(
                f"Failed to convert interval '{self._interval}' to a valid integer of seconds. "
                f"Got: {monitor_interval_value}"
            )
        self.monitor_interval_seconds = monitor_interval_value


        self._indicator_configs = None
        self.position_value = 0.0
        self.opening_date_str = None

        self.position_type = "none"

        self.entry_trade_price = None





        self.entry_trade_price = None

        self.stop_loss_percentage: float = stop_loss # Store the stop-loss percentage directly (e.g., 0.05 for 5%)        # entry_price from constructor is the initial capital allocation for this monitor
        self.initial_capital_allocation: float = float(entry_price)
        # current_value is the total equity of the monitor, starts with the initial allocation
        self.current_value: float = float(entry_price) 
        # equity_at_trade_open stores current_value just before a new trade is opened
        self.equity_at_trade_open: Optional[float] = None 
        
        self.current_price: Optional[float] = None # Latest market price

        # self.position_value (existing) remains market value of current asset holding (price * quantity)

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

        # Process the full DataFrame fetched for the period.
        # Indicators within the strategy will use the necessary historical window from this DataFrame.

        # Pass a copy to strategy.run() to prevent unintended modifications to the original DataFrame.
        strategy = BaseStrategy(indicator_configs=self._indicator_configs)
        signals_df = strategy.run(latest_data_df.copy())

        # Initialize price and signal to defaults before conditional assignment
        price = None
        signal = "HOLD"
        actioned_signals = {}

        if signals_df is not None and not signals_df.empty:
            # Extract signal, price, and actioned_signals from the *last row* of the processed DataFrame
            last_signal_row = signals_df.iloc[-1]
            signal = last_signal_row.get('Strategy_Signal', "HOLD") # Re-assign if available
            price = last_signal_row.get('Close', None) # Re-assign if available

            # Using pd.isna() to robustly check for None, np.nan, pd.NA
            if pd.isna(price) or price == 0:
                print(f"WARN [{self.process_name}]: No valid price (None, NA, or 0) from the last signal row; skipping order emission.")
                return
            


            # Ensure price is float for calculations
            price = float(price)
            self.current_price = price # Update current_price with the latest valid market price

            # Update self.current_value (total equity) and self.position_value based on P&L of any open position
            if self.position_type != "none" and \
               self.equity_at_trade_open is not None and \
               self.entry_trade_price is not None and \
               self.quantity != 0: # Price is guaranteed not None here
                unrealized_pnl = 0.0
                if self.position_type == "long":
                    unrealized_pnl = (self.current_price - self.entry_trade_price) * self.quantity * self.leverage
                elif self.position_type == "short":
                    unrealized_pnl = (self.entry_trade_price - self.current_price) * self.quantity * self.leverage                
                # self.current_value reflects total equity including unrealized P&L of the current open trade
                self.current_value = self.equity_at_trade_open + unrealized_pnl
                self.position_value = self.quantity * self.current_price # Market value of current asset holding
            
            elif self.position_type == "none":
                # If flat, current_value is already the total equity after the last closed trade.
                # Position value is 0.
                self.position_value = 0.0
            # If self.current_value was None (e.g., very first run before __init__ fully sets if using entry_price=0),
            # it would remain None until a trade properly initializes equity_at_trade_open.
            # However, __init__ now ensures current_value is float.




            actioned_signals = {}
            # Populate actioned_signals with all indicator signals (True, False, or None for pd.NA)
            for col_name in last_signal_row.index:
                if col_name != 'Strategy_Signal' and not col_name.endswith(('_Raw_Signal', '_Strength')): # Exclude non-boolean/raw signals if any
                    raw_signal_value = last_signal_row[col_name] # This might be a scalar or Series

                    # Ensure we are working with a scalar for subsequent checks
                    value_to_process = raw_signal_value
                    if isinstance(raw_signal_value, pd.Series):
                        if not raw_signal_value.empty:
                            value_to_process = raw_signal_value.iloc[0] # Take the first element
                        else:
                            value_to_process = np.nan # Treat empty series as NA to be handled by pd.isna()


                    # Now value_to_process is expected to be a scalar (or np.nan)
                    
                    # Check for NA, handling if pd.isna returns a Series
                    is_na_check_result = pd.isna(value_to_process)
                    is_actually_na = False
                    if isinstance(is_na_check_result, pd.Series):
                        is_actually_na = is_na_check_result.any() # True if any element in the series is NA
                    elif isinstance(is_na_check_result, (bool, np.bool_)): # if pd.isna returned a scalar boolean
                        is_actually_na = bool(is_na_check_result)

                    if is_actually_na:
                        actioned_signals[col_name] = None
                    elif isinstance(value_to_process, (bool, np.bool_)): # Check the (potentially extracted) scalar
                        actioned_signals[col_name] = bool(value_to_process)
                    # Optionally, handle other types or log them if unexpected
                    # else:
                    #     print(f"DEBUG: Unexpected signal type for {col_name} after NA check: {type(value_to_process)}, value: {value_to_process}")
        position_before = self.position_value
        position_type_before = self.position_type
        order = None
        timestamp = pd.Timestamp.now(tz='UTC').isoformat()



        # Stop-loss logic
        # Ensure self.current_price is not None before attempting comparisons for stop-loss
        if self.current_price is not None and self.position_type in ("long", "short") and self.entry_trade_price is not None:
            stop_loss_triggered = False
            threshold_price = 0.0 # Initialize to avoid undefined variable if logic path missed

            if self.position_type == "long":
                threshold_price = self.entry_trade_price * (1 - self.stop_loss_percentage)
                if self.current_price < threshold_price:
                    stop_loss_triggered = True
            elif self.position_type == "short":
                threshold_price = self.entry_trade_price * (1 + self.stop_loss_percentage)
                if self.current_price > threshold_price:
                    stop_loss_triggered = True

            if stop_loss_triggered:
                print(f"DEBUG [{self.process_name}]: Stop-loss triggered for {self.position_type} at {self.current_price:.2f}, threshold was {threshold_price:.2f}")
                action_to_close = "SELL" if self.position_type == "long" else "BUY"
                
                # Calculate realized P&L for this specific trade
                realized_pnl_this_trade = 0.0
                if self.equity_at_trade_open is not None and self.entry_trade_price is not None: # Should be true
                    if self.position_type == "long":                        realized_pnl_this_trade = (self.current_price - self.entry_trade_price) * self.quantity * self.leverage
                    elif self.position_type == "short":
                        realized_pnl_this_trade = (self.entry_trade_price - self.current_price) * self.quantity * self.leverage
                    # Update total equity
                    self.current_value = self.equity_at_trade_open + realized_pnl_this_trade
                else: # Fallback if equity_at_trade_open was somehow not set
                    print(f"WARN [{self.process_name}]: equity_at_trade_open not set for stop-loss P&L calculation. Current equity might be inaccurate.")
                
                print(f"INFO [{self.process_name}]: Stop-loss triggered. Closing {self.position_type} position at {self.current_price:.2f}. Trade P&L: {realized_pnl_this_trade:.2f}. New Total Equity: {self.current_value:.2f}")

                order = {
                    "action": action_to_close,
                    "ticker": self.ticker,
                    "price": self.current_price,
                    "quantity": self.quantity, # The quantity being closed
                    "asset_value_traded": 0.0, # Market value of asset holding becomes 0
                    "equity_after_trade": self.current_value, # Total equity after this trade
                    "pnl_this_trade": realized_pnl_this_trade,
                    "timestamp": timestamp,
                    "actioned_signals": {**actioned_signals, "stop_loss_triggered": True}
                }
                
                # Reset position state
                self.position_value = 0.0 
                self.quantity = 0
                self.position_type = "none"                
                self.entry_trade_price = None
                self.equity_at_trade_open = None # Reset for next trade

                self.trade_order_queue.put(order)
                self._store_forwardtest_result(order)
                return

        # Signal-based trade logic
        # `current_price` is already set, `current_value` reflects unrealized P&L if a position is open
        
        if signal == "BUY":
            if self.position_type == "none":

                # Open NEW LONG position
                self.equity_at_trade_open = self.current_value # Capture equity before this trade
                if self.current_price is None or self.current_price == 0: # Should not happen due to earlier check
                     print(f"WARN [{self.process_name}]: Cannot open BUY position, current price is invalid: {self.current_price}")                     
                     return
                print(f"DEBUG_QTY_CALC [{self.process_name}]: BUY New Long. Initial Capital: {self.initial_capital_allocation}, Current Price: {self.current_price}")
                self.quantity = self.initial_capital_allocation / self.current_price # Use initial capital for consistent trade size
                print(f"DEBUG_QTY_CALC [{self.process_name}]: BUY New Long. Calculated Quantity: {self.quantity}")
                self.position_type = "long"
                self.entry_trade_price = self.current_price
                self.position_value = self.quantity * self.current_price # Market value of assets bought
                
                order = {
                    "action": "BUY",
                    "ticker": self.ticker,
                    "price": self.current_price,
                    "quantity": self.quantity,
                    "asset_value_traded": self.position_value,
                    "equity_before_trade": self.equity_at_trade_open,
                    "timestamp": timestamp,
                    "actioned_signals": actioned_signals
                }
            elif self.position_type == "short":
                # Close SHORT position and GO LONG (Reversal)

                # 1. Calculate P&L of the closing short trade
                realized_pnl_closing_short = 0.0
                if self.equity_at_trade_open is not None and \
                   self.entry_trade_price is not None and \
                   self.current_price is not None: # Ensure current_price is not None for type checker
                     realized_pnl_closing_short = (self.entry_trade_price - self.current_price) * self.quantity * self.leverage
                     self.current_value = self.equity_at_trade_open + realized_pnl_closing_short # Update total equity
                
                print(f"INFO [{self.process_name}]: Closing SHORT for reversal. Trade P&L: {realized_pnl_closing_short:.2f}. New Total Equity: {self.current_value:.2f}")
                

                # 2. Open NEW LONG position
                self.equity_at_trade_open = self.current_value # Capture equity before new long trade
                if self.current_price is None or self.current_price == 0:
                     print(f"WARN [{self.process_name}]: Cannot open BUY (reversal) position, current price is invalid: {self.current_price}")
                     # Note: position state might be inconsistent if we return here after closing short
                     return
                print(f"DEBUG_QTY_CALC [{self.process_name}]: BUY Reversal to Long. Initial Capital: {self.initial_capital_allocation}, Current Price: {self.current_price}")
                self.quantity = self.initial_capital_allocation / self.current_price                
                print(f"DEBUG_QTY_CALC [{self.process_name}]: BUY Reversal to Long. Calculated Quantity: {self.quantity}")
                self.position_type = "long"
                self.entry_trade_price = self.current_price
                self.position_value = self.quantity * self.current_price

                order = {
                    "action": "BUY", # This order represents the new LONG position
                    "ticker": self.ticker,
                    "price": self.current_price,
                    "quantity": self.quantity,
                    "asset_value_traded": self.position_value, # Value of new long position
                    "equity_before_trade": self.equity_at_trade_open, # Equity before this new long
                    "pnl_from_prior_short_trade": realized_pnl_closing_short,
                    "timestamp": timestamp,
                    "actioned_signals": actioned_signals
                }
            # If signal is BUY and self.position_type is "long", no 'order' is created here (handled by INFO log later)

        elif signal == "SELL":
            if self.position_type == "none":

                # Open NEW SHORT position
                self.equity_at_trade_open = self.current_value
                if self.current_price is None or self.current_price == 0:
                     print(f"WARN [{self.process_name}]: Cannot open SELL position, current price is invalid: {self.current_price}")
                     return
                print(f"DEBUG_QTY_CALC [{self.process_name}]: SELL New Short. Initial Capital: {self.initial_capital_allocation}, Current Price: {self.current_price}")                
                self.quantity = self.initial_capital_allocation / self.current_price
                print(f"DEBUG_QTY_CALC [{self.process_name}]: SELL New Short. Calculated Quantity: {self.quantity}")                
                self.position_type = "short"
                self.entry_trade_price = self.current_price
                self.position_value = self.quantity * self.current_price # Market value of assets shorted (absolute)

                order = {
                    "action": "SELL",
                    "ticker": self.ticker,
                    "price": self.current_price,
                    "quantity": self.quantity,
                    "asset_value_traded": self.position_value,
                    "equity_before_trade": self.equity_at_trade_open,
                    "timestamp": timestamp,                    "actioned_signals": actioned_signals
                }

            elif self.position_type == "long":

                # Close LONG position and GO SHORT (Reversal)                # 1. Calculate P&L of the closing long trade
                realized_pnl_closing_long = 0.0
                if self.equity_at_trade_open is not None and \
                   self.entry_trade_price is not None and \
                   self.current_price is not None: # Ensure current_price is not None for type checker
                    realized_pnl_closing_long = (self.current_price - self.entry_trade_price) * self.quantity * self.leverage
                    self.current_value = self.equity_at_trade_open + realized_pnl_closing_long # Update total equity
                
                print(f"INFO [{self.process_name}]: Closing LONG for reversal. Trade P&L: {realized_pnl_closing_long:.2f}. New Total Equity: {self.current_value:.2f}")


                # 2. Open NEW SHORT position
                self.equity_at_trade_open = self.current_value # Capture equity before new short trade
                if self.current_price is None or self.current_price == 0:
                     print(f"WARN [{self.process_name}]: Cannot open SELL (reversal) position, current price is invalid: {self.current_price}")
                     return # Position state might be inconsistent if we return here
                print(f"DEBUG_QTY_CALC [{self.process_name}]: SELL Reversal to Short. Initial Capital: {self.initial_capital_allocation}, Current Price: {self.current_price}")
                self.quantity = self.initial_capital_allocation / self.current_price
                print(f"DEBUG_QTY_CALC [{self.process_name}]: SELL Reversal to Short. Calculated Quantity: {self.quantity}")
                self.position_type = "short"
                self.entry_trade_price = self.current_price
                self.position_value = self.quantity * self.current_price

                order = {
                    "action": "SELL", # This order represents the new SHORT position
                    "ticker": self.ticker,
                    "price": self.current_price,
                    "quantity": self.quantity,
                    "asset_value_traded": self.position_value, # Value of new short position
                    "equity_before_trade": self.equity_at_trade_open, # Equity before this new short                    "pnl_from_prior_long_trade": realized_pnl_closing_long,
                    "timestamp": timestamp,
                    "actioned_signals": actioned_signals
                }
            # If signal is SELL and self.position_type is "short", no 'order' is created here (handled by INFO log later)

        if order:
            # Log executed trade (BUY or SELL)
            print(f"INFO [{self.process_name}]: Signal {signal} | Executing {order['action']} | Price: {self.current_price:.2f} | "
                  f"From PosType: {position_type_before} -> {self.position_type} | "
                  f"Asset Value: ${position_before:.2f} -> ${self.position_value:.2f} | "
                  f"Quantity: {order['quantity']:.4f} | "
                  f"Total Equity Before: ${order.get('equity_before_trade', self.current_value - order.get('pnl_this_trade', 0) - order.get('pnl_from_prior_short_trade',0) - order.get('pnl_from_prior_long_trade',0)):.2f} -> "
                  f"After: ${self.current_value:.2f}")

            self.trade_order_queue.put(order)
            self._store_forwardtest_result(order) # Store BUY/SELL trades
            if order["action"] in ["SELL", "BUY"]: # Send notification for actual trades
                asset_value_field = "asset_value_traded" if "asset_value_traded" in order else "position_value" # backward compatibility
                send_notification(
                    f"Trade Order {order['action']}:{order['ticker']}",
                    f"Price: ${order['price']:.2f}, Asset Value: ${order[asset_value_field]:.2f}, Total Equity: ${self.current_value:.2f}"
                )

        else:
            # No trade order was generated (HOLD signal, or signal matches current position)
            info_status_reason = "Hold signal received" # Default
            current_actioned_signals = {**actioned_signals} # Initialize current_actioned_signals here

            if signal == "BUY" and self.position_type == "long":
                info_status_reason = "Already long, signal BUY. Holding."
                current_actioned_signals["status_reason"] = "already_long"            
            elif signal == "SELL" and self.position_type == "short":
                info_status_reason = "Already short, signal SELL. Holding."
                current_actioned_signals["status_reason"] = "already_short"
            elif signal == "HOLD":
                info_status_reason = f"Hold signal received. Current position: {self.position_type}."
                current_actioned_signals["status_reason"] = "hold_signal"
            # Other cases (e.g. price was None) are handled by returning earlier.

            log_equity_value = f"${self.current_value:.2f}" if self.current_value is not None else "N/A"
            log_asset_value = f"${self.position_value:.2f}" if self.position_value is not None else "N/A"

            log_market_price = f"${self.current_price:.2f}" if self.current_price is not None else "N/A"

            print(f"INFO [{self.process_name}]: {info_status_reason} | Ticker: {self.ticker} | Market Price: {log_market_price} | "
                  f"Asset Value: {log_asset_value} | Total Equity: {log_equity_value}")
            
            print(f"DEBUG_INFO_MSG_PREP [{self.process_name}]: Preparing INFO. Current Qty: {self.quantity}, PosType: {self.position_type}, Current Equity: {self.current_value}, Current Price: {self.current_price}")

            info_order = {
                "action": "INFO",
                "ticker": self.ticker,
                "timestamp": timestamp,
                "status_reason": info_status_reason,
                "current_market_price": self.current_price,
                "asset_value_held": self.position_value,
                "total_equity": self.current_value,

                "current_position_type": self.position_type,
                "current_quantity": self.quantity, # Added current quantity
                "actioned_signals": current_actioned_signals
            }
            self.trade_order_queue.put(info_order)


            # Typically, INFO orders are not stored in the same way as trade executions.
            # If _store_forwardtest_result is desired for INFO, uncomment the next line:
            # self._store_forwardtest_result(info_order)
            

    def run(self):
        print(f"DEBUG: TickerMonitor.run() called for {self.ticker}")
        print(f"INFO [{self.process_name}]: Starting monitor for {self.ticker} with entry price {self.entry_price:.2f}...")

        # Attempt to load/generate indicator configurations
        try:
            self._indicator_configs = self._load_optimized_config_from_disk()
            if self._indicator_configs is None:
                print(f"CRITICAL [{self.process_name}]: Failed to load or generate indicator configurations for {self.ticker}. Monitor stopping.")
                self._running = False # Ensure consistent state
                return # Stop the monitor
        except Exception as e:
            # This catches exceptions from _load_optimized_config_from_disk if it doesn't handle them (e.g. unexpected errors),
            # or if _run_backtest() within it raises something not caught by _load_optimized_config_from_disk's own try-except.
            print(f"CRITICAL [{self.process_name}]: Unhandled exception during indicator configuration loading for {self.ticker}: {e}. Monitor stopping.")
            self._running = False
            return

        # Set running to true only if config load was successful and we intend to proceed
        self._running = True


        print(f"INFO [{self.process_name}]: Monitor loop started. Interval: {self.monitor_interval_seconds}s.")
        while self._running:
            start_time = time.time()
            print(f"INFO [{self.process_name}]: Cycle started at {pd.Timestamp.now(tz='UTC')}.")

            try:
                latest_data_df = self._fetch_latest_data() # This can raise if fetcher.fetch_data fails
                if latest_data_df is not None and not latest_data_df.empty:
                    self._process_data_and_decide(latest_data_df)
                # If latest_data_df is None or empty, _fetch_latest_data might have returned an empty DataFrame                # after printing a warning (this is fine). The critical part is if _fetch_latest_data *raises* an exception.
            except Exception as e: # Catches exceptions from _fetch_latest_data or _process_data_and_decide
                print(f"ERROR [{self.process_name}]: Unhandled exception during monitoring cycle for {self.ticker}: {e}. Monitor stopping.")
                self._running = False # Signal to stop; loop will terminate
            
            if not self._running: # If an error above set _running to False, break immediately
                break

            elapsed_time = time.time() - start_time
            sleep_duration = self.monitor_interval_seconds - elapsed_time

            if sleep_duration > 0:
                print(f"INFO [{self.process_name}]: Sleeping for {sleep_duration:.2f}s...")
                # Check self._running again before a potentially long sleep,
                # in case stop() was called from another thread.
                if not self._running:
                    break
                time.sleep(sleep_duration)
            
            if not self._running: # Check after sleep or if sleep_duration was <=0
                break        
        print(f"INFO [{self.process_name}]: Monitor loop stopped for {self.ticker}.")

   

    def stop(self):
        self._running = False

