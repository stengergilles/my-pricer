"""
Error handling utilities.
"""

import logging
import sys
import os
from flask import jsonify

# Add auth module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from auth.middleware import AuthError

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Register error handlers for the Flask app."""
    
    @app.errorhandler(AuthError)
    def handle_auth_error(ex):
        """Handle Auth0 authentication errors."""
        logger.warning(f"Auth error: {ex.error}")
        return jsonify(ex.error), ex.status_code
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle bad request errors."""
        return jsonify({
            'error': 'Bad request',
            'message': 'The request could not be understood by the server'
        }), 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle not found errors."""
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
