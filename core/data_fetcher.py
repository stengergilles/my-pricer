import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time

from core.optimizer import CoinGeckoRateLimitError

def get_crypto_data(crypto_id, days, config):
    """Fetches OHLC data from CoinGecko, with caching based on implicit granularity."""
    days = int(days)

    # Determine implicit granularity and TTL from the 'days' parameter based on CoinGecko API behavior.
    if days == 1:
        # For days=1, CoinGecko returns minute-level data. Per user, TTL is 30 minutes.
        ttl_seconds = 30 * 60
        granularity_label = "minutes"
    elif 2 <= days <= 90:
        # For 2-90 days, CoinGecko returns hourly data. TTL is 1 hour.
        ttl_seconds = 60 * 60
        granularity_label = "hourly"
    else:  # days > 90
        # For >90 days, CoinGecko returns daily data. TTL is 24 hours.
        ttl_seconds = 24 * 60 * 60
        granularity_label = "daily"

    cache_dir = config.CACHE_DIR
    safe_crypto_id = crypto_id.replace(" ", "_").lower()
    # Use a more descriptive cache filename
    cache_filename = f"{safe_crypto_id}_{days}d_{granularity_label}.json"
    cache_filepath = os.path.join(cache_dir, cache_filename)

    os.makedirs(cache_dir, exist_ok=True)

    # Check cache for freshness
    if os.path.exists(cache_filepath):
        file_mod_time = os.path.getmtime(cache_filepath)
        age_seconds = time.time() - file_mod_time
        if age_seconds < ttl_seconds:
            logging.info(f"Cache hit for {crypto_id} ({days} days, {granularity_label}). Reading from {cache_filepath}")
            try:
                with open(cache_filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to read cache file {cache_filepath}: {e}. Re-fetching.")
        else:
            logging.info(f"Cache stale for {crypto_id} ({days} days, {granularity_label}).")

    logging.info(f"Cache miss or stale for {crypto_id} ({days} days, {granularity_label}). Fetching from CoinGecko.")
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/ohlc?vs_currency=usd&days={days}"
    try:
        response = requests.get(url)
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