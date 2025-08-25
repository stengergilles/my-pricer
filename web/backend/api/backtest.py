"""
Backtest API endpoints using unified trading engine.
"""

import logging
from flask import request
from flask_restful import Resource
from datetime import datetime
import sys
import os

# Add core module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from core.trading_engine import TradingEngine
from core.app_config import Config
from auth.decorators import auth_required

logger = logging.getLogger(__name__)

class BacktestAPI(Resource):
    """API endpoints for backtesting operations."""
    
    def __init__(self):
        """Initialize backtest API with trading engine."""
        self.config = Config()
        self.engine = TradingEngine(self.config)
    
    # @auth_required  # Commented out for now to avoid auth issues during testing
    def post(self):
        """
        Run backtest or optimization.
        
        Expected JSON body for backtest:
        {
            "action": "backtest",
            "crypto_id": "bitcoin",
            "strategy_name": "EMA_Only",
            "parameters": {...},
            "timeframe": "7d" (optional),
            "interval": "30m" (optional)
        }
        
        Expected JSON body for optimization:
        {
            "action": "optimize",
            "crypto_id": "bitcoin",
            "strategy_name": "EMA_Only",
            "n_trials": 50 (optional),
            "timeout": 300 (optional)
        }
        
        Expected JSON body for volatile optimization:
        {
            "action": "optimize_volatile",
            "strategy_name": "EMA_Only",
            "n_trials": 30 (optional),
            "top_count": 10 (optional),
            "min_volatility": 5.0 (optional)
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
                # Run single backtest
                crypto_id = data.get('crypto_id')
                strategy_name = data.get('strategy_name')
                parameters = data.get('parameters', {})
                timeframe = data.get('timeframe', '7d')
                interval = data.get('interval', '30m')
                
                logger.info(f"Backtest request - crypto_id: {crypto_id}, strategy_name: {strategy_name}, timeframe: {timeframe}, interval: {interval}")

                if not crypto_id or not strategy_name:
                    logger.error(f"Missing required backtest parameters: crypto_id={crypto_id}, strategy_name={strategy_name}")
                    return {'error': 'crypto_id and strategy_name are required for backtest'}, 400
                
                result = self.engine.run_backtest(
                    crypto_id=crypto_id,
                    strategy_name=strategy_name,
                    parameters=parameters,
                    timeframe=timeframe,
                    interval=interval
                )
                
                return {
                    'action': 'backtest',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action == 'optimize':
                # Run single crypto optimization
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
                
                return {
                    'action': 'optimize',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action == 'optimize_volatile':
                # Run volatile crypto optimization
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
                
                return {
                    'action': 'optimize_volatile',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                }
            
            else:
                return {'error': f'Unknown action: {action}'}, 400
                
        except Exception as e:
            logger.error(f"Error in backtest API: {e}")
            return {'error': f'Operation failed: {str(e)}'}, 500
    
    # @auth_required  # Commented out for now to avoid auth issues during testing
    def get(self, backtest_id=None):
        """Get backtest results or history."""
        try:
            if backtest_id:
                # Get specific backtest result (would need to be implemented)
                return {'error': 'Backtest retrieval by ID not yet implemented'}, 501
            else:
                # Get backtest history
                crypto_id = request.args.get('crypto_id')
                strategy = request.args.get('strategy')
                limit = int(request.args.get('limit', 50))
                
                history = self.engine.get_backtest_history(
                    crypto_id=crypto_id,
                    strategy_name=strategy,
                    limit=limit
                )
                
                return {
                    'backtests': history,
                    'count': len(history),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting backtest: {e}")
            return {'error': 'Internal server error'}, 500
