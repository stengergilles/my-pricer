import urwid
import multiprocessing as mp
import sys
import time
import os

try:
    # Adjust this import path as needed for your project layout
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
except ImportError:
    TickerMonitor = None

if sys.platform == "win32":
    mp.set_start_method("spawn", force=True)
else:
    mp.set_start_method("fork", force=True)

def monitor_worker(ticker, entry_price, scope, conn):
    # Capture and send child stdout/stderr output to parent
    import os, sys

    class WriterToPipe:
        def __init__(self, conn):
            self.conn = conn
        def write(self, s):
            if s.strip():
                self.conn.send({"type": "stdout", "data": s})
        def flush(self):
            pass

    sys.stdout = WriterToPipe(conn)
    sys.stderr = WriterToPipe(conn)

    if TickerMonitor is None:
        conn.send({"type": "error", "data": f"ERROR: TickerMonitor not found."})
        conn.close()
        return
    try:
        process_name = f"Monitor-{ticker}"
        # Pipe as queue-like for compatibility
        class PipeAsQueue:
            def __init__(self, conn):
                self.conn = conn
            def put(self, item):
                self.conn.send(item)
        queue_like = PipeAsQueue(conn)
        monitor = TickerMonitor(
            ticker,
            queue_like,
            entry_price,
            process_name=process_name,
            backtest_scope=scope
        )
        monitor.run()
    except Exception as e:
        conn.send({"type": "error", "data": f"EXCEPTION: {e}"})
    finally:
        conn.close()

class Monitor:
    def __init__(self, ticker, entry, scope):
        self.ticker = ticker
        self.entry = entry
        self.scope = scope
        self.parent_conn, self.child_conn = mp.Pipe()
        self.process = None
        self.status = "STOPPED"
        self.logs = []
        self.stdout_log = []

    def start(self):
        if self.process is None or not self.process.is_alive():
            self.process = mp.Process(target=monitor_worker, args=(self.ticker, self.entry, self.scope, self.child_conn))
            self.process.start()
            self.status = "RUNNING"
            self.logs.append(f"[PARENT] Started monitor for {self.ticker} entry={self.entry} scope={self.scope}")

    def stop(self):
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join()
            self.status = "STOPPED"
            self.logs.append(f"[PARENT] Stopped monitor for {self.ticker}")

    def poll(self):
        while self.parent_conn.poll():
            msg = self.parent_conn.recv()
            # If message is dict AND has a type key, handle accordingly
            if isinstance(msg, dict) and "type" in msg:
                mtype = msg["type"]
                if mtype == "stdout":
                    self.stdout_log.append(msg["data"].rstrip('\n'))
                elif mtype == "error":
                    self.logs.append(f"[CHILD] {msg['data']}")
                    self.status = "STOPPED"
                else:
                    # Assume type 'data' or other: try to format as trade/monitor dict
                    self._format_monitor_message(msg)
            elif isinstance(msg, dict):
                self._format_monitor_message(msg)
            else:
                # fallback to string output
                self.logs.append(f"[CHILD] {msg}")
                if (
                    ("DONE" in str(msg))
                    or ("ERROR" in str(msg))
                    or ("EXCEPTION" in str(msg))
                ):
                    self.status = "STOPPED"

    def _format_monitor_message(self, msg):
        ts = msg.get("timestamp", "")
        action = msg.get("action", "")
        ticker = msg.get("ticker", "")
        price = msg.get("price", "")
        quantity = msg.get("quantity", "")
        pos_value = msg.get("position_value", "")
        try:
            price = f"{float(price):,.2f}"
        except Exception:
            price = str(price)
        try:
            quantity = f"{float(quantity):.5f}"
        except Exception:
            quantity = str(quantity)
        try:
            pos_value = f"{float(pos_value):,.2f}"
        except Exception:
            pos_value = str(pos_value)
        sigs = msg.get("actioned_signals", {})
        sigs_str = " ".join(f"{k}:{v}" for k, v in sigs.items()) if isinstance(sigs, dict) else str(sigs)
        log_line = (
            f"{ts} | {action} | {ticker} | price: {price} | qty: {quantity} | pos_value: {pos_value}"
        )
        if sigs_str:
            log_line += f" | {sigs_str}"
        log_line = "[CHILD] " + log_line
        self.logs.append(log_line)
        if (
            ("DONE" in str(msg))
            or ("ERROR" in str(msg))
            or ("EXCEPTION" in str(msg))
        ):
            self.status = "STOPPED"

    def cleanup(self):
        self.stop()
        try:
            self.parent_conn.close()
        except Exception:
            pass
        try:
            self.child_conn.close()
        except Exception:
            pass

