

import multiprocessing as mp
import time # Added for a small delay to check process status after start
from typing import Dict, Optional, List
import logging # Added for logging
from .tui_models import TUIMonitorData, MonitorTUIStatus

try:
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
except ImportError:
    print("FATAL: TickerMonitor class not found. Ensure stock_monitoring_app is in PYTHONPATH.")

    TickerMonitor = None

class TUIMonitorManager:
    def __init__(self, logger: Optional[logging.Logger] = None):        
        self._monitors_data: Dict[str, TUIMonitorData] = {}
        self._processes: Dict[str, mp.Process] = {}
        self._queues: Dict[str, mp.Queue] = {}
        self.logger = logger if logger else logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers: # Configure a default console handler if no handlers are present

            _handler = logging.StreamHandler()
            # Basic formatter for fallback, TUI handler will use its own
            _formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
            _handler.setFormatter(_formatter)
            self.logger.addHandler(_handler)
            self.logger.setLevel(logging.INFO) # Default level for this fallback logger

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
            self.logger.error("TickerMonitor class is not available. Cannot start monitor.")
            monitor_data = self.get_monitor_data(tui_id)
            if monitor_data:
                monitor_data.status = MonitorTUIStatus.ERROR                
                monitor_data.last_error_message = "TickerMonitor class not loaded."
            return False

        monitor_data = self.get_monitor_data(tui_id)
        if not monitor_data:
            self.logger.error(f"No monitor data found for TUI ID {tui_id} to start.")
            return False
        if tui_id in self._processes and self._processes[tui_id].is_alive():
            self.logger.info(f"Monitor {monitor_data.ticker} ({tui_id[:8]}) is already running.")
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

                # This first try-except is for setting up logging within the child process.
                # Its prints should go to sys.__stderr__ if log file opening fails.
                log_path = f"/tmp/monitor_{config_dict.get('ticker', 'unknown')}_{config_dict.get('process_name', 'pid'+str(os.getpid()))}.log"
                try:
                    sys.stdout = open(log_path, "a", buffering=1)
                    sys.stderr = sys.stdout
                    # This print goes to the child's log file.
                    print(f"DEBUG: Child process log for {config_dict.get('process_name', 'UNKNOWN')} (PID: {os.getpid()}) started. Output to: {log_path}")
                except Exception as e_log_setup:
                    # If log setup fails, print to original stderr of the child process.
                    print(f"CRITICAL_ERROR_CHILD: Could not open log file {log_path}: {e_log_setup}", file=sys.__stderr__)
                    # Optionally, re-raise or exit if logging is critical for the child
                    # For now, we'll let it continue and attempt to run the monitor.

                # This try-except-finally is for the actual monitor logic.
                # Its prints will go to the file log (if setup succeeded) or wherever stdout is now.
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
                    print(f"INFO_CHILD: TickerMonitor instance created for {config_dict.get('process_name')}. Starting run().")
                    monitor_instance.run()
                except ImportError as e_import:
                    print(f"ERROR_CHILD: Failed to import ActualTickerMonitor in process {config_dict.get('process_name', 'Unknown')}: {e_import}")
                except Exception as e_run:
                    print(f"ERROR_CHILD: Exception in TickerMonitor process {config_dict.get('process_name', 'Unknown')}: {e_run}")                
                finally:
                    print(f"INFO_CHILD: TickerMonitor process {config_dict.get('process_name', 'Unknown')} finished.")

            config_for_process = {
                "ticker": monitor_data.ticker,
                "monitor_interval_seconds": monitor_data.monitor_interval_seconds,
                "entry_price": monitor_data.entry_price,
                "process_name": monitor_data.process_name,

                "backtest_scope": monitor_data.backtest_scope
            }

            self.logger.debug(f"About to start process for {monitor_data.ticker} ({tui_id[:8]}) with config: {config_for_process}")
            process = mp.Process(
                target=_run_monitor_process,
                args=(config_for_process, trade_queue),
                daemon=True
            )
            process.start()
            self.logger.debug(f"process.start() called for {monitor_data.ticker} ({tui_id[:8]}), PID: {process.pid if process.pid else 'N/A'}")
            
            # Brief pause and check if process started and is alive
            time.sleep(0.2) # Small delay to allow process to initialize or fail quickly            
            if process.is_alive():
                self._processes[tui_id] = process
                monitor_data.process = process # Store the process object
                monitor_data.status = MonitorTUIStatus.RUNNING
                self.logger.info(f"TickerMonitor process for {monitor_data.ticker} ({tui_id[:8]}) with PID {process.pid} appears to be running.")
                return True
            else:
                # Process died immediately after start
                exit_code = process.exitcode                
                self.logger.error(f"Process for {monitor_data.ticker} ({tui_id[:8]}) failed to start or terminated immediately. Exit code: {exit_code}. Check child process log in /tmp/ for details.")
                monitor_data.status = MonitorTUIStatus.ERROR
                monitor_data.last_error_message = f"Process terminated immediately after start (exitcode {exit_code}). Check /tmp/monitor_{monitor_data.process_name}.log"
                # Clean up queue if created
                if tui_id in self._queues:
                    try:
                        self._queues[tui_id].close()                    
                    except Exception:
                        pass # Ignore errors on close if already problematic
                    del self._queues[tui_id]
                    monitor_data.trade_order_queue = None
                return False

        except Exception as e:
            self.logger.error(f"Failed to start monitor process for {monitor_data.ticker} ({tui_id[:8]}): {e}", exc_info=True)
            monitor_data.status = MonitorTUIStatus.ERROR
            monitor_data.last_error_message = str(e)
            if tui_id in self._queues: # Clean up if queue was created before failure

                try:
                    self._queues[tui_id].close()
                except Exception:
                    pass
                del self._queues[tui_id]            # No need to delete from self._processes as it might not have been added yet or the key is invalid
            return False

        # Fallback return statement to ensure a boolean is always returned,
        # especially if a BaseException (e.g., SystemExit) occurs in the try block.
        return False

    def stop_monitor(self, tui_id: str, timeout_seconds: int = 5) -> bool:
        monitor_data = self.get_monitor_data(tui_id)
        process = self._processes.get(tui_id)

        if not monitor_data:
            self.logger.error(f"No monitor data found for TUI ID {tui_id} to stop.")            
            return False

        if not process or not process.is_alive():
            self.logger.info(f"Monitor {monitor_data.ticker} ({tui_id[:8]}) is not running or process not found.")            
            monitor_data.status = MonitorTUIStatus.STOPPED
            if tui_id in self._processes:
                del self._processes[tui_id]
            if tui_id in self._queues and self._queues.get(tui_id) is not None:
                try:
                    self._queues[tui_id].close()
                except Exception as e_q_close:
                    self.logger.warning(f"Error closing queue for {tui_id} during stop (process not alive): {e_q_close}")
                del self._queues[tui_id]
            monitor_data.trade_order_queue = None
            monitor_data.process = None
            return True

        monitor_data.status = MonitorTUIStatus.STOPPING
        self.logger.info(f"Attempting to stop TickerMonitor process for {monitor_data.ticker} ({tui_id[:8]}) PID {process.pid}...")

        try:
            process.terminate()
            process.join(timeout=timeout_seconds)
            if process.is_alive():
                self.logger.warning(f"Process for {monitor_data.ticker} PID {process.pid} did not terminate gracefully. Forcing kill...")
                process.kill()
                process.join(timeout=1) # Brief wait for kill
            exit_code = process.exitcode            
            self.logger.info(f"Process for {monitor_data.ticker} PID {process.pid} stopped. Exit code: {exit_code}")
            monitor_data.status = MonitorTUIStatus.STOPPED
            monitor_data.last_error_message = f"Stopped (Exit: {exit_code})" if exit_code is not None else "Stopped (Killed)"
        except Exception as e:
            self.logger.error(f"Exception while stopping monitor {monitor_data.ticker}: {e}", exc_info=True)
            monitor_data.status = MonitorTUIStatus.ERROR # Or UNKNOWN if stop state uncertain
            monitor_data.last_error_message = f"Error stopping: {str(e)}"
        finally:
            # Ensure cleanup happens
            if tui_id in self._processes:
                del self._processes[tui_id]
            if tui_id in self._queues and self._queues.get(tui_id) is not None:
                try:
                    # Attempt to drain and close queue
                    q = self._queues[tui_id]
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except Exception: # mp.queues.Empty or other issues
                            break                    
                        q.close()
                    q.join_thread() # Wait for queue feeder threads to finish
                except Exception as e_q_final:
                    self.logger.warning(f"Error finalizing queue for {tui_id} post-stop: {e_q_final}")
                finally: # Ensure deletion even if close/join fails
                    if tui_id in self._queues:
                         del self._queues[tui_id]
            monitor_data.trade_order_queue = None
            monitor_data.process = None # Clear the process attribute on TUIMonitorData
        
        return monitor_data.status == MonitorTUIStatus.STOPPED

    def delete_monitor_config(self, tui_id: str) -> bool:
        monitor_data = self.get_monitor_data(tui_id)
        if not monitor_data:
            self.logger.warning(f"No monitor data found for TUI ID {tui_id} to delete.")
            return False
        
        # Log current status before attempting stop
        self.logger.info(f"Attempting to delete monitor config for {monitor_data.ticker} ({tui_id[:8]}), current status: {monitor_data.status}.")

        if monitor_data.status in [MonitorTUIStatus.RUNNING, MonitorTUIStatus.STARTING, MonitorTUIStatus.STOPPING]:
            self.logger.info(f"Monitor {monitor_data.ticker} ({tui_id[:8]}) is active. Stopping before delete.")
            self.stop_monitor(tui_id) # stop_monitor now handles process/queue cleanup

        if tui_id in self._monitors_data:
            del self._monitors_data[tui_id]
            self.logger.info(f"Deleted monitor configuration for {monitor_data.ticker} ({tui_id[:8]}).")
            # stop_monitor should have cleaned _processes and _queues, but double check just in case
            if tui_id in self._processes:
                self.logger.warning(f"Process for {tui_id} still in _processes after stop; removing.")
                del self._processes[tui_id]
            if tui_id in self._queues:
                self.logger.warning(f"Queue for {tui_id} still in _queues after stop; removing.")
                del self._queues[tui_id]
            return True        
        self.logger.warning(f"Monitor configuration for {tui_id} not found in _monitors_data for deletion, though monitor_data object existed.")
        return False

    def get_trade_queue_for_monitor(self, tui_id: str) -> Optional[mp.Queue]:
        return self._queues.get(tui_id)

    def cleanup_all_monitors(self):
        self.logger.info("Cleaning up all active monitors...")
        # Create a list of tui_ids to iterate over, as stop_monitor can modify _monitors_data
        for tui_id in list(self._monitors_data.keys()): 
            monitor_data = self._monitors_data.get(tui_id) # Re-fetch, might have been deleted
            if monitor_data and monitor_data.status in [MonitorTUIStatus.RUNNING, MonitorTUIStatus.STOPPING, MonitorTUIStatus.STARTING]:
                self.logger.info(f"      Stopping {monitor_data.ticker} ({tui_id[:8]}) during cleanup...")
                self.stop_monitor(tui_id, timeout_seconds=2)        
                self.logger.info("All active monitors stopped (or termination attempted).")
                print(f"      Stopping {monitor_data.ticker} ({tui_id[:8]})...")
                self.stop_monitor(tui_id, timeout_seconds=2)
        print("INFO: All active monitors stopped (or termination attempted).")
