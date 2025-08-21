
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

class TestChart(unittest.TestCase):

    @patch('chart.mpf.plot')
    def test_generate_chart(self, mock_mpf_plot):
        from chart import generate_chart
        import importlib
        import chart
        importlib.reload(chart)
        # Arrange
        data = {
            'timestamp': [datetime(2023, 1, 1) + timedelta(minutes=i) for i in range(5)],
            'open': [100, 101, 102, 101, 100],
            'high': [102, 103, 104, 103, 102],
            'low': [98, 99, 100, 99, 98],
            'close': [101, 102, 101, 100, 99],
            'price': [101, 102, 101, 100, 99],
            'volume': [100, 110, 120, 110, 100]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)

        resistance_lines = [{'slope': 0.0, 'intercept': 103.0}]
        support_lines = [{'slope': 0.0, 'intercept': 97.0}]
        active_resistance = {'slope': 0.0, 'intercept': 103.0}
        active_support = {'slope': 0.0, 'intercept': 97.0}
        crypto_id = 'bitcoin'
        filename = 'test_chart.png'

        # Act
        generate_chart(df, resistance_lines, support_lines, active_resistance, active_support, crypto_id, filename)

        # Assert
        mock_mpf_plot.assert_called_once()
        args, kwargs = mock_mpf_plot.call_args
        self.assertEqual(args[0].shape, df.shape)
        self.assertIn('type', kwargs)
        self.assertEqual(kwargs['type'], 'candle')
        self.assertIn('savefig', kwargs)
        self.assertEqual(kwargs['savefig'], filename)

if __name__ == '__main__':
    unittest.main()
