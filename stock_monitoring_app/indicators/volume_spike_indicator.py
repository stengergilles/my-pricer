import pandas as pd
from .base_indicator import Indicator

class VolumeSpikeIndicator(Indicator):
    """

    Identifies volume spikes compared to a moving average of volume.
    """


    @staticmethod
    def get_search_space():
        return {
            "window": [10, 20, 30],
            # Try much smaller multipliers, assuming quote volume can be large and spikes are relative
            # These are just examples; they might need to be even smaller or have a different range
            # e.g., if typical volume is X, and a spike is X + 10%, multiplier is 1.1
            "spike_multiplier": [1.05, 1.1, 1.2, 1.3], # e.g. 5%, 10%, 20%, 30% above average
            "volume_col": ["Volume"],
        }

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

        super().__init__(df) # self.df is set here
        # self.data = df # This line is redundant as self.df is set by super() and should be used
        self.window = window

        # Check if DataFrame has enough data for the given window.
        if len(self.df) < self.window:
            raise ValueError(
                f"Insufficient data for {self.__class__.__name__} (window: {self.window}): "
                f"{len(self.df)} rows provided, requires at least {self.window} rows."
            )

        self.spike_multiplier = spike_multiplier
        self.volume_col = volume_col
        
        # Define signal column name based on params
        self.spike_signal_col = f'Volume_Spike_Signal_{self.window}_{self.spike_multiplier}'
        
        self.signal_orientations: dict[str, str] = {}
        # Assuming a volume spike is a bullish signal for this example
        self.signal_orientations[self.spike_signal_col] = 'buy' 

        if self.volume_col not in self.df.columns:
            raise ValueError(f"Volume column '{self.volume_col}' not found in DataFrame.")


    def calculate(self) -> pd.DataFrame:
        """Calculates the volume spike signal based on the given window and multiplier."""
        if self.df is None or self.df.empty: # Use self.df
            raise ValueError("Input DataFrame (self.df) is empty or None.")

        # Use self.volume_col which is set from parameters
        if self.volume_col not in self.df.columns:
            raise KeyError(f"'{self.volume_col}' column (from parameters) is missing in the input DataFrame.")



        # Use self.df for calculations
        volume_series = self.df[self.volume_col].fillna(0) # Fill NaNs in input volume with 0 before rolling

        # Ensure rolling_avg is based on a full window to be a stable baseline
        rolling_avg = volume_series.rolling(window=self.window, min_periods=self.window).mean()
        spike_threshold = rolling_avg * self.spike_multiplier
        
        # Use self.df to store the signal
        # Compare the original (potentially NaN-containing) volume series to the threshold
        # This ensures that if original volume was NaN, the comparison results in False (as NaN > X is False)        # and these will be handled by the subsequent fillna(False) on the signal column.
        self.df[self.spike_signal_col] = self.df[self.volume_col] > spike_threshold
        self.df[self.spike_signal_col] = self.df[self.spike_signal_col].fillna(False).astype(bool)

        return self.df
