import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from stock_monitoring_app.strategies.base_strategy import BaseStrategy, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from stock_monitoring_app.indicators import RSIIndicator, MACDIndicator
from stock_monitoring_app.fetchers import PolygonFetcher # To get some sample data
from stock_monitoring_app.config import settings

def create_placeholder_data(num_days=60):
    """Creates minimal placeholder OHLCV data if API fetching fails."""
    print(f"Creating placeholder data for {num_days} days for strategy example.")
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(num_days)]    
    data = {
        'Open': [150 + i * 0.1 + (i % 5) - 2 for i in range(num_days)],
        'High': [151 + i * 0.15 + (i % 3) for i in range(num_days)],
        'Low': [149 - i * 0.05 - (i % 4) + 1 for i in range(num_days)],
        'Close': [150.5 + i * 0.08 + (i % 7) - 3 for i in range(num_days)],        'Volume': [1000000 + i * 10000 + (i % 10) * 5000 for i in range(num_days)]
    }    
    df = pd.DataFrame(data, index=pd.DatetimeIndex(dates))
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = pd.to_numeric(df[col])
    return df

def get_sample_data_for_strategy(ticker="MSFT", period="3mo", interval="1d", num_placeholder_days=100):
    """
    Tries to fetch real data for strategy example. Falls back to placeholder.
    """
    print(f"\nAttempting to fetch data for {ticker} ({period}, {interval}) for strategy example...")
    if not settings.POLYGON_API_KEY:
        print("POLYGON_API_KEY not set. Using placeholder data for strategy example.")
        return create_placeholder_data(num_placeholder_days)

    try:
        fetcher = PolygonFetcher()
        df = fetcher.fetch_data(identifier=ticker, period=period, interval=interval)
        if df is not None and not df.empty:
            print(f"Successfully fetched {len(df)} data points for {ticker}.")
            return df
        else:
            print(f"Fetching data for {ticker} returned empty or None. Using placeholder data.")
            return create_placeholder_data(num_placeholder_days)
    except Exception as e:
        print(f"Error fetching real data for {ticker}: {e}. Using placeholder data.")
        return create_placeholder_data(num_placeholder_days)

if __name__ == "__main__":
    # Get sample data
    data_df = get_sample_data_for_strategy()

    if data_df.empty:
        print("Could not obtain data for strategy example. Exiting.")
        sys.exit(1)

    print("\n--- Running BaseStrategy Example ---")
    print("Original Data Sample (first 3 rows):")
    print(data_df.head(3))

    # Define indicator configurations
    indicator_configs = [
        {
            'type': RSIIndicator,
            'params': {'period': 14, 'column': 'Close', 'rsi_oversold': 30, 'rsi_overbought': 70}
        },
        {
            'type': MACDIndicator,
            'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9, 'column': 'Close'}
        }        # Add more indicators here if desired
    ]

    # Initialize the strategy
    strategy = BaseStrategy(indicator_configs=indicator_configs)

    # Run the strategy
    print("\nRunning strategy (calculating indicators and generating signals)...")
    results_df = strategy.run(data_df.copy()) # Pass a copy to keep original data_df unchanged

    print("\nStrategy Results (last 10 rows with signals):")
    # Show relevant columns: Close, all RSI signals, all MACD signals, and Strategy_Signal
    cols_to_show = ['Close']
    for col in results_df.columns:
        if 'RSI_' in col or 'MACD_' in col or 'Strategy_Signal' in col:
            cols_to_show.append(col)
    print(results_df[cols_to_show].tail(10))

    print("\nSignal Summary:")
    if 'Strategy_Signal' in results_df.columns:
        signal_counts = results_df['Strategy_Signal'].value_counts()
        print(signal_counts)
        if SIGNAL_BUY not in signal_counts: print(f"{SIGNAL_BUY}: 0")
        if SIGNAL_SELL not in signal_counts: print(f"{SIGNAL_SELL}: 0")
        if SIGNAL_HOLD not in signal_counts: print(f"{SIGNAL_HOLD}: 0")

    else:
        print("Strategy_Signal column not found in results.")

    print("\nBaseStrategy example completed.")
