import kivy
kivy.require('2.0.0') # Specify Kivy version compatibility

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

from kivy.uix.popup import Popup
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix.behaviors import FocusBehavior # For selection
from kivy.event import EventDispatcher # Import EventDispatcher
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleboxlayout import RecycleBoxLayout # Alternative
from kivy.uix.recycleview.layout import LayoutSelectionBehavior

import multiprocessing as mp
import sys
import os
import time # For Clock
from typing import Optional, List, Dict # For type hinting, Dict might be needed later
import pandas as pd # For timestamp formatting

# Import from project
try:
    from stock_monitoring_app.utils.process_manager import launch_ticker_monitor_process
except ImportError:
    print("CRITICAL KIVY ERROR: process_manager utility not found. Monitoring will not work.", file=sys.stderr)
    launch_ticker_monitor_process = None

# Setup multiprocessing start method
if sys.platform == "win32":
    if hasattr(mp, 'freeze_support'): # Important for Windows when freezing
        mp.freeze_support()
    mp.set_start_method("spawn", force=True)
elif sys.platform == "darwin":
    mp.set_start_method("spawn", force=True)
else: # Linux and other POSIX

    mp.set_start_method("fork", force=True)


class MonitorController(EventDispatcher): # Use the directly imported EventDispatcher
    # Properties that the UI will bind to or observe
    ticker = StringProperty("")
    entry_price_str = StringProperty("") # Keep as string for direct use from input
    scope = StringProperty("")
    leverage = NumericProperty(1.0)
    stop_loss = NumericProperty(0.05)

    status_text = StringProperty("STOPPED")
    last_update_ts_display = StringProperty("N/A")
    display_price_text = StringProperty("N/A")
    display_qty_text = StringProperty("N/A")
    display_equity_text = StringProperty("N/A")
    
    logs = ListProperty([]) # For selected monitor's log panel
    stdout_log = ListProperty([]) # For 'O' popup
    last_error_message_internal = StringProperty("") # For internal error tracking

    is_running = BooleanProperty(False) # To enable/disable Start/Stop buttons

    def __init__(self, ticker, entry, scope, leverage=1.0, stop_loss=0.05, **kwargs):
        super().__init__(**kwargs)
        self.ticker = ticker
        self.entry_price_str = str(entry) # Store entry as string, convert to float for backend
        self.scope = scope
        self.leverage = leverage
        self.stop_loss = stop_loss
        
        self.parent_conn = None
        self.process = None
        
        self.display_price_internal: Optional[float] = None
        self.display_position_size_internal: float = 0.0
        try:
            self.display_equity_internal: float = float(entry)

        except (ValueError, TypeError):
            self.display_equity_internal: float = 0.0
            self.logs.append(f"[PARENT_WARN] Invalid entry '{entry}' for initial equity. Defaulting to 0.0")
        
        self.last_update_ts_internal: Optional[str] = None
        self._update_display_properties() # Initialize text properties

    def _update_display_properties(self):
        self.status_text = self.status_text # Already a property, updated by start/stop/poll
        
        if self.last_update_ts_internal:
            try:
                dt_obj = pd.Timestamp(self.last_update_ts_internal)
                if dt_obj.tzinfo is not None: dt_obj = dt_obj.tz_convert(None)
                now = pd.Timestamp.now()
                if dt_obj.date() == now.date(): self.last_update_ts_display = dt_obj.strftime('%H:%M:%S')
                else: self.last_update_ts_display = dt_obj.strftime('%y%m%d-%H%M')
            except Exception:
                self.last_update_ts_display = str(self.last_update_ts_internal)[:16].replace("T"," ")
        else:

            self.last_update_ts_display = "N/A"

        self.display_price_text = f"{self.display_price_internal:,.2f}" if self.display_price_internal is not None else "N/A"
        self.display_qty_text = f"{self.display_position_size_internal:,.4f}"
        self.display_equity_text = f"{self.display_equity_internal:,.2f}"
        

    def start(self):
        if self.process is None or not self.process.is_alive(): # Ensure colon is present
            if launch_ticker_monitor_process is None:                self.logs.append(f"[PARENT_ERROR] Cannot start {self.ticker}: launcher missing.")
                self.status_text = "ERROR"
                self.last_error_message_internal = "Process launcher missing."
                return

            self.process, self.parent_conn = launch_ticker_monitor_process(
                ticker=self.ticker,
                entry_price=float(self.entry_price_str),
                scope=self.scope,
                leverage=self.leverage,
                stop_loss=self.stop_loss
            )

            if self.process and self.parent_conn:
                self.status_text = "RUNNING"
                self.is_running = True
                self.logs.append(f"[PARENT] Started monitor for {self.ticker} Lev:{self.leverage} SL:{self.stop_loss}")
            else:
                self.logs.append(f"[PARENT_ERROR] Failed to start process for {self.ticker}.")
                self.status_text = "ERROR"
                self.is_running = False
                self.last_error_message_internal = "Process launch failed."
            self._update_display_properties()


    def stop(self):        if self.process and self.process.is_alive():
            try:
                self.process.terminate()
                self.process.join(timeout=5)
                if self.process.is_alive():
                    self.logs.append(f"[PARENT_WARN] Process {self.ticker} force killed.")
                    self.process.kill()
                    self.process.join(timeout=2)
            except Exception as e:
                self.logs.append(f"[PARENT_ERROR] Exception during stop: {e}")
        
        self.status_text = "STOPPED"
        self.is_running = False
        self.logs.append(f"[PARENT] Stopped monitor for {self.ticker}")
        self._update_display_properties()    def poll(self):
        if not self.parent_conn:
            return False
        
        updated_state_this_poll = False
        while self.parent_conn.poll():
            updated_state_this_poll = True
            try:
                raw_msg = self.parent_conn.recv()
            except (EOFError, OSError) as e:
                self.logs.append(f"[PARENT_ERROR] Pipe error for {self.ticker}: {e}")
                if self.status_text == "RUNNING":
                    self.status_text = "ERROR"
                    self.last_error_message_internal = "Pipe communication failed."
                self.is_running = False
                break

            log_entry = None
            msg_ticker = raw_msg.get("ticker", self.ticker) if isinstance(raw_msg, dict) else self.ticker
            if msg_ticker != self.ticker:
                self.logs.append(f"[PARENT_WARN] Msg for {msg_ticker} on {self.ticker} pipe. Ignored.")
                continue

            if isinstance(raw_msg, dict) and "type" in raw_msg:
                mtype = raw_msg["type"]
                data = raw_msg.get("data", "")
                if mtype == "stdout" or mtype == "stderr":

                    prefix = "[CHILD_STDOUT]" if mtype == "stdout" else "[CHILD_STDERR]"
                    output_data = str(data).rstrip('\n')                    self.stdout_log.append(f"{prefix} {output_data}")
                    log_entry = f"{prefix} {output_data}"
                    if any(kw in output_data.upper() for kw in ["CRITICAL", "EXCEPTION", "ERROR [", "FAILED", "GIVING UP"]):
                        if self.status_text != "ERROR":
                            self.status_text = "ERROR"
                            self.last_error_message_internal = output_data.split('\n')[0]
                elif mtype == "error":
                    log_entry = f"[CHILD_WORKER_ERROR] {str(data)}"
                    if self.status_text != "ERROR":
                        self.status_text = "ERROR"
                        self.last_error_message_internal = str(data).split('\n')[0]
                elif mtype == "indicators_loaded":
                    log_entry = f"[PARENT_INFO] Indicators loaded for {self.ticker}."
                elif mtype == "worker_stopped":
                    log_entry = f"[PARENT_INFO] Worker for {self.ticker} stopped (PID: {raw_msg.get('pid','N/A')})."
                    if self.status_text == "RUNNING":
                        self.status_text = "ERROR"
                        self.last_error_message_internal = "Worker stopped unexpectedly."
                    else:
                        self.status_text = "STOPPED"
                    self.is_running = False # Worker has stopped, so it's not running
            
            elif isinstance(raw_msg, dict) and "action" in raw_msg:
                action = raw_msg.get("action", "UNKNOWN_TM_MSG").upper()
                self.last_update_ts_internal = raw_msg.get("timestamp")

                if action == "INFO": price_from_msg = raw_msg.get("current_market_price")
                elif action in ["BUY", "SELL"] or "pnl_this_trade" in raw_msg or raw_msg.get("asset_value_traded") == 0.0: price_from_msg = raw_msg.get("price")
                else: price_from_msg = None
                if price_from_msg is not None:
                    try: self.display_price_internal = float(price_from_msg)
                    except: pass

                new_potential_size = None
                if action == "INFO":
                    if "current_quantity" in raw_msg:
                        try: new_potential_size = float(raw_msg["current_quantity"])
                        except: pass
                elif action in ["BUY", "SELL"]:
                    if "quantity" in raw_msg:
                        try: new_potential_size = float(raw_msg["quantity"])
                        except: pass
                    if "pnl_this_trade" in raw_msg: new_potential_size = 0.0
                elif action == "STOP_LOSS_CLOSE": new_potential_size = 0.0
                
                if new_potential_size is not None: self.display_position_size_internal = new_potential_size


                if action == "INFO":
                    status_reason = str(raw_msg.get("status_reason", "")).upper()
                    if any(kw in status_reason for kw in ["FAIL", "ERROR", "CRITICAL", "INVALID"]):
                        if self.status_text != "ERROR":
                            self.status_text = "ERROR"
                            self.last_error_message_internal = raw_msg.get("status_reason", "Err from INFO")

                log_parts = [f"TS:{pd.Timestamp(self.last_update_ts_internal).strftime('%H:%M:%S') if self.last_update_ts_internal else 'N/A'}", f"ACT:{action}"]
                if self.display_price_internal is not None: log_parts.append(f"PX:{self.display_price_internal:,.2f}")
                log_parts.append(f"QTY:{self.display_position_size_internal:,.4f}")
                if raw_msg.get("pnl_this_trade") is not None: log_parts.append(f"PNL:{float(raw_msg.get('pnl_this_trade')):.2f}")
                
                equity_val = raw_msg.get("equity_after_trade", raw_msg.get("total_equity"))
                if equity_val is not None:
                    try: self.display_equity_internal = float(equity_val)
                    except: pass
                log_parts.append(f"EQ:{self.display_equity_internal:,.2f}")
                log_entry = f"[CHILD_MSG] {' | '.join(log_parts)}"
                # SIGS part ommitted for brevity, can be added if needed
            
            elif log_entry is None:                log_entry = f"[PARENT_UNHANDLED_MSG] {str(raw_msg)[:100]}"            if log_entry: self.logs.append(log_entry)
            self.logs = self.logs[-100:] # Prune main logs
            self.stdout_log = self.stdout_log[-200:] # Prune stdout logs


        if self.status_text == "RUNNING" and self.process and not self.process.is_alive():
            if self.status_text != "ERROR":
                self.status_text = "ERROR"
                self.last_error_message_internal = "Process terminated unexpectedly."
            self.logs.append(f"[PARENT] Monitor {self.ticker} died.")
            self.is_running = False
            updated_state_this_poll = True
        
        if updated_state_this_poll:
            self._update_display_properties()
        return updated_state_this_poll

    def cleanup(self):
        self.stop()
        try:
            if self.parent_conn and not self.parent_conn.closed: self.parent_conn.close()
        except: pass
        if self.process and self.process.is_alive():
            try:
                self.process.join(timeout=0.1); self.process.kill(); self.process.join(timeout=0.1)
            except: pass
        self.process = None

