import os
import sys
import pandas as pd

# Add project root to Python path to allow absolute imports
# This assumes the script is run from the 'examples' directory or project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)
from stock_monitoring_app.fetchers import PolygonFetcher, CoinGeckoFetcher
from stock_monitoring_app.config import settings  # To ensure API keys are loaded

def run_polygon_example():
    """Example of using PolygonFetcher."""
    print("\n--- Running PolygonFetcher Example ---")
    if not settings.POLYGON_API_KEY:
        print("POLYGON_API_KEY not set. Skipping PolygonFetcher example.")
        print("Please set the POLYGON_API_KEY environment variable (e.g., in a .env file or export POLYGON_API_KEY=\"your_key\").")
        return

    try:
        fetcher = PolygonFetcher()
        print(f"Fetching AAPL data for '5d' period, '1d' interval using {fetcher.get_service_name()}...")
        # Using a short period and common ticker for example
        data = fetcher.fetch_data(identifier="AAPL", period="5d", interval="1d")
        if data is not None and not data.empty:
            print("Successfully fetched AAPL data:")
            print(data.head())
        elif data is not None and data.empty:
            print("Fetched AAPL data is empty. This might be due to market hours, API limits, or no data for the period.")
        else:
            print("Failed to fetch AAPL data (returned None).")
    except ValueError as ve:
        print(f"Configuration error for PolygonFetcher: {ve}")
    except Exception as e:
        print(f"Error during PolygonFetcher example: {e}")

def run_coingecko_example():
    """Example of using CoinGeckoFetcher."""
    print("\n--- Running CoinGeckoFetcher Example ---")
    # CoinGecko API key is optional for basic use, but good to have for higher rate limits.
    # The CoinGeckoFetcher will use the key from settings if available.
    if not settings.COINGECKO_API_KEY:
        print("COINGECKO_API_KEY not set. Proceeding with public CoinGecko API (rate limits may apply).")
    try:
        fetcher = CoinGeckoFetcher()
        print(f"Fetching Bitcoin data for '5d' period, '1d' interval using {fetcher.get_service_name()}...")
        # Using a short period and common crypto for example
        data = fetcher.fetch_data(identifier="bitcoin", period="5d", interval="1d")  # Interval is 'daily' by default in CG fetcher
        if data is not None and not data.empty:
            print("Successfully fetched Bitcoin data:")
            print(data.head())
        elif data is not None and data.empty:
            print("Fetched Bitcoin data is empty. This might be due to API limits or no data for the period.")
        else:
            print("Failed to fetch Bitcoin data (returned None).")
    except Exception as e:
        print(f"Error during CoinGeckoFetcher example: {e}")

if __name__ == "__main__":
    # Important: Ensure your API keys are set in environment variables or a .env file
    # that your config.py loads (if you have one).
    # e.g., in a .env file at the project root:
    # POLYGON_API_KEY="YOUR_POLYGON_KEY"
    # COINGECKO_API_KEY="YOUR_COINGECKO_KEY" (optional)
    #
    # Alternatively, you can export them in your shell:
    # export POLYGON_API_KEY="YOUR_POLYGON_KEY"
    # export COINGECKO_API_KEY="YOUR_COINGECKO_KEY"

    print("Running fetcher examples...")
    print("Make sure your API keys are configured in your environment or .env file if needed.")
    run_polygon_example()
    run_coingecko_example()

    print("\nFetcher examples completed.")
    print("Note: If you see errors or empty data, check your API keys, internet connection, and API rate limits.")
