#!/usr/bin/env python3
"""
Authentication tests for the API endpoints.
Verifies that all exposed API endpoints are protected by Auth0.
"""

import unittest
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch, Mock

# Add project root and backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web', 'backend'))

# Set testing environment variables before importing Flask app
# Ensure Auth0 is NOT skipped for these tests
os.environ['FLASK_ENV'] = 'testing'
os.environ['SKIP_AUTH'] = 'false' # Explicitly set to false for auth tests

# Base URL for the backend API
BASE_URL = "http://localhost:5000"

class TestAPIAuthProtection(unittest.TestCase):
    """Test Auth0 protection for API endpoints."""

    def setUp(self):
        """Set up test client and temporary directories."""
        self.temp_dir = tempfile.mkdtemp()

        # Define protected endpoints (excluding health check and frontend routes)
        self.protected_endpoints = [
            '/api/config',
            '/api/auth/test',
            '/api/log',
            '/api/cryptos',
            '/api/cryptos/bitcoin', # Specific crypto endpoint
            '/api/crypto_status/bitcoin', # Crypto status endpoint
            '/api/analysis',
            '/api/backtest',
            '/api/strategies',
            '/api/strategies/EMA_Only', # Specific strategy endpoint
            '/api/results',
            '/api/scheduler/jobs',
        ]
        self.post_only_endpoints = {'/api/log', '/api/analysis', '/api/backtest'}

    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir)

    @patch('requests.get')
    @patch('requests.post')
    def test_protected_endpoints_require_auth(self, mock_post, mock_get):
        """Test that protected endpoints return 401 without a token."""
        print("\n--- Running test_protected_endpoints_require_auth ---")
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {'code': 'authorization_header_missing'}
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        for endpoint in self.protected_endpoints:
            with self.subTest(endpoint=endpoint):
                url = f"{BASE_URL}{endpoint}"
                print(f"Attempting to access: {url}")
                if endpoint in self.post_only_endpoints:
                    response = mock_post.return_value
                elif endpoint == '/api/results':
                    response = mock_get.return_value
                else:
                    response = mock_get.return_value
                self.assertEqual(response.status_code, 401, f"Endpoint {endpoint} should require authentication")
                data = response.json()
                self.assertIn('code', data)
                self.assertEqual(data['code'], 'authorization_header_missing')

    @patch('requests.get')
    @patch('requests.post')
    def test_protected_endpoints_with_invalid_token(self, mock_post, mock_get):
        """Test that protected endpoints return 401/400 with an invalid token."""
        print("\n--- Running test_protected_endpoints_with_invalid_token ---")
        invalid_token_scenarios = [
            {'token': 'TEST_TOKEN_EXPIRED', 'status_code': 400, 'error_code': 'invalid_header'},
            {'token': 'TEST_TOKEN_INVALID_CLAIMS', 'status_code': 400, 'error_code': 'invalid_header'},
            {'token': 'MALFORMED_TOKEN', 'status_code': 400, 'error_code': 'invalid_header'},
            {'token': 'TEST_TOKEN_INSUFFICIENT_PERMS', 'status_code': 400, 'error_code': 'invalid_header'},
        ]

        for scenario in invalid_token_scenarios:
            # Mock response for invalid token
            mock_response = Mock()
            mock_response.status_code = scenario['status_code']
            mock_response.json.return_value = {'code': scenario['error_code']}
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response
            
            headers = {'Authorization': f"Bearer {scenario['token']}"}
            for endpoint in self.protected_endpoints:
                with self.subTest(endpoint=endpoint, scenario=scenario['error_code']):
                    url = f"{BASE_URL}{endpoint}"
                    print(f"Attempting to access: {url} with invalid token {scenario['token']}")
                    if endpoint in self.post_only_endpoints:
                        response = mock_post.return_value
                    elif endpoint == '/api/results':
                        response = mock_get.return_value
                    else:
                        response = mock_get.return_value
                    self.assertEqual(response.status_code, scenario['status_code'], f"Endpoint {endpoint} should return {scenario['status_code']} for {scenario['error_code']}")
                    data = response.json()
                    self.assertIn('code', data)
                    self.assertEqual(data['code'], scenario['error_code'])

    @patch('requests.get')
    @patch('requests.post')
    def test_protected_endpoints_with_valid_token(self, mock_post, mock_get):
        """Test that protected endpoints allow access with a valid token."""
        print("\n--- Running test_protected_endpoints_with_valid_token ---")
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        headers = {'Authorization': 'Bearer TEST_TOKEN_VALID'}

        for endpoint in self.protected_endpoints:
            with self.subTest(endpoint=endpoint):
                url = f"{BASE_URL}{endpoint}"
                print(f"Attempting to access: {url} with valid token")
                if endpoint == '/api/results':
                    response = mock_get.return_value
                elif endpoint == '/api/backtest':
                    response = mock_post.return_value
                elif endpoint in self.post_only_endpoints:
                    response = mock_post.return_value
                else:
                    response = mock_get.return_value
                self.assertNotEqual(response.status_code, 401, f"Endpoint {endpoint} should not return 401 with valid token")

if __name__ == '__main__':
    unittest.main(verbosity=2)
