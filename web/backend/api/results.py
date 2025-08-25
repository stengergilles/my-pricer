"""
Results API endpoints using unified trading engine.
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

class ResultsAPI(Resource):
    """API endpoints for optimization and backtest results."""
    
    def __init__(self):
        """Initialize results API with trading engine."""
        self.config = Config()
        self.engine = TradingEngine(self.config)
    
    # @auth_required  # Commented out for now to avoid auth issues during testing
    def get(self, result_type=None):
        """
        Get optimization and backtest results.
        
        Query parameters:
        - crypto_id: Filter by crypto
        - strategy: Filter by strategy
        - limit: Maximum results to return
        - type: 'top' | 'all' | 'optimization' | 'backtest'
        """
        try:
            result_type = result_type or request.args.get('type', 'all')
            crypto_id = request.args.get('crypto_id')
            strategy = request.args.get('strategy')
            limit = int(request.args.get('limit', 50))
            
            if result_type == 'top':
                # Get top optimization results
                results = self.engine.get_top_results(limit=limit)
                
                # Apply filters
                if crypto_id:
                    results = [r for r in results if r.get('crypto') == crypto_id]
                if strategy:
                    results = [r for r in results if r.get('strategy') == strategy]
                
                return {
                    'type': 'top',
                    'results': results,
                    'count': len(results),
                    'timestamp': datetime.now().isoformat()
                }
            
            elif result_type == 'all':
                # Get all optimization results
                results = self.engine.get_all_results()
                
                # Apply filters
                if crypto_id:
                    results = [r for r in results if r.get('crypto') == crypto_id]
                if strategy:
                    results = [r for r in results if r.get('strategy') == strategy]
                
                # Apply limit
                results = results[:limit]
                
                return {
                    'type': 'all',
                    'results': results,
                    'count': len(results),
                    'timestamp': datetime.now().isoformat()
                }
            
            elif result_type == 'optimization':
                # Get specific optimization result
                if not crypto_id or not strategy:
                    return {'error': 'crypto_id and strategy are required for optimization results'}, 400
                
                result = self.engine.get_optimization_results(crypto_id, strategy)
                
                if not result:
                    return {'error': 'Optimization result not found'}, 404
                
                return {
                    'type': 'optimization',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                }
            
            elif result_type == 'backtest':
                # Get backtest history
                history = self.engine.get_backtest_history(
                    crypto_id=crypto_id,
                    strategy_name=strategy,
                    limit=limit
                )
                
                return {
                    'type': 'backtest',
                    'results': history,
                    'count': len(history),
                    'timestamp': datetime.now().isoformat()
                }
            
            else:
                return {'error': f'Unknown result type: {result_type}'}, 400
                
        except ValueError as e:
            return {'error': f'Invalid parameter: {str(e)}'}, 400
        except Exception as e:
            logger.error(f"Error in results API: {e}")
            return {'error': 'Internal server error'}, 500
