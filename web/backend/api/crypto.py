"""
Cryptocurrency API endpoints.
"""

import logging
import sys
import os
import glob
from flask import request
from flask_restful import Resource

# Add core module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from auth.middleware import requires_auth
from core.trading_engine import TradingEngine
from core.app_config import Config
from config import param_sets

logger = logging.getLogger(__name__)
trading_engine = TradingEngine(Config())

class CryptoAPI(Resource):
    """Cryptocurrency management API."""
    
    # @requires_auth()
    def get(self, crypto_id=None):
        """Get cryptocurrency information."""
        try:
            if crypto_id:
                # Get specific crypto info
                cryptos = self._get_cryptos_with_params()
                crypto = next((c for c in cryptos if c['id'] == crypto_id), None)
                
                if not crypto:
                    return {'error': 'Cryptocurrency not found'}, 404
                
                # Add current price if available
                try:
                    # Mock current price for now
                    crypto['current_price'] = 50000.0
                except Exception as e:
                    logger.warning(f"Could not fetch current price for {crypto_id}: {e}")
                
                return {'crypto': crypto}
            else:
                # Get list of cryptos with optimization parameters or results
                cryptos = self._get_cryptos_with_params()
                return {'cryptos': cryptos}
                
        except Exception as e:
            logger.error(f"Error in CryptoAPI.get: {str(e)}")
            return {'error': 'Internal server error'}, 500
    
    def _get_cryptos_with_params(self):
        """Get list of cryptocurrencies that have optimization parameters or results."""
        cryptos = []
        
        # Get cryptos from param_sets (those with specific parameter configurations)
        crypto_ids_from_config = set()
        for crypto_id, param_set in param_sets.items():
            if crypto_id != 'default_sets':  # Skip the default parameter sets
                crypto_ids_from_config.add(crypto_id)
        
        # Get cryptos from backtest results (those we've actually optimized)
        crypto_ids_from_results = set()
        try:
            base_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..')
            results_dir = os.path.join(base_dir, 'backtest_results')
            
            if os.path.exists(results_dir):
                # Look for best_params_*.json files
                pattern = os.path.join(results_dir, 'best_params_*.json')
                result_files = glob.glob(pattern)
                
                for file_path in result_files:
                    filename = os.path.basename(file_path)
                    # Extract crypto name from filename: best_params_CRYPTO_STRATEGY_TYPE.json
                    if filename.startswith('best_params_'):
                        parts = filename[12:].split('_')  # Remove 'best_params_' prefix
                        if parts:
                            crypto_id = parts[0]
                            crypto_ids_from_results.add(crypto_id)
        except Exception as e:
            logger.warning(f"Could not scan backtest results: {e}")
        
        # Combine both sets
        all_crypto_ids = crypto_ids_from_config.union(crypto_ids_from_results)
        
        # Create crypto objects with proper names and symbols
        crypto_mapping = {
            'bitcoin': {'name': 'Bitcoin', 'symbol': 'BTC'},
            'ethereum': {'name': 'Ethereum', 'symbol': 'ETH'},
            'solana': {'name': 'Solana', 'symbol': 'SOL'},
            'chainlink': {'name': 'Chainlink', 'symbol': 'LINK'},
            'okb': {'name': 'OKB', 'symbol': 'OKB'},
            'mantle': {'name': 'Mantle', 'symbol': 'MNT'},
            'pudgy-penguins': {'name': 'Pudgy Penguins', 'symbol': 'PENGU'},
        }
        
        for crypto_id in sorted(all_crypto_ids):
            if crypto_id in crypto_mapping:
                crypto_info = crypto_mapping[crypto_id]
                cryptos.append({
                    'id': crypto_id,
                    'name': crypto_info['name'],
                    'symbol': crypto_info['symbol'],
                    'has_config_params': crypto_id in crypto_ids_from_config,
                    'has_optimization_results': crypto_id in crypto_ids_from_results
                })
            else:
                # Fallback for unknown cryptos
                cryptos.append({
                    'id': crypto_id,
                    'name': crypto_id.replace('-', ' ').title(),
                    'symbol': crypto_id.upper()[:4],
                    'has_config_params': crypto_id in crypto_ids_from_config,
                    'has_optimization_results': crypto_id in crypto_ids_from_results
                })
        
        return cryptos
