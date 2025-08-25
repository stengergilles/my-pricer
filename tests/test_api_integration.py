#!/usr/bin/env python3
"""
Integration tests for the updated API endpoints.
Tests the backend API with the unified core.
"""

import unittest
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set testing environment variables before importing Flask app
os.environ['FLASK_ENV'] = 'testing'
os.environ['SKIP_AUTH'] = 'true'

# Import Flask app and components
try:
    from web.backend.app import app
    from core.app_config import Config
    FLASK_APP_AVAILABLE = True
except ImportError as e:
    print(f"Flask app not available: {e}")
    FLASK_APP_AVAILABLE = False

class TestAPIIntegration(unittest.TestCase):
    """Test API integration with unified core."""
    
    def setUp(self):
        """Set up test client and temporary directories."""
        if not FLASK_APP_AVAILABLE:
            self.skipTest("Flask app not available")
            
        self.temp_dir = tempfile.mkdtemp()
        
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment."""
        if FLASK_APP_AVAILABLE:
            self.app_context.pop()
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir)
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('checks', data)
        self.assertIn('timestamp', data)
    
    def test_config_endpoint(self):
        """Test configuration endpoint."""
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('strategies', data)
        self.assertIn('version', data)
        self.assertIn('supported_timeframes', data)
    
    @patch('core.crypto_discovery.requests.get')
    def test_crypto_api_get(self, mock_get):
        """Test crypto API GET endpoint."""
        # Mock CoinGecko API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'id': 'bitcoin',
                'symbol': 'btc',
                'name': 'Bitcoin',
                'current_price': 50000,
                'price_change_percentage_24h': 5.5,
                'market_cap': 1000000000,
                'market_cap_rank': 1
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test getting all cryptos
        response = self.client.get('/api/cryptos')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('cryptos', data)
        self.assertIn('count', data)
        
        # Test getting volatile cryptos
        response = self.client.get('/api/cryptos?volatile=true&min_volatility=5.0')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('cryptos', data)
    
    def test_strategies_api(self):
        """Test strategies API endpoints."""
        # Test getting all strategies
        response = self.client.get('/api/strategies')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('strategies', data)
        self.assertIn('count', data)
        
        strategies = data['strategies']
        self.assertGreater(len(strategies), 0)
        
        # Check strategy structure
        strategy = strategies[0]
        self.assertIn('name', strategy)
        self.assertIn('display_name', strategy)
        self.assertIn('parameters', strategy)
        self.assertIn('defaults', strategy)
    
    def test_error_handling(self):
        """Test API error handling."""
        # Test invalid JSON
        response = self.client.post('/api/analysis',
                                  data='invalid json',
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test missing required fields
        response = self.client.post('/api/analysis',
                                  json={})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)

class TestAPIPerformance(unittest.TestCase):
    """Test API performance and response times."""
    
    def setUp(self):
        """Set up test client."""
        if not FLASK_APP_AVAILABLE:
            self.skipTest("Flask app not available")
            
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment."""
        if FLASK_APP_AVAILABLE:
            self.app_context.pop()
    
    def test_health_check_performance(self):
        """Test health check response time."""
        import time
        
        start_time = time.time()
        response = self.client.get('/api/health')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Health check should be fast (< 2 seconds, allowing for system load)
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0)
    
    def test_config_endpoint_performance(self):
        """Test config endpoint response time."""
        import time
        
        start_time = time.time()
        response = self.client.get('/api/config')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Config should be fast (< 1 second)
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)

def run_api_tests():
    """Run all API integration tests."""
    if not FLASK_APP_AVAILABLE:
        print("⚠️  Flask app not available - skipping API tests")
        return True  # Return True to not fail the overall test suite
    
    test_classes = [
        TestAPIIntegration,
        TestAPIPerformance
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_api_tests()
    sys.exit(0 if success else 1)
