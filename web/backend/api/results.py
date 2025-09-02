import logging
from flask import request, jsonify
from flask_restful import Resource
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from web.backend.auth.middleware import requires_auth
from core.trading_engine import TradingEngine # Import TradingEngine

logger = logging.getLogger(__name__)

class ResultsAPI(Resource):
    """API endpoints for optimization and backtest results."""

    def __init__(self, engine):
        """Initialize results API with trading engine."""
        super().__init__() # Call parent constructor without args/kwargs
        self.engine = engine

    @requires_auth('read:results')
    def get(self, result_type):
        """
        Get optimization or backtest results.

        Args:
            result_type: 'optimization' or 'backtest'

        Query parameters:
        - crypto_id: Filter by crypto
        - strategy_name: Filter by strategy
        - limit: Max number of results
        """
        try:
            crypto_id = request.args.get('crypto_id')
            strategy_name = request.args.get('strategy_name')
            limit = int(request.args.get('limit', 50))

            if result_type == 'optimization':
                if crypto_id and strategy_name:
                    results = self.engine.get_optimization_results(crypto_id, strategy_name)
                else:
                    results = self.engine.get_all_results()
            elif result_type == 'backtest':
                results = self.engine.get_backtest_history(crypto_id, strategy_name, limit)
            elif result_type == 'analysis':
                results = self.engine.get_analysis_history(crypto_id, limit)
            else:
                return {'error': 'Invalid result type'}, 400

            return {
                'result_type': result_type,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting results: {e}")
            return {'error': 'Internal server error'}, 500
