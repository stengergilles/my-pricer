import pandas as pd
import pandas_ta as ta
from .base_indicator import Indicator

class MAIndicator(Indicator):    

    """
    Calculates Moving Averages (SMA or EMA).
    """
    def __init__(self, 
                 df: pd.DataFrame, 
                 window: int = 20, 
                 ma_type: str = 'sma', 
                 column: str = 'Close'):
        """
        Args:
            df: OHLCV DataFrame.
            window: The time period for the moving average.
            ma_type: Type of moving average ('sma' for Simple, 'ema' for Exponential).
            column: The DataFrame column to use for MA calculation.
        """
        super().__init__(df)
        self.window = window
        self.ma_type = ma_type.lower()
        self.column = column        
        if self.column not in self.df.columns:
            raise ValueError(f"Column '{self.column}' not found in DataFrame for MA calculation.")
        if self.ma_type not in ['sma', 'ema']:
            raise ValueError("ma_type must be 'sma' or 'ema'.")

    def calculate(self) -> pd.DataFrame:
        """
        Calculates the specified moving average and adds it as a new column.
        Column name will be like 'SMA_20_Close' or 'EMA_50_Open'.
        """
        ma_column_name = f'{self.ma_type.upper()}_{self.window}_{self.column}'
        
        if self.ma_type == 'sma':
            self.df[ma_column_name] = self.df.ta.sma(close=self.df[self.column], length=self.window, append=False)
        elif self.ma_type == 'ema':
            self.df[ma_column_name] = self.df.ta.ema(close=self.df[self.column], length=self.window, append=False)

        return self.df
    
    @staticmethod
    def get_search_space():
        return {
            "window": [10, 20, 50],
            "ma_type": ["sma", "ema"],
            "column": ["Close"],
        }

