

import urwid
import multiprocessing as mp
import sys
import time
import os
from typing import Optional # Added for type hinting
import pandas as pd # Added for timestamp formatting

try:
    # Adjust this import path as needed for your project layout
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
except ImportError:
    TickerMonitor = None


if sys.platform == "win32":
    mp.set_start_method("spawn", force=True)
elif sys.platform == "darwin":  # macOS
    mp.set_start_method("spawn", force=True)  # Use 'spawn' on macOS to avoid fork-related crashes
else:  # Other POSIX systems (e.g., Linux)
    # 'fork' is generally fine and more performant on Linux, but 'spawn' can also be used if needed.

    # Sticking with 'fork' for Linux for now unless issues arise there.
    mp.set_start_method("fork", force=True)

# Import the new centralized process launcher
try:
    from stock_monitoring_app.utils.process_manager import launch_ticker_monitor_process
except ImportError:
    print("CRITICAL TUI ERROR: process_manager utility not found. Monitoring will not work.", file=sys.stderr)
    launch_ticker_monitor_process = None


class Monitor:
    def __init__(self, ticker, entry, scope, leverage=1.0, stop_loss=0.05):
        self.ticker = ticker
        self.entry = entry # This is initial_capital_allocation
        self.scope = scope
        self.leverage = leverage
        self.stop_loss = stop_loss
        # self.parent_conn and self.child_conn are now managed by launch_ticker_monitor_process
        self.parent_conn = None # Will be set by start()
        self.process = None
        self.status = "STOPPED"
        self.logs = [] # Detailed logs from child process or formatted messages
        self.stdout_log = [] # Raw stdout from child TickerMonitor process


        self.last_update_ts: Optional[str] = None
        self.display_price: Optional[float] = None
        self.display_position_size: float = 0.0  # Initialize to 0.0 for clearer start
        try:
            # Initialize display_equity with the entry value provided when monitor is added
            self.display_equity: float = float(entry)
        except (ValueError, TypeError):
            self.logs.append(f"[PARENT_WARN] Invalid entry value '{entry}' for initial equity. Defaulting to 0.0")
            self.display_equity: float = 0.0
        self.last_error_message: Optional[str] = None


    def start(self):
        if self.process is None or not self.process.is_alive():
            if launch_ticker_monitor_process is None:
                self.logs.append(f"[PARENT_ERROR] Cannot start {self.ticker}: launch_ticker_monitor_process is not available.")
                self.status = "ERROR"
                self.last_error_message = "Process launcher missing."
                return


            # TUI currently doesn't ask for leverage/stop-loss, so pass defaults.
            # self.entry is used as initial_capital_allocation.
            # Leverage and stop_loss are now passed from Monitor instance
            
            self.process, self.parent_conn = launch_ticker_monitor_process(
                ticker=self.ticker,
                entry_price=float(self.entry), # Ensure entry is float
                scope=self.scope,
                leverage=self.leverage,
                stop_loss=self.stop_loss

            )



            if self.process and self.parent_conn:
                self.status = "RUNNING"
                self.logs.append(f"[PARENT] Started monitor for {self.ticker} entry={self.entry} scope={self.scope} Lev:{self.leverage} SL:{self.stop_loss}")
            else:
                self.logs.append(f"[PARENT_ERROR] Failed to start monitor process for {self.ticker}.")
                self.status = "ERROR"
                self.last_error_message = "Process launch failed."
                
    def stop(self):
        # Send a "stop_request" message if TickerMonitor supports graceful shutdown via pipe.
        # For now, stick to terminate for simplicity as TickerMonitor.stop() is for internal loop flag.
        if self.process and self.process.is_alive():
            try:
                self.process.terminate() # SIGTERM
                self.process.join(timeout=5) # Wait for termination
                if self.process.is_alive(): # Still alive
                    self.logs.append(f"[PARENT_WARN] Process {self.ticker} did not terminate gracefully, killing.")
                    self.process.kill() # SIGKILL                    self.process.join(timeout=2)
            except Exception as e:
                self.logs.append(f"[PARENT_ERROR] Exception during stop: {e}")
            
            self.status = "STOPPED"
            self.logs.append(f"[PARENT] Stopped monitor for {self.ticker}")



    def poll(self):
        updated_state_this_poll = False
        if not self.parent_conn: # If pipe not initialized (e.g. start failed or not called)
            return False

        while self.parent_conn.poll():
            updated_state_this_poll = True
            try:
                raw_msg = self.parent_conn.recv()
            except (EOFError, OSError) as e: # Pipe might have been closed unexpectedly
                self.logs.append(f"[PARENT_ERROR] Error receiving from pipe for {self.ticker}: {e}")
                if self.status == "RUNNING":
                    self.status = "ERROR"
                    self.last_error_message = "Pipe communication failed."
                break # Exit while loop

            log_entry = None # Reset for each message

            # Ensure message is for this monitor instance
            msg_ticker = raw_msg.get("ticker", self.ticker) if isinstance(raw_msg, dict) else self.ticker
            if msg_ticker != self.ticker:
                self.logs.append(f"[PARENT_WARN] Received message for {msg_ticker} on {self.ticker}'s pipe. Ignoring.")
                continue

            # 1. Handle system messages from process_manager (stdout, stderr, worker errors, etc.)
            if isinstance(raw_msg, dict) and "type" in raw_msg:
                mtype = raw_msg["type"]
                data = raw_msg.get("data", "") # Default to empty string for data


                if mtype == "stdout" or mtype == "stderr":
                    log_origin_prefix = "[CHILD_STDOUT]" if mtype == "stdout" else "[CHILD_STDERR]"
                    output_data = str(data).rstrip('\n')
                    self.stdout_log.append(f"{log_origin_prefix} {output_data}") # Add to raw stdout log first
                    log_entry = f"{log_origin_prefix} {output_data}" # For main log panel
                    # Check for critical errors hinted in TickerMonitor's own stdout/stderr
                    if any(err_keyword in output_data.upper() for err_keyword in [
                        "CRITICAL", "EXCEPTION DURING MONITORING CYCLE", "UNHANDLED EXCEPTION",
                        "ERROR [", "FAILED TO LOAD", "GIVING UP", "WORKER_CRITICAL_ERROR",
                        "CRITICAL_WORKER_EXCEPTION" # Errors from canonical_monitor_worker itself
                    ]):
                        if self.status != "ERROR":
                            self.status = "ERROR"
                            self.last_error_message = output_data.split('\n')[0] # Get first line
                elif mtype == "error": # Generic error from canonical_monitor_worker (e.g. unhandled exception)
                    log_entry = f"[CHILD_WORKER_ERROR] {str(data)}"
                    if self.status != "ERROR":
                        self.status = "ERROR"
                        self.last_error_message = str(data).split('\n')[0]
                elif mtype == "indicators_loaded":
                    # Data might contain the indicator configs if needed by TUI, or just be a notification
                    log_entry = f"[PARENT_INFO] Indicator configurations loaded by worker for {self.ticker}."
                    # You could store raw_msg['data'] (the indicator_configs) in self if needed later
                elif mtype == "worker_stopped":
                    log_entry = f"[PARENT_INFO] Worker process for {self.ticker} reported stopped (PID: {raw_msg.get('pid','N/A')})."

                    if self.status == "RUNNING": # If it was supposed to be running and stopped without explicit TUI stop
                        self.status = "ERROR" 
                        self.last_error_message = "Worker stopped unexpectedly."
                    else: # If TUI initiated stop, or it was already stopped/error
                        self.status = "STOPPED" # Ensure it's marked stopped
            

            # 2. Handle messages from TickerMonitor itself (relayed by PipeAsQueue)
            # These are dicts but do NOT have the top-level "type" from process_manager
            elif isinstance(raw_msg, dict) and "action" in raw_msg:
                action = raw_msg.get("action", "UNKNOWN_TM_MSG").upper() # TM_MSG = TickerMonitor Message
                timestamp_str = raw_msg.get("timestamp")
                
                if timestamp_str:
                    self.last_update_ts = timestamp_str

                # Update display price (logic from original code)
                price_from_msg = None
                if action == "INFO": price_from_msg = raw_msg.get("current_market_price")
                elif action in ["BUY", "SELL"] or "pnl_this_trade" in raw_msg or raw_msg.get("asset_value_traded") == 0.0: price_from_msg = raw_msg.get("price")
                if price_from_msg is not None:
                    try: self.display_price = float(price_from_msg)
                    except (ValueError, TypeError): self.logs.append(f"[PARENT_WARN] Invalid price format for TUI: {price_from_msg}")

                # Update display position size (logic from original code)
                new_potential_size = None
                if action == "INFO":
                    if "current_quantity" in raw_msg:
                        try: new_potential_size = float(raw_msg["current_quantity"])
                        except (ValueError, TypeError): self.logs.append(f"[PARENT_WARN] Invalid 'current_quantity' from INFO: {raw_msg.get('current_quantity')}")
                elif action in ["BUY", "SELL"]:
                    if "quantity" in raw_msg:
                        try: new_potential_size = float(raw_msg["quantity"])
                        except (ValueError, TypeError): self.logs.append(f"[PARENT_WARN] Invalid 'quantity' for {action}: {raw_msg.get('quantity')}")
                    if "pnl_this_trade" in raw_msg: # Position closed
                        if new_potential_size is not None and new_potential_size != 0.0:
                             self.logs.append(f"[PARENT_INFO] {action} with PNL. Assuming pos closed, Qty forced to 0.")
                        new_potential_size = 0.0
                elif action == "STOP_LOSS_CLOSE": new_potential_size = 0.0
                
                if new_potential_size is not None and self.display_position_size != new_potential_size:
                    self.logs.append(f"[PARENT_QTY_UPDATE] Act:'{action}'. Qty:{self.display_position_size:.4f} -> {new_potential_size:.4f}.")
                    self.display_position_size = new_potential_size

                # Status updates based on INFO messages (logic from original code)
                if action == "INFO":
                    status_reason = str(raw_msg.get("status_reason", "")).upper()
                    if any(err_keyword in status_reason for err_keyword in ["FAIL", "ERROR", "CRITICAL", "INVALID PRICE", "SKIPPING DECISION", "NO DATA RETURNED", "NO VALID PRICE"]):                        
                        if self.status != "ERROR": self.status = "ERROR"; self.last_error_message = raw_msg.get("status_reason", "Err from INFO")
                

                # Format log entry for [CHILD_MSG] (logic from original code)
                log_parts = []
                if timestamp_str:                    
                    try: log_parts.append(f"TS:{pd.Timestamp(timestamp_str).strftime('%H:%M:%S')}")
                    except: log_parts.append(f"TS:{str(timestamp_str)[:19].replace('T',' ')}") # Fallback
                else: log_parts.append("TS:N/A")
                log_parts.append(f"ACT:{action}")

                if self.display_price is not None: log_parts.append(f"PX:{self.display_price:,.2f}")
                # self.display_position_size is already float, no need to check for None before formatting as it's initialized to 0.0
                log_parts.append(f"QTY:{self.display_position_size:,.4f}")
                
                pnl_val = raw_msg.get("pnl_this_trade")
                if pnl_val is not None:
                    try: log_parts.append(f"PNL:{float(pnl_val):.2f}")
                    except: pass # ignore if not floatable
                

                equity_val = raw_msg.get("equity_after_trade", raw_msg.get("total_equity"))
                if equity_val is not None:
                    try:
                        parsed_equity_val = float(equity_val)
                        if self.display_equity != parsed_equity_val: # Compare against current display_equity
                            self.logs.append(f"[PARENT_EQ_UPDATE] Act:'{action}'. Equity:{self.display_equity:,.2f} -> {parsed_equity_val:,.2f}.")
                            self.display_equity = parsed_equity_val # Update self.display_equity
                        log_parts.append(f"EQ:{self.display_equity:,.2f}") # Log the current self.display_equity
                    except (ValueError, TypeError):
                        self.logs.append(f"[PARENT_WARN] Invalid equity format: {equity_val}")
                        log_parts.append("EQ:ERR_FMT")
                else: # equity_val is None in this TickerMonitor message
                    if self.display_equity is not None: log_parts.append(f"EQ:{self.display_equity:,.2f}")                    
                    else: log_parts.append("EQ:N/A_STATE")
                
                log_entry = f"[CHILD_MSG] {' | '.join(log_parts)}"
                
                actioned_sigs = raw_msg.get("actioned_signals", {})
                if isinstance(actioned_sigs, dict) and actioned_sigs:
                    sigs_parts = []
                    if actioned_sigs.get("stop_loss_triggered"): sigs_parts.append("STOP_LOSS!")
                    for k,v_raw in actioned_sigs.items():
                        if k == "stop_loss_triggered" and v_raw: continue
                        if v_raw is not None:
                            k_short = k.replace('_Signal','').replace('_Indicator','').replace('ATR_','A').replace('MACD_','M').replace('BB_','BB').replace('Breakout_','Brk').replace('SMA_','S').replace('RSI_','R').replace('Volume_','V').replace('_','').replace('CrossAbove','XAbv').replace('CrossBelow','XBlw').replace('Cross','X').replace('Lower','Low').replace('Upper','Up').replace('Bullish','Bull').replace('Bearish','Bear').replace('Oversold','OSold').replace('Overbought','OBought').replace('Spike','Spk')
                            v_str = "T" if isinstance(v_raw, bool) and v_raw else ("F" if isinstance(v_raw, bool) else (f"{v_raw:.1f}" if isinstance(v_raw, (int,float)) else str(v_raw)))
                            sigs_parts.append(f"{k_short}:{v_str[:4]}")
                    if sigs_parts: log_entry += f" | SIGS: {', '.join(sigs_parts)}"
                        # 3. Fallback for any other unhandled or non-dict message types (should be rare with unified worker)
            elif log_entry is None: # If not a system message and not a TickerMonitor action dict
                log_entry = f"[PARENT_UNHANDLED_MSG_TYPE] {type(raw_msg)}: {str(raw_msg)[:200]}"
                # Check for error strings in these rare unhandled messages too
                if isinstance(raw_msg, str) and any(err_keyword in raw_msg.upper() for err_keyword in ["ERROR", "EXCEPTION", "FAIL", "CRITICAL"]):
                    if self.status != "ERROR":
                        self.status = "ERROR"
                        self.last_error_message = raw_msg.split('\n')[0]
            
            # Append the determined log entry
            if log_entry:
                self.logs.append(log_entry)

        # After processing all queued messages, check process status
        if self.status == "RUNNING" and self.process and not self.process.is_alive():
            # This block is entered if the process died without sending a "worker_stopped" or other error message via pipe
            if self.status != "ERROR": # Only update if not already in a more specific error state
                self.status = "ERROR"
                self.last_error_message = "Process terminated unexpectedly."
            self.logs.append(f"[PARENT] Monitor {self.ticker} died unexpectedly.")
            updated_state_this_poll = True

        # Prune logs
        max_logs = 1 
        max_stdout_logs = 2 
        if len(self.logs) > max_logs:
            self.logs = self.logs[-max_logs:]
        if len(self.stdout_log) > max_stdout_logs:
            self.stdout_log = self.stdout_log[-max_stdout_logs:]            
        return updated_state_this_poll

    def cleanup(self):
        self.stop() # Ensure the process is stopped first
        # Close pipes safely
        try:
            if hasattr(self, 'parent_conn') and self.parent_conn and not self.parent_conn.closed:
                self.parent_conn.close()
        except Exception:
            pass # Ignore errors during cleanup

        try:
            # child_conn is no longer an attribute of Monitor; it's local to launch_ticker_monitor_process
            # and closed there after process start.
            pass
        except Exception:
            pass
        # Release process resource if it exists and is still alive (should have been stopped)
        if self.process and self.process.is_alive():            
            try:
                self.process.join(timeout=0.5) # Attempt a brief join
                if self.process.is_alive(): # Still alive after join attempt
                    self.process.kill() # Force kill if terminate+join didn't work

                    self.process.join(timeout=0.5) # Wait for kill
            except Exception:
                pass # If killing fails, not much more can be done
        self.process = None # Clear the process reference

