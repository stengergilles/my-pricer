import pandas as pd
from .base_indicator import Indicator

class MACDIndicator(Indicator):




    @staticmethod
    def get_search_space():
        return {
            # Wider spread between fast and slow, still relatively short for intraday
            "fast_period": [3, 5, 8], 
            "slow_period": [10, 15, 21], # Ensure slow > fast
            "signal_period": [3, 5, 7],     
            "column": ["Close"],
        }

    """
    Calculates MACD and generates cross signals.
    """
    def __init__(self, 
                 df: pd.DataFrame, 
                 fast_period: int = 12, 
                 slow_period: int = 26, 
                 signal_period: int = 9,
                 column: str = 'Close'):
        """
        Args:
            df: OHLCV DataFrame.
            fast_period: Period for the fast EMA.
            slow_period: Period for the slow EMA.
            signal_period: Period for the signal EMA.
            column: The DataFrame column to use for calculation (typically 'Close').
        """

        super().__init__(df)
        self.fast_period = fast_period
        self.slow_period = slow_period
        
        # Check if DataFrame has enough data for the slow_period (longest EMA).
        if len(self.df) < self.slow_period:
            raise ValueError(
                f"Insufficient data for {self.__class__.__name__} (slow_period: {self.slow_period}): "
                f"{len(self.df)} rows provided, requires at least {self.slow_period} rows."
            )
        
        self.signal_period = signal_period
        self.column = column

        if self.column not in self.df.columns:
            raise ValueError(f"Column '{self.column}' not found in DataFrame for MACD calculation.")

    def calculate(self) -> pd.DataFrame:
        """
        Calculates MACD, Signal, Histogram, and adds buy/sell cross signals.
        """
        price = self.df[self.column]
        ema_fast = price.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = price.ewm(span=self.slow_period, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.signal_period, adjust=False).mean()
        hist = macd - signal

        macd_col = f"MACD_{self.fast_period}_{self.slow_period}"
        signal_col = f"MACD_Signal_{self.signal_period}"
        hist_col = f"MACD_Hist_{self.fast_period}_{self.slow_period}_{self.signal_period}"

        self.df[macd_col] = macd
        self.df[signal_col] = signal
        self.df[hist_col] = hist

        # Generate cross signals
        signal_buy_col = f"MACD_Cross_Above_{self.fast_period}_{self.slow_period}_{self.signal_period}"
        signal_sell_col = f"MACD_Cross_Below_{self.fast_period}_{self.slow_period}_{self.signal_period}"

        self.df[signal_buy_col] = (macd > signal) & (macd.shift(1) <= signal.shift(1))
        self.df[signal_sell_col] = (macd < signal) & (macd.shift(1) >= signal.shift(1))

        self.df[signal_buy_col] = self.df[signal_buy_col].fillna(False).astype(bool)
        self.df[signal_sell_col] = self.df[signal_sell_col].fillna(False).astype(bool)

        self.signal_orientations[signal_buy_col] = "buy"
        self.signal_orientations[signal_sell_col] = "sell"

        return self.df
