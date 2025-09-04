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

class BacktestAPI(Resource):
    """API endpoints for backtesting operations."""

    def __init__(self, engine):
        """Initialize backtest API with trading engine."""
        super().__init__() # Call parent constructor without args/kwargs
        self.engine = engine

    @requires_auth('read:backtest')
    def get(self, backtest_id=None):
        """Get backtest results."""
        try:
            if backtest_id:
                # Get specific backtest
                result = self.engine.get_backtest(backtest_id)
                if not result:
                    return {'error': 'Backtest not found'}, 404
                return {'backtest': result}
            else:
                # Get backtest history
                crypto_id = request.args.get('crypto_id')
                strategy_name = request.args.get('strategy_name')
                limit = int(request.args.get('limit', 50))
                results = self.engine.get_backtest_history(crypto_id, strategy_name, limit)
                return {'backtests': results}
        except Exception as e:
            logger.error(f"Error getting backtest: {e}")
            return {'error': 'Failed to get backtest'}, 500

    @requires_auth('execute:backtest')
    def post(self):
        """
        Run a backtest or optimization.

        Expected JSON body for backtest:
        {
            "action": "backtest",
            "crypto_id": "bitcoin",
            "strategy_name": "EMA_Only",
            "parameters": {...},
            "timeframe": "7d"
        }

        Expected JSON body for optimization:
        {
            "action": "optimize",
            "crypto_id": "bitcoin",
            "strategy_name": "EMA_Only",
            "n_trials": 50
        }
        """
        try:
            data = request.get_json()
            logger.info(f"Incoming backtest data: {data}")
            if not data:
                logger.error("No JSON data provided for backtest.")
                return {'error': 'No JSON data provided'}, 400

            action = data.get('action', 'backtest')

            if action == 'backtest':
                crypto_id = data.get('crypto_id')
                strategy_name = data.get('strategy_name')
                parameters = data.get('parameters', {})
                timeframe = data.get('timeframe', '7d')
                interval = data.get('interval', '30m')

                if not crypto_id or not strategy_name:
                    return {'error': 'crypto_id and strategy_name are required for backtest'}, 400

                result = self.engine.run_backtest(
                    crypto_id=crypto_id,
                    strategy_name=strategy_name,
                    parameters=parameters,
                    timeframe=timeframe,
                    interval=interval
                )
                return {'action': 'backtest', 'result': result}

            elif action == 'optimize':
                crypto_id = data.get('crypto_id')
                strategy_name = data.get('strategy_name')
                n_trials = data.get('n_trials', 50)
                timeout = data.get('timeout')

                if not crypto_id or not strategy_name:
                    return {'error': 'crypto_id and strategy_name are required for optimization'}, 400

                result = self.engine.run_optimization(
                    crypto_id=crypto_id,
                    strategy_name=strategy_name,
                    n_trials=n_trials,
                    timeout=timeout
                )
                return {'action': 'optimize', 'result': result}

            elif action == 'optimize_volatile':
                strategy_name = data.get('strategy_name')
                n_trials = data.get('n_trials', 30)
                top_count = data.get('top_count', 10)
                min_volatility = data.get('min_volatility', 5.0)

                if not strategy_name:
                    return {'error': 'strategy_name is required for volatile optimization'}, 400

                result = self.engine.run_volatile_optimization(
                    strategy_name=strategy_name,
                    n_trials=n_trials,
                    top_count=top_count,
                    min_volatility=min_volatility
                )
                return {'action': 'optimize_volatile', 'result': result}

            else:
                return {'error': f'Unknown action: {action}'}, 400

        except Exception as e:
            logger.error(f"Error in backtest API: {e}")
            return {'error': f'Operation failed: {str(e)}'}, 500
