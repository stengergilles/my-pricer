import pytest
import pandas as pd
from stock_monitoring_app.indicators.rsi_indicator import RSIIndicator

@pytest.fixture
def sample_ohlcv():
    # 30 days of fake prices
    data = {
        "Open": [100 + i for i in range(30)],
        "High": [101 + i for i in range(30)],
        "Low": [99 + i for i in range(30)],
        "Close": [100 + i + (i % 3 - 1) for i in range(30)],
        "Volume": [1000 + 10*i for i in range(30)],
    }
    return pd.DataFrame(data)

def test_rsi_calculation_basic(sample_ohlcv):
    indicator = RSIIndicator(sample_ohlcv, period=14, column="Close")
    result_df = indicator.calculate()
    rsi_col = f'RSI_{indicator.period}'
    assert rsi_col in result_df
    # Should have NaNs for at least the first 'period' rows, and valid values after that
    assert result_df[rsi_col].isnull().sum() >= indicator.period - 1
    assert result_df[rsi_col].dropna().between(0, 100).all()

def test_rsi_signals(sample_ohlcv):
    # Make prices drop to create oversold
    sample_ohlcv.loc[20:, 'Close'] = 50
    indicator = RSIIndicator(sample_ohlcv, period=14, rsi_oversold=30, rsi_overbought=70)
    result_df = indicator.calculate()
    oversold_col = f'RSI_Oversold_Signal_{indicator.period}'
    assert oversold_col in result_df
    # There should be at least some oversold signals
    assert result_df[oversold_col].any()
