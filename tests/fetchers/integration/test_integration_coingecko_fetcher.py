import pytest
import os
import pandas as pd
from stock_monitoring_app.fetchers import CoinGeckoFetcher
from stock_monitoring_app.config import settings as app_settings # Import the global settings instance



# Skips tests requiring an API key if COINGECKO_API_KEY is not set
# This decorator is now removed from test_coingecko_fetcher_authenticated_api_smoke_test
# requires_coingecko_key_env = pytest.mark.skipif(
#     not os.getenv("COINGECKO_API_KEY"),
#     reason="COINGECKO_API_KEY environment variable not set. Skipping authenticated CoinGecko test."
# ) # This is kept for reference but test_coingecko_fetcher_authenticated_api_smoke_test will no longer use it.

@pytest.mark.integration
def test_coingecko_fetcher_public_api_smoke_test(monkeypatch):
    """
    A smoke test for CoinGecko's public API (no key).
    Fetches a small amount of real data.
    """
    # Ensure CoinGecko API key is None in settings for this public test,
    # overriding the autouse set_mock_env_vars fixture.
    monkeypatch.setattr(app_settings, 'COINGECKO_API_KEY', None)

    print("\nAttempting CoinGecko public API integration test (no key)...")
    fetcher = CoinGeckoFetcher()    
    try:
        # Bitcoin is generally a safe bet for data availability.
        df = fetcher.fetch_data(identifier="bitcoin", period="1d", interval="1d")
        
        assert isinstance(df, pd.DataFrame), "Data should be a Pandas DataFrame"
        assert not df.empty, "DataFrame should not be empty for Bitcoin over 1 day from CoinGecko (public)"
        
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in expected_columns:
            assert col in df.columns, f"Column '{col}' is missing"
        assert isinstance(df.index, pd.DatetimeIndex), "Index should be a DatetimeIndex"
        print(f"Successfully fetched {len(df)} rows for Bitcoin from CoinGecko (public API).")



    except Exception as e:        pytest.fail(f"CoinGecko public API integration test failed: {e}")

# The test_coingecko_fetcher_authenticated_or_public_smoke_test has been removed# as per the request to only test the public endpoint without an API key.
# The existing test_coingecko_fetcher_public_api_smoke_test covers this scenario.

