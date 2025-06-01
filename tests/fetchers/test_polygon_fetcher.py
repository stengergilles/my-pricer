import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from stock_monitoring_app.fetchers.polygon_fetcher import PolygonFetcher

@pytest.fixture
def mock_response():
    """Mock response from Polygon API"""
    return {
        "results": [
            {
                "c": 150.0,  # close
                "h": 155.0,  # high
                "l": 145.0,  # low
                "o": 148.0,  # open
                "t": 1625097600000,  # timestamp
                "v": 1000,  # volume
                "vw": 149.5  # volume weighted price
            },
            {
                "c": 152.0,
                "h": 157.0,
                "l": 147.0,
                "o": 150.0,
                "t": 1625184000000,
                "v": 1200,
                "vw": 151.5
            }
        ],
        "status": "OK",
        "request_id": "test_request_id",
        "count": 2
    }

@patch('stock_monitoring_app.fetchers.polygon_fetcher.settings')
@patch('stock_monitoring_app.fetchers.polygon_fetcher.requests.get')
def test_fetch_data(mock_get, mock_settings, mock_response):
    # Configure the mock to return a response with our test data
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=mock_response)
    )
    
    # Mock the settings to provide an API key
    mock_settings.POLYGON_API_KEY = "test_api_key"
    
    # Create an instance of PolygonFetcher
    fetcher = PolygonFetcher()
    
    # Call the fetch_data method
    df = fetcher.fetch_data(identifier="AAPL", period="1d", interval="1h")
    
    # Verify the result is a DataFrame with expected columns
    assert isinstance(df, pd.DataFrame)
    assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(df.columns)
    assert len(df) == 2  # We provided 2 data points in our mock
    
    # Verify the API was called with expected parameters
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "AAPL" in kwargs.get('url', '') or "AAPL" in args[0]

@patch('stock_monitoring_app.fetchers.polygon_fetcher.settings')
@patch('stock_monitoring_app.fetchers.polygon_fetcher.requests.get')
def test_handle_api_error(mock_get, mock_settings):
    # Configure the mock to return an error response
    mock_get.return_value = MagicMock(
        status_code=401,
        json=MagicMock(return_value={"status": "ERROR", "message": "Invalid API key"})
    )
    
    # Mock the settings to provide an API key
    mock_settings.POLYGON_API_KEY = "test_api_key"
    
    # Create an instance of PolygonFetcher
    fetcher = PolygonFetcher()
    
    # Call the fetch_data method and expect it to handle the error
    with pytest.raises(Exception) as excinfo:
        fetcher.fetch_data(identifier="AAPL", period="1d", interval="1h")
    
    # Verify the error message contains useful information
    error_message = str(excinfo.value)
    assert "Invalid API key" in error_message
