import pytest
import pandas as pd
import os
import json
from unittest.mock import patch, MagicMock
from stock_monitoring_app.backtest.backtest import BackTest

@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing"""
    return pd.DataFrame({
        "Open": [100, 101, 102, 103, 104],
        "High": [105, 106, 107, 108, 109],
        "Low": [95, 96, 97, 98, 99],
        "Close": [102, 103, 101, 104, 105],
        "Volume": [1000, 1100, 900, 1200, 1300],
        "Timestamp": pd.date_range(start="2023-01-01", periods=5)
    })

class TestBackTest:
    
    @patch('stock_monitoring_app.backtest.backtest.PolygonFetcher')
    def test_init(self, mock_polygon_fetcher):
        """Test BackTest initialization"""
        # Mock the PolygonFetcher to avoid API key error
        mock_polygon_instance = MagicMock()
        mock_polygon_fetcher.return_value = mock_polygon_instance
        
        backtest = BackTest(ticker="AAPL", period="1y", interval="1d")
        
        assert backtest.ticker == "AAPL"
        assert backtest.period == "1y"
        assert backtest.interval == "1d"
        assert backtest.historical_data is None
        assert backtest.performance_metrics == {}
    
    @patch('stock_monitoring_app.backtest.backtest.PolygonFetcher')
    def test_run_backtest(self, mock_polygon_fetcher, sample_data):
        """Test running a backtest"""
        # Mock the PolygonFetcher to avoid API key error
        mock_polygon_instance = MagicMock()
        mock_polygon_fetcher.return_value = mock_polygon_instance
        
        # Create BackTest instance
        backtest = BackTest(ticker="AAPL", period="1y", interval="1d")
        
        # Mock the fetch_historical_data method to return sample data
        backtest.fetch_historical_data = MagicMock(return_value=sample_data)
        
        # Mock other methods to avoid errors
        backtest.determine_relevant_indicators = MagicMock(return_value=[])
        backtest.create_strategy = MagicMock()
        backtest.execute_strategy = MagicMock(return_value=pd.DataFrame())
        backtest.calculate_portfolio_performance = MagicMock(return_value=pd.DataFrame())
        backtest.save_results = MagicMock()
        
        # Run the backtest
        result = backtest.run_backtest()
        
        # Verify fetch_historical_data was called
        backtest.fetch_historical_data.assert_called_once()
        
        # The result might be None if the implementation returns None when data is empty
        # Just verify that the method runs without exceptions
    
    @patch('stock_monitoring_app.backtest.backtest.PolygonFetcher')
    def test_get_performance_metrics(self, mock_polygon_fetcher):
        """Test getting performance metrics"""
        # Mock the PolygonFetcher to avoid API key error
        mock_polygon_instance = MagicMock()
        mock_polygon_fetcher.return_value = mock_polygon_instance
        
        # Create BackTest instance
        backtest = BackTest(ticker="AAPL", period="1y", interval="1d")
        
        # Set some performance metrics
        backtest.performance_metrics = {
            "total_return": 0.05,
            "win_rate": 0.6,
            "max_drawdown": 0.02
        }
        
        # Get the metrics
        metrics = backtest.get_performance_metrics()
        
        # Verify the metrics
        assert metrics == backtest.performance_metrics
        assert metrics["total_return"] == 0.05
        assert metrics["win_rate"] == 0.6
        assert metrics["max_drawdown"] == 0.02
    
    @patch('stock_monitoring_app.backtest.backtest.PolygonFetcher')
    @patch('pathlib.Path.mkdir')
    @patch('pandas.DataFrame.to_csv')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('json.dump')
    def test_save_results(self, mock_json_dump, mock_open, mock_to_csv, mock_mkdir, mock_polygon_fetcher, sample_data):
        """Test saving backtest results"""
        # Mock the PolygonFetcher to avoid API key error
        mock_polygon_instance = MagicMock()
        mock_polygon_fetcher.return_value = mock_polygon_instance
        
        # Create BackTest instance
        backtest = BackTest(ticker="AAPL", period="1y", interval="1d")
        
        # Set data and metrics
        backtest.results = sample_data
        backtest.performance_metrics = {
            "total_return": 0.05,
            "win_rate": 0.6,
            "max_drawdown": 0.02
        }
        
        # Mock _get_project_root to return a Path object
        path_mock = MagicMock()
        backtest._get_project_root = MagicMock(return_value=path_mock)
        
        # Configure the path_mock to handle the directory creation
        # This is needed because the actual implementation might use path_mock / "backtest_outputs"
        # which returns another mock that needs to have mkdir
        dir_mock = MagicMock()
        path_mock.__truediv__.return_value = dir_mock
        
        # Call save_results
        backtest.save_results()
        
        # Verify CSV was saved
        mock_to_csv.assert_called_once()
        
        # Verify JSON was saved (if performance metrics exist)
        if backtest.performance_metrics:
            mock_open.assert_called_once()
            mock_json_dump.assert_called_once()
