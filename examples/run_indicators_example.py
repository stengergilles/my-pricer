import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from stock_monitoring_app.indicators import (
    RSIIndicator,
    MACDIndicator,
    BollingerBandsIndicator,
    MAIndicator,
    BreakoutIndicator,
    ATRIndicator,
    VolumeSpikeIndicator
)
from stock_monitoring_app.fetchers import PolygonFetcher # To get some sample data
from stock_monitoring_app.config import settings


def create_placeholder_data(num_days=30):
    """Creates minimal placeholder OHLCV data if API fetching fails."""
    print(f"Creating placeholder data for {num_days} days.")

    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(num_days)]
    data = {
        'Open': [150 + i * 0.1 + (i % 5) - 2 for i in range(num_days)],  # Add some variation
        'High': [151 + i * 0.15 + (i % 3) for i in range(num_days)],
        'Low': [149 - i * 0.05 - (i % 4) + 1 for i in range(num_days)],
        'Close': [150.5 + i * 0.08 + (i % 7) - 3 for i in range(num_days)],
        'Volume': [1000000 + i * 10000 + (i % 10) * 5000 for i in range(num_days)]
    }
    df = pd.DataFrame(data, index=pd.DatetimeIndex(dates))
    # Ensure columns have correct dtype, especially for pandas-ta
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = pd.to_numeric(df[col])
    return df

def get_sample_data(ticker="AAPL", period="1mo", interval="1d", num_placeholder_days=60):
    """
    Tries to fetch real data using PolygonFetcher.
    Falls back to placeholder data if fetching fails or API key is missing.
    """
    print(f"\nAttempting to fetch data for {ticker} ({period}, {interval})...")
    if not settings.POLYGON_API_KEY:
        print("POLYGON_API_KEY not set. Using placeholder data for indicator examples.")
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
    # Get sample data (real or placeholder)
    sample_df = get_sample_data(ticker="AAPL", period="3mo", interval="1d")

    if sample_df.empty:
        print("Could not obtain data for indicator examples. Exiting.")
        sys.exit(1)

    print("\n--- Running Indicator Examples ---")
    print(f"Using data with {len(sample_df)} rows, from {sample_df.index.min()} to {sample_df.index.max()}")
    print("Original Data Sample (first 5 rows):")
    print(sample_df.head())    # --- RSI Indicator ---
    print("\n--- RSI Indicator Example ---")
    try:
        rsi_indicator = RSIIndicator(df=sample_df.copy(), period=14, rsi_oversold=30, rsi_overbought=70)
        rsi_df = rsi_indicator.calculate()        
        print("RSI DataFrame (last 5 rows with RSI and signals):")
        print(rsi_df[['Close', 'RSI_14', 'RSI_Oversold_Signal_14', 'RSI_Overbought_Signal_14']].tail())
        print("RSI Signal Orientations:", rsi_indicator.get_signal_orientations())
    except Exception as e:
        print(f"Error with RSIIndicator: {e}")

    # --- MACD Indicator ---
    print("\n--- MACD Indicator Example ---")
    try:
        macd_indicator = MACDIndicator(df=sample_df.copy(), fast_period=12, slow_period=26, signal_period=9)
        macd_df = macd_indicator.calculate()
        macd_cols_to_show = [col for col in macd_df.columns if 'MACD' in col]
        print("MACD DataFrame (last 5 rows with MACD lines and signals):")
        print(macd_df[['Close'] + macd_cols_to_show].tail())
        print("MACD Signal Orientations:", macd_indicator.get_signal_orientations())
    except Exception as e:
        print(f"Error with MACDIndicator: {e}")

    # --- Bollinger Bands Indicator ---
    print("\n--- Bollinger Bands Indicator Example ---")
    try:
        bb_indicator = BollingerBandsIndicator(df=sample_df.copy(), window=20, num_std_dev=2)
        bb_df = bb_indicator.calculate()
        bb_cols_to_show = [col for col in bb_df.columns if 'BB' in col or col.startswith('BBL_') or col.startswith('BBM_') or col.startswith('BBU_')]
        print("Bollinger Bands DataFrame (last 5 rows with Bands and signals):")
        print(bb_df[['Close'] + bb_cols_to_show].tail())
        print("Bollinger Bands Signal Orientations:", bb_indicator.get_signal_orientations())
    except Exception as e:
        print(f"Error with BollingerBandsIndicator: {e}")

    # --- MA Indicator (SMA) ---
    print("\n--- MA Indicator (SMA) Example ---")
    try:
        sma_indicator = MAIndicator(df=sample_df.copy(), window=20, ma_type='sma')
        sma_df = sma_indicator.calculate()
        print("SMA DataFrame (last 5 rows with SMA_20_Close):")
        print(sma_df[['Close', 'SMA_20_Close']].tail())
    except Exception as e:
        print(f"Error with MAIndicator (SMA): {e}")

    # --- MA Indicator (EMA) ---
    print("\n--- MA Indicator (EMA) Example ---")
    try:
        ema_indicator = MAIndicator(df=sample_df.copy(), window=50, ma_type='ema', column='Open')
        ema_df = ema_indicator.calculate()
        print("EMA DataFrame (last 5 rows with EMA_50_Open):")
        print(ema_df[['Open', 'EMA_50_Open']].tail())
    except Exception as e:
        print(f"Error with MAIndicator (EMA): {e}")

    # --- Breakout Indicator ---
    print("\n--- Breakout Indicator Example ---")
    try:
        breakout_indicator = BreakoutIndicator(df=sample_df.copy(), window=20)
        breakout_df = breakout_indicator.calculate()
        print("Breakout DataFrame (last 5 rows with Breakout signals):")
        print(breakout_df[['Close', 'Breakout_Bullish_Signal_20', 'Breakout_Bearish_Signal_20']].tail())
        print("Breakout Signal Orientations:", breakout_indicator.get_signal_orientations())
    except Exception as e:
        print(f"Error with BreakoutIndicator: {e}")    # --- ATR Indicator ---
    print("\n--- ATR Indicator Example ---")
    try:
        atr_indicator = ATRIndicator(df=sample_df.copy(), window=14)
        atr_df = atr_indicator.calculate()
        print("ATR DataFrame (last 5 rows with ATR_14):")
        print(atr_df[['Close', 'High', 'Low', 'ATR_14']].tail())
    except Exception as e:
        print(f"Error with ATRIndicator: {e}")

    # --- Volume Spike Indicator ---
    print("\n--- Volume Spike Indicator Example ---")
    if 'Volume' in sample_df.columns:
        try:
            volume_spike_indicator = VolumeSpikeIndicator(df=sample_df.copy(), window=20, spike_multiplier=2.0)
            volume_spike_df = volume_spike_indicator.calculate()
            print("Volume Spike DataFrame (last 5 rows with Volume_Spike_Signal):")
            print(volume_spike_df[['Volume', 'Volume_Spike_Signal_20_2.0']].tail())
        except Exception as e:
            print(f"Error with VolumeSpikeIndicator: {e}")
    else:
        print("Volume column not present in sample data, skipping VolumeSpikeIndicator example.")

    print("\nIndicator examples completed.")