import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time
from functools import wraps
from typing import Optional, Dict
import multiprocessing
import uuid

from .exceptions import CoinGeckoRateLimitError, CoinGeckoAPIError

def _perform_request_static(url: str, params: Optional[Dict] = None, timeout: int = 30):
    try:
        response = requests.get(url, params=params, timeout=timeout)
        return response
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None
        if status_code == 429:
            raise CoinGeckoRateLimitError(f"Rate limit exceeded: {e}")
        raise CoinGeckoAPIError(f"Failed to fetch data from CoinGecko: {e}", status_code=status_code)
    except requests.exceptions.RequestException as e:
        raise CoinGeckoAPIError(f"Failed to fetch data from CoinGecko: {e}")

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

from core.app_config import Config

class DataFetcher:
    def __init__(self, request_queue: multiprocessing.Queue, response_queue: multiprocessing.Queue, config: Config):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)

    def fetch_ohlc_data(self, crypto_id, days):
        """Fetches OHLC data from CoinGecko, with a 30-minute cache."""
        days = int(days)
        ttl_seconds = 30 * 60

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
            data = self.make_coingecko_request(url)
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
        if days < 1:
            days = 1
        days = int(days)
        url = f"https://api.coingecko.com/api/v3/coins/{symbol}/ohlc?vs_currency=usd&days={days}"
        try:
            return self.make_coingecko_request(url)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching klines for {symbol}: {e}")
            raise

    def make_coingecko_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        request_id = str(uuid.uuid4())
        
        self.request_queue.put((_perform_request_static, (url,), {'params': params, 'timeout': 30}, request_id))

        while True:
            result, received_request_id = self.response_queue.get()
            if received_request_id == request_id:
                if isinstance(result, Exception):
                    raise result
                
                response = result
                response.raise_for_status()
                return response.json()
            else:
                self.response_queue.put((result, received_request_id))
                time.sleep(0.01)

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

    def _get_current_prices_from_api(self, crypto_ids):
        """Fetches the current prices of cryptos from CoinGecko with retries."""
        ids_string = ",".join(crypto_ids)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_string}&vs_currencies=usd"
        data = self.make_coingecko_request(url)
        return {crypto_id: data.get(crypto_id, {}).get('usd') for crypto_id in crypto_ids}

    def get_current_prices(self, crypto_ids):
        """Fetches the current prices of a list of cryptos from CoinGecko, with 1-minute caching."""
        if not crypto_ids:
            return {}

        sorted_ids = sorted(crypto_ids)
        cache_key = ",".join(sorted_ids)
        cache_dir = self.config.CACHE_DIR
        cache_filename = f"prices_{hash(cache_key)}.json"
        cache_filepath = os.path.join(cache_dir, cache_filename)
        ttl_seconds = 60

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
                raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded for cryptos: {', '.join(crypto_ids)}.") from e
            else:
                self.logger.error(f"HTTP Error fetching current prices for {', '.join(crypto_ids)}: {e}")
                return {crypto_id: None for crypto_id in crypto_ids}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching current prices for {', '.join(crypto_ids)}: {e}")
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
