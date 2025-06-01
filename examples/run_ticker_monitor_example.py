#!/usr/bin/env python3
"""
Example script demonstrating how to use the TickerMonitor class.

The TickerMonitor is responsible for:
1. Continuously monitoring a specific ticker (stock or crypto)
2. Applying a trading strategy to real-time or near-real-time data
3. Generating trading signals and notifications
4. Managing position tracking

This example shows how to set up and run a TickerMonitor instance.
"""

import time
import multiprocessing as mp
from stock_monitoring_app.monitoring.ticker_monitor import TickerMonitor
from stock_monitoring_app.strategies.base_strategy import BaseStrategy
from stock_monitoring_app.indicators.moving_average import SimpleMovingAverage
from stock_monitoring_app.indicators.rsi import RSI

def create_example_strategy():
    """Create a simple strategy combining SMA crossover and RSI."""
    strategy = BaseStrategy()
    
    # Add a simple moving average crossover (fast crosses above slow = buy, below = sell)
    strategy.add_indicator(SimpleMovingAverage(window=20, column='close', name='sma_fast'))
    strategy.add_indicator(SimpleMovingAverage(window=50, column='close', name='sma_slow'))
    
    # Add RSI for overbought/oversold conditions
    strategy.add_indicator(RSI(window=14, column='close', name='rsi'))
    
    # Define signal generation rules
    def generate_signals(data):
        signals = []
        
        # Initialize with HOLD signals
        for i in range(len(data)):
            signals.append('HOLD')
        
        # Apply strategy rules starting from index where all indicators are available
        start_idx = max(50, 14)  # Max of SMA slow window and RSI window
        
        for i in range(start_idx, len(data)):
            # SMA crossover (fast crosses above slow)
            if (data['sma_fast'].iloc[i-1] <= data['sma_slow'].iloc[i-1] and 
                data['sma_fast'].iloc[i] > data['sma_slow'].iloc[i]):
                # Only buy if RSI is not overbought
                if data['rsi'].iloc[i] < 70:
                    signals[i] = 'BUY'
            
            # SMA crossover (fast crosses below slow)
            elif (data['sma_fast'].iloc[i-1] >= data['sma_slow'].iloc[i-1] and 
                  data['sma_fast'].iloc[i] < data['sma_slow'].iloc[i]):
                # Only sell if RSI is not oversold
                if data['rsi'].iloc[i] > 30:
                    signals[i] = 'SELL'
            
            # Additional rule: Sell if RSI is extremely overbought
            elif data['rsi'].iloc[i] > 80:
                signals[i] = 'SELL'
            
            # Additional rule: Buy if RSI is extremely oversold
            elif data['rsi'].iloc[i] < 20:
                signals[i] = 'BUY'
        
        return signals
    
    strategy.set_signal_generator(generate_signals)
    return strategy

def main():
    """Run a simple example of the TickerMonitor."""
    # Create a multiprocessing Queue for trade orders
    trade_order_queue = mp.Queue()
    
    # Create a TickerMonitor instance
    # Parameters:
    # - ticker: The stock/crypto symbol to monitor
    # - trade_order_queue: Queue to send trade signals
    # - entry_price: Initial price (0 if not in a position)
    # - process_name: Name for this monitoring process
    # - backtest_scope: Time frame for analysis ("intraday", "short", or "long")
    # - leverage: Trading leverage (1 = no leverage)
    # - stop_loss: Stop loss percentage (0.05 = 5%)
    monitor = TickerMonitor(
        ticker="AAPL",
        trade_order_queue=trade_order_queue,
        entry_price=0,  # Not in a position initially
        process_name="AAPL_Monitor",
        backtest_scope="intraday",  # Uses 1-minute intervals for 1 day
        leverage=1,
        stop_loss=0.05
    )
    
    # Set the strategy
    strategy = create_example_strategy()
    monitor.set_strategy(strategy)
    
    # Start monitoring
    print(f"Starting to monitor {monitor.ticker}...")
    monitor.start()
    
    try:
        # Run for a specified time or until interrupted
        run_time = 300  # Run for 5 minutes
        print(f"Monitor will run for {run_time} seconds. Press Ctrl+C to stop earlier.")
        
        start_time = time.time()
        while time.time() - start_time < run_time:
            # Check if there are any trade orders
            if not trade_order_queue.empty():
                order = trade_order_queue.get()
                print(f"Received trade order: {order}")
            
            time.sleep(1)  # Check queue every second
    
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user.")
    
    finally:
        # Stop the monitor
        print("Stopping monitor...")
        monitor.stop()
        print("Monitor stopped.")
        
        # Process any remaining orders in the queue
        while not trade_order_queue.empty():
            order = trade_order_queue.get()
            print(f"Remaining trade order: {order}")

if __name__ == "__main__":
    main()
