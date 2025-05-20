import argparse
import multiprocessing
import signal
import sys
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
    monitor = TickerMonitor(
        ticker=ticker,
        monitor_interval_seconds=monitor_interval,
        trade_order_queue=order_queue,
        entry_price=entry_price,
        process_name=f"CLI-Monitor-{ticker}",
    )
    indicator_configs = monitor._load_optimized_config_from_disk()
    # Send indicators to parent through status_queue at start
    status_queue.put({"type": "indicators", "data": indicator_configs})

    last_fetch_status = "Never"
    try:
        while True:
            start_time = time.time()
            try:
                data = monitor._fetch_latest_data()
                if data is None:
                    fetch_status = "No data"
                elif hasattr(data, "empty") and data.empty:
                    fetch_status = "No data"
                else:
                    fetch_status = "OK"
                    last_fetch_status = f"Success at {time.strftime('%H:%M:%S')}"
            except Exception as e:
                if "closed" in str(e).lower():
                    fetch_status = f"Market Closed: {e}"
                else:
                    fetch_status = f"Error: {e}"
                last_fetch_status = fetch_status
                data = None

            # Report fetch status
            status_queue.put({"type": "fetch_status", "data": fetch_status, "last_good": last_fetch_status})

            # Decide and produce orders
            signal = "HOLD"
            if data is not None and hasattr(data, "empty") and not data.empty:
                monitor._process_data_and_decide(data)  # This will put order in order_queue if needed

            # Sleep until next cycle
            elapsed = time.time() - start_time
            sleep_time = monitor_interval - elapsed
            if sleep_time > 0:
                for _ in range(int(sleep_time)):
                    time.sleep(1)
            # Check for stop request (monitor._running flag can be set externally)
            if not getattr(monitor, "_running", True):
                break
    except KeyboardInterrupt:
        pass
    finally:
        status_queue.put({"type": "stopped"})
        return

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
            try:
                # Print indicators at start
                if indicator_configs is None:
                    msg = status_queue.get(timeout=5)
                    if msg["type"] == "indicators":
                        indicator_configs = msg["data"]
                        print_indicator_summary(indicator_configs)
                    continue

                # Print fetch status and orders
                try:
                    msg = status_queue.get(timeout=monitor_interval)
                    if msg["type"] == "fetch_status":
                        print(f"[Fetch status] {msg['data']} | Last good: {msg['last_good']}")
                    elif msg["type"] == "stopped":
                        print("Monitor stopped.")
                        break
                except Empty:
                    pass

                # Print trade orders
                while True:
                    try:
                        order = order_queue.get_nowait()
                        print(f"[TRADE ORDER] {order}")
                    except Empty:
                        break

            except KeyboardInterrupt:
                print("\nReceived Ctrl+C. Stopping monitor...")
                # Send stop signal to process
                monitor_proc.terminate()
                monitor_proc.join(timeout=10)
                print("Monitor terminated.")
                break
    except Exception as e:
        print(f"CLI Error: {e}")
        if monitor_proc.is_alive():
            monitor_proc.terminate()
            monitor_proc.join(timeout=10)

if __name__ == "__main__":
    main()
