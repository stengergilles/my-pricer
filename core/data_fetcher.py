import requests
import logging
import pandas as pd
from datetime import datetime, timedelta

from core.logger_config import setup_logging
from core.optimizer import CoinGeckoRateLimitError

setup_logging()


def get_crypto_data(crypto_id, days):
    """Fetches OHLC data from CoinGecko."""
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/ohlc?vs_currency=usd&days={days}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Successfully fetched OHLC data for {crypto_id} from CoinGecko.")
        return data
    except requests.exceptions.HTTPError as errh:
        if errh.response.status_code == 429:
            raise CoinGeckoRateLimitError(f"CoinGecko API rate limit exceeded for {crypto_id}.") from errh
        else:
            raise # Re-raise other HTTP errors
    except requests.exceptions.ConnectionError as errc:
        raise # Re-raise connection errors
    except requests.exceptions.Timeout as errt:
        raise # Re-raise timeout errors
    except requests.exceptions.RequestException as err:
        raise # Re-raise other request exceptions
    return None


def get_crypto_data_merged(crypto_id, days):
    """Fetches OHLC data from CoinGecko and returns it as a Pandas DataFrame."""
    # Ensure we fetch enough data for indicator calculations
    # Use the days parameter or default to 30 days minimum for sufficient history
    fetch_days = int(days) if days else 1 # Ensure it's an integer, default to 1 if None
    ohlc_data = get_crypto_data(crypto_id, fetch_days)

    if ohlc_data is None:
        return None

    ohlc_df = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'close'])
    ohlc_df['timestamp'] = pd.to_datetime(ohlc_df['timestamp'], unit='ms')
    ohlc_df.set_index('timestamp', inplace=True)

    # Sort by timestamp to ensure proper chronological order
    ohlc_df.sort_index(inplace=True)

    logging.info(f"Fetched {len(ohlc_df)} data points for {crypto_id}")

    return ohlc_df
