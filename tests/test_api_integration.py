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

# Import Flask app and components
from web.backend.app import app
from core.app_config import Config

class TestAPIIntegration(unittest.TestCase):
    """Test API integration with unified core."""
    
    def setUp(self):
        """Set up test client and temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        # Override config directories
        config = Config()
        config.RESULTS_DIR = self.temp_dir
        config.CACHE_DIR = self.temp_dir
        config.LOGS_DIR = self.temp_dir
        
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment."""
        self.app_context.pop()
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
    
    @patch('core.crypto_discovery.requests.get')
    def test_crypto_api_post_actions(self, mock_get):
        """Test crypto API POST actions."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'id': 'bitcoin',
                'symbol': 'btc',
                'name': 'Bitcoin',
                'current_price': 50000,
                'price_change_percentage_24h': 10.0,
                'market_cap': 1000000000,
                'market_cap_rank': 1
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test discover volatile action
        response = self.client.post('/api/cryptos', 
                                  json={
                                      'action': 'discover_volatile',
                                      'min_volatility': 5.0,
                                      'limit': 10
                                  })
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'discover_volatile')
        self.assertIn('cryptos', data)
        
        # Test top movers action
        response = self.client.post('/api/cryptos',
                                  json={
                                      'action': 'top_movers',
                                      'count': 5
                                  })
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'top_movers')
        self.assertIn('movers', data)
    
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
        
        # Test getting specific strategy
        strategy_name = strategy['name']
        response = self.client.get(f'/api/strategies/{strategy_name}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('strategy', data)
        self.assertEqual(data['strategy']['name'], strategy_name)
    
    def test_strategies_api_post(self):
        """Test strategies API POST actions."""
        # Test parameter validation
        response = self.client.post('/api/strategies',
                                  json={
                                      'action': 'validate',
                                      'strategy': 'EMA_Only',
                                      'parameters': {
                                          'short_ema_period': 12,
                                          'long_ema_period': 26
                                      }
                                  })
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'validate')
        self.assertIn('valid', data)
        self.assertIn('errors', data)
        
        # Test getting defaults
        response = self.client.post('/api/strategies',
                                  json={
                                      'action': 'get_defaults',
                                      'strategy': 'EMA_Only'
                                  })
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'get_defaults')
        self.assertIn('defaults', data)
    
    def test_analysis_api(self):
        """Test analysis API endpoints."""
        # Test running analysis
        response = self.client.post('/api/analysis',
                                  json={
                                      'crypto_id': 'bitcoin',
                                      'strategy': 'EMA_Only',
                                      'timeframe': '7d'
                                  })
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('analysis', data)
        self.assertIn('timestamp', data)
        
        # Analysis result should contain crypto and strategy info
        analysis = data['analysis']
        self.assertIn('crypto', analysis)
        self.assertIn('strategy', analysis)
    
    def test_backtest_api(self):
        """Test backtest API endpoints."""
        # Test running backtest
        response = self.client.post('/api/backtest',
                                  json={
                                      'action': 'backtest',
                                      'crypto_id': 'bitcoin',
                                      'strategy': 'EMA_Only',
                                      'parameters': {
                                          'short_ema_period': 12,
                                          'long_ema_period': 26,
                                          'rsi_oversold': 30,
                                          'rsi_overbought': 70
                                      }
                                  })
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'backtest')
        self.assertIn('result', data)
        
        # Backtest result should contain basic info
        result = data['result']
        self.assertIn('crypto', result)
        self.assertIn('strategy', result)
        self.assertIn('success', result)
    
    def test_results_api(self):
        """Test results API endpoints."""
        # Test getting all results
        response = self.client.get('/api/results/all')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['type'], 'all')
        self.assertIn('results', data)
        self.assertIn('count', data)
        
        # Test getting top results
        response = self.client.get('/api/results/top?limit=5')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['type'], 'top')
        self.assertIn('results', data)
    
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
        
        # Test invalid strategy
        response = self.client.get('/api/strategies/invalid_strategy')
        self.assertEqual(response.status_code, 404)
    
    def test_parameter_validation_integration(self):
        """Test parameter validation across API endpoints."""
        # Test invalid parameters in backtest
        response = self.client.post('/api/backtest',
                                  json={
                                      'action': 'backtest',
                                      'crypto_id': 'bitcoin',
                                      'strategy': 'EMA_Only',
                                      'parameters': {
                                          'short_ema_period': 50,  # Invalid: too high
                                          'long_ema_period': 25,   # Invalid: less than short
                                      }
                                  })
        
        # Should return error due to validation failure
        self.assertEqual(response.status_code, 200)  # API returns 200 but with error in result
        data = json.loads(response.data)
        result = data['result']
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)

class TestAPIPerformance(unittest.TestCase):
    """Test API performance and response times."""
    
    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment."""
        self.app_context.pop()
    
    def test_health_check_performance(self):
        """Test health check response time."""
        import time
        
        start_time = time.time()
        response = self.client.get('/api/health')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Health check should be fast (< 1 second)
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)
    
    def test_config_endpoint_performance(self):
        """Test config endpoint response time."""
        import time
        
        start_time = time.time()
        response = self.client.get('/api/config')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Config should be fast (< 0.5 seconds)
        response_time = end_time - start_time
        self.assertLess(response_time, 0.5)

def run_api_tests():
    """Run all API integration tests."""
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
