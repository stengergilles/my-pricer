import pandas as pd
from .base_indicator import Indicator

class RSIIndicator(Indicator):

    @staticmethod
    def get_search_space():
        return {
            "period": [10, 14, 20],
            "rsi_oversold": [25, 30, 35],
            "rsi_overbought": [65, 70, 75],
            "column": ["Close"],
        }

    """
    Calculates the Relative Strength Index (RSI) and signals.
    """
    def __init__(self, 
                 df: pd.DataFrame, 
                 period: int = 14, 
                 column: str = 'Close',
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70):
        """
        Args:
            df: OHLCV DataFrame.
            period: The time period for RSI calculation.
            column: The DataFrame column to use for RSI calculation (typically 'Close').
            rsi_oversold: The RSI level below which an asset is considered oversold.
            rsi_overbought: The RSI level above which an asset is considered overbought.
        """

        super().__init__(df)
        self.period = period

        self.column = column
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        
        if self.column not in self.df.columns:
            raise ValueError(f"Column '{self.column}' not found in DataFrame for RSI calculation.")

        # Define and register signal column names and their orientations
        self.oversold_signal_col = f'RSI_Oversold_Signal_{self.period}'
        self.overbought_signal_col = f'RSI_Overbought_Signal_{self.period}'
        self.signal_orientations[self.oversold_signal_col] = 'buy'  # Buying when oversold
        self.signal_orientations[self.overbought_signal_col] = 'sell' # Selling when overbought

    def calculate(self) -> pd.DataFrame:
        """
        Calculates RSI and adds 'RSI_<period>', 'RSI_Oversold_Signal',
        and 'RSI_Overbought_Signal' columns to the DataFrame.
        """
        close = self.df[self.column]
        delta = close.diff()

        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # Calculate average gain and loss
        avg_gain = gain.rolling(window=self.period, min_periods=self.period).mean()
        avg_loss = loss.rolling(window=self.period, min_periods=self.period).mean()

        # Use the Wilder smoothing method after the first window
        avg_gain = avg_gain.copy()
        avg_loss = avg_loss.copy()

        for i in range(self.period, len(self.df)):
            if i == self.period:
                continue  # already computed
            avg_gain.iat[i] = (avg_gain.iat[i - 1] * (self.period - 1) + gain.iat[i]) / self.period
            avg_loss.iat[i] = (avg_loss.iat[i - 1] * (self.period - 1) + loss.iat[i]) / self.period

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        rsi_col_name = f'RSI_{self.period}'
        self.df[rsi_col_name] = rsi

        # Generate signals
        oversold_signal_col_name = f'RSI_Oversold_Signal_{self.period}'
        overbought_signal_col_name = f'RSI_Overbought_Signal_{self.period}'

        self.df[oversold_signal_col_name] = (self.df[rsi_col_name] < self.rsi_oversold)
        self.df[overbought_signal_col_name] = (self.df[rsi_col_name] > self.rsi_overbought)

        # Populate signal orientations
        self.signal_orientations[oversold_signal_col_name] = 'buy'
        self.signal_orientations[overbought_signal_col_name] = 'sell'

        return self.df
