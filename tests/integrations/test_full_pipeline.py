import pandas as pd
from stock_monitoring_app.indicators.rsi_indicator import RSIIndicator
from stock_monitoring_app.indicators.macd_indicator import MACDIndicator
from stock_monitoring_app.indicators.bollinger_bands_indicator import BollingerBandsIndicator

def test_pipeline_runs_without_error():
    df = pd.DataFrame({
        "Close": [100 + i for i in range(40)],
        "Open": [100 + i for i in range(40)],
        "High": [100 + i for i in range(40)],
        "Low": [100 + i for i in range(40)],
        "Volume": [1000] * 40,
    })
    rsi = RSIIndicator(df.copy())
    macd = MACDIndicator(df.copy())
    bb = BollingerBandsIndicator(df.copy())
    rsi_df = rsi.calculate()
    macd_df = macd.calculate()
    bb_df = bb.calculate()
    assert not rsi_df.empty
    assert not macd_df.empty
    assert not bb_df.empty
    # Check for at least one signal column in each
    assert any("RSI" in col for col in rsi_df.columns)
    assert any("MACD" in col for col in macd_df.columns)
    assert any("BB" in col for col in bb_df.columns)
