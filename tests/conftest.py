import pytest
import pandas as pd
import numpy as np
import os

import requests


# Set mock API keys before other modules import 'config'
# Note: Using monkeypatch is preferred over setting os.environ directly in tests
# Changed scope to 'function' to match monkeypatch scope
@pytest.fixture(scope='function', autouse=True)
def set_mock_env_vars(monkeypatch):
    """Sets mock API keys before each test function."""

    monkeypatch.setenv("POLYGON_API_KEY", "test_polygon_key")
    monkeypatch.setenv("COINGECKO_API_KEY", "test_coingecko_key")

    # Directly update the application's settings object after monkeypatching environment variables.
    # This is necessary because the 'settings' object in 'stock_monitoring_app.config'
    # is typically initialized when the module is first imported. Monkeypatching the
    # environment variables alone won't update this already-loaded object.

    # The AppSettings class in stock_monitoring_app.config already reads from os.getenv().
    # By using monkeypatch.setenv here, the settings object, when imported by any module

    try:
        from stock_monitoring_app.config import settings
        
        # For unit tests, ensure the global 'settings' object reflects the mock keys.
        # monkeypatch.setenv is good for processes/modules that would re-evaluate os.getenv(),
        # but directly patching the already imported 'settings' object ensures consistency
        # for code that has already imported it.
        monkeypatch.setattr(settings, 'POLYGON_API_KEY', "test_polygon_key")
        monkeypatch.setattr(settings, 'COINGECKO_API_KEY', "test_coingecko_key")
        
    except ImportError:
        pytest.fail(
            "Failed to import 'settings' from 'stock_monitoring_app.config' in conftest.py "
            "for mock API key setup. Check path and module integrity."
        )

@pytest.fixture(scope='module') # Reusable DataFrame fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """Provides a sample OHLCV DataFrame for testing indicators."""

    # Increase the number of data points to ensure indicators like MACD can calculate
    num_days = 60  # Increased from 25 to 60
    start_date = '2023-01-01'
    dates = pd.date_range(start=start_date, periods=num_days, freq='B') # Business days

    # Generate more diverse data to potentially trigger more signals    np.random.seed(42) # for reproducibility
    base_price = 100
    open_prices = base_price + np.cumsum(np.random.randn(num_days) * 0.5)
    high_prices = open_prices + np.random.rand(num_days) * 2
    low_prices = open_prices - np.random.rand(num_days) * 2    
    close_prices = (open_prices + high_prices + low_prices) / 3 + np.random.randn(num_days) * 0.2
    # Ensure Low <= Open/Close <= High
    low_prices = np.minimum(low_prices, open_prices)
    low_prices = np.minimum(low_prices, close_prices)
    high_prices = np.maximum(high_prices, open_prices)
    high_prices = np.maximum(high_prices, close_prices)
    
    volumes = np.random.randint(500, 5000, size=num_days) * 1000

    data = {
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volumes.astype(float) # Ensure volume is float if other prices are
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'Timestamp'    
    return df

@pytest.fixture(scope='function') # Can be function scope if modified per test
def mock_polygon_response_success():
    """Provides a sample successful Polygon API response."""
    return {
        "ticker": "AAPL",
        "queryCount": 10,
        "resultsCount": 10,        "adjusted": True,
        "results": [
            {"v": 10000, "vw": 150.1, "o": 150.0, "c": 151.0, "h": 151.5, "l": 149.5, "t": 1672531200000, "n": 1000}, # 2023-01-01
            {"v": 11000, "vw": 151.1, "o": 151.0, "c": 152.0, "h": 152.5, "l": 150.5, "t": 1672617600000, "n": 1100}, # 2023-01-02
            {"v": 12000, "vw": 152.1, "o": 152.0, "c": 151.5, "h": 152.8, "l": 151.0, "t": 1672704000000, "n": 1200}, # 2023-01-03
            # ... add more data points as needed for thorough testing
        ],
        "status": "OK",
        "request_id": "req_id_123"
    }

@pytest.fixture(scope='function')
def mock_polygon_response_no_results():
    """Provides a sample Polygon API response with no results."""
    return {
        "ticker": "NONEXIST",
        "queryCount": 0,
        "resultsCount": 0,
        "adjusted": True,
        "results": [],
        "status": "OK", # Status can still be OK even if no results        "request_id": "req_id_456"
    }

@pytest.fixture(scope='function')
def mock_polygon_response_error():
    """Provides a sample Polygon API error response."""
    return {
        "status": "ERROR",
        "request_id": "req_id_789",
        "message": "Invalid API key or Authentication failed."
    }

@pytest.fixture(scope='function')
def mock_coingecko_response_success():
    """Provides a sample successful CoinGecko API response."""
    return {
        "prices": [
            [1672531200000, 20000.50], # 2023-01-01
            [1672617600000, 20100.75], # 2023-01-02
            [1672704000000, 20050.25], # 2023-01-03
            # ... add more data points as needed
        ],
        "market_caps": [
            # ... market cap data ...
        ],
        "total_volumes": [
            [1672531200000, 5000000000.0],

            [1672617600000, 5500000000.0],
            [1672704000000, 5200000000.0],
             # ... add more data points as needed
        ]
    }

@pytest.fixture(scope='function')
def mock_coingecko_response_malformed():
    """Provides a sample malformed CoinGecko API response."""
    return { "some_unexpected_key": "some_value" }

# Fixture for MockResponse object needed by requests mock
@pytest.fixture
def MockResponse():
    class MockResponse:
        def __init__(self, json_data, status_code):
            self._json_data = json_data
            self.status_code = status_code

        def json(self):
            if self.status_code >= 400 and isinstance(self._json_data, dict) and "error" in self._json_data:
                 return self._json_data # Return error structure if defined
            if self.status_code < 400:
                 return self._json_data # Return success structure
            # Simulate JSONDecodeError for non-JSON error responses
            if isinstance(self._json_data, str):
                 raise requests.exceptions.JSONDecodeError("Simulated decode error", self._json_data, 0)
            return {} # Default empty dict if no specific error/success JSON provided


        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.exceptions.HTTPError(f"HTTP Error {self.status_code}", response=self)

    return MockResponse
