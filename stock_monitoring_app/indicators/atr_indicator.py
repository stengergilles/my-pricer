import pandas as pd
import pandas_ta as ta
from .base_indicator import Indicator

class ATRIndicator(Indicator):
    """
    Calculates Average True Range (ATR).
    """
    def __init__(self, 
                 df: pd.DataFrame, 
                 window: int = 14):
        """
        Args:
            df: OHLCV DataFrame. Must contain 'High', 'Low', 'Close'.
            window: The time period for ATR calculation.        """
        super().__init__(df)
        # ATR requires High, Low, Close, which are already checked by base.
        self.window = window

    def calculate(self) -> pd.DataFrame:
        """
        Calculates ATR and adds 'ATR_<window>' column to the DataFrame.
        """
        # pandas-ta names it 'ATRr_window' if mamode is 'rma' (default)
        # or 'ATR_window' if append=False is used and then assigned.
        # Let's assign to ensure consistent naming.
        atr_series = self.df.ta.atr(high=self.df['High'], 
                                    low=self.df['Low'], 
                                    close=self.df['Close'], 
                                    length=self.window, 
                                    append=False)
        self.df[f'ATR_{self.window}'] = atr_series
        return self.df
