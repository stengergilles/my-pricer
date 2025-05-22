import pytest
import pandas as pd
from stock_monitoring_app.indicators.macd_indicator import MACDIndicator

@pytest.fixture
def sample_ohlcv():
    data = {
        "Open": [100 + i for i in range(40)],
        "High": [101 + i for i in range(40)],
        "Low": [99 + i for i in range(40)],
        "Close": [100 + i for i in range(40)],
        "Volume": [1000 + 10*i for i in range(40)],
    }
    return pd.DataFrame(data)

def test_macd_columns_exist(sample_ohlcv):
    indicator = MACDIndicator(sample_ohlcv)
    result_df = indicator.calculate()
    assert f"MACD_12_26" in result_df
    assert f"MACD_Signal_9" in result_df
    assert f"MACD_Hist_12_26_9" in result_df

def test_macd_cross_signals(sample_ohlcv):
    # Manipulate Close to force a cross
    sample_ohlcv.loc[30:, "Close"] = 50
    indicator = MACDIndicator(sample_ohlcv)
    result_df = indicator.calculate()
    buy_col = f"MACD_Cross_Above_12_26_9"
    sell_col = f"MACD_Cross_Below_12_26_9"
    assert buy_col in result_df
    assert sell_col in result_df
    # At least one of them should be triggered at some point
    assert result_df[buy_col].any() or result_df[sell_col].any()
