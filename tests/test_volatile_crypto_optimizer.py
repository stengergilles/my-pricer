
import unittest
from unittest.mock import patch, MagicMock
from volatile_crypto_optimizer import get_top_volatile_cryptos, select_top_volatile, run_bayesian_optimization

class TestVolatileCryptoOptimizer(unittest.TestCase):

    @patch('requests.get')
    def test_get_top_volatile_cryptos(self, mock_requests_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 'bitcoin', 'price_change_percentage_24h': 5.0},
            {'id': 'ethereum', 'price_change_percentage_24h': -8.0},
            {'id': 'cardano', 'price_change_percentage_24h': 2.0},
        ]
        mock_requests_get.return_value = mock_response

        # Act
        result = get_top_volatile_cryptos()

        # Assert
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['id'], 'ethereum') # Most volatile
        self.assertEqual(result[1]['id'], 'bitcoin')

    def test_select_top_volatile(self):
        # Arrange
        coins = [
            {'id': 'ethereum', 'price_change_percentage_24h': -8.0},
            {'id': 'bitcoin', 'price_change_percentage_24h': 5.0},
            {'id': 'solana', 'price_change_percentage_24h': -6.0},
            {'id': 'cardano', 'price_change_percentage_24h': 2.0},
            {'id': 'dogecoin', 'price_change_percentage_24h': 1.0},
        ]

        # Act
        result = select_top_volatile(coins, count=3)

        # Assert
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['id'], 'bitcoin') # Top gainer
        self.assertEqual(result[1]['id'], 'ethereum') # Top loser
        self.assertEqual(result[2]['id'], 'cardano') # Second gainer

    @patch('subprocess.run')
    def test_run_bayesian_optimization(self, mock_subprocess_run):
        # Arrange
        mock_process = MagicMock()
        mock_process.stdout = 'Value (Total Profit/Loss): 123.45\nParams: \n    short_sma_period: 10'
        mock_subprocess_run.return_value = mock_process

        # Act
        result = run_bayesian_optimization('bitcoin', 'test_strategy')

        # Assert
        self.assertEqual(result['crypto_id'], 'bitcoin')
        self.assertEqual(result['strategy'], 'test_strategy')
        self.assertEqual(result['best_value'], 123.45)
        self.assertIn('short_sma_period', result['best_params'])

if __name__ == '__main__':
    unittest.main()
