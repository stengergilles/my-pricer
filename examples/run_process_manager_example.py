#!/usr/bin/env python3
"""
Example script demonstrating how to use the ProcessManager class.

The ProcessManager is responsible for:
1. Creating and managing multiple ticker monitoring processes
2. Handling inter-process communication
3. Collecting and processing trade signals from multiple monitors
4. Providing a unified interface for monitoring multiple assets

This example shows how to set up and run multiple ticker monitors using ProcessManager.
"""

import time
import multiprocessing as mp
from stock_monitoring_app.utils.process_manager import ProcessManager
from stock_monitoring_app.strategies.base_strategy import BaseStrategy
from stock_monitoring_app.indicators.moving_average import SimpleMovingAverage
from stock_monitoring_app.indicators.rsi import RSI

def main():
    """Run a simple example of the ProcessManager with multiple ticker monitors."""
    # Create a ProcessManager instance
    process_manager = ProcessManager()
    
    # Define tickers to monitor with their parameters
    tickers_to_monitor = [
        {
            "ticker": "AAPL",
            "entry_price": 0,  # Not in a position initially
            "scope": "intraday",  # Uses 1-minute intervals for 1 day
            "leverage": 1,
            "stop_loss": 0.05
        },
        {
            "ticker": "MSFT",
            "entry_price": 0,
            "scope": "short",  # Uses 15-minute intervals for 1 week
            "leverage": 1,
            "stop_loss": 0.05
        },
        {
            "ticker": "bitcoin",  # Cryptocurrency example
            "entry_price": 0,
            "scope": "long",  # Uses daily intervals for 1 month
            "leverage": 1,
            "stop_loss": 0.07
        }
    ]
    
    # Start monitoring processes for each ticker
    for ticker_config in tickers_to_monitor:
        process_manager.start_monitor(
            ticker=ticker_config["ticker"],
            entry_price=ticker_config["entry_price"],
            scope=ticker_config["scope"],
            leverage=ticker_config["leverage"],
            stop_loss=ticker_config["stop_loss"]
        )
    
    print(f"Started monitoring {len(tickers_to_monitor)} tickers.")
    
    try:
        # Run for a specified time or until interrupted
        run_time = 300  # Run for 5 minutes
        print(f"Monitors will run for {run_time} seconds. Press Ctrl+C to stop earlier.")
        
        start_time = time.time()
        while time.time() - start_time < run_time:
            # Process any messages from the monitors
            messages = process_manager.collect_messages(timeout=0.1)
            
            for msg in messages:
                # Handle different types of messages
                if msg.get("type") == "stdout" or msg.get("type") == "stderr":
                    # Log output from monitor processes
                    process_id = msg.get("pid", "unknown")
                    print(f"[Process {process_id}] {msg.get('data', '')}")
                
                elif msg.get("type") == "trade_signal":
                    # Process trade signals
                    ticker = msg.get("ticker")
                    action = msg.get("action")
                    price = msg.get("price")
                    timestamp = msg.get("timestamp")
                    
                    print(f"Trade Signal: {action} {ticker} at ${price} ({timestamp})")
                    
                    # Here you would implement your trade execution logic
                    # For example, calling a broker API to place orders
            
            # Sleep briefly to avoid high CPU usage
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user.")
    
    finally:
        # Stop all monitors
        print("Stopping all monitors...")
        process_manager.stop_all_monitors()
        print("All monitors stopped.")
        
        # Process any remaining messages
        remaining_messages = process_manager.collect_messages(timeout=0.5)
        if remaining_messages:
            print(f"Processing {len(remaining_messages)} remaining messages...")
            # Process remaining messages (simplified here)
            for msg in remaining_messages:
                if msg.get("type") == "trade_signal":
                    print(f"Remaining trade signal: {msg}")

if __name__ == "__main__":
    # Set the start method for multiprocessing
    # 'spawn' is more compatible across platforms but slower
    # 'fork' is faster but can cause issues with some resources
    mp.set_start_method('spawn')
    main()
