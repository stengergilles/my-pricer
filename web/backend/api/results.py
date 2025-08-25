"""
Results management API endpoints.
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

class ResultsAPI(Resource):
    """Results management API."""
    
    # @requires_auth()
    def get(self, result_type=None):
        """Get results by type."""
        try:
            crypto_id = request.args.get('crypto_id')
            strategy_name = request.args.get('strategy_name')
            limit = int(request.args.get('limit', 50))
            
            if result_type == 'analysis':
                results = trading_engine.get_analysis_history(crypto_id, limit)
            elif result_type == 'backtest':
                results = trading_engine.get_backtest_history(crypto_id, strategy_name, limit)
            else:
                return {'error': 'Invalid result type'}, 400
            
            return {'results': results}
            
        except Exception as e:
            logger.error(f"Error in ResultsAPI.get: {str(e)}")
            return {'error': 'Internal server error'}, 500
