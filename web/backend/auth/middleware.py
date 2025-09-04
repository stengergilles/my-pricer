import os
import json
from functools import wraps
from urllib.request import urlopen

from flask import request, g

from jose import jwt

import logging
logger = logging.getLogger(__name__)

# Auth0 configuration
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
API_AUDIENCE = os.getenv('AUTH0_API_AUDIENCE')
ALGORITHMS = ["RS256"]

# Error handler
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header
    """
    auth = request.headers.get('Authorization', None)
    if not auth:
        logger.error("Token rejection reason: Authorization header is missing.")
        raise AuthError({
            'code': 'authorization_header_missing',
            'description': 'Authorization header is expected.'
        }, 401)

    parts = auth.split()
    if parts[0].lower() != 'bearer':
        error_description = 'Authorization header must start with "Bearer".'
        logger.error(f"Token rejection reason: {error_description}")
        raise AuthError({
            'code': 'invalid_header',
            'description': error_description
        }, 401)

    elif len(parts) == 1:
        error_description = 'Token not found.'
        logger.error(f"Token rejection reason: {error_description}")
        raise AuthError({
            'code': 'invalid_header',
            'description': error_description
        }, 401)

    elif len(parts) > 2:
        error_description = 'Authorization header must be bearer token.'
        logger.error(f"Token rejection reason: {error_description}")
        raise AuthError({
            'code': 'invalid_header',
            'description': error_description
        }, 401)

    token = parts[1]
    return token

def check_permissions(permission, payload):
    if permission is None:
        return True
    permissions = payload.get('permissions', [])
    if permission not in permissions:
        error_description = f'Permission "{permission}" not found in token permissions: {permissions}'
        logger.error(f"Token rejection reason: {error_description}")
        raise AuthError({
            'code': 'insufficient_permissions',
            'description': error_description
        }, 403)
    return True

def requires_auth(permission=None):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Bypass authentication if SKIP_AUTH is explicitly set to 'true'
            if os.getenv('SKIP_AUTH', 'false').lower() == 'true':
                # Simulate a valid user for bypassed auth
                g.current_user = {
                    'iss': f'https://{AUTH0_DOMAIN}/',
                    'aud': API_AUDIENCE,
                    'sub': 'auth0|bypasseduser',
                    'permissions': ['read:all', 'write:all', 'read:results', 'create:jobs', 'manage:jobs', 'read:config', 'read:log', 'read:cryptos', 'read:strategies', 'read:analysis', 'read:backtest', 'read:scheduler'],
                    'exp': 9999999999
                }
                return f(*args, **kwargs)

            token = get_token_auth_header() # Moved this line here

            

            jsonurl = urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
            jwks = json.loads(jsonurl.read())

            if not token:
                error_description = "Authorization header is expected"
                logger.error(f"Token rejection reason: {error_description}")
                raise AuthError({"code": "authorization_header_missing",
                                "description": error_description}, 401)

            # Try to get unverified header, catching errors for malformed tokens
            try:
                unverified_header = jwt.get_unverified_header(token)
            except (jwt.JWTError, jwt.JWSError) as e:
                error_description = f'Malformed token header: {e}'
                logger.error(f"Token rejection reason: {error_description}")
                raise AuthError({
                    'code': 'invalid_header',
                    'description': error_description
                }, 400)

            rsa_key = {}
            for key in jwks['keys']:
                if key.get('kid') == unverified_header.get('kid'):
                    rsa_key = {
                        'kty': key['kty'],
                        'kid': key['kid'],
                        'use': key['use'],
                        'n': key['n'],
                        'e': key['e']
                    }
            if rsa_key:
                try:
                    payload = jwt.decode(
                        token,
                        rsa_key,
                        algorithms=ALGORITHMS,
                        audience=API_AUDIENCE,
                        issuer='https://' + AUTH0_DOMAIN + '/'
                    )
                except jwt.ExpiredSignatureError:
                    error_description = 'Token expired.'
                    logger.error(f"Token rejection reason: {error_description}")
                    raise AuthError({
                        'code': 'token_expired',
                        'description': error_description
                    }, 401)
                except jwt.JWTClaimsError as e:
                    error_description = f'Incorrect claims. Please, check the audience and issuer. Error: {e}'
                    logger.error(f"Token rejection reason: {error_description}")
                    raise AuthError({
                        'code': 'invalid_claims',
                        'description': error_description
                    }, 400)
                except (jwt.JWTError, jwt.JWSError) as e: # Catch specific JOSE errors
                    error_description = f'Malformed token: {e}'
                    logger.error(f"Token rejection reason: {error_description}")
                    raise AuthError({
                        'code': 'invalid_header', # Use 'invalid_header' as per test expectation
                        'description': error_description
                    }, 400) # Return 400 for malformed tokens
                except Exception as e: # Catch any other unexpected errors
                    error_description = f'Unable to parse authentication token: {e}'
                    logger.error(f"Token rejection reason: {error_description}")
                    raise AuthError({
                        'code': 'invalid_header',
                        'description': error_description
                    }, 400)

                check_permissions(permission, payload)
                g.current_user = payload
                return f(*args, **kwargs)
            error_description = 'Unable to find the appropriate key.'
            logger.error(f"Token rejection reason: {error_description}")
            raise AuthError({
                'code': 'invalid_header',
                'description': error_description
            }, 400)
        return wrapper
    return requires_auth_decorator