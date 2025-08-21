
import unittest
import pandas as pd
from pricer import get_trade_signal

class TestPricer(unittest.TestCase):

    def test_get_trade_signal_hold(self):
        # Create a sample DataFrame
        data = {
            'timestamp': pd.to_datetime(['2023-01-01 12:00:00', '2023-01-01 12:01:00']),
            'price': [100, 101],
            'volume': [10, 12]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df['close'] = df['price']

        # Create a sample strategy config and params
        strategy_config = {
            'long_entry': ['sma_crossover'],
            'short_entry': ['sma_crossunder']
        }
        params = {
            'short_sma_period': 1,
            'long_sma_period': 2,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'macd_fast_period': 12,
            'macd_slow_period': 26,
            'macd_signal_period': 9
        }

        # Call the function
        signal = get_trade_signal(df, strategy_config, params)

        # Assert the result
        self.assertEqual(signal, 'HOLD')

    def test_get_trade_signal_long(self):
        # Create a sample DataFrame that should trigger a LONG signal
        data = {
            'timestamp': pd.to_datetime(['2023-01-01 12:00:00', '2023-01-01 12:01:00', '2023-01-01 12:02:00', '2023-01-01 12:03:00']),
            'price': [110, 100, 100, 110], # Price is increasing
            'volume': [10, 12, 15, 20]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df['close'] = df['price']

        # Create a sample strategy config and params
        strategy_config = {
            'long_entry': ['sma_crossover'],
            'short_entry': ['sma_crossunder']
        }
        params = {
            'short_sma_period': 2,
            'long_sma_period': 3,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'macd_fast_period': 12,
            'macd_slow_period': 26,
            'macd_signal_period': 9
        }

        # Call the function
        signal = get_trade_signal(df, strategy_config, params)

        # Assert the result
        self.assertEqual(signal, 'LONG')

    def test_get_trade_signal_short(self):
        # Create a sample DataFrame that should trigger a SHORT signal
        data = {
            'timestamp': pd.to_datetime(['2023-01-01 12:00:00', '2023-01-01 12:01:00', '2023-01-01 12:02:00', '2023-01-01 12:03:00']),
            'price': [100, 110, 110, 100], # Price is decreasing
            'volume': [10, 12, 15, 20]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df['close'] = df['price']

        # Create a sample strategy config and params
        strategy_config = {
            'long_entry': ['sma_crossover'],
            'short_entry': ['sma_crossunder']
        }
        params = {
            'short_sma_period': 2,
            'long_sma_period': 3,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'macd_fast_period': 12,
            'macd_slow_period': 26,
            'macd_signal_period': 9
        }

        # Call the function
        signal = get_trade_signal(df, strategy_config, params)

        # Assert the result
        self.assertEqual(signal, 'SHORT')

if __name__ == '__main__':
    unittest.main()
