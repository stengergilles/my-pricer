import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time
from functools import wraps
from typing import Optional, Dict # New import

from .exceptions import CoinGeckoRateLimitError
def retry_on_exception(retries=3, delay=5, backoff=2, exception_to_check=Exception):
    """
    A decorator to retry a function call on exception with exponential backoff.
    Re-raises the exception on failure.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _delay = delay
            last_exception = None
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except exception_to_check as e:
                    last_exception = e
                    logging.warning(f"Caught {e}, retrying in {_delay} seconds... ({i+1}/{retries})")
                    time.sleep(_delay)
                    _delay *= backoff
            logging.error(f"Function {func.__name__} failed after {retries} retries.")
            if last_exception:
                raise last_exception
        return wrapper
    return decorator

from core.rate_limiter import RateLimiter, coingecko_rate_limiter # New import, added coingecko_rate_limiter
from core.app_config import Config # New import for Config

class DataFetcher:
    def __init__(self, rate_limiter: Optional[RateLimiter] = None, config: Config = None): # Made rate_limiter optional
        self.config = config or Config() # Initialize Config if not provided
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session() # Use a session for efficiency
        
        # Use provided rate_limiter or the global coingecko_rate_limiter
        self.rate_limiter = rate_limiter if rate_limiter is not None else coingecko_rate_limiter

    def fetch_ohlc_data(self, crypto_id, days):
        """Fetches OHLC data from CoinGecko, with a 30-minute cache."""
        days = int(days)
        ttl_seconds = 30 * 60  # 30 minutes

        cache_dir = self.config.CACHE_DIR
        safe_crypto_id = crypto_id.replace(" ", "_").lower()
        cache_filename = f"{safe_crypto_id}_{days}d_ohlc.json"
        cache_filepath = os.path.join(cache_dir, cache_filename)

        os.makedirs(cache_dir, exist_ok=True)

        if os.path.exists(cache_filepath):
            file_mod_time = os.path.getmtime(cache_filepath)
            age_seconds = time.time() - file_mod_time
            if age_seconds < ttl_seconds:
                self.logger.info(f"Cache hit for {crypto_id} (OHLC). Reading from {cache_filepath}")
                try:
                    with open(cache_filepath, 'r') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.warning(f"Failed to read cache file {cache_filepath}: {e}. Re-fetching.")
            else:
                self.logger.info(f"Cache stale for {crypto_id} (OHLC).")

        self.logger.info(f"Cache miss or stale for {crypto_id} (OHLC). Fetching from CoinGecko.")
        url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/ohlc?vs_currency=usd&days={days}"
        try:
            response = self.rate_limiter.make_request(self.session.get, url)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Successfully fetched OHLC data for {crypto_id} from CoinGecko.")

            with open(cache_filepath, 'w') as f:
                json.dump(data, f)
            self.logger.info(f"Saved data to cache: {cache_filepath}")

            return data
        except requests.exceptions.HTTPError as errh:
            if errh.response.status_code == 429:
                raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded for {crypto_id}.") from errh
            else:
                self.logger.warning(f"HTTP Error fetching data for {crypto_id}: {errh}")
                if os.path.exists(cache_filepath):
                    self.logger.warning("API call failed. Returning stale cache data.")
                    with open(cache_filepath, 'r') as f:
                        return json.load(f)
                raise
        except requests.exceptions.RequestException as err:
            self.logger.error(f"Request failed for {crypto_id}: {err}")
            if os.path.exists(cache_filepath):
                self.logger.warning("API call failed. Returning stale cache data.")
                with open(cache_filepath, 'r') as f:
                    return json.load(f)
            raise

    def fetch_klines(self, symbol: str, interval: str, start_time: int, end_time: int):
        """Fetches klines data from CoinGecko."""
        days = (end_time - start_time) / (1000 * 60 * 60 * 24)
        days = int(days) + 1
        url = f"https://api.coingecko.com/api/v3/coins/{symbol}/ohlc?vs_currency=usd&days={days}"
        try:
            response = self.rate_limiter.make_request(self.session.get, url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching klines for {symbol}: {e}")
            raise

    @retry_on_exception(retries=3, delay=5, backoff=2, exception_to_check=requests.exceptions.RequestException)
    def make_coingecko_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """
        Makes a rate-limited request to the CoinGecko API.
        """
        try:
            response = self.rate_limiter.make_request(self.session.get, url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as errh:
            if errh.response.status_code == 429:
                raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded for URL: {url}.") from errh
            else:
                self.logger.error(f"HTTP Error making CoinGecko request to {url}: {errh}")
                raise
        except requests.exceptions.RequestException as err:
            self.logger.error(f"Request failed for CoinGecko URL: {url}: {err}")
            raise

    def get_crypto_data_merged(self, crypto_id, days):
        """Fetches OHLC data from CoinGecko and returns it as a Pandas DataFrame."""
        fetch_days = int(days) if days else 1
        ohlc_data = self.fetch_ohlc_data(crypto_id, fetch_days)

        if ohlc_data is None or not ohlc_data:
            self.logger.warning(f"No OHLC data returned for {crypto_id} after fetching.")
            return None

        ohlc_df = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        ohlc_df['timestamp'] = pd.to_datetime(ohlc_df['timestamp'], unit='ms')
        ohlc_df.set_index('timestamp', inplace=True)
        ohlc_df.sort_index(inplace=True)

        self.logger.info(f"Processed {len(ohlc_df)} data points for {crypto_id}")

        return ohlc_df

    @retry_on_exception(retries=3, delay=5, backoff=2, exception_to_check=requests.exceptions.RequestException)
    def _get_current_prices_from_api(self, crypto_ids):
        """Fetches the current prices of cryptos from CoinGecko with retries."""
        ids_string = ",".join(crypto_ids)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_string}&vs_currencies=usd"
        response = self.rate_limiter.make_request(self.session.get, url)
        response.raise_for_status()
        data = response.json()
        return {crypto_id: data.get(crypto_id, {}).get('usd') for crypto_id in crypto_ids}

    def get_current_prices(self, crypto_ids):
        """Fetches the current prices of a list of cryptos from CoinGecko, with 1-minute caching."""
        if not crypto_ids:
            return {}

        # Sort IDs to ensure consistent cache key
        sorted_ids = sorted(crypto_ids)
        cache_key = ",".join(sorted_ids)
        cache_dir = self.config.CACHE_DIR
        cache_filename = f"prices_{hash(cache_key)}.json"
        cache_filepath = os.path.join(cache_dir, cache_filename)
        ttl_seconds = 60  # 1 minute

        os.makedirs(cache_dir, exist_ok=True)

        if os.path.exists(cache_filepath):
            file_mod_time = os.path.getmtime(cache_filepath)
            age_seconds = time.time() - file_mod_time
            if age_seconds < ttl_seconds:
                self.logger.info(f"Cache hit for prices of {len(crypto_ids)} cryptos.")
                try:
                    with open(cache_filepath, 'r') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.warning(f"Failed to read price cache file: {e}. Re-fetching.")

        self.logger.info(f"Cache miss for prices of {len(crypto_ids)} cryptos. Fetching from API.")
        try:
            prices = self._get_current_prices_from_api(crypto_ids)
            with open(cache_filepath, 'w') as f:
                json.dump(prices, f)
            return prices
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded for cryptos: {",".join(crypto_ids)}.") from e
            else:
                self.logger.error(f"HTTP Error fetching current prices for {",".join(crypto_ids)}: {e}")
                return {crypto_id: None for crypto_id in crypto_ids}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching current prices for {",".join(crypto_ids)}: {e}")
            return {crypto_id: None for crypto_id in crypto_ids}

    @retry_on_exception(retries=3, delay=5, backoff=2, exception_to_check=requests.exceptions.RequestException)
    def _get_current_price_from_api(self, crypto_id):
        """DEPRECATED: Fetches the current price of a single crypto. Use get_current_prices for batching."""
        self.logger.warning("DEPRECATED: _get_current_price_from_api is deprecated. Use get_current_prices.")
        prices = self._get_current_prices_from_api([crypto_id])
        return prices.get(crypto_id)

    def get_current_price(self, crypto_id):
        """
        DEPRECATED: Fetches the current price of a single crypto from CoinGecko.
        Use get_current_prices for batch operations to avoid rate limiting.
        """
        self.logger.warning("DEPRECATED: get_current_price is deprecated. Use get_current_prices.")
        return self.get_current_prices([crypto_id]).get(crypto_id)