class AddMonitorDialog(urwid.WidgetWrap):
    signals = ["ok", "cancel"]


    def __init__(self):
        self.ticker_edit = urwid.Edit("Ticker: ")
        self.entry_edit = urwid.Edit("Entry Price: ")
        self.scope_edit = urwid.Edit("Scope: ", edit_text="intraday")
        self.leverage_edit = urwid.Edit("Leverage: ", edit_text="1.0")
        self.stop_loss_edit = urwid.Edit("Stop Loss (e.g. 0.05): ", edit_text="0.05")
        ok_btn = urwid.Button("OK", on_press=self._on_ok)
        cancel_btn = urwid.Button("Cancel", on_press=self._on_cancel)
        pile = urwid.Pile([
            self.ticker_edit,
            self.entry_edit,
            self.scope_edit,
            self.leverage_edit,
            self.stop_loss_edit,
            urwid.Columns([ok_btn, cancel_btn])
        ])
        fill = urwid.Filler(pile)
        super().__init__(urwid.LineBox(fill))

    def _on_ok(self, button):
        ticker = self.ticker_edit.edit_text.strip().upper()

        entry = self.entry_edit.edit_text.strip()
        scope = self.scope_edit.edit_text.strip()
        leverage_str = self.leverage_edit.edit_text.strip()
        stop_loss_str = self.stop_loss_edit.edit_text.strip()

        try:
            entry_val = float(entry)
        except ValueError:
            entry_val = 1000.0 # Default entry if invalid
        
        try:
            leverage_val = float(leverage_str)
            if leverage_val <= 0: leverage_val = 1.0 # Ensure positive leverage
        except ValueError:
            leverage_val = 1.0 # Default leverage if invalid
        
        try:
            stop_loss_val = float(stop_loss_str)
            if not (0 < stop_loss_val < 1): # Ensure stop loss is a sensible fraction
                stop_loss_val = 0.05 
        except ValueError:
            stop_loss_val = 0.05 # Default stop loss if invalid

        urwid.emit_signal(self, "ok", self, ticker, entry_val, scope, leverage_val, stop_loss_val)

    def _on_cancel(self, button):
        urwid.emit_signal(self, "cancel", self)

