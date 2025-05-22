from textual.widgets import DataTablefrom textual.reactive import reactive
from typing import List, Dict
from ..tui_models import TUIMonitorData, MonitorTUIStatus

class MonitorTable(DataTable):
    """A DataTable widget to display TickerMonitor states."""

    monitors_data = reactive([])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zebra_stripes = True
        self.cursor_type = "row"

    COMPONENT_CLASSES = {
        "monitortable--status-running": {"color": "green"},
        "monitortable--status-stopped": {"color": "gray"},
        "monitortable--status-starting": {"color": "blue"},
        "monitortable--status-stopping": {"color": "dark_orange"},
        "monitortable--status-error": {"color": "red"},
        "monitortable--status-unknown": {"color": "magenta"},
    }

    def on_mount(self) -> None:
        self.add_columns(
            "ID", "Ticker", "Status", "Entry Price", "Interval(s)",
            "Position $", "Quantity", "Last Price", "Last Signal",
            "Last Checked", "Scope", "Opening Date"
        )        self.update_table_data(self.monitors_data)


    def watch_monitors_data(self, new_monitors_data: List[TUIMonitorData]) -> None:
        self.update_table_data(new_monitors_data)

    def update_table_data(self, monitors: List[TUIMonitorData]) -> None:
        self.clear()
        sorted_monitors = sorted(monitors, key=lambda m: m.ticker.lower())

        for monitor_data in sorted_monitors:
            status_style_name = f"monitortable--status-{monitor_data.status.lower()}"
            status_style = self.get_component_rich_style(status_style_name, partial=False)

            self.add_row(
                monitor_data.tui_id[:8],
                monitor_data.ticker,
                f"[{status_style}]{monitor_data.status}[/]",
                f"{monitor_data.entry_price:.2f}" if monitor_data.entry_price > 0 else "Strategy",
                str(monitor_data.monitor_interval_seconds),
                f"{monitor_data.display_current_position_value:.2f}",
                f"{monitor_data.display_quantity:.4f}" if monitor_data.display_quantity is not None else "N/A",
                f"{monitor_data.display_last_price:.2f}" if monitor_data.display_last_price is not None else "N/A",
                monitor_data.display_last_signal or "N/A",
                monitor_data.last_checked_str,
                monitor_data.backtest_scope,
                monitor_data.display_opening_date_str or "N/A",
                key=monitor_data.tui_id
            )
