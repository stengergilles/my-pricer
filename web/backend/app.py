"""
Complete Flask backend with Auth0 authentication for Crypto Trading System.
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, g
from flask_cors import CORS
from flask_restful import Api
from dotenv import load_dotenv
from flask_compress import Compress

# Load environment variables from the current directory's .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Add core module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.trading_engine import TradingEngine
from core.app_config import Config
from auth.middleware import AuthError, requires_auth
from api.crypto import CryptoAPI, CryptoStatusAPI
from api.analysis import AnalysisAPI
from api.backtest import BacktestAPI
from api.strategies import StrategiesAPI
from api.results import ResultsAPI
from api.scheduler import ScheduleJobAPI, JobsAPI, JobAPI, JobLogsAPI
from utils.error_handlers import register_error_handlers

# Initialize scheduler
from core.scheduler import init_scheduler, get_scheduler

# Initialize core components
config = Config()

# Initialize scheduler globally
init_scheduler(config)

from core.logger_config import setup_logging

# Set up logging
setup_logging(config)
logger = logging.getLogger(__name__)

logger.info(f"Scheduler DB URI: {config.get_db_uri()}")

# Ensure the database directory exists
db_uri = config.get_db_uri()
relative_db_path = db_uri.replace("sqlite:///", "")
db_path = os.path.join(config.BASE_DIR, relative_db_path)
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_key'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-this')
Compress(app)

# Enable CORS for frontend
CORS(app, origins="*", supports_credentials=True, allow_headers=["Authorization", "Content-Type"])

# Initialize Flask-RESTful
api = Api(app)

trading_engine = TradingEngine(config)
trading_engine.set_scheduler(get_scheduler()) # Link the scheduler to the engine

# Register error handlers
register_error_handlers(app)

@app.errorhandler(AuthError) # Keep this for clarity, though register_error_handler is more direct
def handle_auth_error(ex):
    """Auth error handler"""
    logger.error(f"Authentication Error: Code={ex.error.get('code')}, Description={ex.error.get('description')}, Status={ex.status_code}")
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

# Explicitly register AuthError handler
app.register_error_handler(AuthError, handle_auth_error)

# Register AuthError with Flask-RESTful's error handling
# api.handle_error = handle_auth_error # Handled by @app.errorhandler

# Config endpoint
@app.route('/api/config')
@requires_auth('read:config') # Protect the config endpoint
def get_config():
    """Returns public configuration settings."""
    try:
        config_data = trading_engine.get_config()
        return jsonify(config_data)
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({'error': 'Failed to get configuration'}), 500

# Health check endpoint
@app.route('/api/health')
@requires_auth('read:health')
def health_check():
    """System health check endpoint."""
    try:
        health = trading_engine.health_check()
        return jsonify(health), 200 if health['status'] == 'healthy' else 503
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Health check failed',
            'timestamp': datetime.now().isoformat()
        }), 500

# Auth test endpoint
@app.route('/api/auth/test')
@requires_auth('read:auth_test')
def auth_test():
    """Test Auth0 authentication."""
    return jsonify({
        'message': 'Authentication successful',
        'user': getattr(g, 'current_user', {}),
        'timestamp': datetime.now().isoformat()
    })

# Log receiving endpoint
@app.route('/api/log', methods=['POST'])
@requires_auth('write:log') # Protect the log endpoint
def receive_log():
    try:
        log_data = request.get_json()
        level = log_data.get('level', 'info')
        message = log_data.get('message', 'No message provided')

        if level == 'error':
            logger.error(f"FRONTEND_LOG (ERROR): {message}")
        elif level == 'warn':
            logger.warning(f"FRONTEND_LOG (WARN): {message}")
        else:
            logger.info(f"FRONTEND_LOG (INFO): {message}")

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"Error receiving frontend log: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Register API resources with Auth0 protection
api.add_resource(CryptoAPI, '/api/cryptos', '/api/cryptos/<string:crypto_id>', resource_class_kwargs={'engine': trading_engine})
api.add_resource(CryptoStatusAPI, '/api/crypto_status/<string:crypto_id>', resource_class_kwargs={'engine': trading_engine})
api.add_resource(AnalysisAPI, '/api/analysis', '/api/analysis/<string:analysis_id>', resource_class_kwargs={'engine': trading_engine})
api.add_resource(BacktestAPI, '/api/backtest', '/api/backtest/<string:backtest_id>', resource_class_kwargs={'engine': trading_engine})
api.add_resource(StrategiesAPI, '/api/strategies', '/api/strategies/<string:strategy_name>', resource_class_kwargs={'engine': trading_engine})
api.add_resource(ResultsAPI, '/api/results', '/api/results/<string:result_type>', resource_class_kwargs={'engine': trading_engine})
api.add_resource(ScheduleJobAPI, '/api/scheduler/schedule', resource_class_kwargs={'engine': trading_engine})
api.add_resource(JobsAPI, '/api/scheduler/jobs', resource_class_kwargs={'engine': trading_engine})
api.add_resource(JobAPI, '/api/scheduler/jobs/<string:job_id>', resource_class_kwargs={'engine': trading_engine})
api.add_resource(JobLogsAPI, '/api/scheduler/jobs/<string:job_id>/logs', resource_class_kwargs={'engine': trading_engine})


# Serve frontend static files (for production)
@app.route('/favicon-v2.ico')
def favicon():
    """Serve the favicon with the correct content type."""
    frontend_build_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'out')
    response = send_from_directory(frontend_build_dir, 'favicon-v2.ico', mimetype='image/vnd.microsoft.icon')
    response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve Next.js frontend files, ignoring API routes."""
    if path.startswith('api/'):
        return jsonify({'code': 'not_found', 'description': 'The requested API endpoint was not found.'}), 404

    frontend_build_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'out')

    if os.path.exists(frontend_build_dir):
        if path and os.path.exists(os.path.join(frontend_build_dir, path)):
            response = send_from_directory(frontend_build_dir, path)
        else:
            response = send_from_directory(frontend_build_dir, 'index.html')

        response.headers['Cache-Control'] = 'public, max-age=31536000'
        return response
    else:
        return jsonify({
            'message': 'Frontend not built. Run in development mode.',
            'frontend_url': os.getenv('FRONTEND_URL', 'http://localhost:3000')
        })

if __name__ == '__main__':
    import signal
    import sys

    def signal_handler(sig, frame):
        logger.info("SIGINT received. Shutting down scheduler...")
        try:
            scheduler_instance = get_scheduler()
            if scheduler_instance:
                scheduler_instance.shutdown()
                logger.info("Scheduler shut down gracefully.")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting Crypto Trading Backend...")
    logger.info(f"Auth0 Domain: {os.getenv('AUTH0_DOMAIN')}")
    logger.info(f"API Audience: {os.getenv('AUTH0_API_AUDIENCE')}")
    
    app.run(
        host=os.getenv('API_HOST', 'localhost'),
        port=int(os.getenv('API_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true',
        use_reloader=False
    )