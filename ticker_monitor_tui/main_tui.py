import asyncio
from textual.app import App, ComposeResult,CSSPathType
from textual.widgets import Header, Footer, Static, Button, Log, DataTable
from textual.containers import Vertical, HorizontalScroll
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
import queue # For queue.Empty exception

from tui_models import TUIMonitorData, MonitorTUIStatus
from tui_monitor_manager import TUIMonitorManager
from widgets.monitor_table import MonitorTable
from widgets.add_monitor_dialog import AddMonitorDialog

# Attempt to resolve path for TickerMonitor, mainly for ensuring PYTHONPATH is okay during dev
try:
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitorexcept ImportError as e:
    print(f"Could not import TickerMonitor from stock_monitoring_app.monitoring.ticker_monitor: {e}")
    print("Please ensure 'stock_monitoring_app' is in your PYTHONPATH or installed.")
    TickerMonitor = None # This will be checked in TUIMonitorManager

class StatusLog(Log):
    """A simple log widget for status messages."""
    pass

class TickerMonitorApp(App[None]):
    """A TUI application for managing TickerMonitors."""

    TITLE = "Ticker Monitor Control Panel"
    # CSS_PATH = "main_tui.tcss" # Optional: for custom CSS

    BINDINGS = [
        Binding("ctrl+q", "quit_app", "Quit", show=True, priority=True),
        Binding("ctrl+a", "add_monitor_dialog", "Add Monitor", show=True),
        Binding("ctrl+s", "start_selected_monitor", "Start Selected", show=False),
        Binding("ctrl+x", "stop_selected_monitor", "Stop Selected", show=False),
        Binding("delete", "delete_selected_monitor", "Delete Selected", show=False),
        Binding("enter", "toggle_selected_monitor", "Start/Stop Selected", show=False),
    ]

    # Reactive list of monitor data objects
    monitors_data_list = reactive([])

    class MonitorStatusUpdate(Message):
        """Message to signal an update to a monitor's status or data."""
        def __init__(self, tui_id: str, updated_data: TUIMonitorData):
            super().__init__()
            self.tui_id = tui_id
            self.updated_data = updated_data
            
    class UIRefreshRequest(Message):
        """Message to request a general UI refresh for the monitor table."""
        pass


    def __init__(self):
        super().__init__()
        self.manager = TUIMonitorManager()
        self.status_log_widget: Optional[StatusLog] = None
        self.monitor_table_widget: Optional[MonitorTable] = None
        self._queue_poll_workers: Dict[str, asyncio.Task] = {} # {tui_id: Task}

    def compose(self) -> ComposeResult:
        yield Header()
        self.monitor_table_widget = MonitorTable(id="monitor_list_table")
        yield self.monitor_table_widget
        self.status_log_widget = StatusLog(highlight=True, markup=True, max_lines=200, id="status_log")
        yield HorizontalScroll(self.status_log_widget, id="log_container")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.log_status("[bold cyan]Ticker Monitor TUI Started.[/bold cyan]")
        self.log_status("Use Ctrl+A to Add, Enter to Start/Stop, Delete to Remove.")
        if TickerMonitor is None:
            self.log_status("[bold red]ERROR: TickerMonitor class not found. Monitors cannot be started.[/]")
        self.refresh_monitor_table_display()        # Periodically refresh the table for process status updates
        self.set_interval(5.0, self.request_ui_refresh)


    def log_status(self, message: str):
        if self.status_log_widget:
            self.status_log_widget.write_line(message)

    def request_ui_refresh(self):
        """Posts a message to trigger UI refresh from the main thread."""
        self.post_message(TickerMonitorApp.UIRefreshRequest())

    def refresh_monitor_table_display(self):
        """Updates the monitor table with the latest data from the manager."""
        self.monitors_data_list = self.manager.get_all_monitor_data()
        if self.monitor_table_widget:            self.monitor_table_widget.monitors_data = self.monitors_data_list
        self.update_contextual_bindings()

    def update_contextual_bindings(self):
        """Enable/disable bindings based on selected monitor state."""
        selected_row_key = self.monitor_table_widget.cursor_row if self.monitor_table_widget else None
        can_start = False
        can_stop = False        can_delete = False
        can_toggle = False

        if selected_row_key is not None:            monitor_data = self.manager.get_monitor_data(str(selected_row_key))            if monitor_data:
                can_delete = True # Always allow delete attempt
                can_toggle = True                if monitor_data.status == MonitorTUIStatus.STOPPED or \
                   monitor_data.status == MonitorTUIStatus.ERROR or \
                   monitor_data.status == MonitorTUIStatus.UNKNOWN:
                    can_start = True
                elif monitor_data.status == MonitorTUIStatus.RUNNING or \
                     monitor_data.status == MonitorTUIStatus.STARTING: # Allow stopping if starting too
                    can_stop = True
        
        self.bindings["ctrl+s"].show = can_start
        self.bindings["ctrl+x"].show = can_stop
        self.bindings["delete"].show = can_delete
        self.bindings["enter"].show = can_toggle # "Enter" toggles start/stop

    async def on_data_table_row_selected(self, event: DataTable.RowSelected):
        self.update_contextual_bindings()

    async def on_ticker_monitor_app_monitor_status_update(self, message: MonitorStatusUpdate):
        """Handle updates pushed from queue polling workers."""
        # The TUIMonitorData instance in manager is directly updated by the worker.
        # We just need to refresh the view.
        self.refresh_monitor_table_display()
        self.log_status(f"[dim]UI Updated for {message.updated_data.ticker} ({message.tui_id[:8]})[/dim]")
        
    async def on_ticker_monitor_app_ui_refresh_request(self, message: UIRefreshRequest):
        """Handle explicit UI refresh requests."""
        self.refresh_monitor_table_display()


    async def action_add_monitor_dialog(self) -> None:
        """Shows the add monitor dialog."""
        dialog = AddMonitorDialog()
        returned_config = await self.app.push_screen_wait(dialog)        if returned_config:
            try:
                self.manager.add_monitor_config(returned_config)
                self.log_status(f"[green]Added new monitor config for: {returned_config.ticker}[/green]")
                self.refresh_monitor_table_display()
            except ValueError as e:
                self.log_status(f"[bold red]Error adding monitor: {e}[/bold red]")

    def _get_selected_monitor_id(self) -> Optional[str]:
        if self.monitor_table_widget and self.monitor_table_widget.cursor_row is not None:
            return str(self.monitor_table_widget.get_row_key(self.monitor_table_widget.cursor_row))
        self.log_status("[yellow]No monitor selected in the table.[/yellow]")
        return None

    async def action_start_selected_monitor(self) -> None:
        tui_id = self._get_selected_monitor_id()
        if tui_id:
            monitor_data = self.manager.get_monitor_data(tui_id)
            if monitor_data:
                self.log_status(f"Attempting to start monitor: {monitor_data.ticker} ({tui_id[:8]})")
                if self.manager.start_monitor(tui_id):
                    self.log_status(f"[green]Successfully initiated start for {monitor_data.ticker}.[/green]")
                    self.start_queue_polling_worker(tui_id) # Start polling its queue
                else:
                    self.log_status(f"[bold red]Failed to start {monitor_data.ticker}. Check logs.[/bold red]")
                self.refresh_monitor_table_display() # Update status immediately

    async def action_stop_selected_monitor(self) -> None:
        tui_id = self._get_selected_monitor_id()
        if tui_id:
            monitor_data = self.manager.get_monitor_data(tui_id)
            if monitor_data:
                self.log_status(f"Attempting to stop monitor: {monitor_data.ticker} ({tui_id[:8]})")
                if self.manager.stop_monitor(tui_id):
                    self.log_status(f"[green]Successfully stopped {monitor_data.ticker}.[/green]")
                else:
                    self.log_status(f"[bold red]Failed to stop {monitor_data.ticker} gracefully. Check logs.[/bold red]")
                self.stop_queue_polling_worker(tui_id) # Stop polling its queue
                self.refresh_monitor_table_display()

    async def action_delete_selected_monitor(self) -> None:
        tui_id = self._get_selected_monitor_id()
        if tui_id:
            monitor_data = self.manager.get_monitor_data(tui_id) # Get data before deleting
            if monitor_data:                ticker_name = monitor_data.ticker
                if self.manager.delete_monitor_config(tui_id):
                    self.log_status(f"[green]Deleted monitor: {ticker_name} ({tui_id[:8]})[/green]")
                    self.stop_queue_polling_worker(tui_id) # Ensure worker is stopped
                else:
                    self.log_status(f"[bold red]Failed to delete monitor {ticker_name}.[/bold red]")
                self.refresh_monitor_table_display()

    async def action_toggle_selected_monitor(self) -> None:
        tui_id = self._get_selected_monitor_id()
        if tui_id:
            monitor_data = self.manager.get_monitor_data(tui_id)
            if monitor_data:
                if monitor_data.status == MonitorTUIStatus.RUNNING or \
                   monitor_data.status == MonitorTUIStatus.STARTING:
                    await self.action_stop_selected_monitor()
                elif monitor_data.status == MonitorTUIStatus.STOPPED or \
                     monitor_data.status == MonitorTUIStatus.ERROR or \
                     monitor_data.status == MonitorTUIStatus.UNKNOWN:
                    await self.action_start_selected_monitor()
                else: # E.g. STOPPING
                    self.log_status(f"[yellow]Monitor {monitor_data.ticker} is currently {monitor_data.status}. Please wait.[/yellow]")


    def _poll_monitor_queue(self, tui_id: str, monitor_data: TUIMonitorData):
        """Polls a single monitor's queue for trade orders. Runs in a Textual Worker."""
        mp_queue = self.manager.get_trade_queue_for_monitor(tui_id)
        if not mp_queue:
            self.log_status(f"[bold red]Error: No queue found for monitor {monitor_data.ticker} ({tui_id[:8]}) polling worker.[/bold red]")
            return

        self.log_status(f"[dim]Starting queue poller for {monitor_data.ticker} ({tui_id[:8]}).[/dim]")
        try:
            while True: # Loop indefinitely until worker is cancelled
                if self.app._exit: # Check if app is exiting
                    break
                try:                    order = mp_queue.get(block=True, timeout=1.0) # Block with timeout
                    if order:
                        # Update the TUIMonitorData instance directly.
                        # This instance is shared (by reference) with the manager's list.
                        monitor_data.update_from_trade_order(order)
                        # Post a message to the app to trigger UI update from the main thread
                        self.app.post_message(TickerMonitorApp.MonitorStatusUpdate(tui_id, monitor_data))

                except queue.Empty:                    # Timeout, check if process is still alive
                    if monitor_data.process and not monitor_data.process.is_alive():
                        self.log_status(f"[yellow]Process for {monitor_data.ticker} ({tui_id[:8]}) ended. Stopping poller.[/yellow]")
                        monitor_data.status = MonitorTUIStatus.STOPPED # Update status
                        monitor_data.last_error_message = f"Process ended (exitcode {monitor_data.process.exitcode})."
                        self.app.post_message(TickerMonitorApp.MonitorStatusUpdate(tui_id, monitor_data))
                        break # Exit polling loop
                    continue # Continue polling
                except (EOFError, BrokenPipeError) as e: # Queue might be closed                    self.log_status(f"[yellow]Queue error for {monitor_data.ticker} ({tui_id[:8]}): {type(e).__name__}. Stopping poller.[/yellow]")
                    break
                except Exception as e:
                    self.log_status(f"[bold red]Error polling queue for {monitor_data.ticker} ({tui_id[:8]}): {e}[/bold red]")
                    # Consider if we should break or continue after certain errors
                    break # For most errors, stop polling this queue
        finally:
            self.log_status(f"[dim]Queue poller for {monitor_data.ticker} ({tui_id[:8]}) stopped.[/dim]")
            # Ensure worker is removed from tracking if it exits on its own
            if tui_id in self._queue_poll_workers:
                del self._queue_poll_workers[tui_id]
            # Request a final UI update for this monitor
            self.app.post_message(TickerMonitorApp.UIRefreshRequest())


    def start_queue_polling_worker(self, tui_id: str):
        if tui_id in self._queue_poll_workers and not self._queue_poll_workers[tui_id].done():
            self.log_status(f"[yellow]Queue poller for TUI ID {tui_id[:8]} already running.[/yellow]")
            return

        monitor_data = self.manager.get_monitor_data(tui_id)
        if not monitor_data or monitor_data.trade_order_queue is None:
            self.log_status(f"[bold red]Cannot start poller: No monitor data or queue for TUI ID {tui_id[:8]}.[/bold red]")
            return

        # Use self.run_worker for Textual's background task management
        worker = self.run_worker(
            self._poll_monitor_queue(tui_id, monitor_data),
            name=f"QueuePoller-{tui_id[:8]}",
            group=f"monitor_pollers",
            exclusive=False # Allow multiple pollers
        )
        self._queue_poll_workers[tui_id] = worker # Store the asyncio.Task like object

    def stop_queue_polling_worker(self, tui_id: str):
        if tui_id in self._queue_poll_workers:
            worker_task = self._queue_poll_workers.pop(tui_id)
            if worker_task and not worker_task.done():
                try:
                    worker_task.cancel() # Request cancellation
                    self.log_status(f"[dim]Requested cancellation for queue poller {tui_id[:8]}.[/dim]")
                except Exception as e:
                    self.log_status(f"[bold red]Error cancelling queue poller {tui_id[:8]}: {e}[/bold red]")
        else:
            self.log_status(f"[dim]No active queue poller found to stop for TUI ID {tui_id[:8]}.[/dim]")

    async def on_key(self, event: "events.Key") -> None:
        # Pass key events to the table if it's focused, e.g., for navigation
        if self.monitor_table_widget and self.monitor_table_widget.has_focus:
             await self.monitor_table_widget.forward_event(event)


    async def action_quit_app(self) -> None:        self.log_status("[bold cyan]Initiating shutdown...[/bold cyan]")
        # Stop all queue pollers first
        for tui_id in list(self._queue_poll_workers.keys()): # list() for safe iteration
            self.stop_queue_polling_worker(tui_id)
        
        # Allow some time for pollers to acknowledge cancellation if needed
        # This might be too short if workers are blocked on queue.get() with long timeout
        await asyncio.sleep(0.2)


        self.manager.cleanup_all_monitors() # Stop actual TickerMonitor processes
        
        # Wait a moment for processes to terminate
        # This is a best-effort; truly robust cleanup might need more complex IPC or process watching
        await asyncio.sleep(0.5)

        self.log_status("[bold cyan]Exiting Ticker Monitor TUI.[/bold cyan]")
        await super().action_quit()


