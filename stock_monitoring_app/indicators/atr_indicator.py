import pandas as pd
from .base_indicator import Indicator

class ATRIndicator(Indicator):
    """
    Calculates Average True Range (ATR) using only pandas.
    """

    @staticmethod
    def get_search_space():
        return {
            "window": [10, 14, 20],
        }

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 14
    ):
        """
        Args:
            df: OHLCV DataFrame. Must contain 'High', 'Low', 'Close'.
            window: The time period for ATR calculation.
        """
        super().__init__(df)
        self.window = window

    def calculate(self) -> pd.DataFrame:
        """
        Calculates ATR and adds 'ATR_<window>' column to the DataFrame.
        Uses native pandas only.
        """
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close']
        prev_close = close.shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)

        atr = tr.rolling(window=self.window, min_periods=self.window).mean()

        self.df[f'ATR_{self.window}'] = atr
        return self.df
