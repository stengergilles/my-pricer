import pandas as pd
from .base_indicator import Indicator

class MAIndicator(Indicator):
    """
    Calculates Simple Moving Average (SMA) or Exponential Moving Average (EMA) using pandas.
    """

    @staticmethod
    def get_search_space():
        return {
            "window": [10, 20, 50, 100, 200],
            "ma_type": ["sma", "ema"],
            "column": ["Close", "Open", "High", "Low"]
        }

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        ma_type: str = "sma",
        column: str = "Close"
    ):
        """
        Args:
            df: OHLCV DataFrame.
            window: The time period for the moving average.
            ma_type: 'sma' for Simple, 'ema' for Exponential.
            column: Which column to calculate MA on.
        """
        super().__init__(df)
        self.window = window
        self.ma_type = ma_type.lower()
        self.column = column

    def calculate(self) -> pd.DataFrame:
        """
        Calculates MA and adds 'SMA_<window>_<column>' or 'EMA_<window>_<column>' column.
        """
        source = self.df[self.column]
        if self.ma_type == "sma":
            ma_series = source.rolling(window=self.window, min_periods=self.window).mean()
            col_name = f"SMA_{self.window}_{self.column}"
        elif self.ma_type == "ema":
            ma_series = source.ewm(span=self.window, min_periods=self.window, adjust=False).mean()
            col_name = f"EMA_{self.window}_{self.column}"
        else:
            raise ValueError(f"Unknown ma_type: {self.ma_type}")

        self.df[col_name] = ma_series
        return self.df
