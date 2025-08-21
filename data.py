import requests
import logging
import pandas as pd

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
        logging.error(f"Http Error fetching OHLC data for {crypto_id}: {errh}")
    except requests.exceptions.ConnectionError as errc:
        logging.error(f"Connection Error fetching OHLC data for {crypto_id}: {errc}")
    except requests.exceptions.Timeout as errt:
        logging.error(f"Timeout Error fetching OHLC data for {crypto_id}: {errt}")
    except requests.exceptions.RequestException as err:
        logging.error(f"Request Error fetching OHLC data for {crypto_id}: {err}")
    return None



def get_crypto_data_merged(crypto_id, days):
    """Fetches OHLC data from CoinGecko."""
    # Ensure we fetch enough data for indicator calculations
    # Use the days parameter or default to 30 days minimum for sufficient history
    fetch_days = max(int(days), 30) if days else 30
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
