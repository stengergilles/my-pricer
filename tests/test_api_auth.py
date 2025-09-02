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
import base64
from functools import wraps
from unittest.mock import patch, MagicMock

# Add project root and backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web', 'backend'))

# Set testing environment variables before importing Flask app
# Ensure Auth0 is NOT skipped for these tests
os.environ['FLASK_ENV'] = 'testing'
os.environ['SKIP_AUTH'] = 'false' # Explicitly set to false for auth tests

# Import Flask app and components
try:
    from web.backend.app import app
    from core.app_config import Config
    from flask import g # Import g for mocking in tests
    from jose import jwt # Import jwt for mocking in tests
    FLASK_APP_AVAILABLE = True
except ImportError as e:
    print(f"Flask app not available: {e}")
    FLASK_APP_AVAILABLE = False

from web.backend.auth import middleware # Import middleware for other purposes

class TestAPIAuthProtection(unittest.TestCase):
    """Test Auth0 protection for API endpoints."""

    def setUp(self):
        """Set up test client and temporary directories."""
        if not FLASK_APP_AVAILABLE:
            self.skipTest("Flask app not available")

        self.app = app # Use the globally imported app
        self.config = Config() # Use the globally imported Config

        self.temp_dir = tempfile.mkdtemp()

        # Configure app for testing
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Mock Auth0 environment variables
        self.mock_auth0_domain = 'test-auth0-domain.auth0.com'
        self.mock_api_audience = 'test-api-audience'
        os.environ['AUTH0_DOMAIN'] = self.mock_auth0_domain
        os.environ['AUTH0_API_AUDIENCE'] = self.mock_api_audience

        # Define protected endpoints (excluding health check and frontend routes)
        self.protected_endpoints = [
            '/api/config',
            '/api/auth/test',
            '/api/log',
            '/api/cryptos',
            '/api/cryptos/bitcoin', # Specific crypto endpoint
            '/api/crypto_status/bitcoin', # Crypto status endpoint
            '/api/analysis',
            '/api/analysis/123', # Specific analysis endpoint (if applicable, though POST is primary)
            '/api/backtest',
            '/api/backtest/456', # Specific backtest endpoint (if applicable, though POST is primary)
            '/api/strategies',
            '/api/strategies/EMA_Only', # Specific strategy endpoint
            '/api/results',
            '/api/results/optimization', # Specific results type
            '/api/scheduler/schedule',
            '/api/scheduler/jobs',
            '/api/scheduler/jobs/789' # Specific job endpoint
        ]

    def tearDown(self):
        """Clean up test environment."""
        if FLASK_APP_AVAILABLE:
            self.app_context.pop()
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir)
        # Clean up mock environment variables
        del os.environ['AUTH0_DOMAIN']
        del os.environ['AUTH0_API_AUDIENCE']

    def test_protected_endpoints_require_auth(self):
        """Test that protected endpoints return 401 without a token."""
        for endpoint in self.protected_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 401, f"Endpoint {endpoint} should require authentication")
                data = json.loads(response.data)
                self.assertIn('code', data)
                self.assertEqual(data['code'], 'authorization_header_missing')

    @patch('web.backend.auth.middleware.jwt.decode')
    @patch('web.backend.auth.middleware.jwt.get_unverified_header')
    @patch('web.backend.auth.middleware.urlopen') # Mock urlopen for these specific tests
    def test_protected_endpoints_with_invalid_token(self, mock_urlopen, mock_get_unverified_header, mock_jwt_decode):
        """Test that protected endpoints return 401/400 with an invalid token."""
        # Configure mock_urlopen to return a JWKS with a matching kid
        dummy_n = base64.urlsafe_b64encode(os.urandom(256)).decode('utf-8').rstrip('=')
        dummy_e = "AQAB" # Standard public exponent in base64url
        mock_urlopen.return_value.read.return_value = json.dumps({
            "keys": [{
                "kid": "mock_kid",
                "kty": "RSA",
                "use": "sig",
                "n": dummy_n,
                "e": dummy_e
            }]
        })

        # A structurally valid JWT with an invalid signature.
        # This allows jwt.get_unverified_header to work, but jwt.decode will fail.
        invalid_token = "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Im1vY2tfa2lkIn0.eyJpc3MiOiJodHRwczovL3Rlc3QtYXV0aDAtZG9tYWluLmF1dGgwLmNvbS8iLCJhdWQiOiJ0ZXN0LWFwaS1hdWRpZW5jZSIsInN1YiI6ImF1dGgwfHRlc3R1c2VyIiwicGVybWlzc2lvbnMiOlsicmVhZDphbGwiLCJ3cml0ZTphbGwiXSwiZXhwIjo5OTk5OTk5OTk5fQ.invalid_signature"
        headers = {'Authorization': invalid_token}

        # Mock get_unverified_header to return a header with a matching kid
        mock_get_unverified_header.return_value = {'kid': 'mock_kid', 'alg': 'RS256'}
        # Mock jwt.decode to raise an ExpiredSignatureError or similar for invalid token
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError("Token expired.") # Use self.jwt

        for endpoint in self.protected_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint, headers=headers)
                self.assertEqual(response.status_code, 401, f"Endpoint {endpoint} should reject invalid token")
                data = json.loads(response.data)
                self.assertIn('code', data)
                self.assertEqual(data['code'], 'token_expired') # Expecting this specific error code

    @patch('web.backend.auth.middleware.jwt.decode')
    @patch('web.backend.auth.middleware.jwt.get_unverified_header')
    @patch('web.backend.auth.middleware.urlopen') # Mock urlopen for these specific tests
    def test_protected_endpoints_with_valid_token(self, mock_urlopen, mock_get_unverified_header, mock_jwt_decode):
        """Test that protected endpoints allow access with a valid token."""
        # Configure mock_urlopen to return a JWKS with a matching kid
        dummy_n = base64.urlsafe_b64encode(os.urandom(256)).decode('utf-8').rstrip('=')
        dummy_e = "AQAB" # Standard public exponent in base64url
        mock_urlopen.return_value.read.return_value = json.dumps({
            "keys": [{
                "kid": "mock_kid",
                "kty": "RSA",
                "use": "sig",
                "n": dummy_n,
                "e": dummy_e
            }]
        })

        # A dummy token string, its content doesn't matter as jwt.decode is mocked
        valid_token = "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Im1vY2tfa2lkIn0.eyJpc3MiOiJodHRwczovL3Rlc3QtYXV0aDAtZG9tYWluLmF1dGgwLmNvbS8iLCJhdWQiOiJ0ZXN0LWFwaS1hdWRpZW5jZSIsInN1YiI6ImF1dGgwfHRlc3R1c2VyIiwicGVybWlzc2lvbnMiOlsicmVhZDphbGwiLCJ3cml0ZTphbGwiXSwiZXhwIjo5OTk5OTk5OTk5fQ.valid_signature"
        headers = {'Authorization': valid_token}

        # Mock get_unverified_header to return a header with a matching kid
        mock_get_unverified_header.return_value = {'kid': 'mock_kid', 'alg': 'RS256'}

        # Mock jwt.decode to return a valid payload
        mock_jwt_decode.return_value = {
            'iss': f'https://{self.mock_auth0_domain}/',
            'aud': self.mock_api_audience,
            'sub': 'auth0|testuser',
            'permissions': ['read:all', 'write:all'],
            'exp': 9999999999
        }

        for endpoint in self.protected_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint, headers=headers)
                # This will likely fail with 500 or 400 because the backend logic isn't fully mocked,
                # but we are testing auth, so 401/403 should not be returned.
                self.assertNotEqual(response.status_code, 401, f"Endpoint {endpoint} should not return 401 with valid token. Response: {response.data}")
                self.assertNotEqual(response.status_code, 403, f"Endpoint {endpoint} should not return 403 with valid token. Response: {response.data}")


def run_api_auth_tests():
    """Run all API authentication tests."""
    # The FLASK_APP_AVAILABLE check is now handled within the TestAPIAuthProtection.setUp method.
    # If the Flask app is not available, the tests will be skipped.
    test_classes = [
        TestAPIAuthProtection
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
    success = run_api_auth_tests()
    sys.exit(0 if success else 1)
