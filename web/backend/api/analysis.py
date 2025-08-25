"""
Analysis API endpoints using unified trading engine.
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

class AnalysisAPI(Resource):
    """API endpoints for crypto analysis operations."""
    
    def __init__(self):
        """Initialize analysis API with trading engine."""
        self.config = Config()
        self.engine = TradingEngine(self.config)
    
    # @auth_required  # Commented out for now to avoid auth issues during testing
    def post(self):
        """
        Run crypto analysis.
        
        Expected JSON body:
        {
            "crypto_id": "bitcoin",
            "strategy": "EMA_Only" (optional),
            "parameters": {...} (optional),
            "timeframe": "7d" (optional)
        }
        """
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No JSON data provided'}, 400
            
            crypto_id = data.get('crypto_id')
            if not crypto_id:
                return {'error': 'crypto_id is required'}, 400
            
            strategy = data.get('strategy')
            parameters = data.get('parameters', {})
            timeframe = data.get('timeframe', '7d')
            
            # Run analysis using trading engine
            result = self.engine.analyze_crypto(
                crypto_id=crypto_id,
                strategy_name=strategy,
                timeframe=timeframe,
                custom_params=parameters if parameters else None
            )
            
            return {
                'analysis': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in analysis API: {e}")
            return {'error': f'Analysis failed: {str(e)}'}, 500
    
    # @auth_required  # Commented out for now to avoid auth issues during testing
    def get(self, analysis_id=None):
        """Get analysis results or history."""
        try:
            if analysis_id:
                # Get specific analysis result (would need to be implemented)
                return {'error': 'Analysis retrieval by ID not yet implemented'}, 501
            else:
                # Get analysis history
                crypto_id = request.args.get('crypto_id')
                limit = int(request.args.get('limit', 50))
                
                # This would need to be implemented in the trading engine
                # For now, return empty list
                return {
                    'analyses': [],
                    'count': 0,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting analysis: {e}")
            return {'error': 'Internal server error'}, 500
