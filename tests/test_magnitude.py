
import unittest
import pandas as pd
from datetime import datetime, timedelta
from magnitude import predict_movement_magnitude

class TestMagnitude(unittest.TestCase):

    def test_predict_movement_magnitude_up(self):
        # Arrange
        first_timestamp = datetime(2023, 1, 1)
        data = {
            'timestamp': [first_timestamp, first_timestamp + timedelta(minutes=1)],
            'price': [100, 101]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        latest_price_point = df.iloc[-1]
        predicted_direction = 'up'
        active_resistance = {'slope': 0.0, 'intercept': 105.0}
        active_support = None

        # Act
        magnitude = predict_movement_magnitude(df, latest_price_point, predicted_direction, active_resistance, active_support)

        # Assert
        self.assertEqual(magnitude, "+4.00")

    def test_predict_movement_magnitude_down(self):
        # Arrange
        first_timestamp = datetime(2023, 1, 1)
        data = {
            'timestamp': [first_timestamp, first_timestamp + timedelta(minutes=1)],
            'price': [100, 99]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        latest_price_point = df.iloc[-1]
        predicted_direction = 'down'
        active_resistance = None
        active_support = {'slope': 0.0, 'intercept': 95.0}

        # Act
        magnitude = predict_movement_magnitude(df, latest_price_point, predicted_direction, active_resistance, active_support)

        # Assert
        self.assertEqual(magnitude, "-4.00")

    def test_predict_movement_magnitude_none(self):
        # Arrange
        first_timestamp = datetime(2023, 1, 1)
        data = {
            'timestamp': [first_timestamp, first_timestamp + timedelta(minutes=1)],
            'price': [100, 101]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        latest_price_point = df.iloc[-1]
        predicted_direction = 'neutral'
        active_resistance = {'slope': 0.0, 'intercept': 105.0}
        active_support = {'slope': 0.0, 'intercept': 95.0}

        # Act
        magnitude = predict_movement_magnitude(df, latest_price_point, predicted_direction, active_resistance, active_support)

        # Assert
        self.assertEqual(magnitude, "0.00")

if __name__ == '__main__':
    unittest.main()
