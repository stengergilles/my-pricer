import argparse
import multiprocessing
import time
from queue import Empty

from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor

def print_indicator_summary(indicator_configs):
    print("\n--- Indicators from backtest ---")
    if not indicator_configs:
        print("No optimized indicator configuration found for this ticker.")
        return
    for conf in indicator_configs:
        cls = conf.get("type")
        params = conf.get("params")
        print(f"- {getattr(cls, '__name__', str(cls))} | Params: {params}")

def monitor_worker(ticker, monitor_interval, entry_price, order_queue, status_queue):
    import traceback
    try:
        monitor = TickerMonitor(
            ticker=ticker,
            monitor_interval_seconds=monitor_interval,
            trade_order_queue=order_queue,
            entry_price=entry_price,
            process_name=f"CLI-Monitor-{ticker}",
        )
        indicator_configs = monitor._load_optimized_config_from_disk()
        status_queue.put({"type": "indicators", "data": indicator_configs})

        last_fetch_status = "Never"
        while True:
            start_time = time.time()
            try:
                data = monitor._fetch_latest_data()
                if data is None or (hasattr(data, "empty") and data.empty):
                    fetch_status = "No data"
                else:
                    fetch_status = "OK"
                    last_fetch_status = f"Success at {time.strftime('%H:%M:%S')}"
            except Exception as e:
                tb = traceback.format_exc().strip().splitlines()
                error_line = ""
                for line in reversed(tb):
                    if line.strip().startswith('File '):
                        error_line = line
                        break
                exception_type = type(e).__name__
                msg = str(e) or f"[{exception_type}]"
                fetch_status = f"Error: {msg} ({error_line.strip()})"
                last_fetch_status = fetch_status
                data = None

            status_queue.put({"type": "fetch_status", "data": fetch_status, "last_good": last_fetch_status})

            if data is not None and not (hasattr(data, "empty") and data.empty):
                monitor._process_data_and_decide(data)

            elapsed = time.time() - start_time
            sleep_time = monitor_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            if not getattr(monitor, "_running", True):
                break
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
    parser = argparse.ArgumentParser(description="Start a real-time ticker monitor.")
    parser.add_argument("ticker", help="Ticker symbol (e.g., AAPL, BTC)")
    parser.add_argument("--interval", type=int, default=15, help="Monitor interval in seconds (default: 15)")
    parser.add_argument("--entry", type=float, default=100.0, help="Entry price (default: 100.0)")
    args = parser.parse_args()

    ticker = args.ticker
    monitor_interval = args.interval
    entry_price = args.entry

    order_queue = multiprocessing.Queue()
    status_queue = multiprocessing.Queue()
    monitor_proc = multiprocessing.Process(
        target=monitor_worker,
        args=(ticker, monitor_interval, entry_price, order_queue, status_queue),
        daemon=True,
    )

    print(f"Starting monitor for {ticker} (every {monitor_interval}s)...\n")

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
