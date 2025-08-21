"""
Data fetching and caching manager.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class DataManager:
    """Manages data fetching and caching."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_duration = 300  # 5 minutes
    
    def get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if valid."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now() - cache_time < timedelta(seconds=self.cache_duration):
                return cached_data['data']
        except Exception as e:
            print(f"Error reading cache {cache_key}: {e}")
        
        return None
    
    def set_cached_data(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store data in cache."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        cached_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cached_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error writing cache {cache_key}: {e}")
    
    def clear_cache(self, cache_key: Optional[str] = None) -> None:
        """Clear cache files."""
        if cache_key:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
        else:
            # Clear all cache files
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
