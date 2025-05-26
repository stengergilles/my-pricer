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
        Args:            df: OHLCV DataFrame. Must contain 'High', 'Low', 'Close'.
            window: The time period for ATR calculation.
        """
        super().__init__(df)
        self.window = window

        if len(self.df) < self.window + 1: # Needs window + 1 for prev_close and rolling
            raise ValueError(
                f"Insufficient data for {self.__class__.__name__} (window: {self.window}): "
                f"{len(self.df)} rows provided, requires at least {self.window + 1} rows."
            )

        self.atr_col_name = f'ATR_{self.window}'
        self.low_atr_signal_col = f'ATR_Low_Signal_{self.window}'
        self.high_atr_signal_col = f'ATR_High_Signal_{self.window}'

        # Example signal orientations:
        # Buy on low ATR (anticipating volatility increase / end of consolidation)
        # Sell on high ATR (anticipating volatility decrease / exhaustion)
        self.signal_orientations[self.low_atr_signal_col] = 'buy'
        self.signal_orientations[self.high_atr_signal_col] = 'sell'

    def calculate(self) -> pd.DataFrame:
        """
        Calculates ATR and adds 'ATR_<window>' column.
        Also adds example 'ATR_Low_Signal_<window>' and 'ATR_High_Signal_<window>' columns.
        """
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close']
        prev_close = close.shift(1)

        # Calculate True Range (TR)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr_series = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR
        atr_series = tr_series.rolling(window=self.window, min_periods=self.window).mean()
        self.df[self.atr_col_name] = atr_series

        # Generate example signals based on ATR relative to its own median
        # This ensures that changing 'window' can change the signals
        if not atr_series.dropna().empty:

            # Using a rolling median for a more dynamic threshold.
            # The window for the rolling median of ATR could be self.window or another value.
            # Using self.window here for consistency with ATR calculation window.
            # Ensure min_periods for median is reasonable, e.g., at least half the window or a fixed number.
            rolling_median_window = max(1, self.window // 2) # Example: half of ATR window, min 1
            atr_median_threshold = atr_series.rolling(window=self.window, min_periods=rolling_median_window).median()
            
            self.df[self.low_atr_signal_col] = (atr_series < atr_median_threshold)
            self.df[self.high_atr_signal_col] = (atr_series > atr_median_threshold)
            
            self.df[self.low_atr_signal_col] = self.df[self.low_atr_signal_col].fillna(False).astype(bool)
            self.df[self.high_atr_signal_col] = self.df[self.high_atr_signal_col].fillna(False).astype(bool)
        else:
            self.df[self.low_atr_signal_col] = False
            self.df[self.high_atr_signal_col] = False
            
        return self.df
