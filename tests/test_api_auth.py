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
import requests
# Removed: import subprocess, time, socket, errno (no longer needed for server management)

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

    def test_protected_endpoints_require_auth(self):
        """Test that protected endpoints return 401 without a token."""
        print("\n--- Running test_protected_endpoints_require_auth ---")
        for endpoint in self.protected_endpoints:
            with self.subTest(endpoint=endpoint):
                url = f"{BASE_URL}{endpoint}"
                print(f"Attempting to access: {url}")
                if endpoint in self.post_only_endpoints:
                    response = requests.post(url, json={})
                elif endpoint == '/api/results':
                    response = requests.get(f"{url}/optimization")
                else:
                    response = requests.get(url)
                self.assertEqual(response.status_code, 401, f"Endpoint {endpoint} should require authentication. Response: {response.text}")
                data = response.json()
                self.assertIn('code', data)
                self.assertEqual(data['code'], 'authorization_header_missing')

    def test_protected_endpoints_with_invalid_token(self):
        """Test that protected endpoints return 401/400 with an invalid token."""
        print("\n--- Running test_protected_endpoints_with_invalid_token ---")
        invalid_token_scenarios = [
            # All these tokens are "malformed" from the perspective of the JOSE library
            # because they are not valid JWT structures.
            # As per the principle, the backend should return 400 for malformed requests.
            {'token': 'TEST_TOKEN_EXPIRED', 'status_code': 400, 'error_code': 'invalid_header'},
            {'token': 'TEST_TOKEN_INVALID_CLAIMS', 'status_code': 400, 'error_code': 'invalid_header'},
            {'token': 'MALFORMED_TOKEN', 'status_code': 400, 'error_code': 'invalid_header'},
            {'token': 'TEST_TOKEN_INSUFFICIENT_PERMS', 'status_code': 400, 'error_code': 'invalid_header'},
        ]

        for scenario in invalid_token_scenarios:
            headers = {'Authorization': f"Bearer {scenario['token']}"}
            for endpoint in self.protected_endpoints:
                with self.subTest(endpoint=endpoint, scenario=scenario['error_code']):
                    url = f"{BASE_URL}{endpoint}"
                    print(f"Attempting to access: {url} with invalid token {scenario['token']}")
                    if endpoint in self.post_only_endpoints:
                        response = requests.post(url, headers=headers, json={})
                    elif endpoint == '/api/results':
                        response = requests.get(f"{url}/optimization", headers=headers)
                    else:
                        response = requests.get(url, headers=headers)
                    self.assertEqual(response.status_code, scenario['status_code'], f"Endpoint {endpoint} should return {scenario['status_code']} for {scenario['error_code']}. Response: {response.text}")
                    data = response.json()
                    self.assertIn('code', data)
                    self.assertEqual(data['code'], scenario['error_code'])

    def test_protected_endpoints_with_valid_token(self):
        """Test that protected endpoints allow access with a valid token."""
        print("\n--- Running test_protected_endpoints_with_valid_token ---")
        headers = {'Authorization': 'Bearer TEST_TOKEN_VALID'}

        for endpoint in self.protected_endpoints:
            with self.subTest(endpoint=endpoint):
                url = f"{BASE_URL}{endpoint}"
                print(f"Attempting to access: {url} with valid token")
                if endpoint == '/api/results':
                    response = requests.get(f"{url}/optimization", headers=headers)
                elif endpoint == '/api/backtest':
                    response = requests.post(url, headers=headers, json={"strategy": "EMA_Only", "symbol": "BTC/USDT", "start_date": "2023-01-01", "end_date": "2023-01-31", "capital": 10000, "params": {"ema_short": 12, "ema_long": 26}})
                elif endpoint in self.post_only_endpoints:
                    response = requests.post(url, headers=headers, json={})
                else:
                    response = requests.get(url, headers=headers)
                self.assertNotEqual(response.status_code, 401, f"Endpoint {endpoint} should not return 401 with valid token. Response: {response.text}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
