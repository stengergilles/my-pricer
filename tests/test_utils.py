import pytest
import pandas as pd

def test_basic_ohlcv_fixture(basic_ohlcv):
    assert isinstance(basic_ohlcv, pd.DataFrame)
    assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(basic_ohlcv.columns)
    assert len(basic_ohlcv) >= 5
