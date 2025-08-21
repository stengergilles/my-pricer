
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import requests
from data import get_crypto_data, get_crypto_data_merged

class TestData(unittest.TestCase):

    @patch('requests.get')
    def test_get_crypto_data_success(self, mock_requests_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = [1, 2, 3]
        mock_requests_get.return_value = mock_response

        # Act
        result = get_crypto_data('bitcoin', 1)

        # Assert
        self.assertEqual(result, [1, 2, 3])

    @patch('requests.get')
    def test_get_crypto_data_http_error(self, mock_requests_get):
        # Arrange
        mock_requests_get.side_effect = requests.exceptions.HTTPError('HTTP Error')

        # Act
        result = get_crypto_data('bitcoin', 1)

        # Assert
        self.assertIsNone(result)

    @patch('data.get_crypto_data')
    def test_get_crypto_data_merged(self, mock_get_crypto_data):
        # Arrange
        mock_get_crypto_data.return_value = [
            [1672531200000, 100, 110, 90, 105],
            [1672534800000, 105, 115, 95, 110],
        ]

        # Act
        result = get_crypto_data_merged('bitcoin', 1)

        # Assert
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['open'], 100)

if __name__ == '__main__':
    unittest.main()
