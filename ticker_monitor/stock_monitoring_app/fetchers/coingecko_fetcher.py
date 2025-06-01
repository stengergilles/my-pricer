


 

import random
import time
from .base_fetcher import Fetcher
import pandas as pd
import numpy as np
import requests
from datetime import datetime # Not timedelta or date directly, pandas handles date manipulation well.
from requests.exceptions import RequestException

from ..config import settings # Import the global settings instance

class CoinGeckoFetcher(Fetcher):
    """
    Fetcher implementation for the CoinGecko API.
    Retrieves cryptocurrency data.
    """

    API_BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        """
        Initializes the CoinGeckoFetcher.
        Reads the optional API key from the global application settings.
        """
        # CoinGecko key is optional, so we just load it. Might be None.
        self.api_key = settings.COINGECKO_API_KEY
        # In a real application, you might initialize an HTTP session here:
        # self.session = requests.Session()
        # if self.api_key:
        #     # Depending on CoinGecko's Pro API, key might be passed in headers or params
        #     # e.g., self.session.headers.update({'X-CG-PRO-API-KEY': self.api_key}) 

        #     # or self.session.params = {'x_cg_pro_api_key': self.api_key}
        #     pass

    def fetch_data(self, identifier: str, period: str, interval: str) -> pd.DataFrame:
        """
        Fetches historical market data for a given cryptocurrency ID from CoinGecko
        using the /coins/{id}/market_chart endpoint.

        Args:
            identifier: The ID of the cryptocurrency (e.g., 'bitcoin', 'ethereum').
            period: The duration for which to fetch data. Mapped to CoinGecko's 'days' parameter.
                    Supported: "1d", "5d" (maps to 7 days), "1mo" (30d), "3mo" (90d), 
                               "6mo" (180d), "1y" (365d), "2y", "5y", "max" (maps to "max").
            "1w": (mapped to 7d)
            interval: This implementation targets 'daily' data from CoinGecko. Other requested
                      intervals might not be precisely matched.

        Returns:
            A pandas DataFrame with 'Timestamp' (index), 'Open', 'High', 'Low', 'Close', 'Volume'.
            'Open', 'High', 'Low' are approximated as 'Close' due to endpoint limitations for OHLC.
        
        Raises:
            ValueError: If the period is unsupported.
            Exception: If the API request fails, data parsing is unsuccessful, or other errors occur.
        """
        coin_id = identifier.lower() # CoinGecko IDs are typically lowercase
        vs_currency = 'usd' # Hardcode for simplicity

        # 1. Translate period to CoinGecko's 'days'
        # CoinGecko's /market_chart with interval=daily supports specific 'days' values:
        # 1, 7, 14, 30, 90, 180, 365, "max"
        period_map_cg = {
            "1d": 1, "5d": 7, # "5d" is mapped to 7 as it's the closest supported short period
            "1w": 7,
            "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365,
            "2y": "max", # No direct 2y, map to max
            "5y": "max", # No direct 5y, map to max
            "max": "max"        }
        if period.lower() not in period_map_cg:
            raise ValueError(f"Unsupported period for CoinGecko: {period}. Supported: {list(period_map_cg.keys())}")
        cg_days = period_map_cg[period.lower()]

        # API endpoint: /coins/{id}/market_chart

        api_url = f"{self.API_BASE_URL}/coins/{coin_id}/market_chart"
        
        params = {
            'vs_currency': vs_currency,
            'days': cg_days
            # 'interval' parameter will be set conditionally below
        }

        # Determine CoinGecko interval parameter based on cg_days.
        # For short periods (<= 90 days), omitting 'interval' lets CoinGecko provide
        # finer granularity (e.g., hourly for free API, potentially minutes for Pro).
        # For longer periods (> 90 days or 'max'), explicitly request 'daily'.
        if isinstance(cg_days, str) and cg_days == "max":
            params['interval'] = 'daily'
        elif isinstance(cg_days, int) and cg_days > 90:
            params['interval'] = 'daily'
        else:
            # For cg_days <= 90 (e.g., for periods like "1d", "1w", "1mo", "3mo"),
            # do not set params['interval']. CoinGecko will automatically select
            # a more granular interval (e.g., hourly for its free/standard API tier).
            pass

        if self.api_key: # Include API key if provided (for Pro features, higher rate limits)
            # CoinGecko API key might be passed as a header or query parameter depending on plan.
            # For demo/public it's often x_cg_demo_api_key, for pro x_cg_pro_api_key
            # Assuming query parameter for this example if it's a common pattern.
            # Check CoinGecko's specific instructions for your key type.
            # params['x_cg_pro_api_key'] = self.api_key # Example
            pass # No standard public way to pass key in query, usually header for Pro.


        headers = {}
        if self.api_key:
            # Example for Pro API key passed as header:
            # headers['X-CG-PRO-API-KEY'] = self.api_key
            # Example for Demo API Key:
            headers['X-CG-DEMO-API-KEY'] = self.api_key # More likely for free/demo keys

        # 2. Make API request with retry logic
        MAX_RETRIES = 5 
        INITIAL_BACKOFF_SECONDS = 1

        BACKOFF_FACTOR = 2
        
        retries = 0
        last_exception = None
        response = None # Initialize response to ensure it's always bound

        while retries < MAX_RETRIES:
            try:
                response = requests.get(api_url, params=params, headers=headers, timeout=10) # Added timeout
                response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
                
                # If successful, break the loop and proceed to process data
                break 
            except requests.exceptions.HTTPError as e:
                last_exception = e
                should_retry = False
                # Retry on 429 (Too Many Requests)
                if e.response.status_code == 429:
                    should_retry = True 
                elif e.response.status_code == 401 and not self.api_key:
                    should_retry = True
                
                if should_retry and retries < MAX_RETRIES -1: # Don't sleep on the last attempt
                    backoff_time = INITIAL_BACKOFF_SECONDS * (BACKOFF_FACTOR ** retries) + random.uniform(0, 1)
                    print(f"WARN [{self.get_service_name()}]: Request for {coin_id} failed with {e.response.status_code}. Retrying in {backoff_time:.2f}s... (Attempt {retries + 1}/{MAX_RETRIES})")
                    time.sleep(backoff_time)
                elif not should_retry: # If not a retryable HTTP error, raise immediately
                    raise e 
            except RequestException as e: # Catches other network errors (ConnectionError, Timeout, etc.)
                last_exception = e
                if retries < MAX_RETRIES -1: # Don't sleep on the last attempt
                    backoff_time = INITIAL_BACKOFF_SECONDS * (BACKOFF_FACTOR ** retries) + random.uniform(0, 1)
                    print(f"WARN [{self.get_service_name()}]: Request for {coin_id} failed with network error: {e}. Retrying in {backoff_time:.2f}s... (Attempt {retries + 1}/{MAX_RETRIES})")
                    time.sleep(backoff_time)
            

            retries += 1
                # After the loop, if response is still None, it means no request was successful.

        if response is None:
            final_exception_message = f"Failed to fetch data for {coin_id} from {self.get_service_name()} after {retries} attempts."
            if last_exception: # If any exception occurred during attempts, it would be in last_exception
                final_exception_message += f" Last error: {last_exception}"
            # Raise an exception, chaining last_exception if it exists for better context.
            raise Exception(final_exception_message) from last_exception

        # If we reach here, 'response' must hold a valid requests.Response object from a successful attempt.
        try:
            data = response.json()
            if not data or 'prices' not in data or 'total_volumes' not in data:
                raise Exception(f"CoinGecko API response for {coin_id} is malformed or missing data after successful HTTP request.")

            prices_data = data.get('prices', [])
            volumes_data = data.get('total_volumes', [])

            if not prices_data: # If prices are empty, likely no data for the period
                print(f"No price data returned from CoinGecko for {coin_id} ({period}, daily).")
                return pd.DataFrame()

            # 3. Process response into DataFrame
            df_prices = pd.DataFrame(prices_data, columns=['Timestamp', 'Close'])
            df_prices['Timestamp'] = pd.to_datetime(df_prices['Timestamp'], unit='ms')
            df_prices = df_prices.set_index('Timestamp')

            if volumes_data:
                df_volumes = pd.DataFrame(volumes_data, columns=['Timestamp', 'Volume'])
                df_volumes['Timestamp'] = pd.to_datetime(df_volumes['Timestamp'], unit='ms')
                df_volumes = df_volumes.set_index('Timestamp')
                df = df_prices.join(df_volumes, how='outer')
            else:
                df = df_prices
                df['Volume'] = np.nan

            df['Open'] = df['Close']            
            df['High'] = df['Close']            
            df['Low'] = df['Close']
            
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = np.nan
            
            df = df[required_columns]
            df = df.dropna(subset=['Close'])

            if df.empty:
                print(f"Resulting DataFrame is empty after processing CoinGecko data for {coin_id} ({period}, daily).")
            
            return df

        except ValueError as e: # Includes JSONDecodeError if response.json() fails
            raise Exception(f"Failed to parse JSON response from CoinGecko for {coin_id}: {e}")
        except Exception as e: 

            # Catch-all for unexpected errors during data processing AFTER successful fetch
            raise Exception(f"An unexpected error occurred processing data for {coin_id} from CoinGecko: {e}")

    def get_service_name(self) -> str:
        return "CoinGecko"
