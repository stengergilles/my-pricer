import uuid
from dataclasses import dataclass, field
from typing import Optional
from multiprocessing import Process, Queue as MpQueue # Using MpQueue to avoid confusion with asyncio.Queue
from datetime import datetime

# Assuming TickerMonitor and BACKTEST_SCOPE_PRESETS are accessible for type hinting / default values
# If not, define them as strings or use forward references.
try:
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor, BACKTEST_SCOPE_PRESETS
except ImportError:
    print("WARNING: TickerMonitor not found. Ensure stock_monitoring_app is in PYTHONPATH.")
    TickerMonitor = None # Placeholder
    BACKTEST_SCOPE_PRESETS = {"intraday": {}, "short": {}, "long": {}} # Placeholder


class MonitorTUIStatus: # Using a class for status strings
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
    entry_price: float = 0.0 # 0.0 means no forced entry, rely on strategy
    backtest_scope: str = "intraday" # Default, must be a key in BACKTEST_SCOPE_PRESETS
    
    # Process and communication related
    process: Optional[Process] = None
    trade_order_queue: Optional[MpQueue] = None # For TickerMonitor to send orders to
    # ticker_monitor_instance: Optional[TickerMonitor] = None # The instance lives in another process

    # Displayable state, updated by TUI based on queue messages or actions
    status: str = MonitorTUIStatus.STOPPED
    display_last_price: Optional[float] = None    display_current_position_value: float = 0.0
    display_quantity: float = 0.0
    display_last_signal: Optional[str] = None # e.g., BUY, SELL, HOLD (inferred)
    display_last_checked: Optional[datetime] = None # Timestamp of last known activity
    display_opening_date_str: Optional[str] = None # From TickerMonitor's forward test file naming
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
        self.display_quantity = order.get("quantity")
        self.display_current_position_value = order.get("position_value")
        self.display_last_checked = datetime.fromisoformat(order.get("timestamp"))        if not self.display_opening_date_str and self.display_last_signal == "BUY":
             # Try to infer opening date if not set yet; TickerMonitor sets its own
             # This is a rough inference for TUI display only.
            self.display_opening_date_str = self.display_last_checked.strftime("%Y%m%d_%H%M%S")

