"""
Backtest API endpoints.
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
from utils.validators import validate_request_data, backtest_schema

logger = logging.getLogger(__name__)
trading_engine = TradingEngine(Config())

class BacktestAPI(Resource):
    """Backtest API."""
    
    @requires_auth()
    def post(self):
        """Run backtest."""
        try:
            # Get request data
            data = request.get_json()
            if not data:
                return {'error': 'Request data is required'}, 400
            
            # Validate request data
            validated_data = validate_request_data(data, backtest_schema)
            
            crypto_id = validated_data['crypto_id']
            strategy_name = validated_data['strategy_name']
            parameters = validated_data['parameters']
            timeframe = validated_data.get('timeframe', 30)
            
            # Validate parameters
            validated_params = trading_engine.validate_parameters(strategy_name, parameters)
            
            logger.info(f"Starting backtest for {crypto_id} with {strategy_name}")
            
            # Run backtest
            result = trading_engine.run_backtest(
                crypto_id=crypto_id,
                strategy_name=strategy_name,
                parameters=validated_params,
                timeframe=timeframe,
                save_result=True
            )
            
            return {
                'success': True,
                'backtest': result
            }
            
        except ValueError as e:
            logger.warning(f"Validation error in backtest: {str(e)}")
            return {'error': str(e)}, 400
        except Exception as e:
            logger.error(f"Error in BacktestAPI.post: {str(e)}")
            return {'error': 'Backtest failed'}, 500
    
    @requires_auth()
    def get(self, backtest_id=None):
        """Get backtest results."""
        try:
            if backtest_id:
                # Get specific backtest result
                result = trading_engine.result_manager.get_backtest_by_id(backtest_id)
                if not result:
                    return {'error': 'Backtest not found'}, 404
                return {'backtest': result}
            else:
                # Get backtest history
                crypto_id = request.args.get('crypto_id')
                strategy_name = request.args.get('strategy_name')
                limit = int(request.args.get('limit', 50))
                
                history = trading_engine.get_backtest_history(crypto_id, strategy_name, limit)
                return {'backtests': history}
                
        except Exception as e:
            logger.error(f"Error in BacktestAPI.get: {str(e)}")
            return {'error': 'Internal server error'}, 500