class MonitorWidget(BoxLayout):
    monitor_controller = ObjectProperty(None)

    def __init__(self, monitor_controller: MonitorController, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height='120dp', spacing=2, padding=5, **kwargs)
        self.monitor_controller = monitor_controller

        # Bind widget properties to controller properties
        self.monitor_controller.bind(
            ticker=self.update_ticker_label,
            status_text=self.update_status_label,
            last_update_ts_display=self.update_ts_label,
            display_price_text=self.update_price_label,
            display_qty_text=self.update_qty_label,
            display_equity_text=self.update_equity_label,
            scope=self.update_scope_label,
            is_running=self.update_button_state
        )

        # Top row: Ticker, Status, Scope
        top_row = BoxLayout(orientation='horizontal', size_hint_y=0.3)
        self.ticker_label = Label(text=f"Ticker: {monitor_controller.ticker}", size_hint_x=0.3, halign='left', valign='middle')
        self.ticker_label.bind(size=self.ticker_label.setter('text_size'))
        self.status_label = Label(text=f"Status: {monitor_controller.status_text}", size_hint_x=0.4, halign='left', valign='middle')
        self.status_label.bind(size=self.status_label.setter('text_size'))
        self.scope_label = Label(text=f"Scope: {monitor_controller.scope}", size_hint_x=0.3, halign='left', valign='middle')        self.scope_label.bind(size=self.scope_label.setter('text_size'))        top_row.add_widget(self.ticker_label)
        top_row.add_widget(self.status_label)
        top_row.add_widget(self.scope_label)
        self.add_widget(top_row)

        # Middle row: Upd, Px, Qty, Eq
        mid_row = BoxLayout(orientation='horizontal', size_hint_y=0.3)
        self.ts_label = Label(text=f"Upd: {monitor_controller.last_update_ts_display}", halign='left', valign='middle')
        self.ts_label.bind(size=self.ts_label.setter('text_size'))
        self.price_label = Label(text=f"Px: {monitor_controller.display_price_text}", halign='left', valign='middle')
        self.price_label.bind(size=self.price_label.setter('text_size'))
        self.qty_label = Label(text=f"Qty: {monitor_controller.display_qty_text}", halign='left', valign='middle')
        self.qty_label.bind(size=self.qty_label.setter('text_size'))
        self.equity_label = Label(text=f"Eq: {monitor_controller.display_equity_text}", halign='left', valign='middle')
        self.equity_label.bind(size=self.equity_label.setter('text_size'))
        mid_row.add_widget(self.ts_label)
        mid_row.add_widget(self.price_label)
        mid_row.add_widget(self.qty_label)
        mid_row.add_widget(self.equity_label)
        self.add_widget(mid_row)

        # Bottom row: Buttons
        button_row = BoxLayout(orientation='horizontal', size_hint_y=0.4, spacing=10)
        self.start_button = Button(text="Start", on_press=self.start_monitor, disabled=monitor_controller.is_running)
        self.stop_button = Button(text="Stop", on_press=self.stop_monitor, disabled=not monitor_controller.is_running)
        self.output_button = Button(text="Output", on_press=self.show_output)        self.delete_button = Button(text="Delete", on_press=self.delete_monitor)        button_row.add_widget(self.start_button)
        button_row.add_widget(self.stop_button)
        button_row.add_widget(self.output_button)        button_row.add_widget(self.delete_button)
        self.add_widget(button_row)

        # Initial update
        self.update_ticker_label()
        self.update_status_label()
        self.update_ts_label()
        self.update_price_label()
        self.update_qty_label()
        self.update_equity_label()

        self.update_scope_label()
        self.update_button_state() # Initial button state

    def update_ticker_label(self, *args): self.ticker_label.text = f"Ticker: {self.monitor_controller.ticker}"
    def update_status_label(self, *args): 
        status = self.monitor_controller.status_text
        if status == "ERROR" and self.monitor_controller.last_error_message_internal:            error_summary = self.monitor_controller.last_error_message_internal.split('\n')[0][:30]
            self.status_label.text = f"Status: ERROR ({error_summary}...)"
        elif status == "RUNNING" and self.monitor_controller.process and not self.monitor_controller.process.is_alive():
            self.status_label.text = "Status: ERROR (Dead)"
        else:
            self.status_label.text = f"Status: {status}"

    def update_ts_label(self, *args): self.ts_label.text = f"Upd: {self.monitor_controller.last_update_ts_display}"

    def update_price_label(self, *args): self.price_label.text = f"Px: {self.monitor_controller.display_price_text}"
    def update_qty_label(self, *args): self.qty_label.text = f"Qty: {self.monitor_controller.display_qty_text}"
    def update_equity_label(self, *args): self.equity_label.text = f"Eq: {self.monitor_controller.display_equity_text}"
    def update_scope_label(self, *args): self.scope_label.text = f"Scope: {self.monitor_controller.scope}"
    
    def update_button_state(self, *args):
        self.start_button.disabled = self.monitor_controller.is_running
        self.stop_button.disabled = not self.monitor_controller.is_running    def start_monitor(self, instance):
        self.monitor_controller.start()

    def stop_monitor(self, instance):
        self.monitor_controller.stop()

    def show_output(self, instance):
        # This will be handled by the main app, which knows about popups
        App.get_running_app().open_output_popup_for_monitor(self.monitor_controller)

    def delete_monitor(self, instance):
        # This will be handled by the main app
        App.get_running_app().delete_monitor_controller(self.monitor_controller)

