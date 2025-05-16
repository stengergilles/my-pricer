import pytest
import pandas as pd
from stock_monitoring_app.indicators import BollingerBandsIndicator



# Uses sample_ohlcv_data fixture from conftest.py
def test_bbands_calculation(sample_ohlcv_data):
    """Tests basic Bollinger Bands calculation and column addition."""
    window = 20
    std_dev = 2.0
    indicator = BollingerBandsIndicator(sample_ohlcv_data, window=window, num_std_dev=std_dev)
    result_df = indicator.calculate()

    # Dynamically find expected column names (more robust)
    lower_col = next((col for col in result_df.columns if col.startswith('BBL_')), None)
    middle_col = next((col for col in result_df.columns if col.startswith('BBM_')), None)
    upper_col = next((col for col in result_df.columns if col.startswith('BBU_')), None)
    bw_col = next((col for col in result_df.columns if col.startswith('BBB_')), None) # Bandwidth
    bp_col = next((col for col in result_df.columns if col.startswith('BBP_')), None) # Percent B

    assert lower_col is not None
    assert middle_col is not None
    assert upper_col is not None
    assert bw_col is not None
    assert bp_col is not None

    assert pd.api.types.is_numeric_dtype(result_df[lower_col])
    assert pd.api.types.is_numeric_dtype(result_df[middle_col])
    assert pd.api.types.is_numeric_dtype(result_df[upper_col])
    assert pd.api.types.is_numeric_dtype(result_df[bw_col])
    assert pd.api.types.is_numeric_dtype(result_df[bp_col])

    # Check NaNs at the beginning
    assert result_df[lower_col].iloc[window - 1:].notna().all()

    # Check signal columns were added correctly
    signal_lower_col = f'BB_Cross_Lower_{window}_{std_dev}'
    signal_upper_col = f'BB_Cross_Upper_{window}_{std_dev}'
    assert signal_lower_col in result_df.columns
    assert signal_upper_col in result_df.columns
    assert pd.api.types.is_bool_dtype(result_df[signal_lower_col])
    assert pd.api.types.is_bool_dtype(result_df[signal_upper_col])
    assert not result_df[signal_lower_col].isna().any() # Should be filled with False
    assert not result_df[signal_upper_col].isna().any()

def test_bbands_init_invalid_column(sample_ohlcv_data):
    """Tests ValueError if specified column doesn't exist."""
    with pytest.raises(ValueError, match="Column 'NonExistent' not found"):  
        BollingerBandsIndicator(sample_ohlcv_data, column='NonExistent')

def test_bbands_init_empty_df():
    """Tests ValueError on empty DataFrame initialization."""
    with pytest.raises(ValueError, match="Input DataFrame cannot be empty"):


        BollingerBandsIndicator(pd.DataFrame())

def test_bbands_init_missing_ohlc(sample_ohlcv_data):
    """Tests ValueError if required OHLC columns are missing."""
    df_missing = sample_ohlcv_data.drop(columns=['Open'])
    with pytest.raises(ValueError, match="DataFrame is missing required OHLC columns: Open"):
        BollingerBandsIndicator(df_missing)
