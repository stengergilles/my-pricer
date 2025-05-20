import os
import sys
import time
import pytest
import multiprocessing

from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor

# Only run if POLYGON_API_KEY is set in the shell
requires_polygon_key = pytest.mark.skipif(
    not os.getenv("POLYGON_API_KEY"),
    reason="POLYGON_API_KEY environment variable not set in shell. Skipping monitor integration test."
)

def monitor_process(queue, ticker, monitor_interval, seconds_to_run):
    """
    Run the TickerMonitor in a subprocess, then stop after a few seconds.
    """
    monitor = TickerMonitor(
        ticker=ticker,
        monitor_interval_seconds=monitor_interval,
        process_name="pytest-monitor",
        trade_order_queue=queue,
        entry_price=150.0,
    )
    try:
        # Run the monitor (will loop until stopped)
        monitor_proc = multiprocessing.Process(target=monitor.run)
        monitor_proc.start()
        time.sleep(seconds_to_run)
        monitor.stop()
        monitor_proc.join(timeout=10)
        queue.put("monitor-stopped")
    except Exception as e:
        queue.put(f"monitor-exception: {e}")

@pytest.mark.integration
@requires_polygon_key
def test_monitor_real_fetch_and_subprocess():
    """
    Integration test: runs the monitor in a subprocess, using real Polygon fetch.
    Verifies that the monitor starts, fetches, and can be stopped.
    """
    ticker = "AAPL"
    monitor_interval = 5  # seconds
    seconds_to_run = 10   # Let it run two fetch cycles

    queue = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=monitor_process,
        args=(queue, ticker, monitor_interval, seconds_to_run)
    )
    p.start()
    p.join(timeout=seconds_to_run + 15)

    assert p.exitcode == 0, "Monitor subprocess should exit cleanly"
    results = []
    while not queue.empty():
        results.append(queue.get())
    assert any("monitor-stopped" in r for r in results), f"Monitor did not stop as expected, results: {results}"
