"""
Shared configuration for both CLI and web interface.
"""

import os

# Try to load environment variables if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, use system environment variables only
    pass

class Config:
    """Centralized configuration management."""
    
    def __init__(self, **kwargs):
        # Base directories
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.DATA_DIR = os.path.join(self.BASE_DIR, 'data')
        
        # Data directories
        self.RESULTS_DIR = os.path.join(self.DATA_DIR, 'results')
        self.CACHE_DIR = os.path.join(self.DATA_DIR, 'cache')
        self.LOGS_DIR = os.path.join(self.DATA_DIR, 'logs')
        
        # API configuration
        self.API_HOST = os.getenv('API_HOST', 'localhost')
        self.API_PORT = int(os.getenv('API_PORT', 5000))
        self.API_BASE_URL = f'http://{self.API_HOST}:{self.API_PORT}'
        
        # Frontend configuration
        self.FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', 3000))
        self.FRONTEND_URL = os.getenv('FRONTEND_URL', f'http://localhost:{self.FRONTEND_PORT}')
        
        # Auth0 configuration
        self.AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
        self.AUTH0_API_AUDIENCE = os.getenv('AUTH0_API_AUDIENCE')
        self.AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
        self.AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
        
        # Flask configuration
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-this')
        self.FLASK_ENV = os.getenv('FLASK_ENV', 'development')
        self.FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

        # Database configuration
        db_path = os.path.join(self.BASE_DIR, 'data', 'scheduler.db')
        self.DB_URI = f'sqlite:///{db_path}'
        
        # Ensure directories exist
        self._create_directories()
    
    def get_db_uri(self):
        return self.DB_URI

    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        for directory in [self.DATA_DIR, self.RESULTS_DIR, self.CACHE_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)
    
    def validate_auth0_config(self):
        """Validate Auth0 configuration."""
        required_vars = ['AUTH0_DOMAIN', 'AUTH0_API_AUDIENCE', 'AUTH0_CLIENT_ID', 'AUTH0_CLIENT_SECRET']
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        
        if missing_vars:
            raise ValueError(f"Missing Auth0 configuration: {', '.join(missing_vars)}")
        
        return True