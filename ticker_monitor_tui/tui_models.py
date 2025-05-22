import uuid
from dataclasses import dataclass, field
from typing import Optional
from multiprocessing import Process, Queue as MpQueue
from datetime import datetime

try:
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor, BACKTEST_SCOPE_PRESETS
except ImportError:
    print("WARNING: TickerMonitor not found. Ensure stock_monitoring_app is in PYTHONPATH.")
    TickerMonitor = None
    BACKTEST_SCOPE_PRESETS = {"intraday": {}, "short": {}, "long": {}}

class MonitorTUIStatus:
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    STARTING = "STARTING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

@dataclass
class TUIMonitorData:
    tui_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = "BTC-USD"
    monitor_interval_seconds: int = 60
    entry_price: float = 0.0
    backtest_scope: str = "intraday"
    process: Optional[Process] = None
    trade_order_queue: Optional[MpQueue] = None

    status: str = MonitorTUIStatus.STOPPED
    display_last_price: Optional[float] = None
    display_current_position_value: float = 0.0
    display_quantity: float = 0.0
    display_last_signal: Optional[str] = None
    display_last_checked: Optional[datetime] = None
    display_opening_date_str: Optional[str] = None
    last_error_message: Optional[str] = None

    @property
    def process_name(self) -> str:
        return f"TUI-Mon-{self.ticker}-{self.tui_id[:4]}"

    @property
    def last_checked_str(self) -> str:
        if self.display_last_checked:
            return self.display_last_checked.strftime("%Y-%m-%d %H:%M:%S")
        return "N/A"

    def update_from_trade_order(self, order: dict):
        self.display_last_signal = order.get("action")
        self.display_last_price = order.get("price")
        self.display_quantity = float(order.get("quantity") or 0.0)
        self.display_current_position_value = float(order.get("position_value") or 0.0)
        ts = order.get("timestamp")
        if ts:
            self.display_last_checked = datetime.fromisoformat(ts)
        if not self.display_opening_date_str and self.display_last_signal == "BUY" and self.display_last_checked:
            self.display_opening_date_str = self.display_last_checked.strftime("%Y%m%d_%H%M%S")
