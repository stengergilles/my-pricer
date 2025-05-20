import os
import time
import pytest
import multiprocessing

from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor

requires_polygon_key = pytest.mark.skipif(
    not os.getenv("POLYGON_API_KEY"),
    reason="POLYGON_API_KEY environment variable not set in shell. Skipping Polygon monitor integration test."
)
requires_coingecko = pytest.mark.skipif(
    False,  # CoinGecko can use public API, so no key required for basic tests
    reason="CoinGecko API key not set, but test can use public API."
)

def monitor_process(queue, ticker, monitor_interval, seconds_to_run, process_name="pytest-monitor"):
    monitor = TickerMonitor(
        ticker=ticker,
        monitor_interval_seconds=monitor_interval,
        trade_order_queue=queue,
        entry_price=150.0 if process_name == "pytest-monitor" else 30000.0,
        process_name=process_name,
    )
    try:
        # Use a thread to stop the monitor after seconds_to_run
        import threading
        def stopper():
            time.sleep(seconds_to_run)
            monitor.stop()
        threading.Thread(target=stopper, daemon=True).start()
        monitor.run()
        queue.put("monitor-stopped")
    except Exception as e:
        queue.put(f"monitor-exception: {e}")

@pytest.mark.integration
@requires_polygon_key
def test_monitor_polygon_real_fetch_and_subprocess():
    ticker = "AAPL"
    monitor_interval = 5
    seconds_to_run = 10

    queue = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=monitor_process,
        args=(queue, ticker, monitor_interval, seconds_to_run, "pytest-monitor")
    )
    p.start()
    p.join(timeout=seconds_to_run + 15)

    assert p.exitcode == 0, "Monitor subprocess should exit cleanly"
    results = []
    while not queue.empty():
        results.append(queue.get())
    assert any("monitor-stopped" in r for r in results), f"Monitor did not stop as expected, results: {results}"

@pytest.mark.integration
@requires_coingecko
def test_monitor_coingecko_real_fetch_and_subprocess():
    ticker = "bitcoin"
    monitor_interval = 5
    seconds_to_run = 10

    queue = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=monitor_process,
        args=(queue, ticker, monitor_interval, seconds_to_run, "pytest-monitor-coingecko")
    )
    p.start()
    p.join(timeout=seconds_to_run + 15)

    assert p.exitcode == 0, "Monitor subprocess should exit cleanly"
    results = []
    while not queue.empty():
        results.append(queue.get())
    assert any("monitor-stopped" in r for r in results), f"Monitor did not stop as expected, results: {results}"
