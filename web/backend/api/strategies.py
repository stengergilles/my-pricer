"""
Strategies API endpoints using unified trading engine.
"""

import logging
from core.logger_config import setup_logging
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

setup_logging()
logger = logging.getLogger(__name__)

class StrategiesAPI(Resource):
    """API endpoints for trading strategies."""
    
    def __init__(self):
        """Initialize strategies API with trading engine."""
        self.config = Config()
        self.engine = TradingEngine(self.config)
    
    # @auth_required  # Commented out for now to avoid auth issues during testing
    def get(self, strategy_name=None):
        """
        Get trading strategies information.
        """
        try:
            if strategy_name:
                # Get specific strategy info
                try:
                    strategy_info = self.engine.get_strategy_info(strategy_name)
                    return {
                        'strategy': strategy_info,
                        'timestamp': datetime.now().isoformat()
                    }
                except ValueError as e:
                    return {'error': str(e)}, 404
            else:
                # Get all strategies
                strategies = self.engine.get_strategies()
                return {
                    'strategies': strategies,
                    'count': len(strategies),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error in strategies API: {e}")
            return {'error': 'Internal server error'}, 500
    
    # @auth_required  # Commented out for now to avoid auth issues during testing
    def post(self):
        """
        Validate strategy parameters or get defaults.
        
        Expected JSON body:
        {
            "action": "validate" | "get_defaults",
            "strategy": "EMA_Only",
            "parameters": {...} (for validate action)
        }
        """
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No JSON data provided'}, 400
            
            action = data.get('action')
            strategy_name = data.get('strategy')
            
            if not strategy_name:
                return {'error': 'strategy is required'}, 400
            
            if action == 'validate':
                parameters = data.get('parameters', {})
                
                # Validate parameters
                errors = self.engine.validate_parameters(strategy_name, parameters)
                
                return {
                    'action': 'validate',
                    'strategy': strategy_name,
                    'valid': len(errors) == 0,
                    'errors': errors,
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action == 'get_defaults':
                defaults = self.engine.get_default_parameters(strategy_name)
                
                return {
                    'action': 'get_defaults',
                    'strategy': strategy_name,
                    'defaults': defaults,
                    'timestamp': datetime.now().isoformat()
                }
            
            else:
                return {'error': f'Unknown action: {action}'}, 400
                
        except ValueError as e:
            return {'error': str(e)}, 400
        except Exception as e:
            logger.error(f"Error in strategies POST: {e}")
            return {'error': 'Internal server error'}, 500