class AddMonitorDialog(urwid.WidgetWrap):
    signals = ["ok", "cancel"]

    def __init__(self):
        self.ticker_edit = urwid.Edit("Ticker: ")
        self.entry_edit = urwid.Edit("Entry Price: ")
        self.scope_edit = urwid.Edit("Scope: ", edit_text="intraday")
        ok_btn = urwid.Button("OK", on_press=self._on_ok)
        cancel_btn = urwid.Button("Cancel", on_press=self._on_cancel)
        pile = urwid.Pile([
            self.ticker_edit,
            self.entry_edit,
            self.scope_edit,
            urwid.Columns([ok_btn, cancel_btn])
        ])
        fill = urwid.Filler(pile)
        super().__init__(urwid.LineBox(fill))

    def _on_ok(self, button):
        ticker = self.ticker_edit.edit_text.strip().upper()
        entry = self.entry_edit.edit_text.strip()
        scope = self.scope_edit.edit_text.strip()
        try:
            entry = float(entry)
        except Exception:
            entry = 1000.0
        urwid.emit_signal(self, "ok", self, ticker, entry, scope)

    def _on_cancel(self, button):
        urwid.emit_signal(self, "cancel", self)

class OutputPopup(urwid.WidgetWrap):
    def __init__(self, lines, on_close):
        walker = urwid.SimpleFocusListWalker([urwid.Text(l) for l in lines] or [urwid.Text("(No output)")])
        listbox = urwid.ListBox(walker)
        close_btn = urwid.Button("Close", on_press=lambda button: on_close())
        pile = urwid.Pile([
            ('weight', 1, listbox),    # <--- Do NOT wrap ListBox in Filler!
            ('pack', close_btn)
        ])
        super().__init__(urwid.LineBox(pile))

class TUI:
    def __init__(self):
        self.monitors = {}
        self.menu = urwid.Text("Q: quit | A: add | S: start | X: stop | D: delete | O: output | Up/Down: select\n")
        self.monitor_listbox = urwid.SimpleFocusListWalker([])
        self.log_box = urwid.Text("")
        self.listbox = urwid.ListBox(self.monitor_listbox)
        self.layout = urwid.Frame(header=self.menu,
                                  body=self.listbox,
                                  footer=urwid.Pile([urwid.Text("Logs:"), self.log_box]))
        self.selected_index = 0
        self.overlay = None
        self.loop = urwid.MainLoop(self.layout, unhandled_input=self.handle_input)
        self.loop.set_alarm_in(1, self.refresh)

    def refresh(self, loop, data):
        for monitor in self.monitors.values():
            monitor.poll()
        self.update_monitors()
        self.loop.set_alarm_in(1, self.refresh)

    def update_monitors(self):
        items = []
        for i, (key, monitor) in enumerate(self.monitors.items()):
            marker = ">" if i == self.selected_index else " "
            items.append(urwid.Text(f"{marker} {monitor.ticker} [{monitor.status}] entry={monitor.entry} scope={monitor.scope}"))
        self.monitor_listbox[:] = items
        keys = list(self.monitors.keys())
        if keys:
            selected = self.monitors[keys[self.selected_index]]
            self.log_box.set_text("\n".join(selected.logs[-10:]))
        else:
            self.log_box.set_text("")

    def handle_input(self, key):
        keys = list(self.monitors.keys())
        if self.overlay:
            return
        if key in ('q', 'Q'):
            for monitor in self.monitors.values():
                monitor.cleanup()
            raise urwid.ExitMainLoop()
        elif key in ('down',):
            if keys and self.selected_index < len(keys) - 1:
                self.selected_index += 1
        elif key in ('up',):
            if keys and self.selected_index > 0:
                self.selected_index -= 1
        elif key in ('a', 'A'):
            self.open_add_dialog()
        elif key in ('s', 'S'):
            if keys:
                self.monitors[keys[self.selected_index]].start()
        elif key in ('x', 'X'):
            if keys:
                self.monitors[keys[self.selected_index]].stop()
        elif key in ('d', 'D'):
            if keys:
                key_to_delete = keys[self.selected_index]
                self.monitors[key_to_delete].cleanup()
                del self.monitors[key_to_delete]
                if self.selected_index > 0:
                    self.selected_index -= 1
        elif key in ('o', 'O'):
            self.open_output_popup()
        self.update_monitors()

    def open_add_dialog(self):
        dialog = AddMonitorDialog()
        urwid.connect_signal(dialog, "ok", self.add_monitor)
        urwid.connect_signal(dialog, "cancel", lambda dialog: self.close_dialog())
        self.overlay = urwid.Overlay(dialog, self.layout, 'center', 40, 'middle', 10)
        self.loop.widget = self.overlay

    def close_dialog(self):
        self.loop.widget = self.layout
        self.overlay = None

    def add_monitor(self, dialog, ticker, entry, scope):
        key = f"{ticker}-{scope}-{entry}"
        if key not in self.monitors:
            self.monitors[key] = Monitor(ticker, entry, scope)
        self.close_dialog()
        self.selected_index = len(self.monitors) - 1
        self.update_monitors()

    def open_output_popup(self):
        keys = list(self.monitors.keys())
        if not keys:
            return
        selected = self.monitors[keys[self.selected_index]]
        popup = OutputPopup(selected.stdout_log, self.close_dialog)
        self.overlay = urwid.Overlay(popup, self.layout, 'center', 80, 'middle', 24)
        self.loop.widget = self.overlay

    def run(self):
        self.update_monitors()
        self.loop.run()

if __name__ == "__main__":
    if "TERMUX_VERSION" in os.environ:
        print("Running in Termux: urwid TUI should work normally.\n")
    TUI().run()
