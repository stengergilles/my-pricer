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
        self.data = df  # Ensure `data` is initialized
        self.window = window
        self.spike_multiplier = spike_multiplier
        self.volume_col = volume_col
        self.signal_orientations: dict[str, str] = {} # Initialize, will remain empty for this indicator

        if self.volume_col not in self.df.columns:
            raise ValueError(f"Volume column '{self.volume_col}' not found in DataFrame.")

    def calculate(self) -> pd.DataFrame:
        """Calculates the volume spike signal based on the given window and multiplier."""
        if self.data is None or self.data.empty:
            raise ValueError("Input data is empty or None.")

        volume_col = 'Volume'
        if volume_col not in self.data.columns:
            raise KeyError(f"'{volume_col}' column is missing in the input data.")

        rolling_avg = self.data[volume_col].rolling(window=self.window, min_periods=1).mean()
        spike_threshold = rolling_avg * self.spike_multiplier

        signal_col = f'Volume_Spike_Signal_{self.window}_{self.spike_multiplier}'
        self.data[signal_col] = self.data[volume_col] > spike_threshold

        return self.data