class OutputPopup(urwid.WidgetWrap):
    def __init__(self, lines, on_close):
        walker = urwid.SimpleFocusListWalker([urwid.Text(l) for l in lines] or [urwid.Text("(No output)")])
        listbox = urwid.ListBox(walker)
        close_btn = urwid.Button("Close", on_press=lambda button: on_close())
        pile = urwid.Pile([
            ('weight', 1, listbox),    # <--- Do NOT wrap ListBox in Filler!
            ('pack', close_btn)
        ])
        super().__init__(urwid.LineBox(pile))

class TUI:
    def __init__(self):
        self.monitors = {}
        self.menu = urwid.Text("Q: quit | A: add | S: start | X: stop | D: delete | O: output | Up/Down: select\n")
        self.monitor_listbox = urwid.SimpleFocusListWalker([])
        self.log_box = urwid.Text("")
        self.listbox = urwid.ListBox(self.monitor_listbox)
        self.layout = urwid.Frame(header=self.menu,
                                  body=self.listbox,
                                  footer=urwid.Pile([urwid.Text("Logs:"), self.log_box]))
        self.selected_index = 0
        self.overlay = None
        self.loop = urwid.MainLoop(self.layout, unhandled_input=self.handle_input)
        self.loop.set_alarm_in(1, self.refresh)

    def refresh(self, loop, data):
        for monitor in self.monitors.values():
            monitor.poll()
        self.update_monitors()
        self.loop.set_alarm_in(1, self.refresh)


    def update_monitors(self):
        items = []
        selected_monitor_logs_to_display = []
        keys = list(self.monitors.keys())

        for i, key_val in enumerate(keys): # Renamed key to key_val to avoid conflict with input key
            monitor = self.monitors[key_val]
            marker = ">" if i == self.selected_index else " "
            
            status_display = monitor.status
            if monitor.status == "ERROR":
                error_summary = (monitor.last_error_message or "Unknown Error").split('\n')[0]
                status_display = f"ERROR ({error_summary[:30]}...)" 
            elif monitor.status == "RUNNING" and monitor.process and not monitor.process.is_alive():
                 status_display = "ERROR (Dead)"

            ts_display = "N/A"
            if monitor.last_update_ts:
                try:
                    dt_obj = pd.Timestamp(monitor.last_update_ts)
                    if dt_obj.tzinfo is not None: dt_obj = dt_obj.tz_convert(None)
                    now = pd.Timestamp.now()
                    if dt_obj.date() == now.date(): ts_display = dt_obj.strftime('%H:%M:%S')
                    else: ts_display = dt_obj.strftime('%y%m%d-%H%M')

                except Exception:
                    ts_display = str(monitor.last_update_ts)[:16].replace("T"," ")

            price_display = f"{monitor.display_price:,.2f}" if monitor.display_price is not None else "N/A"
            qty_display = f"{monitor.display_position_size:,.4f}" if monitor.display_position_size is not None else "N/A"
            equity_display = f"{monitor.display_equity:,.2f}" if monitor.display_equity is not None else "N/A"



            # Adjust column widths for better alignment (Equity included, Entry (E:) removed)
            # Ticker:10, Status:22, UpdTime:10, Price:10, Qty:10, Equity:10, Scope:Y
            line = (f"{marker} {monitor.ticker:<10} [{status_display:<22}] "
                    f"Upd: {ts_display:<10} Px: {price_display:<10} Qty: {qty_display:<10} Eq: {equity_display:<10} "
                    f"Scp:{monitor.scope}")
            items.append(urwid.Text(line))

            if i == self.selected_index:
                selected_monitor_logs_to_display = monitor.logs[-15:] # Show last 15 logs for selected

        self.monitor_listbox[:] = items
        
        if selected_monitor_logs_to_display:
            self.log_box.set_text("\n".join(selected_monitor_logs_to_display))
        elif keys and 0 <= self.selected_index < len(keys) and self.monitors[keys[self.selected_index]].last_error_message and not selected_monitor_logs_to_display:
            # If no regular logs but there's a last error message for the selected monitor
            self.log_box.set_text(f"LAST ERROR: {self.monitors[keys[self.selected_index]].last_error_message}")
        elif not keys:
            self.log_box.set_text("(No monitors active)")
        else:
            self.log_box.set_text("(Logs will appear here for the selected monitor)")

    def handle_input(self, key):
        keys = list(self.monitors.keys())
        if self.overlay:
            return
        if key in ('q', 'Q'):
            for monitor in self.monitors.values():
                monitor.cleanup()
            raise urwid.ExitMainLoop()
        elif key in ('down',):
            if keys and self.selected_index < len(keys) - 1:
                self.selected_index += 1
        elif key in ('up',):
            if keys and self.selected_index > 0:
                self.selected_index -= 1
        elif key in ('a', 'A'):
            self.open_add_dialog()
        elif key in ('s', 'S'):
            if keys:
                self.monitors[keys[self.selected_index]].start()
        elif key in ('x', 'X'):
            if keys:
                self.monitors[keys[self.selected_index]].stop()
        elif key in ('d', 'D'):
            if keys:
                key_to_delete = keys[self.selected_index]
                self.monitors[key_to_delete].cleanup()
                del self.monitors[key_to_delete]
                if self.selected_index > 0:
                    self.selected_index -= 1
        elif key in ('o', 'O'):
            self.open_output_popup()
        self.update_monitors()

    def open_add_dialog(self):
        dialog = AddMonitorDialog()
        urwid.connect_signal(dialog, "ok", self.add_monitor)
        urwid.connect_signal(dialog, "cancel", lambda dialog: self.close_dialog())
        self.overlay = urwid.Overlay(dialog, self.layout, 'center', 40, 'middle', 10)
        self.loop.widget = self.overlay

    def close_dialog(self):
        self.loop.widget = self.layout

        self.overlay = None

    def add_monitor(self, dialog, ticker, entry, scope, leverage, stop_loss):
        # Key remains based on ticker, scope, and entry for TUI identification.
        # Leverage and stop_loss are passed to the Monitor instance for backend use.
        key = f"{ticker}-{scope}-{entry}" 
        if key not in self.monitors:
            self.monitors[key] = Monitor(ticker, entry, scope, leverage, stop_loss)
        self.close_dialog()
        self.selected_index = len(self.monitors) - 1
        self.update_monitors()

    def open_output_popup(self):
        keys = list(self.monitors.keys())
        if not keys:
            return
        selected = self.monitors[keys[self.selected_index]]
        popup = OutputPopup(selected.stdout_log, self.close_dialog)
        self.overlay = urwid.Overlay(popup, self.layout, 'center', 80, 'middle', 24)
        self.loop.widget = self.overlay

    def run(self):
        self.update_monitors()
        self.loop.run()

if __name__ == "__main__":
    if "TERMUX_VERSION" in os.environ:
        print("Running in Termux: urwid TUI should work normally.\n")
    TUI().run()
