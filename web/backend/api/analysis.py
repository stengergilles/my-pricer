"""
Analysis API endpoints.
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
from core.app_config import Config
from utils.validators import validate_request_data, analysis_schema

logger = logging.getLogger(__name__)
trading_engine = TradingEngine(Config())

class AnalysisAPI(Resource):
    """Crypto analysis API."""
    
    # @requires_auth()
    def post(self):
        """Run crypto analysis."""
        try:
            # Get request data
            data = request.get_json()
            if not data:
                return {'error': 'Request data is required'}, 400
            
            # Validate request data
            validated_data = validate_request_data(data, analysis_schema)
            
            crypto_id = validated_data['crypto_id']
            strategy_name = validated_data.get('strategy_name')
            timeframe = validated_data.get('timeframe', 7)
            custom_params = validated_data.get('parameters')
            
            
            
            # Run analysis
            result = trading_engine.analyze_crypto(
                crypto_id=crypto_id,
                strategy_name=strategy_name,
                timeframe=timeframe,
                custom_params=custom_params,
                save_result=True
            )
            
            return {
                'success': True,
                'analysis': result
            }
            
        except ValueError as e:
            logger.warning(f"Validation error in analysis: {str(e)}")
            return {'error': str(e)}, 400
        except Exception as e:
            logger.error(f"Error in AnalysisAPI.post: {str(e)}")
            return {'error': 'Analysis failed'}, 500
    
    # @requires_auth()
    def get(self, analysis_id=None):
        """Get analysis results."""
        try:
            if analysis_id:
                # Get specific analysis result
                result = trading_engine.result_manager.get_analysis_by_id(analysis_id)
                if not result:
                    return {'error': 'Analysis not found'}, 404
                return {'analysis': result}
            else:
                # Get analysis history
                crypto_id = request.args.get('crypto_id')
                limit = int(request.args.get('limit', 50))
                
                history = trading_engine.get_analysis_history(crypto_id, limit)
                return {'analyses': history}
                
        except Exception as e:
            logger.error(f"Error in AnalysisAPI.get: {str(e)}")
            return {'error': 'Internal server error'}, 500
