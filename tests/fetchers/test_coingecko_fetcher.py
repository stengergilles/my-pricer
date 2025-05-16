import pytest
import pandas as pd
import requests
from stock_monitoring_app.fetchers import CoinGeckoFetcher

from requests.exceptions import RequestException

# Test successful initialization (relies on mock env var from conftest.py)
def test_coingecko_fetcher_init_success_with_key():
    """Tests successful initialization when API key is set."""
    fetcher = CoinGeckoFetcher()

    assert fetcher.api_key == "test_coingecko_key"
    assert fetcher.get_service_name() == "CoinGecko"


def test_coingecko_fetcher_init_success_no_key(monkeypatch):
    """Tests successful initialization when API key is NOT set."""
    # First, remove from environment so os.getenv in AppSettings sees it as None if AppSettings were re-initialized.
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
        # Because set_mock_env_vars (autouse=True) runs and *directly sets* settings.COINGECKO_API_KEY,
    # we also need to directly modify the settings object for this test after set_mock_env_vars has run.
    # This ensures that CoinGeckoFetcher reads None from the settings object during its __init__.
    from stock_monitoring_app.config import settings
    monkeypatch.setattr(settings, 'COINGECKO_API_KEY', None)

    fetcher = CoinGeckoFetcher()

    assert fetcher.api_key is None
    assert fetcher.get_service_name() == "CoinGecko"

def test_fetch_data_success(mocker, mock_coingecko_response_success, MockResponse):
    """Tests successful data fetching and DataFrame processing."""
    mock_get = mocker.patch("requests.get", return_value=MockResponse(mock_coingecko_response_success, 200))

    fetcher = CoinGeckoFetcher() # Will use mock key from conftest fixture
    df = fetcher.fetch_data(identifier="bitcoin", period="1mo", interval="1d") # Interval ignored by current impl

    # Assertions
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart" in args[0]
    assert kwargs['params']['vs_currency'] == "usd"
    assert kwargs['params']['days'] == 30 # '1mo' maps to 30 days
    assert kwargs['params']['interval'] == "daily"
    assert 'X-CG-DEMO-API-KEY' in kwargs['headers'] # Check if key is passed (adjust if Pro key header used)
    assert kwargs['headers']['X-CG-DEMO-API-KEY'] == "test_coingecko_key"

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.shape[0] == len(mock_coingecko_response_success['prices'])
    # Check approximated OHL values
    assert (df['Open'] == df['Close']).all()
    assert (df['High'] == df['Close']).all()
    assert (df['Low'] == df['Close']).all()    # Check a specific value

    assert df.loc['2023-01-01', 'Close'] == 20000.50
    assert df.loc['2023-01-01', 'Volume'] == 5000000000.0


def test_fetch_data_success_no_api_key(mocker, mock_coingecko_response_success, MockResponse, monkeypatch):
    """Tests successful fetch when no API key is provided."""
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    
    # Ensure the settings object reflects no API key for this specific test,
    # overriding the autouse set_mock_env_vars fixture for this instance.
    from stock_monitoring_app.config import settings
    monkeypatch.setattr(settings, 'COINGECKO_API_KEY', None)
    
    mock_get = mocker.patch("requests.get", return_value=MockResponse(mock_coingecko_response_success, 200))

    # import importlib
    # import stock_monitoring_app.config
    # importlib.reload(stock_monitoring_app.config) # Ensure settings reloaded without key

    fetcher = CoinGeckoFetcher()
    fetcher.fetch_data(identifier="ethereum", period="5d", interval="1d")

    # Assertions
    mock_get.assert_called_once()

    args, kwargs = mock_get.call_args
    assert "https://api.coingecko.com/api/v3/coins/ethereum/market_chart" in args[0]
    assert kwargs['params']['days'] == 7 # '5d' maps to 7 days
    assert 'X-CG-DEMO-API-KEY' not in kwargs['headers'] # Check that key is NOT passed

def test_fetch_data_no_results(mocker, MockResponse):
    """Tests handling of API response with empty price data."""
    empty_response = {"prices": [], "total_volumes": []}
    mocker.patch("requests.get", return_value=MockResponse(empty_response, 200))
    fetcher = CoinGeckoFetcher()

    df = fetcher.fetch_data(identifier="shiba-inu", period="1d", interval="1d")
    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_fetch_data_api_error_malformed(mocker, mock_coingecko_response_malformed, MockResponse):
    """Tests handling of malformed JSON response."""
    mocker.patch("requests.get", return_value=MockResponse(mock_coingecko_response_malformed, 200))
    fetcher = CoinGeckoFetcher()

    with pytest.raises(Exception, match="CoinGecko API response .* is malformed"):
        fetcher.fetch_data(identifier="bitcoin", period="1mo", interval="1d")

def test_fetch_data_http_error(mocker, MockResponse):
    """Tests handling of HTTP errors."""
    mocker.patch("requests.get", return_value=MockResponse({"error": "Rate limit exceeded"}, 429))
    fetcher = CoinGeckoFetcher()

    with pytest.raises(requests.exceptions.HTTPError): # Caught by raise_for_status
        fetcher.fetch_data(identifier="bitcoin", period="1y", interval="1d")

def test_fetch_data_network_error(mocker):
    """Tests handling of network errors."""

    mocker.patch("requests.get", side_effect=RequestException("Connection failed"))
    fetcher = CoinGeckoFetcher()

    # Updated regex to match the more specific error message from CoinGeckoFetcher
    with pytest.raises(Exception, match=r"Network error \(non-HTTP\) fetching data from CoinGecko for bitcoin: Connection failed"):
        fetcher.fetch_data(identifier="bitcoin", period="1mo", interval="1d")

def test_fetch_data_invalid_period(mocker):
    """Tests handling of unsupported period."""
    fetcher = CoinGeckoFetcher()
    with pytest.raises(ValueError, match="Unsupported period for CoinGecko"):
        fetcher.fetch_data(identifier="bitcoin", period="invalid_period", interval="1d")


