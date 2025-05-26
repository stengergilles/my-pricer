import pandas as pd
from .base_indicator import Indicator

class BreakoutIndicator(Indicator):

    @staticmethod
    def get_search_space():
        return {
            "window": [10, 20, 30],
            # Add more parameters here if your indicator supports/needs them
        }

    """
    Identifies price breakouts above a recent high or below a recent low.
    """
    def __init__(self,
                 df: pd.DataFrame,
                 window: int = 20,
                 high_col: str = 'High',
                 low_col: str = 'Low',
                 close_col: str = 'Close'):
        """
        Args:
            df: OHLCV DataFrame.
            window: The lookback period to determine recent high/low.
            high_col: Name of the high price column.
            low_col: Name of the low price column.
            close_col: Name of the close price column.
        """

        super().__init__(df)
        self.window = window

        # Rolling max/min needs 'window' periods for first value, then shift(1).
        # So, to get at least one comparable value, len(df) >= window + 1.
        if len(self.df) < self.window + 1:
            raise ValueError(
                f"Insufficient data for {self.__class__.__name__} (window: {self.window}): "
                f"{len(self.df)} rows provided, requires at least {self.window + 1} rows."
            )
        self.high_col = high_col

        self.low_col = low_col
        self.close_col = close_col

        # Populate signal orientations (the attribute self.signal_orientations is initialized in super().__init__())
        # self.signal_orientations: dict[str, str] = {} # This line was redundant and has been removed.
        # Ensure these names match the columns generated in the calculate() method
        bullish_signal_col_name = f'Breakout_Bullish_Signal_{self.window}'
        bearish_signal_col_name = f'Breakout_Bearish_Signal_{self.window}'        
        self.signal_orientations[bullish_signal_col_name] = 'buy' # Bullish breakout is a buy signal
        self.signal_orientations[bearish_signal_col_name] = 'sell' # Bearish breakout is a sell signal

        # Check for required columns
        for col in [high_col, low_col, close_col]:
            if col not in self.df.columns:
                raise ValueError(f"Column '{col}' not found in DataFrame for Breakout calculation.")

    def calculate(self) -> pd.DataFrame:
        """
        Adds 'Breakout_Bullish_Signal_<window>' and 'Breakout_Bearish_Signal_<window>' columns.
        - Breakout_Bullish_Signal: True for bullish breakout, False otherwise.
        - Breakout_Bearish_Signal: True for bearish breakout, False otherwise.
        """
        bullish_signal_col_name = f'Breakout_Bullish_Signal_{self.window}'
        bearish_signal_col_name = f'Breakout_Bearish_Signal_{self.window}'

        # Calculate recent high and low (excluding current bar, so shift(1))
        recent_high = self.df[self.high_col].rolling(window=self.window, min_periods=self.window).max().shift(1)
        recent_low = self.df[self.low_col].rolling(window=self.window, min_periods=self.window).min().shift(1)

        # Bullish breakout: Close breaks above recent N-period high
        bullish_breakout_condition = (self.df[self.close_col] > recent_high)
        self.df[bullish_signal_col_name] = bullish_breakout_condition.fillna(False).astype(bool)

        # Bearish breakout: Close breaks below recent N-period low
        bearish_breakout_condition = (self.df[self.close_col] < recent_low)
        self.df[bearish_signal_col_name] = bearish_breakout_condition.fillna(False).astype(bool)

        return self.df

