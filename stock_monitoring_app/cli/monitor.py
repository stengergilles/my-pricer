

import argparse
import multiprocessing
import time
import sys # Import the sys module
# queue.Empty is not needed as we'll use pipe.poll() and non-blocking recv()
# from queue import Empty # No longer needed

# TickerMonitor class itself is not directly instantiated here anymore
# from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor 
from stock_monitoring_app.monitoring.ticker_monitor import BACKTEST_SCOPE_PRESETS # Still needed for interval
from stock_monitoring_app.utils.process_manager import launch_ticker_monitor_process # Import the unified launcher

# For type hinting if desired, TickerMonitor can be imported if needed for type checks on config data
# For example: from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor

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

        print(f"- {getattr(cls, '__name__', str(cls))} | Params: {params if params else '{}'}") # Handle empty params

# monitor_worker is now centralized in process_manager.py

def main():
    available_scopes = list(BACKTEST_SCOPE_PRESETS.keys())
    available_scopes = list(BACKTEST_SCOPE_PRESETS.keys())
    parser = argparse.ArgumentParser(description="Start a real-time ticker monitor.")
    parser.add_argument("ticker", help="Ticker symbol (e.g., AAPL, BTC)")
    parser.add_argument("--entry", type=float, default=100.0, help="Entry price (default: 100.0)")
    parser.add_argument("--leverage",type=float,default=1.0,help="Position Leverage (default: 1.0)")
    parser.add_argument("--stop_loss",type=float,default=0.05,help=" (default: 0.05)")
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

    monitor_interval = parse_interval_to_seconds(BACKTEST_SCOPE_PRESETS[scope]['interval']) # For user info

    if launch_ticker_monitor_process is None:
        print("CLI CRITICAL ERROR: launch_ticker_monitor_process not available. Exiting.", file=sys.stderr)
        return

    monitor_proc, parent_conn = launch_ticker_monitor_process(
        ticker=ticker,
        entry_price=entry_price,
        scope=scope,
        leverage=args.leverage,
        stop_loss=args.stop_loss
    )

    if not monitor_proc or not parent_conn:
        print(f"CLI Error: Failed to start monitor process for {ticker}. Exiting.")
        return

    print(f"Starting monitor for {ticker} (scope: {scope}, PID: {monitor_proc.pid})...\n")
    
    indicator_configs_printed = False
    monitor_running = True

    try:
        while monitor_running and monitor_proc.is_alive():
            if parent_conn.poll(timeout=0.1): # Poll with a short timeout
                try:
                    msg = parent_conn.recv()
                except (EOFError, OSError) as e:
                    print(f"CLI Error: Pipe connection to monitor {ticker} lost: {e}")
                    monitor_running = False
                    break

                # Ensure message is for this CLI's monitor instance (though less critical for single CLI monitor)
                msg_ticker = msg.get("ticker", ticker) if isinstance(msg, dict) else ticker
                if msg_ticker != ticker:
                    print(f"CLI Warning: Received message for {msg_ticker} on {ticker}'s pipe. Ignoring.")
                    continue

                if isinstance(msg, dict) and "type" in msg: # System messages from process_manager
                    mtype = msg["type"]
                    data = msg.get("data", "")

                    if mtype == "stdout" or mtype == "stderr":
                        print(f"[{mtype.upper()}-{msg.get('pid','P')}] {data.strip()}")
                    elif mtype == "error": # Worker-level critical errors
                        print(f"[WORKER_ERROR-{msg.get('pid','P')}] {data.strip()}")
                        # Consider if CLI should exit on certain worker errors
                    elif mtype == "indicators_loaded":
                        if not indicator_configs_printed:
                            print_indicator_summary(data) # data is the indicator_configs list
                            indicator_configs_printed = True
                    elif mtype == "worker_stopped":
                        print(f"Monitor worker process for {ticker} (PID: {msg.get('pid','N/A')}) has stopped.")
                        monitor_running = False # Signal to exit main CLI loop
                    # else: unhandled system message type
                
                elif isinstance(msg, dict) and "action" in msg: # Messages from TickerMonitor
                    action = msg.get("action", "UNKNOWN_TM_MSG").upper()
                    # For CLI, print all TickerMonitor messages, or filter as desired
                    # Example: only print BUY/SELL/STOP_LOSS_CLOSE or INFO with errors
                    if action not in ["INFO"] or "error" in str(msg.get("status_reason","")).lower():                        # Basic print of the dict, or format it nicely
                        print(f"[MONITOR_MSG] {msg}")
                    # If you want more detailed CLI output for INFOs, add here.
                
                else: # Unexpected message format
                    print(f"[CLI_UNEXPECTED_MSG] Type: {type(msg)}, Content: {str(msg)[:200]}")
            
            # If no message, just loop. The timeout in poll() prevents busy-waiting.
            # Check if process died without sending "worker_stopped"
            if not monitor_proc.is_alive() and monitor_running:
                print(f"CLI Error: Monitor process for {ticker} (PID: {monitor_proc.pid}) exited unexpectedly.")
                monitor_running = False                
                break
            
            time.sleep(0.05) # Small sleep to prevent tight loop if poll timeout is very short

    except KeyboardInterrupt:
        print(f"\nReceived Ctrl+C. Stopping monitor {ticker} (PID: {monitor_proc.pid})...")
        if monitor_proc.is_alive():
            monitor_proc.terminate()
            monitor_proc.join(timeout=5)
            if monitor_proc.is_alive():
                monitor_proc.kill()
                monitor_proc.join(timeout=2)
        print(f"Monitor {ticker} terminated.")
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        print(f"CLI Unhandled Exception: {e}\n{tb_str}")

        if monitor_proc and monitor_proc.is_alive():            
            monitor_proc.terminate()
            monitor_proc.join(timeout=5)
            monitor_proc.join(timeout=10)

if __name__ == "__main__":
    main()
