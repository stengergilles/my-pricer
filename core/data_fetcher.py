import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time
from functools import wraps

from core.optimizer import CoinGeckoRateLimitError

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

from core.rate_limiter import coingecko_rate_limiter

def get_crypto_data(crypto_id, days, config):
    """Fetches OHLC data from CoinGecko, with a 30-minute cache."""
    days = int(days)
    ttl_seconds = 30 * 60  # 30 minutes

    cache_dir = config.CACHE_DIR
    safe_crypto_id = crypto_id.replace(" ", "_").lower()
    cache_filename = f"{safe_crypto_id}_{days}d_ohlc.json"
    cache_filepath = os.path.join(cache_dir, cache_filename)

    os.makedirs(cache_dir, exist_ok=True)

    if os.path.exists(cache_filepath):
        file_mod_time = os.path.getmtime(cache_filepath)
        age_seconds = time.time() - file_mod_time
        if age_seconds < ttl_seconds:
            logging.info(f"Cache hit for {crypto_id} (OHLC). Reading from {cache_filepath}")
            try:
                with open(cache_filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to read cache file {cache_filepath}: {e}. Re-fetching.")
        else:
            logging.info(f"Cache stale for {crypto_id} (OHLC).")

    logging.info(f"Cache miss or stale for {crypto_id} (OHLC). Fetching from CoinGecko.")
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/ohlc?vs_currency=usd&days={days}"
    try:
        response = coingecko_rate_limiter.make_request(requests.get, url)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Successfully fetched OHLC data for {crypto_id} from CoinGecko.")

        with open(cache_filepath, 'w') as f:
            json.dump(data, f)
        logging.info(f"Saved data to cache: {cache_filepath}")

        return data
    except requests.exceptions.HTTPError as errh:
        if errh.response.status_code == 429:
            raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded for {crypto_id}.") from errh
        else:
            logging.warning(f"HTTP Error fetching data for {crypto_id}: {errh}")
            if os.path.exists(cache_filepath):
                logging.warning("API call failed. Returning stale cache data.")
                with open(cache_filepath, 'r') as f:
                    return json.load(f)
            raise
    except requests.exceptions.RequestException as err:
        logging.error(f"Request failed for {crypto_id}: {err}")
        if os.path.exists(cache_filepath):
            logging.warning("API call failed. Returning stale cache data.")
            with open(cache_filepath, 'r') as f:
                return json.load(f)
        raise

def get_crypto_data_merged(crypto_id, days, config):
    """Fetches OHLC data from CoinGecko and returns it as a Pandas DataFrame."""
    fetch_days = int(days) if days else 1
    ohlc_data = get_crypto_data(crypto_id, fetch_days, config)

    if ohlc_data is None or not ohlc_data:
        logging.warning(f"No OHLC data returned for {crypto_id} after fetching.")
        return None

    ohlc_df = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'close'])
    ohlc_df['timestamp'] = pd.to_datetime(ohlc_df['timestamp'], unit='ms')
    ohlc_df.set_index('timestamp', inplace=True)
    ohlc_df.sort_index(inplace=True)

    logging.info(f"Processed {len(ohlc_df)} data points for {crypto_id}")

    return ohlc_df

@retry_on_exception(retries=3, delay=5, backoff=2, exception_to_check=requests.exceptions.RequestException)
def get_current_prices_from_api(crypto_ids):
    """Fetches the current prices of cryptos from CoinGecko with retries."""
    ids_string = ",".join(crypto_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_string}&vs_currencies=usd"
    response = coingecko_rate_limiter.make_request(requests.get, url)
    response.raise_for_status()
    data = response.json()
    return {crypto_id: data.get(crypto_id, {}).get('usd') for crypto_id in crypto_ids}

def get_current_prices(crypto_ids, config):
    """Fetches the current prices of a list of cryptos from CoinGecko, with 1-minute caching."""
    if not crypto_ids:
        return {}

    # Sort IDs to ensure consistent cache key
    sorted_ids = sorted(crypto_ids)
    cache_key = ",".join(sorted_ids)
    cache_dir = config.CACHE_DIR
    cache_filename = f"prices_{hash(cache_key)}.json"
    cache_filepath = os.path.join(cache_dir, cache_filename)
    ttl_seconds = 60  # 1 minute

    os.makedirs(cache_dir, exist_ok=True)

    if os.path.exists(cache_filepath):
        file_mod_time = os.path.getmtime(cache_filepath)
        age_seconds = time.time() - file_mod_time
        if age_seconds < ttl_seconds:
            logging.info(f"Cache hit for prices of {len(crypto_ids)} cryptos.")
            try:
                with open(cache_filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to read price cache file: {e}. Re-fetching.")

    logging.info(f"Cache miss for prices of {len(crypto_ids)} cryptos. Fetching from API.")
    try:
        prices = get_current_prices_from_api(crypto_ids)
        with open(cache_filepath, 'w') as f:
            json.dump(prices, f)
        return prices
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded for cryptos: {",".join(crypto_ids)}.") from e
        else:
            logging.error(f"HTTP Error fetching current prices for {",".join(crypto_ids)}: {e}")
            return {crypto_id: None for crypto_id in crypto_ids}
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching current prices for {",".join(crypto_ids)}: {e}")
        return {crypto_id: None for crypto_id in crypto_ids}

@retry_on_exception(retries=3, delay=5, backoff=2, exception_to_check=requests.exceptions.RequestException)
def get_current_price_from_api(crypto_id):
    """DEPRECATED: Fetches the current price of a single crypto. Use get_current_prices for batching."""
    logging.warning("DEPRECATED: get_current_price_from_api is deprecated. Use get_current_prices.")
    prices = get_current_prices_from_api([crypto_id])
    return prices.get(crypto_id)

def get_current_price(crypto_id, config):
    """
    DEPRECATED: Fetches the current price of a single crypto from CoinGecko.
    Use get_current_prices for batch operations to avoid rate limiting.
    """
    logging.warning("DEPRECATED: get_current_price is deprecated. Use get_current_prices.")
    return get_current_prices([crypto_id], config).get(crypto_id)