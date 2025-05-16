import pytest
import pandas as pd
from stock_monitoring_app.indicators import RSIIndicator

def test_rsi_calculation(sample_ohlcv_data):
    """Tests basic RSI calculation and column addition."""
    indicator = RSIIndicator(sample_ohlcv_data, period=14, rsi_oversold=25, rsi_overbought=75)
    result_df = indicator.calculate()

    assert f'RSI_14' in result_df.columns
    assert f'RSI_Oversold_Signal_14' in result_df.columns
    assert f'RSI_Overbought_Signal_14' in result_df.columns
    assert pd.api.types.is_numeric_dtype(result_df[f'RSI_14'])
    assert pd.api.types.is_bool_dtype(result_df[f'RSI_Oversold_Signal_14'])
    assert pd.api.types.is_bool_dtype(result_df[f'RSI_Overbought_Signal_14'])
    # Check for NaNs only at the beginning
    assert result_df[f'RSI_14'].iloc[14:].notna().all() # RSI needs 'period' bars to calculate