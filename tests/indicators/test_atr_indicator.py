import pytest
import pandas as pd
from stock_monitoring_app.indicators import ATRIndicator


# Uses sample_ohlcv_data fixture from conftest.py
def test_atr_calculation(sample_ohlcv_data):
    """Tests basic ATR calculation and column addition."""
    window = 14
    indicator = ATRIndicator(sample_ohlcv_data, window=window)
    result_df = indicator.calculate()

    expected_col_name = f'ATR_{window}'    
    assert expected_col_name in result_df.columns
    assert pd.api.types.is_numeric_dtype(result_df[expected_col_name])

    # Check for NaNs only at the beginning
    assert result_df[expected_col_name].iloc[window:].notna().all() 
    # ATR needs 'window' periods of TR

def test_atr_init_empty_df():
    """Tests ValueError on empty DataFrame initialization."""
    with pytest.raises(ValueError, match="Input DataFrame cannot be empty"):

        ATRIndicator(pd.DataFrame())

def test_atr_init_missing_ohlc(sample_ohlcv_data):
    """Tests ValueError if required OHLC columns are missing."""
    df_missing_high = sample_ohlcv_data.drop(columns=['High'])
    with pytest.raises(ValueError, match="DataFrame is missing required OHLC columns: High"):
        ATRIndicator(df_missing_high)

    df_missing_low = sample_ohlcv_data.drop(columns=['Low'])
    with pytest.raises(ValueError, match="DataFrame is missing required OHLC columns: Low"):
        ATRIndicator(df_missing_low)

    df_missing_close = sample_ohlcv_data.drop(columns=['Close'])
    with pytest.raises(ValueError, match="DataFrame is missing required OHLC columns: Close"):
        ATRIndicator(df_missing_close)

