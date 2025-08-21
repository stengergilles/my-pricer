
import unittest
from unittest.mock import patch, MagicMock
import json
from optimize_bayesian import objective

class TestOptimizeBayesian(unittest.TestCase):

    @patch('subprocess.run')
    def test_objective_success(self, mock_subprocess_run):
        # Arrange
        mock_trial = MagicMock()
        mock_trial.suggest_int.side_effect = [10, 20, 10, 20, 10, 30, 12, 26, 9, 14]
        mock_trial.suggest_float.side_effect = [2.0, 0.01, 1.5]

        crypto = 'bitcoin'
        strategy = 'test_strategy'

        # Mock the subprocess result
        mock_process = MagicMock()
        mock_process.stdout = 'OPTIMIZER_RESULTS:{"total_profit_loss": 123.45, "total_trades": 10}'
        mock_subprocess_run.return_value = mock_process

        # Act
        result = objective(mock_trial, crypto, strategy)

        # Assert
        self.assertEqual(result, 123.45)
        mock_subprocess_run.assert_called_once()

    @patch('subprocess.run')
    def test_objective_no_results(self, mock_subprocess_run):
        # Arrange
        mock_trial = MagicMock()
        mock_trial.suggest_int.side_effect = [10, 20, 10, 20, 10, 30, 12, 26, 9, 14]
        mock_trial.suggest_float.side_effect = [2.0, 0.01, 1.5]

        crypto = 'bitcoin'
        strategy = 'test_strategy'

        # Mock the subprocess result
        mock_process = MagicMock()
        mock_process.stdout = 'Some other output'
        mock_subprocess_run.return_value = mock_process

        # Act
        result = objective(mock_trial, crypto, strategy)

        # Assert
        self.assertEqual(result, -1000000.0)

    @patch('subprocess.run')
    def test_objective_subprocess_error(self, mock_subprocess_run):
        # Arrange
        mock_trial = MagicMock()
        mock_trial.suggest_int.side_effect = [10, 20, 10, 20, 10, 30, 12, 26, 9, 14]
        mock_trial.suggest_float.side_effect = [2.0, 0.01, 1.5]

        crypto = 'bitcoin'
        strategy = 'test_strategy'

        # Mock the subprocess error
        mock_subprocess_run.side_effect = FileNotFoundError('File not found')

        # Act
        result = objective(mock_trial, crypto, strategy)

        # Assert
        self.assertEqual(result, -1000000.0)

if __name__ == '__main__':
    unittest.main()
