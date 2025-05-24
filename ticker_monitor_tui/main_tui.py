import multiprocessing as mp

import asyncio
from typing import Optional
import logging

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Log
from textual.containers import HorizontalScroll, VerticalScroll
from textual.binding import Binding
from textual.reactive import reactive

from .tui_models import TUIMonitorData, MonitorTUIStatus
from .tui_monitor_manager import TUIMonitorManager
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

    manager: TUIMonitorManager
    monitors_data_list = reactive([])
    selected_monitor: Optional[TUIMonitorData] = None
    logger: Optional[logging.Logger] = None

    def compose(self) -> ComposeResult:
        yield Header()
        self.monitor_table_widget = MonitorTable()
        yield HorizontalScroll(self.monitor_table_widget)
        self.log_widget = Log(highlight=True, auto_scroll=True)
        yield VerticalScroll(self.log_widget, id="log-view-container")
        yield Footer()

    async def on_mount(self):
        logging.basicConfig(
            level=logging.INFO,
            filename="ticker_monitor_tui.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger("ticker_monitor_tui")
        self.logger.info("File logger setup complete and logging to ticker_monitor_tui.log.")

        self.manager = TUIMonitorManager(logger=self.logger)
        self.logger.info("Ticker Monitor TUI started. Logging initialized. Use Ctrl+A to add a new monitor.")

        self.refresh_monitor_table_display()
        self.set_interval(5.0, self.refresh_monitor_table_display)

    def refresh_monitor_table_display(self):
        self.monitors_data_list = self.manager.get_all_monitor_data()
        if self.monitor_table_widget:
            self.monitor_table_widget.monitors_data = self.monitors_data_list
        self.update_contextual_bindings()

    def update_contextual_bindings(self):
        pass

    def can_start_monitor(self):
        return self.selected_monitor and self.selected_monitor.status == MonitorTUIStatus.STOPPED

    def can_stop_monitor(self):
        return self.selected_monitor and self.selected_monitor.status == MonitorTUIStatus.RUNNING

    def can_delete_monitor(self):
        return self.selected_monitor is not None

    def can_edit_monitor(self):
        return self.selected_monitor is not None

    async def action_add_monitor(self):
        async def show_dialog():
            dialog = AddMonitorDialog()
            config = await self.push_screen_wait(dialog)
            if config:
                try:
                    tui_id = self.manager.add_monitor_config(config)
                    if self.logger:
                        self.logger.info(f"Added new monitor config for: {config.ticker}")
                    self.refresh_monitor_table_display()
                    if tui_id:
                        started = self.manager.start_monitor(tui_id)
                        if started:
                            self.logger.info(f"Automatically started monitor for: {config.ticker}")
                            self.start_pipe_polling_worker(tui_id)
                        else:
                            self.logger.error(f"Failed to automatically start monitor for: {config.ticker}")
                        self.refresh_monitor_table_display()
                except ValueError as e:
                    if self.logger:
                        self.logger.error(f"Error adding monitor: {e}")
        self.run_worker(show_dialog(), exclusive=True)

    def start_pipe_polling_worker(self, tui_id: str):
        monitor_data = self.manager.get_monitor_data(tui_id)
        parent_conn = self.manager.get_pipe_for_monitor(tui_id)
        if not monitor_data or not parent_conn:
            if self.logger:
                self.logger.error(f"No monitor data or pipe found for TUI ID {tui_id}.")
            return

        async def poll_pipe():
            proc = self.manager.processes.get(tui_id)
            if proc and proc.is_alive():
                monitor_data.status = MonitorTUIStatus.RUNNING
                self.refresh_monitor_table_display()
            while True:
                try:
                    has_msg = await asyncio.to_thread(parent_conn.poll, 1)
                    if has_msg:
                        order = await asyncio.to_thread(parent_conn.recv)
                        # Update monitor_data with order info as appropriate for your models
                        monitor_data.update_from_trade_order(order)
                        self.refresh_monitor_table_display()
                except EOFError:
                    if self.logger:
                        self.logger.warning(f"Pipe closed for monitor {getattr(monitor_data, 'ticker', tui_id)} ({tui_id[:8]}).")
                    break
                if proc and not proc.is_alive():
                    if self.logger:
                        self.logger.warning(f"Process for monitor {getattr(monitor_data, 'ticker', tui_id)} ({tui_id[:8]}) ended.")
                    self.refresh_monitor_table_display()
                    break

        self.run_worker(poll_pipe(), exclusive=False, name=f"pipe_poll_{tui_id[:8]}")

    def action_start_monitor(self):
        if self.selected_monitor:
            success = self.manager.start_monitor(self.selected_monitor.tui_id)
            if success:
                if self.logger:
                    self.logger.info(f"Started monitor {self.selected_monitor.ticker}.")
                self.start_pipe_polling_worker(self.selected_monitor.tui_id)
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
                    self.logger.info(f"Stopped monitor {self.selected_monitor.ticker}.")
            else:
                if self.logger:
                    self.logger.error(f"Failed to stop monitor {self.selected_monitor.ticker}.")
            self.refresh_monitor_table_display()
        else:
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

    def action_edit_monitor(self):
        self.logger.info("Edit monitor dialog not yet implemented.")

if __name__ == "__main__":
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass
    app = TickerMonitorApp()
    app.run()
