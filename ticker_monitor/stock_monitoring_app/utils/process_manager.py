import multiprocessing as mp
import sys
import os # Required for TickerMonitor import path adjustment if necessary
import traceback # For detailed exception logging in worker

# Attempt to import TickerMonitor. Adjust path as necessary if this utility moves.
# Assuming this util is in stock_monitoring_app/utils/ and TickerMonitor is in stock_monitoring_app/monitoring/
try:
    from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
except ImportError:
    # This might happen if the module structure is different or paths are not set up.
    # For robustness, allow it to be None and handle in worker.
    print("ERROR in process_manager: TickerMonitor could not be imported. Monitoring will fail.", file=sys.stderr)
    TickerMonitor = None

class WriterToPipe:
    """Redirects stdout/stderr to a multiprocessing Pipe connection."""
    def __init__(self, conn, origin="stdout"):
        self.conn = conn
        self.origin = origin # "stdout" or "stderr"


    def write(self, s):
        if s.strip(): # Send only if there's non-whitespace content
            try:
                self.conn.send({"type": self.origin, "data": s, "pid": os.getpid()})
            except Exception:
                # If pipe is broken, can't do much.
                pass
    def flush(self):
        pass # Typically no-op for this kind of redirection

class PipeAsQueue:
    """Adapts a multiprocessing Pipe connection to behave like a Queue for TickerMonitor."""
    def __init__(self, conn):
        self.conn = conn

    def put(self, item):
        try:
            self.conn.send(item) # Item is usually a dict from TickerMonitor
        except Exception:
            # If pipe is broken.
            pass

def canonical_monitor_worker(ticker, entry_price, scope, leverage, stop_loss, conn):
    """
    The canonical worker function that runs in the child process.
    Sets up environment, instantiates TickerMonitor, and runs it.
    """
    # Redirect stdout and stderr of this child process    
    sys.stdout = WriterToPipe(conn, origin="stdout")
    sys.stderr = WriterToPipe(conn, origin="stderr")

    if TickerMonitor is None:
        print(f"ERROR [Worker-{ticker}]: TickerMonitor class not available. Cannot start monitor.", file=sys.stderr)
        conn.send({"type": "error", "data": f"WORKER_CRITICAL_ERROR: TickerMonitor class not imported/found for {ticker}.", "ticker": ticker})
        conn.close()
        return

    try:
        process_name = f"Monitor-{ticker}" # Consistent process naming prefix
        queue_like_adapter = PipeAsQueue(conn)

        monitor_instance = TickerMonitor(
            ticker=ticker,
            trade_order_queue=queue_like_adapter,
            entry_price=entry_price,
            process_name=process_name,
            backtest_scope=scope,
            leverage=leverage,
            stop_loss=stop_loss
        )

        # Attempt to load indicator configurations and send to parent
        # TickerMonitor._load_optimized_config_from_disk() prints its own INFO/ERROR messages via redirected stdout
        indicator_configs = monitor_instance._load_optimized_config_from_disk()
        if indicator_configs:
            conn.send({"type": "indicators_loaded", "data": indicator_configs, "ticker": ticker})
        # If load fails, TickerMonitor.run() will handle it (prints CRITICAL, then exits)

        monitor_instance.run() # This is a blocking call until the monitor stops or errors

    except Exception as e:
        # Catch any unexpected exceptions during TickerMonitor instantiation or if run() itself fails critically early
        tb_str = traceback.format_exc()
        print(f"CRITICAL_WORKER_EXCEPTION [Worker-{ticker}]: {e}\n{tb_str}", file=sys.stderr) # Goes via WriterToPipe
        conn.send({"type": "error", "data": f"WORKER_UNHANDLED_EXCEPTION for {ticker}: {e}\n{tb_str}", "ticker": ticker})
    finally:
        # Signal that the worker function is completing
        conn.send({"type": "worker_stopped", "ticker": ticker, "pid": os.getpid()})
        conn.close()


def launch_ticker_monitor_process(ticker: str, entry_price: float, scope: str, leverage: float = 1.0, stop_loss: float = 0.05):
    """
    Launches a new TickerMonitor process using the canonical_monitor_worker.    Args:
        ticker (str): The ticker symbol.
        entry_price (float): Initial capital allocation or entry price.
        scope (str): Monitoring scope (e.g., "intraday").
        leverage (float): Leverage for trading. Defaults to 1.0.
        stop_loss (float): Stop-loss percentage (e.g., 0.05 for 5%). Defaults to 0.05.

    Returns:
        tuple: (multiprocessing.Process, multiprocessing.Connection)
               The started process object and the parent's end of the pipe for communication.
               Returns (None, None) if process creation fails.
    """
    try:
        parent_conn, child_conn = mp.Pipe()
        process = mp.Process(target=canonical_monitor_worker,
            args=(ticker, entry_price, scope, leverage, stop_loss, child_conn),
            daemon=True # Ensure child process exits if parent exits
        )        
        process.start()
        # Child connection is passed to the child, parent should close its reference to child_conn
        child_conn.close()
        return process, parent_conn
    except Exception as e:
        # Log this error appropriately in a real app
        print(f"FATAL: Failed to launch monitor process for {ticker}: {e}", file=sys.stderr)
        return None, None

