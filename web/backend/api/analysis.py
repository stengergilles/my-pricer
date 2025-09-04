import logging
from flask import request, jsonify
from werkzeug.exceptions import BadRequest # Import BadRequest
from flask_restful import Resource
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from web.backend.auth.middleware import requires_auth # Import requires_auth
from core.trading_engine import TradingEngine # Import TradingEngine

logger = logging.getLogger(__name__)

class AnalysisAPI(Resource):
    """API endpoints for crypto analysis operations."""

    def __init__(self, engine):
        """Initialize analysis API with trading engine."""
        super().__init__() # Call parent constructor without args/kwargs
        self.engine = engine

    @requires_auth('read:analysis')
    def get(self, analysis_id=None):
        """Get analysis results."""
        try:
            if analysis_id:
                # Get specific analysis
                result = self.engine.get_analysis(analysis_id)
                if not result:
                    return {'error': 'Analysis not found'}, 404
                return {'analysis': result}
            else:
                # Get analysis history
                crypto_id = request.args.get('crypto_id')
                limit = int(request.args.get('limit', 50))
                results = self.engine.get_analysis_history(crypto_id, limit)
                return {'analyses': results}
        except Exception as e:
            logger.error(f"Error getting analysis: {e}")
            return {'error': 'Failed to get analysis'}, 500

    @requires_auth('execute:analysis')
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