class AddMonitorDialogKivy(Popup):
    def __init__(self, on_ok_callback, **kwargs):
        super().__init__(title="Add New Monitor", size_hint=(0.8, 0.7), **kwargs)
        self.on_ok_callback = on_ok_callback

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        self.ticker_input = TextInput(hint_text="Ticker (e.g., BTC-USD)", multiline=False)
        self.entry_input = TextInput(hint_text="Entry Price (e.g., 1000.0)", input_filter='float', multiline=False)
        self.scope_input = TextInput(hint_text="Scope (e.g., intraday)", text="intraday", multiline=False)
        self.leverage_input = TextInput(hint_text="Leverage (e.g., 1.0)", text="1.0", input_filter='float', multiline=False)
        self.stop_loss_input = TextInput(hint_text="Stop Loss (e.g., 0.05)", text="0.05", input_filter='float', multiline=False)

        content.add_widget(Label(text="Ticker:"))
        content.add_widget(self.ticker_input)
        content.add_widget(Label(text="Entry Price (Initial Capital):"))
        content.add_widget(self.entry_input)
        content.add_widget(Label(text="Scope:"))
        content.add_widget(self.scope_input)
        content.add_widget(Label(text="Leverage:"))
        content.add_widget(self.leverage_input)
        content.add_widget(Label(text="Stop Loss (as decimal, e.g., 0.05 for 5%):"))
        content.add_widget(self.stop_loss_input)

        buttons = BoxLayout(size_hint_y=None, height='50dp', spacing=10)
        ok_button = Button(text="OK", on_press=self.on_ok)
        cancel_button = Button(text="Cancel", on_press=self.dismiss)
        buttons.add_widget(ok_button)
        buttons.add_widget(cancel_button)
        content.add_widget(buttons)
        self.content = content

    def on_ok(self, instance):
        ticker = self.ticker_input.text.strip().upper()
        entry_str = self.entry_input.text.strip()
        scope = self.scope_input.text.strip()
        leverage_str = self.leverage_input.text.strip()
        stop_loss_str = self.stop_loss_input.text.strip()

        if not ticker: # Basic validation            # Could show an error label in the popup
            return 

        try: entry_val = float(entry_str)
        except ValueError: entry_val = 1000.0
        
        try: leverage_val = float(leverage_str)
        except ValueError: leverage_val = 1.0
        if leverage_val <= 0: leverage_val = 1.0
        
        try: stop_loss_val = float(stop_loss_str)
        except ValueError: stop_loss_val = 0.05
        if not (0 < stop_loss_val < 1): stop_loss_val = 0.05
        
        self.on_ok_callback(ticker, entry_val, scope, leverage_val, stop_loss_val)
        self.dismiss()

