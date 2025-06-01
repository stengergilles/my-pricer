
import pandas as pd
import numpy as np # Added for np.bool_ and np.integer
from typing import List, Dict, Type
from stock_monitoring_app.indicators.base_indicator import Indicator # Assuming this is the correct path

# Define signal constants
SIGNAL_BUY = 'BUY'
SIGNAL_SELL = 'SELL'
SIGNAL_HOLD = 'HOLD'

class BaseStrategy:    
    """
    A base class for trading strategies.
    It uses a configurable list of indicators to generate trading signals.
    """

    def __init__(self, indicator_configs: List[Dict]):
        """
        Initializes the BaseStrategy with a list of indicator configurations.

        Args:
            indicator_configs: A list of dictionaries, where each dictionary
                               configures an indicator.
                               Example:
                               [
                                   {
                                       'type': RSIIndicator,
                                       'params': {'period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70}
                                   },
                                   {
                                       'type': MACDIndicator,
                                       'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
                                   }
                               ]
        """
        self.indicator_configs = indicator_configs
        self.active_indicators: List[Indicator] = []

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates all configured indicators and adds their output to the DataFrame.

        Args:
            df: The input DataFrame with OHLCV data.


        Returns:
            A DataFrame augmented with columns from all calculated indicators.
        """
        processed_df = df.copy()
        self.active_indicators.clear() # Clear any previous instances

        for config in self.indicator_configs:
            IndicatorClass = config['type']
            params: Dict = config.get('params', {})

            if not issubclass(IndicatorClass, Indicator):
                raise TypeError(f"Configured type {IndicatorClass} is not a subclass of Indicator.")

            # Store the columns present in processed_df *before* this indicator runs
            cols_before_indicator = set(processed_df.columns)

            # Instantiate the indicator. It will make its own copy of processed_df.
            indicator_instance = IndicatorClass(df=processed_df, **params)
            
            # The calculate method modifies indicator_instance.df and returns it.
            # This returned df contains columns from processed_df plus new ones from this indicator.
            current_indicator_output_df = indicator_instance.calculate()

            # Add only the *newly added* columns by this indicator to processed_df
            for col in current_indicator_output_df.columns:
                if col not in cols_before_indicator:
                    processed_df[col] = current_indicator_output_df[col]
                # If the column already existed in cols_before_indicator,
                # and the indicator modified it, that modification is now in processed_df                # because indicator_instance was initialized with processed_df (copied),
                # so current_indicator_output_df already contains those updates.
                # However, if pandas-ta functions return a DataFrame that might re-include
                # original columns, this could still be an issue if not handled by indicators.
                # The current individual indicator logic (assigning ta result columns one-by-one)
                # should prevent indicators from re-adding base OHLCV columns.
                # This loop is primarily for new signal/value columns.

            self.active_indicators.append(indicator_instance)
            
        return processed_df


    def generate_signals(self, df_with_indicators: pd.DataFrame) -> pd.DataFrame:
        """Generates trading signals (BUY, SELL, HOLD) based on the calculated indicators.

        Args:
            df_with_indicators: DataFrame that includes the output from all indicators.

        Returns:
            DataFrame with an additional 'Strategy_Signal' column.
        """
        final_df = df_with_indicators.copy()
        
        # Default to HOLD
        final_df['Strategy_Signal'] = SIGNAL_HOLD

        if not self.active_indicators:
            print("Warning: No active indicators to generate signals from.")
            return final_df

        for i in range(len(final_df)):
            buy_triggered_this_row = False
            sell_triggered_this_row = False

            for indicator in self.active_indicators:
                orientations = indicator.get_signal_orientations()
                for signal_col_name, orientation in orientations.items():

                    if signal_col_name in final_df.columns:
                        signal_value_at_i = final_df[signal_col_name].iloc[i]
                        
                        # Skip if signal is NaN, None, or pd.NA
                        if pd.isna(signal_value_at_i):
                            continue

                        # Check for boolean signals (True for trigger)                        # This covers Python bool, numpy.bool_, and True from BooleanDtype (which converts to Python bool on scalar access if not NA)
                        if isinstance(signal_value_at_i, (bool, np.bool_)): 
                            if signal_value_at_i == True: # Explicitly check for True
                                if orientation == 'buy':
                                    buy_triggered_this_row = True
                                elif orientation == 'sell':
                                    sell_triggered_this_row = True
                        # Check for integer signals (1 for buy, -1 for sell, as per orientation)
                        elif isinstance(signal_value_at_i, (int, np.integer)):
                            if orientation == 'buy' and signal_value_at_i == 1:
                                buy_triggered_this_row = True
                            elif orientation == 'sell' and signal_value_at_i == -1:
                                sell_triggered_this_row = True
                    # else:
                        # This might happen if an indicator's calculate method didn't add the column
                        # or if the column is not boolean/integer as expected
                        # print(f"Warning: Signal column '{signal_col_name}' not found or not of expected type in DataFrame for row {i}.")

            # Determine final signal for the row
            # Using .loc with the row's index for assignment is safer
            row_index = final_df.index[i]
            if buy_triggered_this_row and not sell_triggered_this_row:
                final_df.loc[row_index, 'Strategy_Signal'] = SIGNAL_BUY
            elif sell_triggered_this_row and not buy_triggered_this_row:
                final_df.loc[row_index, 'Strategy_Signal'] = SIGNAL_SELL
            # If both are true, or neither are true, it remains HOLD (as per default)

        return final_df

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Runs the full strategy: calculates indicators and then generates signals.

        Args:
            df: The input DataFrame with OHLCV data.

        Returns:
            DataFrame with indicator columns and the 'Strategy_Signal' column.
        """
        if df.empty:
            print("Warning: Input DataFrame for strategy is empty. Returning empty DataFrame.")
            return pd.DataFrame(columns=list(df.columns) + ['Strategy_Signal'])
            
        df_with_indicators = self.calculate_indicators(df)
        df_with_signals = self.generate_signals(df_with_indicators)
        return df_with_signals

