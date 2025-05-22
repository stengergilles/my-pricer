from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button, Static, Select
from textual.containers import Vertical, Horizontal
from textual.validation import Number

from ..tui_models import TUIMonitorData # For default values and type hints

# Attempt to import BACKTEST_SCOPE_PRESETS for the Select widget
try:    from stock_monitoring_app.monitoring.ticker_monitor import BACKTEST_SCOPE_PRESETS
except ImportError:
    BACKTEST_SCOPE_PRESETS = {"intraday": {}, "short": {}, "long": {}} # Fallback


class AddMonitorDialog(ModalScreen[TUIMonitorData | None]):
    """A dialog screen for adding a new TickerMonitor configuration."""

    DEFAULT_CSS = """
    AddMonitorDialog {
        align: center middle;
    }
    #add_monitor_dialog_content {
        width: 60;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }
    Label { margin-top: 1; }
    Input, Select { margin-bottom: 1; }
    #add_monitor_buttons_container {
        align-horizontal: right;
        margin-top: 1;
    }
    Button { margin-left: 1; }
    """

    def __init__(self): # Simplified: always for adding new
        super().__init__()
        self.title_text = "Add New Ticker Monitor"

    def compose(self) -> ComposeResult:
        # Prepare options for the Select widget
        scope_options = [(scope_name, scope_name) for scope_name in BACKTEST_SCOPE_PRESETS.keys()]

        with Vertical(id="add_monitor_dialog_content"):
            yield Label(self.title_text)
            yield Label("Ticker (e.g., BTC-USD, AAPL):")
            yield Input(placeholder="BTC-USD", id="ticker_input")
            
            yield Label("Entry Price (USD, 0 for strategy-only entry):")
            yield Input(
                value="0.0",
                id="entry_price_input",
                validators=[Number(minimum=0.0)]
            )
            yield Label("Monitor Interval (seconds):")
            yield Input(
                value="60",
                id="interval_input",                validators=[Number(minimum=5, maximum=86400)] # 5s to 1 day
            )
            yield Label("Backtest Scope:")
            yield Select(options=scope_options, value="intraday", id="backtest_scope_select")

            with Horizontal(id="add_monitor_buttons_container"):                yield Button("Save", variant="primary", id="save_button")
                yield Button("Cancel", id="cancel_button")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_button":
            ticker_input = self.query_one("#ticker_input", Input)
            entry_price_input = self.query_one("#entry_price_input", Input)
            interval_input = self.query_one("#interval_input", Input)
            scope_select = self.query_one("#backtest_scope_select", Select)

            if not ticker_input.value or not entry_price_input.is_valid or not interval_input.is_valid:
                self.app.bell()
                return

            new_config = TUIMonitorData(
                ticker=ticker_input.value.upper(),
                entry_price=float(entry_price_input.value),                monitor_interval_seconds=int(interval_input.value),
                backtest_scope=str(scope_select.value) # value is an object, ensure it's string
            )
            self.dismiss(new_config)
        elif event.button.id == "cancel_button":
            self.dismiss(None)
