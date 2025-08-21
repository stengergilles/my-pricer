
import unittest
from unittest.mock import patch
from pricer import LiveTrader
from datetime import datetime
import pandas as pd
from config import ATR_MULTIPLE

class TestLiveTrader(unittest.TestCase):

    @patch('pricer.calculate_hybrid_position_size')
    @patch('pricer.get_daily_volatility')
    def test_update_position_sizing(self, mock_get_daily_volatility, mock_calculate_hybrid_position_size):
        # Arrange
        mock_get_daily_volatility.return_value = 0.05 # 5% volatility
        mock_calculate_hybrid_position_size.return_value = 0.5 # 50% position size

        trader = LiveTrader(
            crypto_id='bitcoin',
            initial_capital=1000,
            trade_size_percentage=0.1,
            strategy_config={},
            params={},
            simulation_start_time=datetime.now(),
            win_rate=0.5,
            spread_percentage=0.01,
            slippage_percentage=0.0005,
            intermediate_stop_loss_percentage=0.1,
            best_config_name='test_config'
        )

        # Act
        trader.update_position_sizing()

        # Assert
        self.assertEqual(trader.trade_size_percentage, 0.5)
        mock_get_daily_volatility.assert_called_once_with('bitcoin')
        mock_calculate_hybrid_position_size.assert_called_once_with(
            'bitcoin', 
            trader.base_trade_size, 
            trader.recent_trade_results
        )

    @patch('pricer.calculate_atr')
    @patch('pricer.get_trade_signal')
    @patch.object(LiveTrader, 'fetch_latest_data')
    def test_execute_trade_step_trailing_stop_long(self, mock_fetch_latest_data, mock_get_trade_signal, mock_calculate_atr):
        # Arrange
        mock_fetch_latest_data.return_value = True
        mock_get_trade_signal.return_value = 'HOLD'
        mock_calculate_atr.return_value = pd.Series([2]) # Mock ATR value

        trader = LiveTrader(
            crypto_id='bitcoin',
            initial_capital=1000,
            trade_size_percentage=0.1,
            strategy_config={},
            params={
                'short_sma_period': 20, 'long_sma_period': 50,
                'rsi_overbought': 70, 'rsi_oversold': 30,
                'macd_fast_period': 12, 'macd_slow_period': 26, 'macd_signal_period': 9
            },
            simulation_start_time=datetime.now(),
            win_rate=0.5,
            spread_percentage=0.01,
            slippage_percentage=0.0005,
            intermediate_stop_loss_percentage=0.1,
            best_config_name='test_config'
        )
        trader.position = 'LONG'
        trader.entry_price = 100
        trader.highest_price_since_entry = 110
        trader.trailing_stop_loss = 105

        # Mock the data history
        data = {
            'timestamp': pd.to_datetime(['2023-01-01 12:00:00']),
            'price': [115], # New highest price
            'close': [115],
            'ask_price': [115.1],
            'bid_price': [114.9],
            'high': [116], # Add high/low for ATR calculation
            'low': [114]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        trader.df_history = df

        # Act
        trader.execute_trade_step()

        # Assert
        self.assertEqual(trader.highest_price_since_entry, 115)
        self.assertEqual(trader.trailing_stop_loss, 115 - (2 * ATR_MULTIPLE))

if __name__ == '__main__':
    unittest.main()
