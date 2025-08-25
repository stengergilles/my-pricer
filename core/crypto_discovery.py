"""
Unified cryptocurrency discovery and volatility analysis.
Consolidates logic from get_volatile_cryptos.py and volatile_crypto_optimizer.py.
"""

import requests
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os

class CryptoDiscovery:
    """
    Handles cryptocurrency discovery, volatility analysis, and data caching.
    """
    
    def __init__(self, cache_dir: str = "backtest_results"):
        """Initialize crypto discovery with caching directory."""
        self.cache_dir = cache_dir
        self.logger = logging.getLogger(__name__)
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # CoinGecko API configuration
        self.base_url = "https://api.coingecko.com/api/v3"
        self.rate_limit_delay = 1.1  # Seconds between API calls
        
    def get_volatile_cryptos(self, 
                           limit: int = 100, 
                           min_volatility: float = 5.0,
                           cache_hours: int = 1) -> List[Dict]:
        """
        Fetch volatile cryptocurrencies based on 24h price change.
        
        Args:
            limit: Maximum number of cryptos to fetch
            min_volatility: Minimum absolute price change percentage
            cache_hours: Hours to cache results
            
        Returns:
            List of crypto dictionaries with volatility data
        """
        cache_file = os.path.join(self.cache_dir, "volatile_cryptos.json")
        
        # Check cache first
        if self._is_cache_valid(cache_file, cache_hours):
            self.logger.info("Using cached volatile crypto data")
            return self._load_cache(cache_file)
        
        self.logger.info(f"Fetching volatile cryptos from CoinGecko (limit: {limit})")
        
        # Fetch from CoinGecko
        url = f"{self.base_url}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': min(limit, 250),  # CoinGecko limit
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '24h'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Filter and process data
            volatile_cryptos = self._process_crypto_data(data, min_volatility)
            
            # Cache results
            self._save_cache(cache_file, volatile_cryptos)
            
            self.logger.info(f"Found {len(volatile_cryptos)} volatile cryptos")
            return volatile_cryptos
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching data from CoinGecko: {e}")
            
            # Try to return cached data even if expired
            if os.path.exists(cache_file):
                self.logger.warning("Using expired cache due to API error")
                return self._load_cache(cache_file)
            
            return []
    
    def get_top_movers(self, 
                      count: int = 10, 
                      include_gainers: bool = True, 
                      include_losers: bool = True) -> Dict[str, List[Dict]]:
        """
        Get top gaining and losing cryptocurrencies.
        
        Args:
            count: Number of top movers in each category
            include_gainers: Include top gainers
            include_losers: Include top losers
            
        Returns:
            Dictionary with 'gainers' and 'losers' lists
        """
        volatile_cryptos = self.get_volatile_cryptos()
        
        if not volatile_cryptos:
            return {'gainers': [], 'losers': []}
        
        # Sort by price change
        sorted_cryptos = sorted(volatile_cryptos, 
                              key=lambda x: x.get('price_change_percentage_24h', 0), 
                              reverse=True)
        
        result = {}
        
        if include_gainers:
            # Top gainers (positive change)
            gainers = [crypto for crypto in sorted_cryptos 
                      if crypto.get('price_change_percentage_24h', 0) > 0]
            result['gainers'] = gainers[:count]
        
        if include_losers:
            # Top losers (negative change)
            losers = [crypto for crypto in sorted_cryptos 
                     if crypto.get('price_change_percentage_24h', 0) < 0]
            result['losers'] = losers[-count:]  # Take from end (most negative)
        
        return result
    
    def get_crypto_by_volatility(self, min_volatility: float = 20.0) -> List[Dict]:
        """
        Get cryptocurrencies above a specific volatility threshold.
        
        Args:
            min_volatility: Minimum absolute price change percentage
            
        Returns:
            List of cryptos meeting volatility criteria
        """
        volatile_cryptos = self.get_volatile_cryptos()
        
        high_volatility = [
            crypto for crypto in volatile_cryptos
            if abs(crypto.get('price_change_percentage_24h', 0)) >= min_volatility
        ]
        
        # Sort by absolute volatility
        high_volatility.sort(
            key=lambda x: abs(x.get('price_change_percentage_24h', 0)), 
            reverse=True
        )
        
        return high_volatility
    
    def get_crypto_info(self, crypto_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific cryptocurrency.
        
        Args:
            crypto_id: CoinGecko crypto ID
            
        Returns:
            Crypto information dictionary or None if not found
        """
        url = f"{self.base_url}/coins/{crypto_id}"
        params = {
            'localization': False,
            'tickers': False,
            'market_data': True,
            'community_data': False,
            'developer_data': False,
            'sparkline': False
        }
        
        try:
            time.sleep(self.rate_limit_delay)  # Rate limiting
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching info for {crypto_id}: {e}")
            return None
    
    def search_cryptos(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for cryptocurrencies by name or symbol.
        
        Args:
            query: Search query (name or symbol)
            limit: Maximum results to return
            
        Returns:
            List of matching cryptocurrencies
        """
        url = f"{self.base_url}/search"
        params = {'query': query}
        
        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Return coins only (not exchanges or categories)
            coins = data.get('coins', [])[:limit]
            return coins
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error searching for '{query}': {e}")
            return []
    
    def _process_crypto_data(self, raw_data: List[Dict], min_volatility: float) -> List[Dict]:
        """Process and filter raw crypto data from API."""
        processed = []
        
        for coin in raw_data:
            price_change = coin.get('price_change_percentage_24h')
            
            # Skip coins without price change data
            if price_change is None:
                continue
            
            # Skip coins below volatility threshold
            if abs(price_change) < min_volatility:
                continue
            
            # Extract relevant data
            crypto_data = {
                'id': coin.get('id'),
                'symbol': coin.get('symbol', '').upper(),
                'name': coin.get('name'),
                'current_price': coin.get('current_price'),
                'market_cap': coin.get('market_cap'),
                'market_cap_rank': coin.get('market_cap_rank'),
                'price_change_percentage_24h': price_change,
                'total_volume': coin.get('total_volume'),
                'circulating_supply': coin.get('circulating_supply'),
                'last_updated': coin.get('last_updated'),
                'volatility_score': abs(price_change),  # Add volatility score
                'fetch_timestamp': datetime.now().isoformat()
            }
            
            processed.append(crypto_data)
        
        # Sort by volatility (highest first)
        processed.sort(key=lambda x: x['volatility_score'], reverse=True)
        
        return processed
    
    def _is_cache_valid(self, cache_file: str, cache_hours: int) -> bool:
        """Check if cache file exists and is within the cache period."""
        if not os.path.exists(cache_file):
            return False
        
        try:
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            cache_expiry = datetime.now() - timedelta(hours=cache_hours)
            return file_time > cache_expiry
        except OSError:
            return False
    
    def _load_cache(self, cache_file: str) -> List[Dict]:
        """Load data from cache file."""
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self.logger.error(f"Error loading cache: {e}")
            return []
    
    def _save_cache(self, cache_file: str, data: List[Dict]) -> None:
        """Save data to cache file."""
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            self.logger.error(f"Error saving cache: {e}")
    
    def get_market_summary(self) -> Dict:
        """Get overall market summary statistics."""
        volatile_cryptos = self.get_volatile_cryptos()
        
        if not volatile_cryptos:
            return {}
        
        price_changes = [crypto.get('price_change_percentage_24h', 0) 
                        for crypto in volatile_cryptos]
        
        return {
            'total_cryptos': len(volatile_cryptos),
            'avg_price_change': sum(price_changes) / len(price_changes),
            'max_gain': max(price_changes),
            'max_loss': min(price_changes),
            'high_volatility_count': len([p for p in price_changes if abs(p) >= 20]),
            'gainers_count': len([p for p in price_changes if p > 0]),
            'losers_count': len([p for p in price_changes if p < 0]),
            'last_updated': datetime.now().isoformat()
        }
