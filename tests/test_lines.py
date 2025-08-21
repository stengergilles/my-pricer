
import unittest
import pandas as pd
from lines import find_swing_points, calculate_line_equation, find_support_resistance_lines, analyze_line_durations

class TestLines(unittest.TestCase):

    def test_find_swing_points(self):
        # Arrange
        data = {
            'timestamp': pd.to_datetime(['2023-01-01 12:00:00', '2023-01-01 12:01:00', '2023-01-01 12:02:00', 
                                        '2023-01-01 12:03:00', '2023-01-01 12:04:00', '2023-01-01 12:05:00']),
            'price': [100, 110, 90, 80, 95, 100]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)

        # Act
        swing_highs, swing_lows = find_swing_points(df, percentage_change=0.05, min_bars_confirmation=1)

        # Assert
        self.assertEqual(len(swing_highs), 1)
        self.assertEqual(swing_highs.iloc[0]['price'], 100)
        self.assertEqual(len(swing_lows), 1)
        self.assertEqual(swing_lows.iloc[0]['price'], 80)

    def test_calculate_line_equation(self):
        # Arrange
        from datetime import datetime, timedelta
        first_timestamp = datetime(2023, 1, 1)
        points = [
            {'timestamp': first_timestamp + timedelta(minutes=1), 'price': 101},
            {'timestamp': first_timestamp + timedelta(minutes=2), 'price': 102},
            {'timestamp': first_timestamp + timedelta(minutes=3), 'price': 103},
        ]

        # Act
        slope, intercept, r_value, std_err = calculate_line_equation(points, first_timestamp)

        # Assert
        self.assertAlmostEqual(slope, 1.0 / 60.0) # 1 unit price change per minute
        self.assertAlmostEqual(intercept, 100.0)

    def test_find_support_resistance_lines(self):
        # Arrange
        from datetime import datetime, timedelta
        first_timestamp = datetime(2023, 1, 1)
        swing_points_data = {
            'timestamp': [first_timestamp + timedelta(minutes=1), first_timestamp + timedelta(minutes=3)],
            'price': [101, 103]
        }
        swing_points_df = pd.DataFrame(swing_points_data)

        # Act
        lines = find_support_resistance_lines(swing_points_df, 'resistance', first_timestamp)

        # Assert
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['type'], 'resistance')
        self.assertIn('equation', lines[0])

    def test_analyze_line_durations(self):
        # Arrange
        from datetime import datetime, timedelta
        first_timestamp = datetime(2023, 1, 1)
        data = {
            'timestamp': [first_timestamp + timedelta(minutes=i) for i in range(5)],
            'price': [100, 101, 102, 101, 100]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)

        resistance_lines = [{
            'equation': 'y = 0.0x + 103.0',
            'slope': 0.0,
            'intercept': 103.0
        }]
        support_lines = [{
            'equation': 'y = 0.0x + 99.0',
            'slope': 0.0,
            'intercept': 99.0
        }]

        # Act
        durations = analyze_line_durations(df, resistance_lines, support_lines, first_timestamp)

        # Assert
        self.assertEqual(len(durations), 1)
        self.assertEqual(durations[0]['resistance_equation'], 'y = 0.0x + 103.0')
        self.assertEqual(durations[0]['support_equation'], 'y = 0.0x + 99.0')
        self.assertEqual(durations[0]['num_occurrences'], 1)
        self.assertAlmostEqual(durations[0]['avg_duration_seconds'], 240.0)

if __name__ == '__main__':
    unittest.main()
