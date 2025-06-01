import pandas as pd
from .base_indicator import Indicator

class BollingerBandsIndicator(Indicator):

    @staticmethod
    def get_search_space():
        return {
            "window": [15, 20, 25],
            "num_std_dev": [1.5, 2.0, 2.5],
            "column": ["Close"],
        }

    """
    Calculates Bollinger Bands and signals.
    """
    def __init__(self, 
                 df: pd.DataFrame, 
                 window: int = 20, 
                 num_std_dev: float = 2.0,
                 column: str = 'Close'):
        """
        Args:
            df: OHLCV DataFrame.
            window: The rolling window size for the moving average.
            num_std_dev: Number of standard deviations for the bands.
            column: The DataFrame column to use for calculation (typically 'Close').
        """


        super().__init__(df)
        self.window = window

        # Check if DataFrame has enough data for the given window.
        if len(self.df) < self.window:            raise ValueError(
                f"Insufficient data for {self.__class__.__name__} (window: {self.window}): "
                f"{len(self.df)} rows provided, requires at least {self.window} rows."
            )
        self.num_std_dev = num_std_dev
        self.column = column

        if self.column not in self.df.columns:
            raise ValueError(f"Column '{self.column}' not found in DataFrame for Bollinger Bands calculation.")

    def calculate(self) -> pd.DataFrame:
        """
        Calculates Bollinger Bands and adds columns:
        - BBL_{window}_{num_std_dev}: Lower band
        - BBM_{window}_{num_std_dev}: Middle band (SMA)
        - BBU_{window}_{num_std_dev}: Upper band
        Also generates buy/sell signals:
        - BB_Cross_Lower_{window}_{num_std_dev}: True if price crosses below lower band
        - BB_Cross_Upper_{window}_{num_std_dev}: True if price crosses above upper band
        """
        price = self.df[self.column]
        sma = price.rolling(window=self.window, min_periods=self.window).mean()
        std = price.rolling(window=self.window, min_periods=self.window).std()

        lower_band = sma - self.num_std_dev * std
        upper_band = sma + self.num_std_dev * std

        lower_band_col = f'BBL_{self.window}_{self.num_std_dev}'
        middle_band_col = f'BBM_{self.window}_{self.num_std_dev}'
        upper_band_col = f'BBU_{self.window}_{self.num_std_dev}'

        self.df[lower_band_col] = lower_band
        self.df[middle_band_col] = sma
        self.df[upper_band_col] = upper_band

        # Generate signals: price crosses below lower band (buy), above upper band (sell)
        signal_lower_col_name = f'BB_Cross_Lower_{self.window}_{self.num_std_dev}'
        signal_upper_col_name = f'BB_Cross_Upper_{self.window}_{self.num_std_dev}'

        self.df[signal_lower_col_name] = (price < lower_band)
        self.df[signal_upper_col_name] = (price > upper_band)

        # Fill signal NaNs with False and ensure boolean type
        self.df[signal_lower_col_name] = self.df[signal_lower_col_name].fillna(False).astype(bool)
        self.df[signal_upper_col_name] = self.df[signal_upper_col_name].fillna(False).astype(bool)

        self.signal_orientations[signal_lower_col_name] = 'buy'
        self.signal_orientations[signal_upper_col_name] = 'sell'

        return self.df
