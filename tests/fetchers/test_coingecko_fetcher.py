import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from stock_monitoring_app.fetchers.coingecko_fetcher import CoinGeckoFetcher

@pytest.fixture
def mock_response():
    """Mock response from CoinGecko API"""
    return {
        "prices": [
            [1625097600000, 35000.0],  # timestamp, price
            [1625184000000, 36000.0]
        ],
        "market_caps": [
            [1625097600000, 650000000000],
            [1625184000000, 670000000000]
        ],
        "total_volumes": [
            [1625097600000, 1500000000],
            [1625184000000, 1600000000]
        ]
    }

@patch('stock_monitoring_app.fetchers.coingecko_fetcher.settings')
@patch('stock_monitoring_app.fetchers.coingecko_fetcher.requests.get')
def test_fetch_data(mock_get, mock_settings, mock_response):
    # Configure the mock to return a response with our test data
    mock_get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=mock_response)
    )
    
    # Mock the settings to provide an API key (optional for CoinGecko)
    mock_settings.COINGECKO_API_KEY = "test_api_key"
    
    # Create an instance of CoinGeckoFetcher
    fetcher = CoinGeckoFetcher()
    
    # Call the fetch_data method
    df = fetcher.fetch_data(identifier="bitcoin", period="1d", interval="1h")
    
    # Verify the result is a DataFrame with expected columns
    assert isinstance(df, pd.DataFrame)
    assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(df.columns)
    assert len(df) == 2  # We provided 2 data points in our mock
    
    # Verify the API was called with expected parameters
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "bitcoin" in kwargs.get('url', '') or "bitcoin" in args[0]

@patch('stock_monitoring_app.fetchers.coingecko_fetcher.settings')
@patch('stock_monitoring_app.fetchers.coingecko_fetcher.requests.get')
def test_handle_api_error(mock_get, mock_settings):
    # Configure the mock to return an error response
    mock_get.return_value = MagicMock(
        status_code=429,
        raise_for_status=MagicMock(side_effect=Exception("Too many requests")),
        text="Too many requests"
    )
    
    # Mock the settings to provide an API key (optional for CoinGecko)
    mock_settings.COINGECKO_API_KEY = "test_api_key"
    
    # Create an instance of CoinGeckoFetcher
    fetcher = CoinGeckoFetcher()
    
    # Call the fetch_data method and expect it to handle the error
    with pytest.raises(Exception) as excinfo:
        fetcher.fetch_data(identifier="bitcoin", period="1d", interval="1h")
    
    # Verify the error message contains useful information
    error_message = str(excinfo.value)
    assert "Too many requests" in error_message
