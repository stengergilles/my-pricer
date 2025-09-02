import os
import json
from functools import wraps
from urllib.request import urlopen

from flask import request, g

from jose import jwt

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
        raise AuthError({
            'code': 'authorization_header_missing',
            'description': 'Authorization header is expected.'
        }, 401)

    parts = auth.split()
    if parts[0].lower() != 'bearer':
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization header must start with "Bearer".'
        }, 401)

    elif len(parts) == 1:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Token not found.'
        }, 401)

    elif len(parts) > 2:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization header must be bearer token.'
        }, 401)

    token = parts[1]
    return token

def check_permissions(permission, payload):
    if permission is None:
        return True
    if 'permissions' not in payload:
        raise AuthError({
            'code': 'invalid_claims',
            'description': 'Permissions not included in JWT.'
        }, 400)
    if permission not in payload['permissions']:
        raise AuthError({
            'code': 'unauthorized',
            'description': 'Permission not found.'
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
                    'permissions': ['read:all', 'write:all'],
                    'exp': 9999999999
                }
                return f(*args, **kwargs)

            token = get_token_auth_header()
            try:
                jsonurl = urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
                jwks = json.loads(jsonurl.read())
            except Exception as e:
                raise AuthError({
                    'code': 'jwks_fetch_error',
                    'description': f'Error fetching JWKS: {e}'
                }, 500)

            unverified_header = jwt.get_unverified_header(token)

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
                    raise AuthError({
                        'code': 'token_expired',
                        'description': 'Token expired.'
                    }, 401)
                except jwt.JWTClaimsError:
                    raise AuthError({
                        'code': 'invalid_claims',
                        'description': 'Incorrect claims. Please, check the audience and issuer.'
                    }, 401)
                except Exception as e:
                    raise AuthError({
                        'code': 'invalid_header',
                        'description': f'Unable to parse authentication token: {e}'
                    }, 400)

                check_permissions(permission, payload)
                g.current_user = payload
                return f(*args, **kwargs)
            raise AuthError({
                'code': 'invalid_header',
                'description': 'Unable to find the appropriate key.'
            }, 400)
        return wrapper
    return requires_auth_decorator