if __name__ == "__main__":
    # Ensure the current working directory is the project root if running directly
    # This helps with relative paths in TickerMonitor or its dependencies
    # import os
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # project_root_for_tui = os.path.abspath(os.path.join(script_dir, ".."))
    # if os.getcwd() != project_root_for_tui:    #     try:
    #         os.chdir(project_root_for_tui)
    #         print(f"Changed CWD to: {os.getcwd()} for TUI execution.")
    #     except Exception as e_chdir:
    #         print(f"Could not change CWD to {project_root_for_tui}: {e_chdir}")


    app = TickerMonitorApp()
    app.run()
```

This provides a comprehensive starting point for your TUI application.

**Key Next Steps & Considerations:**

1.  **PYTHONPATH and `TickerMonitor` Accessibility:** The most critical step is ensuring that when `main_tui.py` runs, it can import `stock_monitoring_app.monitoring.ticker_monitor.TickerMonitor`. This usually means:
    *   Running `python ticker_monitor_tui/main_tui.py` from the `my-pricer` directory (parent of both `stock_monitoring_app` and `ticker_monitor_tui`).
    *   Or, setting your `PYTHONPATH` environment variable to include the `my-pricer` directory.
    *   Or, structuring your project as an installable package.

2.  **Refine `_run_monitor_process` in `TUIMonitorManager`:**
    *   The current implementation of `_run_monitor_process`