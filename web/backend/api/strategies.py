"""
Trading strategies API endpoints.
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
from core.config import Config

logger = logging.getLogger(__name__)
trading_engine = TradingEngine(Config())

class StrategiesAPI(Resource):
    """Trading strategies API."""
    
    @requires_auth()
    def get(self, strategy_name=None):
        """Get trading strategies."""
        try:
            if strategy_name:
                # Get specific strategy
                strategies = trading_engine.get_available_strategies()
                strategy = next((s for s in strategies if s['name'] == strategy_name), None)
                
                if not strategy:
                    return {'error': 'Strategy not found'}, 404
                
                return {'strategy': strategy}
            else:
                # Get all strategies
                strategies = trading_engine.get_available_strategies()
                return {'strategies': strategies}
                
        except Exception as e:
            logger.error(f"Error in StrategiesAPI.get: {str(e)}")
            return {'error': 'Internal server error'}, 500
