import multiprocessing as mp
import time
import uuid
from typing import Dict, Any, Optional
import logging
from .tui_models import TUIMonitorData, MonitorTUIStatus

try:
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
except ImportError:
    print("FATAL: TickerMonitor class not found. Ensure stock_monitoring_app is in PYTHONPATH.")
    TickerMonitor = None

class TUIMonitorManager:
    def __init__(self, logger=None):
        self.logger = logger
        self.monitors: Dict[str, Any] = {}      # keyed by tui_id
        self.processes: Dict[str, mp.Process] = {}     # keyed by tui_id
        self.pipes: Dict[str, mp.connection.Connection] = {}         # keyed by tui_id

    def add_monitor_config(self, config):
        tui_id = f"{config.ticker}-{uuid.uuid4().hex[:8]}"
        config.tui_id = tui_id
        self.monitors[tui_id] = config
        return tui_id

    def start_monitor(self, tui_id):
        if tui_id in self.processes and self.processes[tui_id].is_alive():
            if self.logger:
                self.logger.warning(f"Monitor process for {tui_id} already running.")
            return False

        config = self.monitors[tui_id]
        parent_conn, child_conn = mp.Pipe()
        self.pipes[tui_id] = parent_conn

        # Extract only primitives for the subprocess
        ticker = config.ticker
        monitor_interval_seconds = getattr(config, "monitor_interval_seconds", 60)
        entry_price = getattr(config, "entry_price", 1000.0)
        process_name = f"Monitor-{tui_id[:8]}"
        backtest_scope = getattr(config, "backtest_scope", "intraday")

        p = mp.Process(
            target=self._run_ticker_monitor_worker,
            args=(ticker, monitor_interval_seconds, child_conn, entry_price, process_name, backtest_scope),
            daemon=True
        )
        p.start()
        self.processes[tui_id] = p
        if self.logger:
            self.logger.info(
                f"Monitor process for {ticker} ({tui_id[:8]}) with PID {p.pid} appears to be running."
            )
        time.sleep(0.3)
        if not p.is_alive():
            if self.logger:
                self.logger.error(f"Failed to start monitor process for {ticker} ({tui_id[:8]}). See logs above.")
            return False
        return True

    @staticmethod
    def _run_ticker_monitor_worker(ticker, monitor_interval_seconds, trade_order_conn, entry_price, process_name, backtest_scope):
        import multiprocessing.queues

        class PipeAsQueue:
            def __init__(self, conn):
                self.conn = conn
            def put(self, item):
                self.conn.send(item)
            def get(self, timeout=None):
                if self.conn.poll(timeout):
                    return self.conn.recv()
                raise multiprocessing.queues.Empty

        try:
            queue_like = PipeAsQueue(trade_order_conn)
            monitor = TickerMonitor(
                ticker,
                monitor_interval_seconds,
                queue_like,
                entry_price,
                process_name=process_name,
                backtest_scope=backtest_scope
            )
            monitor.run()
        except Exception as e:
            print(f"FATAL: Exception in TickerMonitor worker for {ticker} - {e}")

    def get_pipe_for_monitor(self, tui_id):
        return self.pipes.get(tui_id)

    def get_monitor_data(self, tui_id):
        return self.monitors.get(tui_id)

    def get_all_monitor_data(self):
        return list(self.monitors.values())

    def stop_monitor(self, tui_id):
        proc = self.processes.get(tui_id)
        if proc and proc.is_alive():
            proc.terminate()
            proc.join(timeout=2)
            if self.logger:
                self.logger.info(f"Stopped monitor {tui_id}")
            return True
        return False

    def delete_monitor_config(self, tui_id):
        self.stop_monitor(tui_id)
        self.monitors.pop(tui_id, None)
        self.processes.pop(tui_id, None)
        self.pipes.pop(tui_id, None)
        if self.logger:
            self.logger.info(f"Deleted monitor config {tui_id}")
        return True
