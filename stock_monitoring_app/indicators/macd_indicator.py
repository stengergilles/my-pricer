import pandas as pd
import pandas_ta as ta
from .base_indicator import Indicator

class MACDIndicator(Indicator):

    @staticmethod
    def get_search_space():
        return {
            "fast_period": [8, 12, 15],
            "slow_period": [20, 26, 30],
            "signal_period": [7, 9, 12],
            "column": ["Close"],
        }

    """
    Calculates Moving Average Convergence Divergence (MACD).
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
            fast_period: The period for the fast EMA.
            slow_period: The period for the slow EMA.
            signal_period: The period for the signal line EMA.
            column: The DataFrame column to use for MACD calculation.
        """
        super().__init__(df)
        self.fast_period = fast_period
        self.slow_period = slow_period


        self.signal_period = signal_period
        self.column = column
        self.signal_orientations: dict[str, str] = {} # Initialize specific to this class instance

        if self.column not in self.df.columns:
            raise ValueError(f"Column '{self.column}' not found in DataFrame for MACD calculation.")

    def calculate(self) -> pd.DataFrame:
        """
        Calculates MACD and adds MACD line, signal line, and histogram to the DataFrame.
        Columns: 'MACD_F_S_Sig', 'MACD_Signal_F_S_Sig', 'MACD_Hist_F_S_Sig'
        (where F=fast_period, S=slow_period, Sig=signal_period)
        """



        # Calculate MACD using pandas_ta functional call
        indicator_specific_df = ta.macd(close=self.df[self.column],                                        fast=self.fast_period,
                                        slow=self.slow_period,
                                        signal=self.signal_period,
                                        append=False) # Should return only MACD columns

        if indicator_specific_df is None or indicator_specific_df.empty:
            print(f"Warning: pandas_ta.macd returned empty or None for {self.column}. Skipping calculation.")
            return self.df


        # Assign new MACD columns to self.df
        # This assumes indicator_specific_df contains only the new columns.
        for col_name in indicator_specific_df.columns:
            self.df[col_name] = indicator_specific_df[col_name]
        
        # Define expected column names for signal generation based on pandas-ta naming
        # These names are now known because indicator_specific_df's columns were just added to self.df
        macd_line_col = f'MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}'
        signal_line_col = f'MACDs_{self.fast_period}_{self.slow_period}_{self.signal_period}'
        # histogram_col = f'MACDh_{self.fast_period}_{self.slow_period}_{self.signal_period}' # Optional for signals, but good to know

        # Ensure the necessary columns for signals were added to self.df
        if macd_line_col not in self.df.columns or signal_line_col not in self.df.columns:
            print(f"Warning: MACD line ({macd_line_col}) or Signal line ({signal_line_col}) not found after pandas-ta calculation. Signals not generated.")
            return self.df

        # Generate Crossover Signals
        # Bullish crossover: MACD line crosses above the signal line
        # Check: MACD[current] > Signal[current] AND MACD[previous] < Signal[previous]
        bullish_crossover_col_name = f'MACD_Cross_Bullish_{self.fast_period}_{self.slow_period}_{self.signal_period}'
        self.df[bullish_crossover_col_name] = (
            (self.df[macd_line_col] > self.df[signal_line_col]) &
            (self.df[macd_line_col].shift(1) < self.df[signal_line_col].shift(1))
        ).fillna(False).astype(bool)

        # Bearish crossover: MACD line crosses below the signal line
        # Check: MACD[current] < Signal[current] AND MACD[previous] > Signal[previous]
        bearish_crossover_col_name = f'MACD_Cross_Bearish_{self.fast_period}_{self.slow_period}_{self.signal_period}'        
        self.df[bearish_crossover_col_name] = (
            (self.df[macd_line_col] < self.df[signal_line_col]) &
            (self.df[macd_line_col].shift(1) > self.df[signal_line_col].shift(1))
        ).fillna(False).astype(bool)

        # Populate signal orientations
        self.signal_orientations[bullish_crossover_col_name] = 'buy'
        self.signal_orientations[bearish_crossover_col_name] = 'sell'
        
        return self.df
