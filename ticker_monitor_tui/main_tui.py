
import multiprocessing as mp

# mp.set_start_method("fork", force=True) # Moved down

import asyncio
from typing import Optional, Dict
import logging # Added for logging

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log # Added Log
from textual.containers import HorizontalScroll, VerticalScroll # Added VerticalScroll
from textual.binding import Binding
from textual.logging import TextualHandler # Added for Textual logging
from textual.reactive import reactive

from .tui_models import TUIMonitorData, MonitorTUIStatus
from .tui_monitor_manager import TUIMonitorManager, TickerMonitor
from .widgets.monitor_table import MonitorTable
from .widgets.add_monitor_dialog import AddMonitorDialog

class TickerMonitorApp(App):
    CSS_PATH = "main_tui.tcss"
    TITLE = "Ticker Monitor Control Panel"
    BINDINGS = [
        Binding("ctrl+a", "add_monitor", "Add Monitor"),
        Binding("ctrl+s", "start_monitor", "Start Monitor"),
        Binding("ctrl+x", "stop_monitor", "Stop Monitor"),

        Binding("delete", "delete_monitor", "Delete Monitor"),
        Binding("enter", "edit_monitor", "Edit Monitor"),
    ]


    manager: TUIMonitorManager # Explicit type hint for the manager instance
    monitors_data_list = reactive([])    
    selected_monitor: Optional[TUIMonitorData] = None
    logger: Optional[logging.Logger] = None # Added logger attribute

    def compose(self) -> ComposeResult:
        yield Header()
        self.monitor_table_widget = MonitorTable()
        yield self.monitor_table_widget
        
        # New Log widget for application messages
        self.log_widget = Log(highlight=True, auto_scroll=True)
        yield VerticalScroll(self.log_widget, id="log-view-container")
        
        yield Footer()

    async def on_mount(self):
        # Configure logging to use Textual's Log widget

        logging.basicConfig(
            level="INFO", # You can set this to DEBUG for more verbose output            handlers=[TextualHandler()],
            force=True, # Override any existing basicConfig
        )
        self.logger = logging.getLogger(__name__) # Get a logger for this app module
        
        self.manager = TUIMonitorManager(logger=self.logger) # Pass logger to manager
        self.logger.info("Ticker Monitor TUI started. Logging initialized. Use Ctrl+A to add a new monitor.")
        
        if TickerMonitor is None:
            self.logger.warning("TickerMonitor class not found. Ensure stock_monitoring_app is in PYTHONPATH.")
        
        self.refresh_monitor_table_display()
        self.set_interval(5.0, self.refresh_monitor_table_display)

    # Removed log_status method, use self.logger directly

    def refresh_monitor_table_display(self):
        self.monitors_data_list = self.manager.get_all_monitor_data()
        if self.monitor_table_widget:
            self.monitor_table_widget.monitors_data = self.monitors_data_list
        self.update_contextual_bindings()

    def update_contextual_bindings(self):
        # No more self.bindings, use can_<action> methods instead.
        pass

    def can_start_monitor(self):
        return self.selected_monitor and self.selected_monitor.status == MonitorTUIStatus.STOPPED

    def can_stop_monitor(self):
        return self.selected_monitor and self.selected_monitor.status == MonitorTUIStatus.RUNNING

    def can_delete_monitor(self):
        return self.selected_monitor is not None

    def can_edit_monitor(self):
        return self.selected_monitor is not None

    # Example command implementations (add your real logic as needed)
    async def action_add_monitor(self):
        async def show_dialog():
            dialog = AddMonitorDialog()
            config = await self.push_screen_wait(dialog)
            if config:


                try:
                    self.manager.add_monitor_config(config)
                    if self.logger:
                        self.logger.info(f"Added new monitor config for: {config.ticker}")
                    self.refresh_monitor_table_display()
                except ValueError as e:
                    if self.logger:
                        self.logger.error(f"Error adding monitor: {e}")
        self.run_worker(show_dialog(), exclusive=True)

    def start_queue_polling_worker(self, tui_id: str):

        monitor_data = self.manager.get_monitor_data(tui_id)
        queue = self.manager.get_trade_queue_for_monitor(tui_id)
        if not monitor_data or not queue:

            if self.logger:
                self.logger.error(f"No monitor data or queue found for TUI ID {tui_id}.")
            return

        async def poll_queue():
            import queue as pyqueue
            process = getattr(monitor_data, 'process', None)
            if process and process.is_alive():
                monitor_data.status = MonitorTUIStatus.RUNNING
                self.refresh_monitor_table_display()
            while True:
                try:
                    order = queue.get(timeout=1)
                    if order:
                        monitor_data.update_from_trade_order(order)
                        self.refresh_monitor_table_display()

                except pyqueue.Empty:
                    process = getattr(monitor_data, 'process', None)
                    if process and not process.is_alive():
                        # The process is no longer alive.


                        # The TUIMonitorManager's get_all_monitor_data will handle updating
                        # the status to STOPPED or ERROR based on its logic.
                        # We just need to log it here and trigger a refresh.
                        if self.logger:
                            self.logger.warning(f"Process for monitor {monitor_data.ticker} ({monitor_data.tui_id[:8]}) ended.")
                        self.refresh_monitor_table_display() # Trigger manager's status update
                        break # Exit polling loop for this monitor
                    elif not process and monitor_data.status == MonitorTUIStatus.RUNNING:
                        # Process object is gone but status was RUNNING. This indicates an anomaly.
                        if self.logger:
                            self.logger.error(f"Anomaly: Monitor {monitor_data.ticker} ({monitor_data.tui_id[:8]}) status is RUNNING but process object is missing.")
                        self.refresh_monitor_table_display() # Trigger manager's status update
                        break # Exit polling loop

        self.run_worker(poll_queue(), exclusive=False, name=f"queue_poll_{tui_id[:8]}")

    def action_start_monitor(self):


        if self.selected_monitor:
            success = self.manager.start_monitor(self.selected_monitor.tui_id)
            if success:
                if self.logger:
                    self.logger.info(f"Started monitor {self.selected_monitor.ticker}.")
                self.start_queue_polling_worker(self.selected_monitor.tui_id)
            else:
                if self.logger:
                    self.logger.error(f"Failed to start monitor {self.selected_monitor.ticker}.")
            self.refresh_monitor_table_display()
        else:
            if self.logger:
                self.logger.warning("No monitor selected to start.")

    def action_stop_monitor(self):
        if self.selected_monitor:
            success = self.manager.stop_monitor(self.selected_monitor.tui_id)


            if success:
                if self.logger:

                    self.logger.info(f"Stopped monitor {self.selected_monitor.ticker}.")            else:
                if self.logger:
                    self.logger.error(f"Failed to stop monitor {self.selected_monitor.ticker}.")
            self.refresh_monitor_table_display()
        else:
            if self.logger:
                self.logger.warning("No monitor selected to stop.")

    def action_delete_monitor(self):
        if self.selected_monitor:
            success = self.manager.delete_monitor_config(self.selected_monitor.tui_id)
            if success:
                self.logger.info(f"Deleted monitor {self.selected_monitor.ticker}.")
            else:
                self.logger.error(f"Failed to delete monitor {self.selected_monitor.ticker}.")
            self.refresh_monitor_table_display()
        else:
            self.logger.warning("No monitor selected to delete.")

    def action_edit_monitor(self):        self.logger.info("Edit monitor dialog not yet implemented.")


if __name__ == "__main__":


if __name__ == "__main__":
    # Moved mp.set_start_method here to ensure it only runs when script is executed directly
    # and not during static analysis or import time, which might affect type checkers.
    try:
        mp.set_start_method("fork", force=True)
    except RuntimeError:
        # Handles cases where the context might have already been set,
        # e.g., if the module is reloaded in some environments or in tests.
        pass
    app = TickerMonitorApp()
    app.run()
