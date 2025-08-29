import logging
from flask import request, jsonify
from werkzeug.exceptions import BadRequest # Import BadRequest
from flask_restful import Resource
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from auth.decorators import auth_required

logger = logging.getLogger(__name__)

class AnalysisAPI(Resource):
    """API endpoints for crypto analysis operations."""

    def __init__(self, engine):
        """Initialize analysis API with trading engine."""
        self.engine = engine

    #@auth_required
    def post(self):
        """
        Run analysis on a cryptocurrency.

        Expected JSON body:
        {
            "crypto_id": "bitcoin",
            "strategy": "EMA_Only" (optional),
            "parameters": {...} (optional),
            "timeframe": "7d" (optional)
        }
        """
        try:
            try:
                data = request.get_json(force=True) # force=True to handle empty body as JSON
            except BadRequest:
                return {'error': 'Invalid JSON data provided'}, 400

            if not data:
                return {'error': 'No JSON data provided'}, 400

            crypto_id = data.get('crypto_id')
            if not crypto_id:
                return {'error': 'crypto_id is required'}, 400

            strategy = data.get('strategy')
            parameters = data.get('parameters', {})
            timeframe = data.get('timeframe', '7d')

            result = self.engine.analyze_crypto(
                crypto_id=crypto_id,
                strategy_name=strategy,
                timeframe=timeframe,
                custom_params=parameters if parameters else None
            )
            logger.debug(f"Analysis result before sending: {result}")

            return {
                'action': 'analysis',
                'result': result,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in analysis API: {e}")
            return {'error': f'Analysis failed: {str(e)}'}, 500