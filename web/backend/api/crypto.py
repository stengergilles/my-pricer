import logging
from flask import request, jsonify
from flask_restful import Resource
from datetime import datetime
import sys
import os

# Add core module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from core.crypto_discovery import CoinGeckoAPIError
from auth.decorators import auth_required

logger = logging.getLogger(__name__)

class CryptoAPI(Resource):
    """API endpoints for cryptocurrency operations."""

    def __init__(self, engine):
        """Initialize crypto API with trading engine."""
        self.engine = engine

    # @auth_required  # Commented out for now to avoid auth issues during testing
    def get(self, crypto_id=None):
        """
        Get cryptocurrency data.

        Query parameters:
        - limit: Maximum number of cryptos to return (default: 100)
        - volatile: Get only volatile cryptos (default: false)
        - min_volatility: Minimum volatility threshold (default: 5.0)
        """
        try:
            if crypto_id:
                # Get specific crypto info
                cryptos = self.engine.get_cryptos(limit=1000)
                crypto = next((c for c in cryptos if c['id'] == crypto_id), None)

                if not crypto:
                    return {'error': f'Cryptocurrency {crypto_id} not found'}, 404

                return {
                    'crypto': crypto,
                    'timestamp': datetime.now().isoformat()
                }

            else:
                # Get list of cryptos
                limit = int(request.args.get('limit', 100))
                volatile_only = request.args.get('volatile', 'false').lower() == 'true'
                min_volatility = float(request.args.get('min_volatility', 20.0))
                force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

                logger.info(f"CryptoAPI GET request: volatile_only={volatile_only}, force_refresh={force_refresh}, limit={limit}, min_volatility={min_volatility}")

                if volatile_only:
                    logger.info("Calling engine.get_volatile_cryptos")
                    cryptos = self.engine.get_volatile_cryptos(
                        min_volatility=min_volatility,
                        limit=limit,
                        force_refresh=force_refresh
                    )
                else:
                    logger.info("Calling engine.get_cryptos")
                    cryptos = self.engine.get_cryptos(limit=limit)

                logger.info(f"Cryptos from engine: {cryptos}")
                print(f"DEBUG: CryptoAPI GET response: {cryptos}") # Added debug
                response = {
                    'cryptos': cryptos,
                    'count': len(cryptos),
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"Response to frontend: {response}")
                return response

        except CoinGeckoAPIError as e:
            logger.error(f"CoinGecko API error in crypto request: {e}")
            return {'error': str(e)}, e.status_code or 500
        except ValueError as e:
            logger.error(f"Invalid parameter in crypto request: {e}")
            return {'error': f'Invalid parameter: {str(e)}'}, 400
        except Exception as e:
            logger.error(f"Error in crypto API: {e}")
            return {'error': 'Internal server error'}, 500

    # @auth_required  # Commented out for now to avoid auth issues during testing
    def post(self):
        """
        Perform crypto operations like analysis or discovery.

        Expected JSON body:
        {
            "action": "analyze" | "discover_volatile" | "search" | "top_movers",
            "crypto_id": "bitcoin" (for analyze),
            "strategy": "EMA_Only" (for analyze),
            "parameters": {...} (for analyze),
            "query": "bitcoin" (for search),
            "min_volatility": 5.0 (for discover_volatile),
            "count": 10 (for top_movers)
        }
        """
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No JSON data provided'}, 400

            action = data.get('action')
            if not action:
                return {'error': 'Action is required'}, 400

            if action == 'analyze':
                crypto_id = data.get('crypto_id')
                strategy = data.get('strategy')
                parameters = data.get('parameters', {})
                timeframe = data.get('timeframe', '7d')

                if not crypto_id:
                    return {'error': 'crypto_id is required for analysis'}, 400

                # Run analysis using trading engine
                result = self.engine.analyze_crypto(
                    crypto_id=crypto_id,
                    strategy_name=strategy,
                    timeframe=timeframe,
                    custom_params=parameters if parameters else None
                )

                return {
                    'action': 'analyze',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                }

            elif action == 'discover_volatile':
                min_volatility = data.get('min_volatility', 5.0)
                limit = data.get('limit', 50)

                cryptos = self.engine.get_volatile_cryptos(
                    min_volatility=min_volatility,
                    limit=limit
                )

                return {
                    'action': 'discover_volatile',
                    'cryptos': cryptos,
                    'count': len(cryptos),
                    'min_volatility': min_volatility,
                    'timestamp': datetime.now().isoformat()
                }

            elif action == 'top_movers':
                count = data.get('count', 10)

                movers = self.engine.get_top_movers(count=count)

                return {
                    'action': 'top_movers',
                    'movers': movers,
                    'count': count,
                    'timestamp': datetime.now().isoformat()
                }

            elif action == 'search':
                query = data.get('query')
                limit = data.get('limit', 10)

                if not query:
                    return {'error': 'query is required for search'}, 400

                results = self.engine.search_cryptos(query, limit=limit)

                return {
                    'action': 'search',
                    'query': query,
                    'results': results,
                    'count': len(results),
                    'timestamp': datetime.now().isoformat()
                }

            else:
                return {'error': f'Unknown action: {action}'}, 400

        except Exception as e:
            logger.error(f"Error in crypto POST: {e}")
            return {'error': 'Internal server error'}, 500

class CryptoStatusAPI(Resource):
    """API endpoint for cryptocurrency status (e.g., has optimization results)."""

    def __init__(self, engine):
        self.engine = engine

    def get(self, crypto_id):
        """Get status for a specific cryptocurrency."""
        try:
            status = self.engine.get_crypto_status(crypto_id)
            print(f"DEBUG: CryptoStatusAPI GET response for {crypto_id}: {status}") # Added debug
            return {
                'crypto_id': crypto_id,
                'has_config_params': status['has_config_params'],
                'has_optimization_results': status['has_optimization_results'],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting crypto status for {crypto_id}: {e}")
            return {'error': 'Internal server error'}, 500
