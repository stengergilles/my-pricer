import pandas as pd
import pandas_ta as ta
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
    Calculates Bollinger Bands (BBands).
    """
    def __init__(self, 
                 df: pd.DataFrame, 
                 window: int = 20, 
                 num_std_dev: float = 2.0,
                 column: str = 'Close'):
        """
        Args:
            df: OHLCV DataFrame.
            window: The time period for the moving average.            num_std_dev: The number of standard deviations for the upper and lower bands.
            column: The DataFrame column to use for BBands calculation.
        """

        super().__init__(df)
        self.window = window

        self.num_std_dev = num_std_dev
        self.column = column
        
        if self.column not in self.df.columns:
            raise ValueError(f"Column '{self.column}' not found in DataFrame for Bollinger Bands calculation.")

        # Define and register signal column names and their orientations
        self.cross_lower_signal_col = f'BB_Cross_Lower_{self.window}_{self.num_std_dev}'
        self.cross_upper_signal_col = f'BB_Cross_Upper_{self.window}_{self.num_std_dev}'
        self.signal_orientations[self.cross_lower_signal_col] = 'buy'  # Price < lower band as a buy signal
        self.signal_orientations[self.cross_upper_signal_col] = 'sell' # Price > upper band as a sell signal

    def calculate(self) -> pd.DataFrame:
        """

        Calculates Bollinger Bands and adds Upper Band, Middle Band (SMA), Lower Band,
        Bandwidth, and Percent B columns to the DataFrame.
        Also adds signals for price crossing the upper or lower bands.
        """

        # Calculate BBands using pandas_ta functional call
        indicator_specific_df = ta.bbands(close=self.df[self.column],
                                           length=self.window,
                                           std=self.num_std_dev,
                                           append=False) # Should return only BBands columns

        if indicator_specific_df is None or indicator_specific_df.empty:
            print(f"Warning: pandas_ta.bbands returned empty or None for {self.column}. Skipping calculation.")
            return self.df


        # Assign new BBands columns to self.df
        # This assumes indicator_specific_df contains only the new columns.
        for col_name in indicator_specific_df.columns:
            self.df[col_name] = indicator_specific_df[col_name]        
        # Now that columns from indicator_specific_df are in self.df,
        # find the specific band columns that pandas-ta created.
        # Default pandas-ta names for bbands are like:
        # BBL_<length>_<std>, BBM_<length>_<std>, BBU_<length>_<std>
        # BBL_20_2.0, BBM_20_2.0, BBU_20_2.0 (if length=20, std=2.0)
                # Construct the expected names more directly
        # pandas-ta typically uses the length and std dev in the column names.
        # Example: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        # The .0 for std dev might be conditional based on pandas-ta version or if std is integer.
        # We will search for columns starting with BBL_ and BBU_ and trust pandas-ta's output.
        
        lower_band_col = next((col for col in indicator_specific_df.columns if col.startswith('BBL_')), None)
        upper_band_col = next((col for col in indicator_specific_df.columns if col.startswith('BBU_')), None)

        if lower_band_col and upper_band_col and (lower_band_col in self.df.columns) and (upper_band_col in self.df.columns):
            signal_lower_col_name = f'BB_Cross_Lower_{self.window}_{self.num_std_dev}'
            signal_upper_col_name = f'BB_Cross_Upper_{self.window}_{self.num_std_dev}'
            
            self.df[signal_lower_col_name] = (self.df[self.column] < self.df[lower_band_col])
            self.df[signal_upper_col_name] = (self.df[self.column] > self.df[upper_band_col])
            
            self.df[signal_lower_col_name] = self.df[signal_lower_col_name].fillna(False).astype(bool)
            self.df[signal_upper_col_name] = self.df[signal_upper_col_name].fillna(False).astype(bool)

            self.signal_orientations[signal_lower_col_name] = 'buy'
            self.signal_orientations[signal_upper_col_name] = 'sell'
        else:
            # Construct attempted names for logging, even if they weren't found or one was missing
            attempted_l_name = f"BBL_{self.window}_{self.num_std_dev}" # A common pattern
            attempted_u_name = f"BBU_{self.window}_{self.num_std_dev}"
            print(f"Warning: Could not reliably find Bollinger Band columns (searched for patterns like '{attempted_l_name}', '{attempted_u_name}' "
                  f"resulting in found lower: '{lower_band_col}', found upper: '{upper_band_col}') in pandas-ta output or self.df. Signals not generated.")
            
        return self.df
