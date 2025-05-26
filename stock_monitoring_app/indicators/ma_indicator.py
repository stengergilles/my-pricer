import pandas as pd
from .base_indicator import Indicator

class MAIndicator(Indicator):
    """
    Calculates Simple Moving Average (SMA) or Exponential Moving Average (EMA) using pandas.
    """


    @staticmethod
    def get_search_space():
        return {
            # Try shorter windows more suitable for intraday 1-minute data (288 points)
            "window": [5, 8, 13, 21, 34], 
            "ma_type": ["sma", "ema"],
            "column": ["Close"] # Focusing on 'Close' for simplicity initially
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

        # Check if DataFrame has enough data for the given window.
        if len(self.df) < self.window:
            raise ValueError(
                f"Insufficient data for {self.__class__.__name__} (window: {self.window}): "
                f"{len(self.df)} rows provided, requires at least {self.window} rows."
            )
        self.ma_type = ma_type.lower()
        self.column = column

        # Signal names for MA crosses
        self.ma_col_name = f"{self.ma_type.upper()}_{self.window}_{self.column}"
        self.buy_signal_col = f"{self.ma_col_name}_Cross_Above"
        self.sell_signal_col = f"{self.ma_col_name}_Cross_Below"

        self.signal_orientations[self.buy_signal_col] = 'buy'
        self.signal_orientations[self.sell_signal_col] = 'sell'


    def calculate(self) -> pd.DataFrame:
        """
        Calculates MA and adds 'SMA_<window>_<column>' or 'EMA_<window>_<column>' column.
        Also generates buy/sell signals when the price crosses the MA.
        """
        price_source = self.df[self.column] # Price source for MA calculation and crosses

        if self.ma_type == "sma":
            ma_series = price_source.rolling(window=self.window, min_periods=self.window).mean()
        elif self.ma_type == "ema":
            ma_series = price_source.ewm(span=self.window, min_periods=self.window, adjust=False).mean()
        else:
            raise ValueError(f"Unknown ma_type: {self.ma_type}")

        self.df[self.ma_col_name] = ma_series

        # Generate cross signals
        # Price crosses above MA (buy signal)
        self.df[self.buy_signal_col] = (price_source > ma_series) & (price_source.shift(1) <= ma_series.shift(1))
        # Price crosses below MA (sell signal)
        self.df[self.sell_signal_col] = (price_source < ma_series) & (price_source.shift(1) >= ma_series.shift(1))

        # Ensure boolean type and fill NaNs (especially at the beginning due to shift)
        self.df[self.buy_signal_col] = self.df[self.buy_signal_col].fillna(False).astype(bool)
        self.df[self.sell_signal_col] = self.df[self.sell_signal_col].fillna(False).astype(bool)

        return self.df
