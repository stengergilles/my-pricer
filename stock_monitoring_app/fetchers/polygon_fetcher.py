

from .base_fetcher import Fetcher

import pandas as pd
import numpy as np # Still used if any part of the new code needs it, or can be removed if not.
import requests
from datetime import datetime, timedelta, date
from requests.exceptions import RequestException

from ..config import settings # Import the global settings instance

class PolygonFetcher(Fetcher):
    """
    Fetcher implementation for the Polygon.io API.
    Retrieves stock market data.
    """

    API_BASE_URL = "https://api.polygon.io"

    def __init__(self):
        """
        Initializes the PolygonFetcher.
        Reads the API key from the global application settings.

        Raises:
            ValueError: If the Polygon API key is not found in the settings.
        """
        api_key = settings.POLYGON_API_KEY
        if not api_key:
            # This check might be redundant if config.py raises an error,
            # but good for explicit class-level requirement.
            raise ValueError("Polygon.io API key not found in application settings (check POLYGON_API_KEY env var).")        
        self.api_key = api_key
        # In a real application, you might initialize an HTTP session:
        # self.session = requests.Session()

        # self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
        # Or, pass api_key as a query parameter in each request if preferred by Polygon's SDK/API style.

    def fetch_data(self, identifier: str, period: str, interval: str) -> pd.DataFrame:
        """
        Fetches historical aggregate bars for a stock ticker from Polygon.io.
        Example Polygon.io endpoint: /v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}

        Args:
            identifier: The stock ticker symbol (e.g., 'AAPL', 'MSFT').
            period: The duration for which to fetch data. Polygon uses 'from' and 'to' dates.
                    This method would need to translate 'period' (e.g., "1y") into date ranges.
            interval: The time interval (timespan). Polygon uses 'day', 'hour', 'minute', etc.
                      Multiplier can be used with timespan (e.g., 1 day, 5 minute).

        Returns:
            A pandas DataFrame with 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'.
        

        Raises:
            Exception: If the API request fails or data parsing is unsuccessful.        """
        # Note: Removed obfuscated_key generation here as it was only for printing mock fetch info.
        # If needed for real logging, it can be added back using self.api_key.
        ticker = identifier.upper() # Polygon.io usually expects uppercase tickers
        
        # 1. Translate period and interval
        try:
            to_date = date.today()
            if period == "1d":
                from_date = to_date - timedelta(days=1)
            elif period == "5d":
                from_date = to_date - timedelta(days=5)
            elif period == "1w":
                from_date = to_date - timedelta(days=7)
            elif period == "1mo":
                from_date = to_date - pd.DateOffset(months=1) # Using pd.DateOffset for month precision
                from_date = pd.Timestamp(from_date).date() # Convert back to datetime.date
            elif period == "3mo":                
                from_date = to_date - pd.DateOffset(months=3)
                from_date = pd.Timestamp(from_date).date()
            elif period == "6mo":
                from_date = to_date - pd.DateOffset(months=6)
                from_date = pd.Timestamp(from_date).date()

            elif period == "1y":
                from_date = to_date - pd.DateOffset(years=1)
                from_date = pd.Timestamp(from_date).date()
            elif period == "2y":
                from_date = to_date - pd.DateOffset(years=2)
                from_date = pd.Timestamp(from_date).date()
            elif period == "5y":
                from_date = to_date - pd.DateOffset(years=5)
                from_date = pd.Timestamp(from_date).date()
            elif period == "max":
                from_date = date(2000, 1, 1) # A reasonable start date for "max"
            else:
                raise ValueError(f"Unsupported period: {period}")

            from_date_str = from_date.strftime('%Y-%m-%d')
            to_date_str = to_date.strftime('%Y-%m-%d')

            interval_map = {
                "1m": (1, "minute"), "5m": (5, "minute"), "15m": (15, "minute"), "30m": (30, "minute"),
                "1h": (1, "hour"), "2h": (2, "hour"),
                "1d": (1, "day"),"1w":(7,"day")
                # Polygon also supports "week", "month", "quarter", "year" as timespan
            }
            if interval not in interval_map:
                raise ValueError(f"Unsupported interval: {interval}. Supported: {list(interval_map.keys())}")
            
            multiplier, timespan = interval_map[interval]

        except ValueError as e:
            print(f"Error processing period/interval: {e}")            # Return empty DataFrame or raise, depending on desired error handling
            return pd.DataFrame()


        # 2. Construct API URL
        # API: /v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}
        api_url = f"{self.API_BASE_URL}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date_str}/{to_date_str}"
        
        params = {
            'apiKey': self.api_key,
            'adjusted': 'true', # Typically, you want adjusted prices
            'sort': 'asc',      # Sort by time ascending
            'limit': 50000      # Max limit, adjust if needed or handle pagination
        }

        # 3. Make API request
        try:

            response = requests.get(api_url, params=params)
            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
            
            data = response.json()

            # Check for API-level errors first
            if data.get('status') == 'ERROR':
                error_message = data.get('message', f"API error for {ticker} with unspecified message.")
                raise Exception(f"Polygon.io API Error for {ticker}: {error_message}")            # Check if results are present
            results = data.get('results', [])
            # Use resultsCount from response if available, otherwise use length of results array
            results_count = data.get('resultsCount', len(results)) 

            if results_count == 0:
                message = f"No data returned from Polygon.io for {ticker} for the period {from_date_str} to {to_date_str} (interval: {interval})."
                # Add more specific context if it's a daily request, as it's more likely a market closure.
                if timespan == "day":
                    message += " This could be due to the market being closed on the requested day(s), no trades occurring, or the ticker not existing/having data for this range."
                else: # For intraday requests
                    message += " This could be due to the market being closed, no trades occurring during the requested intraday period, or the ticker not existing/having data for this range."
                print(message)
                return pd.DataFrame()

            # 4. Process response into DataFrame
            df = pd.DataFrame(results)
            
            # Rename columns and select required ones
            # Polygon keys: v: volume, vw: vwap, o: open, c: close, h: high, l: low, t: timestamp, n: num_transactions
            column_map = {
                't': 'Timestamp',
                'o': 'Open',
                'h': 'High',
                'l': 'Low',
                'c': 'Close',
                'v': 'Volume'
            }
            df = df.rename(columns=column_map)
            
            # Convert timestamp (milliseconds since epoch) to datetime
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
            
            # Set Timestamp as index
            df = df.set_index('Timestamp')
            
            # Ensure all required columns are present, fill with NaN if some are missing from source
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = np.nan # Or handle as an error
            
            df = df[required_columns] # Select and order columns


            return df

        except requests.exceptions.HTTPError as e: # Explicitly handle HTTPError to let it propagate as is
            raise e
        except RequestException as e:
            # This will now catch other network errors (like connection issues)
            # that are not HTTPError.
            raise Exception(f"Network error (non-HTTP) fetching data from Polygon.io for {ticker}: {e}")
        except ValueError as e: # Includes JSONDecodeError if response.json() fails
            raise Exception(f"Failed to parse JSON response or invalid value from Polygon.io for {ticker}: {e}")
        # The most general Exception catch remains for truly unexpected issues.
        except Exception as e: 
            # Log or re-raise more specific errors as needed
            raise Exception(f"An unexpected error occurred fetching data for {ticker} from Polygon.io: {e}")

    def get_service_name(self) -> str:
        return "Polygon.io"