class OutputLogPopupKivy(Popup):
    log_content = StringProperty("")
    def __init__(self, title="Output Log", log_lines=None, **kwargs):
        super().__init__(title=title, size_hint=(0.9, 0.8), **kwargs)
        if log_lines is None: log_lines = []
                self.log_content = "\n".join(log_lines)

        layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
        scroll_view = ScrollView()
        self.log_label = Label(text=self.log_content, size_hint_y=None, halign='left', valign='top')
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll_view.add_widget(self.log_label)
        layout.add_widget(scroll_view)
        
        close_button = Button(text="Close", size_hint_y=None, height='40dp', on_press=self.dismiss)
        layout.add_widget(close_button)
        self.content = layout

    def update_logs(self, new_log_lines):
        self.log_content = "\n".join(new_log_lines)
        self.log_label.text = self.log_content

class TickerMonitorKivyApp(App):
    selected_monitor_controller = ObjectProperty(None, allownone=True)

    def build(self):
        self.title = "Ticker Monitor Kivy"
        self.monitor_controllers: Dict[str, MonitorController] = {} # Store by unique key
        self.monitor_widgets_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.monitor_widgets_layout.bind(minimum_height=self.monitor_widgets_layout.setter('height'))

        # Main layout
        root = BoxLayout(orientation='vertical', spacing=5, padding=5)

        # Top controls
        top_controls = BoxLayout(size_hint_y=None, height='50dp', spacing=10)
        add_button = Button(text="Add Monitor", on_press=self.open_add_dialog)
        quit_button = Button(text="Quit", on_press=self.stop_app)
        top_controls.add_widget(add_button)
        top_controls.add_widget(Label()) # Spacer
        top_controls.add_widget(quit_button)
        root.add_widget(top_controls)

        # Monitor list area (ScrollView for MonitorWidgets)
        scroll_view_monitors = ScrollView(size_hint=(1, 0.6)) # 60% of vertical space
        scroll_view_monitors.add_widget(self.monitor_widgets_layout)
        root.add_widget(scroll_view_monitors)

        # Log display area for selected monitor
        root.add_widget(Label(text="Selected Monitor Logs:", size_hint_y=None, height='30dp'))        self.selected_monitor_log_label = Label(text="(No monitor selected)", size_hint_y=0.4, halign='left', valign='top')
        self.selected_monitor_log_label.bind(size=self.selected_monitor_log_label.setter('text_size'))
        log_scroll = ScrollView()
        log_scroll.add_widget(self.selected_monitor_log_label)
        root.add_widget(log_scroll)

        Clock.schedule_interval(self.refresh_all_monitors, 1.0) # Refresh every 1 second
        self.bind(selected_monitor_controller=self.update_selected_log_display)
        return root

    def refresh_all_monitors(self, dt):
        for controller in self.monitor_controllers.values():
            if controller.process and controller.process.is_alive(): # Only poll if supposed to be running
                 controller.poll()
            elif controller.status_text == "RUNNING" and (not controller.process or not controller.process.is_alive()):
                # Process died without proper worker_stopped message
                if controller.status_text != "ERROR":
                    controller.status_text = "ERROR"
                    controller.last_error_message_internal = "Process died unexpectedly (Kivy Poll)."
                controller.is_running = False
                controller.logs.append(f"[PARENT] Kivy: Monitor {controller.ticker} process died.")
                controller._update_display_properties() # Ensure UI reflects this state change
        
        # Update the selected monitor's log display if it's the one that changed
        if self.selected_monitor_controller:
            self.update_selected_log_display()


    def update_selected_log_display(self, *args):
        if self.selected_monitor_controller:            self.selected_monitor_log_label.text = "\n".join(self.selected_monitor_controller.logs[-15:])
        else:
            self.selected_monitor_log_label.text = "(No monitor selected or logs unavailable)"


    def add_new_monitor_controller(self, ticker, entry, scope, leverage, stop_loss):
        key = f"{ticker}-{scope}-{entry}" # Simple key for now        if key in self.monitor_controllers:
            # Optionally show a popup that monitor already exists
            return        controller = MonitorController(ticker, entry, scope, leverage, stop_loss)
        self.monitor_controllers[key] = controller
        
        widget = MonitorWidget(monitor_controller=controller)
        # Store a reference to the widget on the controller for easy removal
        controller.ui_widget = widget 
        self.monitor_widgets_layout.add_widget(widget)
        
        # Auto-select the newly added monitor
        self.select_monitor_controller(controller)

    def delete_monitor_controller(self, controller_to_delete: MonitorController):        key_to_delete = None
        for key, controller in self.monitor_controllers.items():
            if controller == controller_to_delete:
                key_to_delete = key
                break
        
        if key_to_delete:
            controller_to_delete.cleanup()
            if hasattr(controller_to_delete, 'ui_widget') and controller_to_delete.ui_widget.parent:
                self.monitor_widgets_layout.remove_widget(controller_to_delete.ui_widget)
            del self.monitor_controllers[key_to_delete]

            if self.selected_monitor_controller == controller_to_delete:
                self.select_monitor_controller(None) # Deselect
            # Optionally, select the previous or next monitor    
    def select_monitor_controller(self, controller: Optional[MonitorController]):
        # This method is more for explicitly setting the selected monitor
        # Actual selection might be handled by touch events on MonitorWidgets in a full app        self.selected_monitor_controller = controller
        self.update_selected_log_display()


    def open_add_dialog(self, instance):
        dialog = AddMonitorDialogKivy(on_ok_callback=self.add_new_monitor_controller)
        dialog.open()

    def open_output_popup_for_monitor(self, monitor_controller: MonitorController):
        popup = OutputLogPopupKivy(title=f"Output Log: {monitor_controller.ticker}", log_lines=monitor_controller.stdout_log)
        popup.open()

    def stop_app(self, instance=None): # instance arg for button press
        for controller in self.monitor_controllers.values():
            controller.cleanup()
        App.get_running_app().stop()

if __name__ == '__main__':
    # Ensure an instance of the App is created before setting mp start method on Windows.
    # mp.set_start_method is global and should ideally be at the very top if possible,
    # but for Kivy's `if __name__ == '__main__'` structure, this is a common pattern.
    # The earlier global scope setting for mp.set_start_method is generally preferred.
    if sys.platform == "win32" and hasattr(mp, 'freeze_support'):
         mp.freeze_support() # Call freeze_support at the beginning of main for Windows

    TickerMonitorKivyApp().run()