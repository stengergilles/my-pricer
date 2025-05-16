import pandas as pd
from .base_indicator import Indicator

class VolumeSpikeIndicator(Indicator):
    """

    Identifies volume spikes compared to a moving average of volume.
    """

    def __init__(self,
                 df: pd.DataFrame, 
                 window: int = 20, 
                 spike_multiplier: float = 2.0,
                 volume_col: str = 'Volume'):
        """
        Args:
            df: OHLCV DataFrame. Must contain a volume column.
            window: The lookback period for the moving average of volume.
            spike_multiplier: The factor by which current volume must exceed average volume to be a spike.
            volume_col: Name of the volume column.
        """
        super().__init__(df)


        self.window = window
        self.spike_multiplier = spike_multiplier
        self.volume_col = volume_col
        self.signal_orientations: dict[str, str] = {} # Initialize, will remain empty for this indicator

        if self.volume_col not in self.df.columns:

            raise ValueError(f"Volume column '{self.volume_col}' not found in DataFrame.")

    def calculate(self) -> pd.DataFrame:
        """
        Adds 'Volume_Spike_Signal_<window>_<multiplier>' column.
        Signal: True if volume is a spike, False otherwise.
        """
        signal_col_name = f'Volume_Spike_Signal_{self.window}_{self.spike_multiplier}'
        
        # Calculate simple moving average of volume
        # We compare the current volume to the average *excluding* the current bar's volume,
        # hence the shift(1) after calculating the rolling mean.
        # Using min_periods=1 to get a value even if the window is not full at the start.
        avg_volume = self.df[self.volume_col].rolling(window=self.window, min_periods=1).mean().shift(1)
        
        # Identify spikes where current volume exceeds the average volume by the multiplier
        self.df[signal_col_name] = (self.df[self.volume_col] > (avg_volume * self.spike_multiplier))
        
        # Fill potential NaN values at the beginning (due to rolling mean/shift) with False
        self.df[signal_col_name] = self.df[signal_col_name].fillna(False)

        return self.df