import unittest
from unittest.mock import patch, MagicMock
import sys
import io
import os

# Adjust the path to import the main script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from volatile_crypto_optimizer_v2 import main

class TestVolatileCryptoOptimizerV2(unittest.TestCase):

    @patch('volatile_crypto_optimizer_v2.TradingEngine')
    @patch('volatile_crypto_optimizer_v2.setup_logging')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_successful_optimization(self, mock_stdout, mock_setup_logging, MockTradingEngine):
        # Arrange
        mock_engine_instance = MockTradingEngine.return_value

        # Mock get_strategies
        mock_engine_instance.get_strategies.return_value = [{'name': 'EMA_Only'}]

        # Mock get_volatile_cryptos
        mock_engine_instance.get_volatile_cryptos.return_value = [
            {'symbol': 'BTC', 'price_change_percentage_24h': 10.0},
            {'symbol': 'ETH', 'price_change_percentage_24h': 8.0}
        ]

        # Mock run_volatile_optimization
        mock_engine_instance.run_volatile_optimization.return_value = {
            'success': True,
            'total_cryptos': 2,
            'successful_optimizations': 2,
            'failed_optimizations': 0,
            'total_time': 120.5,
            'best_overall': {
                'crypto_info': {'symbol': 'BTC'},
                'crypto': 'bitcoin',
                'best_value': 15.0,
                'best_params': {'param1': 'value1'}
            }
        }

        # Simulate command-line arguments
        test_args = ['volatile_crypto_optimizer_v2.py', '--strategy', 'EMA_Only', '--n-trials', '1', '--top-count', '2', '--min-volatility', '5.0']
        
        with patch('sys.argv', test_args):
            # Act
            main()

            # Assert
            mock_setup_logging.assert_called_once()
            mock_engine_instance.get_strategies.assert_called_once()
            mock_engine_instance.get_volatile_cryptos.assert_called_once_with(min_volatility=5.0, limit=100)
            mock_engine_instance.run_volatile_optimization.assert_called_once_with(
                strategy_name='EMA_Only',
                n_trials=1,
                top_count=2,
                min_volatility=5.0
            )

            output = mock_stdout.getvalue()
            self.assertIn("Discovering volatile cryptocurrencies", output)
            self.assertIn("Selected 2 cryptos for optimization:", output)
            self.assertIn("BTC: 10.00%", output)
            self.assertIn("ETH: 8.00%", output)
            self.assertIn("Starting batch optimization with EMA_Only", output)
            self.assertIn("Batch optimization completed successfully!", output)
            self.assertIn("Best overall result:", output)
            self.assertIn("Crypto: BTC (bitcoin)", output)
            self.assertIn("Profit: 15.0%", output)
            self.assertIn("Parameters: {'param1': 'value1'}", output)

    @patch('volatile_crypto_optimizer_v2.TradingEngine')
    @patch('volatile_crypto_optimizer_v2.setup_logging')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.exit')
    def test_main_no_volatile_cryptos(self, mock_sys_exit, mock_stdout, mock_setup_logging, MockTradingEngine):
        # Arrange
        mock_engine_instance = MockTradingEngine.return_value
        mock_engine_instance.get_strategies.return_value = [{'name': 'EMA_Only'}]
        mock_engine_instance.get_volatile_cryptos.return_value = [] # No volatile cryptos

        test_args = ['volatile_crypto_optimizer_v2.py', '--strategy', 'EMA_Only']
        
        with patch('sys.argv', test_args):
            # Act
            with self.assertRaises(SystemExit) as cm:
                main()

            # Assert
            self.assertEqual(cm.exception.code, 1)
            mock_setup_logging.assert_called_once()
            mock_engine_instance.get_volatile_cryptos.assert_called_once()

            output = mock_stdout.getvalue()
            self.assertIn("No volatile cryptocurrencies found!", output)

    @patch('volatile_crypto_optimizer_v2.TradingEngine')
    @patch('volatile_crypto_optimizer_v2.setup_logging')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.exit')
    def test_main_unknown_strategy(self, mock_sys_exit, mock_stdout, mock_setup_logging, MockTradingEngine):
        # Arrange
        mock_engine_instance = MockTradingEngine.return_value
        mock_engine_instance.get_strategies.return_value = [{'name': 'AnotherStrategy'}] # Different strategy

        test_args = ['volatile_crypto_optimizer_v2.py', '--strategy', 'UnknownStrategy']
        
        with patch('sys.argv', test_args):
            # Act
            with self.assertRaises(SystemExit) as cm:
                main()

            # Assert
            self.assertEqual(cm.exception.code, 1)
            mock_setup_logging.assert_called_once()
            mock_engine_instance.get_strategies.assert_called_once()

            output = mock_stdout.getvalue()
            self.assertIn("Error: Unknown strategy 'UnknownStrategy'", output)
            self.assertIn("Available strategies: AnotherStrategy", output)

    @patch('volatile_crypto_optimizer_v2.TradingEngine')
    @patch('volatile_crypto_optimizer_v2.setup_logging')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.exit')
    def test_main_optimization_failure(self, mock_sys_exit, mock_stdout, mock_setup_logging, MockTradingEngine):
        # Arrange
        mock_engine_instance = MockTradingEngine.return_value
        mock_engine_instance.get_strategies.return_value = [{'name': 'EMA_Only'}]
        mock_engine_instance.get_volatile_cryptos.return_value = [
            {'symbol': 'BTC', 'price_change_percentage_24h': 10.0}
        ]
        mock_engine_instance.run_volatile_optimization.return_value = {
            'success': False,
            'error': 'Simulated optimization error'
        }

        test_args = ['volatile_crypto_optimizer_v2.py', '--strategy', 'EMA_Only']
        
        with patch('sys.argv', test_args):
            # Act
            with self.assertRaises(SystemExit) as cm:
                main()

            # Assert
            self.assertEqual(cm.exception.code, 1)
            mock_setup_logging.assert_called_once()
            mock_engine_instance.run_volatile_optimization.assert_called_once()

            output = mock_stdout.getvalue()
            self.assertIn("Batch optimization failed: Simulated optimization error", output)

    @patch('volatile_crypto_optimizer_v2.TradingEngine')
    @patch('volatile_crypto_optimizer_v2.setup_logging')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.exit')
    def test_main_exception_handling(self, mock_sys_exit, mock_stdout, mock_setup_logging, MockTradingEngine):
        # Arrange
        mock_engine_instance = MockTradingEngine.return_value
        mock_engine_instance.get_strategies.side_effect = Exception("Simulated unexpected error")

        test_args = ['volatile_crypto_optimizer_v2.py', '--strategy', 'EMA_Only']
        
        with patch('sys.argv', test_args):
            # Act
            with self.assertRaises(SystemExit) as cm:
                main()

            # Assert
            self.assertEqual(cm.exception.code, 1)
            mock_setup_logging.assert_called_once()
            mock_engine_instance.get_strategies.assert_called_once()

            output = mock_stdout.getvalue()
            self.assertIn("Batch optimization failed: Simulated unexpected error", output)

if __name__ == '__main__':
    unittest.main()