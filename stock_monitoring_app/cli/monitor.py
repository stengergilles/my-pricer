import argparse
import multiprocessing
import time
from queue import Empty

from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
from stock_monitoring_app.monitoring.ticker_monitor import BACKTEST_SCOPE_PRESETS

def parse_interval_to_seconds(interval):
    """Convert interval strings like '1m', '15m', '1d', '1s', '2h' to seconds."""
    if isinstance(interval, (int, float)):
        return int(interval)
    if isinstance(interval, str):
        interval = interval.strip().lower()
        if interval.endswith("ms"):
            return float(interval[:-2]) / 1000
        if interval.endswith("s"):
            return int(interval[:-1])
        if interval.endswith("m"):
            return int(interval[:-1]) * 60
        if interval.endswith("h"):
            return int(interval[:-1]) * 60 * 60
        if interval.endswith("d"):
            return int(interval[:-1]) * 60 * 60 * 24
        try:
            return int(interval)
        except ValueError:
            raise ValueError(f"Unrecognized interval format: {interval}")
    raise TypeError(f"Invalid interval type: {type(interval)}")

def print_indicator_summary(indicator_configs):
    print("\n--- Indicators from backtest ---")
    if not indicator_configs:
        print("No optimized indicator configuration found for this ticker.")
        return
    for conf in indicator_configs:
        cls = conf.get("type")
        params = conf.get("params")
        print(f"- {getattr(cls, '__name__', str(cls))} | Params: {params}")

def monitor_worker(ticker, entry_price, order_queue, status_queue, scope):
    import traceback

    monitor_interval = parse_interval_to_seconds(BACKTEST_SCOPE_PRESETS[scope]['interval'])

    try:
        monitor = TickerMonitor(
            ticker=ticker,
            monitor_interval_seconds=monitor_interval,
            trade_order_queue=order_queue,
            entry_price=entry_price,
            process_name=f"CLI-Monitor-{ticker}",
            backtest_scope=scope,
        )

        # Optionally load indicator configs for CLI summary, but actual logic should always use run()
        indicator_configs = monitor._load_optimized_config_from_disk()
        status_queue.put({"type": "indicators", "data": indicator_configs})

        # The key fix: Use monitor.run() so configs and main loop are handled correctly
        monitor.run()

    except Exception as e:
        import traceback
        tb = traceback.format_exc().strip().splitlines()
        error_line = ""
        for line in reversed(tb):
            if line.strip().startswith('File '):
                error_line = line
                break
        exception_type = type(e).__name__
        msg = str(e) or f"[{exception_type}]"
        status_queue.put({"type": "exception", "error": f"{msg} ({error_line.strip()})"})
    finally:
        status_queue.put({"type": "stopped"})

def main():
    available_scopes = list(BACKTEST_SCOPE_PRESETS.keys())
    parser = argparse.ArgumentParser(description="Start a real-time ticker monitor.")
    parser.add_argument("ticker", help="Ticker symbol (e.g., AAPL, BTC)")
    parser.add_argument("--entry", type=float, default=100.0, help="Entry price (default: 100.0)")
    parser.add_argument(
        "--scope",
        type=str,
        default="intraday",
        choices=available_scopes,
        help=f"Scope for monitoring/backtest. Available: {', '.join(available_scopes)}. Default: intraday"
    )
    args = parser.parse_args()

    ticker = args.ticker
    entry_price = args.entry
    scope = args.scope
    monitor_interval = parse_interval_to_seconds(BACKTEST_SCOPE_PRESETS[scope]['interval'])

    order_queue = multiprocessing.Queue()
    status_queue = multiprocessing.Queue()
    monitor_proc = multiprocessing.Process(
        target=monitor_worker,
        args=(ticker, entry_price, order_queue, status_queue, scope),
        daemon=True,
    )

    print(f"Starting monitor for {ticker} (scope: {scope}, interval: {monitor_interval}s)...\n")

    monitor_proc.start()
    indicator_configs = None

    try:
        while True:
            # Print indicators at start
            if indicator_configs is None:
                try:
                    msg = status_queue.get(timeout=5)
                    if msg["type"] == "indicators":
                        indicator_configs = msg["data"]
                        print_indicator_summary(indicator_configs)
                    continue
                except Empty:
                    if not monitor_proc.is_alive():
                        print("CLI Error: Monitor process exited unexpectedly (no status messages in queue).")
                        break
                    continue

            try:
                msg = status_queue.get(timeout=monitor_interval)
                if msg["type"] == "fetch_status":
                    print(f"[Fetch status] {msg['data']} | Last good: {msg['last_good']}")
                elif msg["type"] == "exception":
                    print(f"\n>>> Monitor Exception: {msg['error']}")
                elif msg["type"] == "stopped":
                    print("Monitor stopped.")
                    break
            except Empty:
                if not monitor_proc.is_alive():
                    print("CLI Error: Monitor process exited unexpectedly (no status messages in queue).")
                    break
                # If process is alive, this is just a timeout—continue waiting.

            # Print trade orders
            while True:
                try:
                    order = order_queue.get_nowait()
                    if order.get("action") != "HOLD":
                        print(f"[TRADE ORDER] {order}")
                except Empty:
                    break

    except KeyboardInterrupt:
        print("\nReceived Ctrl+C. Stopping monitor...")
        monitor_proc.terminate()
        monitor_proc.join(timeout=10)
        print("Monitor terminated.")
    except Exception as e:
        import traceback
        tb = traceback.format_exc().strip().splitlines()
        error_line = ""
        for line in reversed(tb):
            if line.strip().startswith('File '):
                error_line = line
                break
        exception_type = type(e).__name__
        msg = str(e) or f"[{exception_type}]"
        print(f"CLI Error: {msg} ({error_line.strip()})")
        if monitor_proc.is_alive():
            monitor_proc.terminate()
            monitor_proc.join(timeout=10)

if __name__ == "__main__":
    main()
