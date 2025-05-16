import pytest
import pandas as pd
import requests
from stock_monitoring_app.fetchers import PolygonFetcher
from requests.exceptions import RequestException


# Test successful initialization (relies on mock env var from conftest.py)
def test_polygon_fetcher_init_success():
    """Tests successful initialization when API key is set."""
    try:
        fetcher = PolygonFetcher()
        assert fetcher.api_key == "test_polygon_key"
        assert fetcher.get_service_name() == "Polygon.io"
    except ValueError:
        pytest.fail("PolygonFetcher initialization failed unexpectedly.")

# Test initialization failure when key is missing (harder to test directly if config checks first)
# def test_polygon_fetcher_init_failure_no_key(monkeypatch):#     """Tests ValueError is raised if API key is missing."""
#     monkeypatch.delenv("POLYGON_API_KEY", raising=False)
#     # Need to force reload config or mock settings directly
#     with pytest.raises(ValueError, match="Polygon.io API key not found"):
#         # import importlib
#         # import stock_monitoring_app.config
#         # importlib.reload(stock_monitoring_app.config) # Force reload after unsetting
#         PolygonFetcher() # This might fail earlier in config import

def test_fetch_data_success(mocker, mock_polygon_response_success, MockResponse):
    """Tests successful data fetching and DataFrame processing."""
    # Mock requests.get
    mock_get = mocker.patch("requests.get", return_value=MockResponse(mock_polygon_response_success, 200))

    fetcher = PolygonFetcher()
    df = fetcher.fetch_data(identifier="AAPL", period="1mo", interval="1d")

    # Assertions
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/" in args[0]
    assert kwargs['params']['apiKey'] == "test_polygon_key"
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.shape[0] == len(mock_polygon_response_success['results']) # Check if all results are processed
    # Check a specific value
    assert df.loc['2023-01-01', 'Open'] == 150.0

def test_fetch_data_no_results(mocker, mock_polygon_response_no_results, MockResponse):
    """Tests handling of API response with zero results."""
    mocker.patch("requests.get", return_value=MockResponse(mock_polygon_response_no_results, 200))
    fetcher = PolygonFetcher()
    df = fetcher.fetch_data(identifier="NONEXIST", period="1d", interval="1d")
    assert isinstance(df, pd.DataFrame) 
    assert df.empty

def test_fetch_data_api_error(mocker, mock_polygon_response_error, MockResponse):
    """Tests handling of Polygon API error status."""
    # Polygon might return 200 OK with status ERROR, or a 4xx/5xx
    mocker.patch("requests.get", return_value=MockResponse(mock_polygon_response_error, 200)) # Simulate 200 OK with error status
    fetcher = PolygonFetcher()
    with pytest.raises(Exception, match="Polygon.io API Error for FAKE"):
        fetcher.fetch_data(identifier="FAKE", period="1mo", interval="1d")

    mocker.patch("requests.get", return_value=MockResponse({"error": "Unauthorized"}, 401)) # Simulate 401
    with pytest.raises(requests.exceptions.HTTPError): # Caught by raise_for_status
         fetcher.fetch_data(identifier="FAKE", period="1mo", interval="1d")


def test_fetch_data_network_error(mocker):
    """Tests handling of network errors during API call."""

    mocker.patch("requests.get", side_effect=RequestException("Network error"))
    fetcher = PolygonFetcher()
    # Updated regex to match the more specific error message from PolygonFetcher
    with pytest.raises(Exception, match=r"Network error \(non-HTTP\) fetching data from Polygon.io for AAPL: Network error"):
        fetcher.fetch_data(identifier="AAPL", period="1y", interval="1d")

def test_fetch_data_invalid_period(mocker):
    """Tests handling of unsupported period."""
    # No need to mock requests.get as it should fail before the call
    fetcher = PolygonFetcher()
    # The current implementation prints an error and returns empty DF for invalid params
    # Adjust assertion if you change it to raise ValueError
    df = fetcher.fetch_data(identifier="AAPL", period="invalid_period", interval="1d")
    assert df.empty
    # OR:
    # with pytest.raises(ValueError, match="Unsupported period"):
    #    fetcher.fetch_data(identifier="AAPL", period="invalid_period", interval="1d")


def test_fetch_data_invalid_interval(mocker):
    """Tests handling of unsupported interval."""
    fetcher = PolygonFetcher()
    # Adjust assertion based on actual error handling (print+empty or raise)
    df = fetcher.fetch_data(identifier="AAPL", period="1mo", interval="invalid_interval")
    assert df.empty
    # OR:
    # with pytest.raises(ValueError, match="Unsupported interval"):
    #     fetcher.fetch_data(identifier="AAPL", period="1mo", interval="invalid_interval")
