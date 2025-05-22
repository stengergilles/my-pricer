from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Static
from textual.containers import Vertical
from textual.reactive import reactive

from ..tui_models import TUIMonitorData

class AddMonitorDialog(ModalScreen):
    """A dialog to add a new TickerMonitor config."""

    input_ticker = reactive("")
    input_interval = reactive("")
    input_entry_price = reactive("")
    input_scope = reactive("")

    def compose(self):
        yield Label("Add New Ticker Monitor", id="dialog-title")
        with Vertical():
            yield Input(placeholder="Ticker (e.g. BTC-USD)", id="input-ticker")
            yield Input(placeholder="Entry Price (optional)", id="input-entry-price")
            yield Input(placeholder="Scope (e.g. intraday, short, long)", id="input-scope")
            yield Button(label="Add", id="btn-add")
            yield Button(label="Cancel", id="btn-cancel")

    def on_mount(self):
        self.query_one("#input-ticker", Input).focus()

    async def on_button_pressed(self, event):
        button_id = event.button.id
        if button_id == "btn-add":
            ticker = self.query_one("#input-ticker", Input).value.strip()
            try:
                entry_price = float(self.query_one("#input-entry-price", Input).value.strip())
            except Exception:
                entry_price = 0.0
            scope = self.query_one("#input-scope", Input).value.strip() or "intraday"

            # Set interval based on scope
            scope_to_interval = {
                "intraday": 60,
                "short": 300,
                "long": 3600,
            }
            interval = scope_to_interval.get(scope.lower(), 60)

            config = TUIMonitorData(
                ticker=ticker or "BTC-USD",
                monitor_interval_seconds=interval,
                entry_price=entry_price,
                backtest_scope=scope,
            )
            self.dismiss(config)
        elif button_id == "btn-cancel":
            self.dismiss(None)
