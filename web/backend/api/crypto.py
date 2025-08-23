"""
Cryptocurrency API endpoints.
"""

import logging
import sys
import os
from flask import request
from flask_restful import Resource

# Add core module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from auth.middleware import requires_auth
from core.trading_engine import TradingEngine
from core.app_config import Config

logger = logging.getLogger(__name__)
trading_engine = TradingEngine(Config())

class CryptoAPI(Resource):
    """Cryptocurrency management API."""
    
    @requires_auth()
    def get(self, crypto_id=None):
        """Get cryptocurrency information."""
        try:
            if crypto_id:
                # Get specific crypto info
                cryptos = trading_engine.get_available_cryptos()
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
                # Get all available cryptos
                cryptos = trading_engine.get_available_cryptos()
                return {'cryptos': cryptos}
                
        except Exception as e:
            logger.error(f"Error in CryptoAPI.get: {str(e)}")
            return {'error': 'Internal server error'}, 500
