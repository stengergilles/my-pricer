

import pytest # Required for pytest.mark decorators
import os
import pandas as pd
from stock_monitoring_app.fetchers import PolygonFetcher
from stock_monitoring_app.config import settings as app_settings # Import the global settings instance

# Attempt to capture the real API key at module load time.
# This happens before session-scoped autouse fixtures (like set_mock_env_vars in conftest.py)
# might modify the environment variables for the test session.
_ACTUAL_POLYGON_API_KEY_FROM_SHELL = os.getenv("POLYGON_API_KEY")

# Skips this test if the POLYGON_API_KEY environment variable was not set in the shell
# when pytest collected the tests. Uses the value captured at module load.
requires_polygon_key = pytest.mark.skipif(
    not _ACTUAL_POLYGON_API_KEY_FROM_SHELL,

    reason="POLYGON_API_KEY environment variable not set in shell. Skipping Polygon integration test."
)

@pytest.mark.integration
@requires_polygon_key
def test_polygon_fetcher_real_data_smoke_test(monkeypatch):
    """
    A simple smoke test to fetch a small amount of real data from Polygon.io.
    Requires POLYGON_API_KEY environment variable to be set with a valid key in the shell.
    """
    # Use the API key captured at module load time. This ensures we get the key
    # from the shell environment, not one potentially overridden by session-wide fixtures.
    real_api_key_for_test = _ACTUAL_POLYGON_API_KEY_FROM_SHELL
    
    # Ensure app_settings.POLYGON_API_KEY uses this real_api_key_for_test for this test's scope.
    # The app_settings object would have been initialized with POLYGON_API_KEY from os.getenv(),
    # which, by the time AppSettings.__init__ runs (due to import order and fixture execution),
    # would likely be the "test_polygon_key" set by the set_mock_env_vars fixture.
    # This monkeypatch.setattr is crucial to override it for this specific test.
    # The monkeypatch will also ensure this change is reverted after the test.
    monkeypatch.setattr(app_settings, 'POLYGON_API_KEY', real_api_key_for_test)

    print(f"\nAttempting Polygon.io integration test with actual API key: {str(real_api_key_for_test)[:5]}...")

    # PolygonFetcher will read its API key from app_settings.POLYGON_API_KEY during its __init__.
    # Since we've patched app_settings, it will now use the real_api_key_for_test.
    fetcher = PolygonFetcher()
    
    try:
        # Fetch a very small, known-good dataset (e.g., 1 day for a major ticker)
        # Fetch a very small, known-good dataset (e.g., 1 day for a major ticker)
        # Using "5d" instead of "1d" to be more robust against single non-trading days.
        df = fetcher.fetch_data(identifier="AAPL", period="5d", interval="1d")        
        assert isinstance(df, pd.DataFrame), "Data should be a Pandas DataFrame"
        assert not df.empty, "DataFrame should not be empty for AAPL over 5 days from Polygon.io"
        
        print(f"Successfully fetched {len(df)} rows for AAPL from Polygon.io.")
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in expected_columns:
            assert col in df.columns, f"Column '{col}' is missing"
        assert isinstance(df.index, pd.DatetimeIndex), "Index should be a DatetimeIndex"

    except Exception as e:
        pytest.fail(f"Polygon.io integration test failed: {e}")