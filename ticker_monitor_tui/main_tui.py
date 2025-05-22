import multiprocessing as mp
mp.set_start_method("fork", force=True)

import asyncio
from typing import Optional, Dict

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import HorizontalScroll
from textual.binding import Binding
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

    monitors_data_list = reactive([])
    selected_monitor: Optional[TUIMonitorData] = None

    def compose(self) -> ComposeResult:
        yield Header()
        self.monitor_table_widget = MonitorTable()
        yield self.monitor_table_widget
        self.status_log_widget = Static(id="status-log")
        yield HorizontalScroll(self.status_log_widget)
        yield Footer()

    async def on_mount(self):
        self.manager = TUIMonitorManager()
        self.log_status("Use Ctrl+A to add a new monitor.")
        if TickerMonitor is None:
            self.log_status("[bold red]WARNING: TickerMonitor not found. Ensure stock_monitoring_app is in PYTHONPATH.[/bold red]")
        self.refresh_monitor_table_display()
        self.set_interval(5.0, self.refresh_monitor_table_display)

    def log_status(self, message: str):
        self.status_log_widget.update(message)

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
                    self.log_status(f"[green]Added new monitor config for: {config.ticker}[/green]")
                    self.refresh_monitor_table_display()
                except ValueError as e:
                    self.log_status(f"[bold red]Error adding monitor: {e}[/bold red]")
        self.run_worker(show_dialog(), exclusive=True)

    def start_queue_polling_worker(self, tui_id: str):
        monitor_data = self.manager.get_monitor_data(tui_id)
        queue = self.manager.get_trade_queue_for_monitor(tui_id)
        if not monitor_data or not queue:
            self.log_status(f"[bold red]No monitor data or queue found for TUI ID {tui_id}.[/bold red]")
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
                        monitor_data.status = MonitorTUIStatus.STOPPED
                        self.refresh_monitor_table_display()
                        break
        self.run_worker(poll_queue(), exclusive=False)

    def action_start_monitor(self):
        if self.selected_monitor:
            success = self.manager.start_monitor(self.selected_monitor.tui_id)
            if success:
                self.log_status(f"Started monitor {self.selected_monitor.ticker}.")
                self.start_queue_polling_worker(self.selected_monitor.tui_id)
            else:
                self.log_status(f"Failed to start monitor {self.selected_monitor.ticker}.")
            self.refresh_monitor_table_display()
        else:
            self.log_status("No monitor selected.")

    def action_stop_monitor(self):
        if self.selected_monitor:
            success = self.manager.stop_monitor(self.selected_monitor.tui_id)
            if success:
                self.log_status(f"Stopped monitor {self.selected_monitor.ticker}.")
            else:
                self.log_status(f"Failed to stop monitor {self.selected_monitor.ticker}.")
            self.refresh_monitor_table_display()
        else:
            self.log_status("No monitor selected.")

    def action_delete_monitor(self):
        if self.selected_monitor:
            success = self.manager.delete_monitor_config(self.selected_monitor.tui_id)
            if success:
                self.log_status(f"Deleted monitor {self.selected_monitor.ticker}.")
            else:
                self.log_status(f"Failed to delete monitor {self.selected_monitor.ticker}.")
            self.refresh_monitor_table_display()
        else:
            self.log_status("No monitor selected.")

    def action_edit_monitor(self):
        self.log_status("Edit monitor dialog not yet implemented.")

if __name__ == "__main__":
    app = TickerMonitorApp()
    app.run()
