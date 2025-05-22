import multiprocessing as mp
from typing import Dict, Optional, List
from .tui_models import TUIMonitorData, MonitorTUIStatus

try:
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
except ImportError:
    print("FATAL: TickerMonitor class not found. Ensure stock_monitoring_app is in PYTHONPATH.")
    TickerMonitor = None

class TUIMonitorManager:
    def __init__(self):
        self._monitors_data: Dict[str, TUIMonitorData] = {}
        self._processes: Dict[str, mp.Process] = {}
        self._queues: Dict[str, mp.Queue] = {}

    def add_monitor_config(self, config: TUIMonitorData) -> str:
        if config.tui_id in self._monitors_data:
            raise ValueError(f"Monitor with TUI ID {config.tui_id} already exists.")
        self._monitors_data[config.tui_id] = config
        return config.tui_id

    def get_monitor_data(self, tui_id: str) -> Optional[TUIMonitorData]:
        return self._monitors_data.get(tui_id)

    def get_all_monitor_data(self) -> 'List[TUIMonitorData]':
        for tui_id, data in self._monitors_data.items():
            process = self._processes.get(tui_id)
            if process:
                if process.is_alive():
                    if data.status not in [MonitorTUIStatus.RUNNING, MonitorTUIStatus.STARTING, MonitorTUIStatus.STOPPING]:
                        data.status = MonitorTUIStatus.RUNNING
                else:
                    if data.status in [MonitorTUIStatus.RUNNING, MonitorTUIStatus.STOPPING]:
                        data.status = MonitorTUIStatus.STOPPED
                        data.last_error_message = f"Process ended unexpectedly (exitcode {process.exitcode})."
                    elif data.status == MonitorTUIStatus.STARTING:
                        data.status = MonitorTUIStatus.ERROR
                        data.last_error_message = "Process failed to stay alive after start."
            elif data.status == MonitorTUIStatus.RUNNING:
                data.status = MonitorTUIStatus.UNKNOWN
                data.last_error_message = "Process not found but status was RUNNING."
        return list(self._monitors_data.values())

    def start_monitor(self, tui_id: str) -> bool:
        if TickerMonitor is None:
            print("ERROR: TickerMonitor class is not available. Cannot start monitor.")
            monitor_data = self.get_monitor_data(tui_id)
            if monitor_data:
                monitor_data.status = MonitorTUIStatus.ERROR
                monitor_data.last_error_message = "TickerMonitor class not loaded."
            return False

        monitor_data = self.get_monitor_data(tui_id)
        if not monitor_data:
            print(f"ERROR: No monitor data found for TUI ID {tui_id} to start.")
            return False
        if tui_id in self._processes and self._processes[tui_id].is_alive():
            print(f"INFO: Monitor {monitor_data.ticker} ({tui_id[:8]}) is already running.")
            monitor_data.status = MonitorTUIStatus.RUNNING
            return True

        monitor_data.status = MonitorTUIStatus.STARTING
        monitor_data.last_error_message = None

        try:
            trade_queue = mp.Queue()
            self._queues[tui_id] = trade_queue
            monitor_data.trade_order_queue = trade_queue

            def _run_monitor_process(config_dict, q):
                import sys, os
                try:
                    log_path = f"/tmp/monitor_{config_dict.get('ticker', 'unknown')}_{os.getpid()}.log"
                    sys.stdout = open(log_path, "a", buffering=1)
                    sys.stderr = sys.stdout
                    print(f"DEBUG: _run_monitor_process called for {config_dict.get('ticker', 'UNKNOWN')}")
                except Exception as e:
                    print(f"ERROR: Could not open log file: {e}", file=sys.__stderr__)
                try:
                    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor as ActualTickerMonitor
                    monitor_instance = ActualTickerMonitor(
                        ticker=config_dict['ticker'],
                        monitor_interval_seconds=config_dict['monitor_interval_seconds'],
                        trade_order_queue=q,
                        entry_price=config_dict['entry_price'],
                        process_name=config_dict['process_name'],
                        backtest_scope=config_dict['backtest_scope']
                    )
                    monitor_instance.run()
                except Exception as e:
                    print(f"ERROR in TickerMonitor process {config_dict.get('process_name', 'Unknown')}: {e}")
                finally:
                    print(f"INFO: TickerMonitor process {config_dict.get('process_name', 'Unknown')} finished.")

            config_for_process = {
                "ticker": monitor_data.ticker,
                "monitor_interval_seconds": monitor_data.monitor_interval_seconds,
                "entry_price": monitor_data.entry_price,
                "process_name": monitor_data.process_name,
                "backtest_scope": monitor_data.backtest_scope
            }

            print(f"DEBUG: About to start process for {monitor_data.ticker} ({tui_id[:8]})")
            process = mp.Process(
                target=_run_monitor_process,
                args=(config_for_process, trade_queue),
                daemon=True
            )
            process.start()
            print(f"DEBUG: process.start() called for {monitor_data.ticker} ({tui_id[:8]}), PID: {process.pid}")
            self._processes[tui_id] = process
            monitor_data.process = process
            monitor_data.status = MonitorTUIStatus.RUNNING
            print(f"INFO: Started TickerMonitor process for {monitor_data.ticker} ({tui_id[:8]}) with PID {process.pid}.")
            return True
        except Exception as e:
            print(f"ERROR: Failed to start monitor process for {monitor_data.ticker} ({tui_id[:8]}): {e}")
            monitor_data.status = MonitorTUIStatus.ERROR
            monitor_data.last_error_message = str(e)
            if tui_id in self._queues:
                del self._queues[tui_id]
            if tui_id in self._processes:
                del self._processes[tui_id]
            return False

    def stop_monitor(self, tui_id: str, timeout_seconds: int = 5) -> bool:
        monitor_data = self.get_monitor_data(tui_id)
        process = self._processes.get(tui_id)

        if not monitor_data:
            print(f"ERROR: No monitor data found for TUI ID {tui_id} to stop.")
            return False

        if not process or not process.is_alive():
            print(f"INFO: Monitor {monitor_data.ticker} ({tui_id[:8]}) is not running or process not found.")
            monitor_data.status = MonitorTUIStatus.STOPPED
            if tui_id in self._processes:
                del self._processes[tui_id]
            if tui_id in self._queues and self._queues[tui_id] is not None:
                try:
                    self._queues[tui_id].close()
                except Exception as e_q_close:
                    print(f"WARN: Error closing queue for {tui_id}: {e_q_close}")
                del self._queues[tui_id]
            monitor_data.trade_order_queue = None
            monitor_data.process = None
            return True

        monitor_data.status = MonitorTUIStatus.STOPPING
        print(f"INFO: Attempting to stop TickerMonitor process for {monitor_data.ticker} ({tui_id[:8]}) PID {process.pid}...")

        try:
            process.terminate()
            process.join(timeout=timeout_seconds)
            if process.is_alive():
                print(f"WARN: Process for {monitor_data.ticker} did not terminate gracefully. Forcing kill...")
                process.kill()
                process.join(timeout=1)
            exit_code = process.exitcode
            print(f"INFO: Process for {monitor_data.ticker} stopped. Exit code: {exit_code}")
            monitor_data.status = MonitorTUIStatus.STOPPED
            monitor_data.last_error_message = f"Stopped (Exit: {exit_code})" if exit_code is not None else "Stopped (Killed)"
        except Exception as e:
            print(f"ERROR: Exception while stopping monitor {monitor_data.ticker}: {e}")
            monitor_data.status = MonitorTUIStatus.ERROR
            monitor_data.last_error_message = f"Error stopping: {str(e)}"
        finally:
            if tui_id in self._processes:
                del self._processes[tui_id]
            if tui_id in self._queues and self._queues[tui_id] is not None:
                try:
                    self._queues[tui_id].close()
                    while not self._queues[tui_id].empty():
                        self._queues[tui_id].get_nowait()
                except Exception as e_q_final:
                    print(f"WARN: Error finalizing queue for {tui_id} post-stop: {e_q_final}")
                del self._queues[tui_id]
            monitor_data.trade_order_queue = None
            monitor_data.process = None
        return monitor_data.status == MonitorTUIStatus.STOPPED

    def delete_monitor_config(self, tui_id: str) -> bool:
        monitor_data = self.get_monitor_data(tui_id)
        if not monitor_data:
            print(f"WARN: No monitor data found for TUI ID {tui_id} to delete.")
            return False
        if monitor_data.status in [MonitorTUIStatus.RUNNING, MonitorTUIStatus.STARTING, MonitorTUIStatus.STOPPING]:
            print(f"INFO: Monitor {monitor_data.ticker} ({tui_id[:8]}) is active. Stopping before delete.")
            self.stop_monitor(tui_id)
        if tui_id in self._monitors_data:
            del self._monitors_data[tui_id]
            print(f"INFO: Deleted monitor configuration for {monitor_data.ticker} ({tui_id[:8]}).")
            if tui_id in self._processes:
                del self._processes[tui_id]
            if tui_id in self._queues:
                del self._queues[tui_id]
            return True
        return False

    def get_trade_queue_for_monitor(self, tui_id: str) -> Optional[mp.Queue]:
        return self._queues.get(tui_id)

    def cleanup_all_monitors(self):
        print("INFO: Cleaning up all active monitors...")
        for tui_id in list(self._monitors_data.keys()):
            monitor_data = self._monitors_data.get(tui_id)
            if monitor_data and monitor_data.status in [MonitorTUIStatus.RUNNING, MonitorTUIStatus.STOPPING, MonitorTUIStatus.STARTING]:
                print(f"      Stopping {monitor_data.ticker} ({tui_id[:8]})...")
                self.stop_monitor(tui_id, timeout_seconds=2)
        print("INFO: All active monitors stopped (or termination attempted).")
