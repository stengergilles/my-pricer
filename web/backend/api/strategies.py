import logging
from flask import request, jsonify
from flask_restful import Resource
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from auth.decorators import auth_required

logger = logging.getLogger(__name__)

class StrategiesAPI(Resource):
    """API endpoints for trading strategies."""

    def __init__(self, engine):
        """Initialize strategies API with trading engine."""
        self.engine = engine

    #@auth_required
    def get(self, strategy_name=None):
        """Get available strategies or details of a specific strategy."""
        try:
            if strategy_name:
                strategy_info = self.engine.get_strategy_info(strategy_name)
                if not strategy_info:
                    return {'error': f'Strategy {strategy_name} not found'}, 404
                return {'strategy': strategy_info}
            else:
                strategies = self.engine.get_strategies()
                return {'strategies': strategies, 'count': len(strategies)}

        except Exception as e:
            logger.error(f"Error in strategies GET: {e}")
            return {'error': 'Internal server error'}, 500

    #@auth_required
    def post(self):
        """
        Validate strategy parameters or get default parameters.

        Expected JSON body:
        {
            "action": "validate_params" | "get_defaults",
            "strategy": "EMA_Only",
            "parameters": {...} (for validate_params)
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

            if action == 'validate_params':
                parameters = data.get('parameters', {})
                errors = self.engine.validate_parameters(strategy_name, parameters)
                return {'valid': not bool(errors), 'errors': errors}

            elif action == 'get_defaults':
                defaults = self.engine.get_default_parameters(strategy_name)
                return {'defaults': defaults}

            else:
                return {'error': f'Unknown action: {action}'}, 400

        except Exception as e:
            logger.error(f"Error in strategies POST: {e}")
            return {'error': 'Internal server error'}, 500