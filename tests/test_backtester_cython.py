import unittest
import numpy as np
import backtester_cython

class TestBacktesterCython(unittest.TestCase):

    def test_run_backtest_cython_long_trade(self):
        # Arrange
        prices = np.array([100, 110, 120, 110, 100], dtype=np.float64)
        long_entry = np.array([1, 0, 0, 0, 0], dtype=np.uint8)
        short_entry = np.zeros(5, dtype=np.uint8)
        long_exit = np.array([0, 0, 0, 1, 0], dtype=np.uint8)
        short_exit = np.zeros(5, dtype=np.uint8)
        atr_values = np.array([1, 1, 1, 1, 1], dtype=np.float64)
        atr_multiple = 2.0
        fixed_stop_loss_percentage = 0.1
        take_profit_multiple = 2.0
        initial_capital = 1000.0
        spread_percentage = 0.01
        slippage_percentage = 0.0005
        daily_volatility = 0.05

        # Act
        results = backtester_cython.run_backtest_cython(
            prices, long_entry, short_entry, long_exit, short_exit,
            atr_values, atr_multiple, fixed_stop_loss_percentage,
            take_profit_multiple, initial_capital, spread_percentage,
            slippage_percentage, daily_volatility
        )

        # Assert
        self.assertEqual(results['total_trades'], 1)
        self.assertEqual(results['winning_trades'], 1)
        self.assertEqual(results['losing_trades'], 0)
        self.assertGreater(results['final_capital'], initial_capital)

if __name__ == '__main__':
    unittest.main()