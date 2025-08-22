"""
Auth0 authentication middleware for Flask backend.
"""

import json
import os
from functools import wraps
from urllib.request import urlopen
from flask import request, jsonify, _request_ctx_stack
from jose import jwt
from dotenv import load_dotenv
import logging # Ensure logging is imported

load_dotenv()

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
API_AUDIENCE = os.getenv('AUTH0_API_AUDIENCE')
ALGORITHMS = ["RS256"]

logger = logging.getLogger(__name__) # Explicitly set level to DEBUG

class AuthError(Exception):
    """Auth0 authentication error."""
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header."""
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                        "description": "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description": "Authorization header must start with 'Bearer'"}, 401)

    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)

    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                        "description": "Authorization header must be bearer token"}, 401)

    token = parts[1]
    return token

def verify_decode_jwt(token):
    """Verify and decode JWT token."""
    logger.debug(f"Attempting to verify token: {token}")
    if not AUTH0_DOMAIN or not API_AUDIENCE:
        raise AuthError({"code": "configuration_error",
                        "description": "Auth0 configuration missing"}, 500)
    
    try:
        jsonurl = urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
        jwks = json.loads(jsonurl.read())
        logger.debug(f"Fetched JWKS: {jwks}")
    except Exception as e:
        logger.error(f"Error fetching JWKS: {str(e)}")
        raise AuthError({"code": "jwks_error",
                        "description": f"Unable to fetch JWKS: {str(e)}"}, 500)
    
    unverified_header = jwt.get_unverified_header(token)
    logger.debug(f"Unverified header: {unverified_header}")
    
    rsa_key = {}
    if "kid" not in unverified_header:
        raise AuthError({"code": "invalid_header",
                        "description": "Authorization malformed."}, 401)

    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    logger.debug(f"RSA Key found: {rsa_key}")
    
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/"
            )
            logger.debug(f"Token decoded successfully. Payload: {payload}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired.")
            raise AuthError({"code": "token_expired",
                            "description": "Token expired."}, 401)

        except jwt.JWTClaimsError:
            logger.warning("Incorrect claims. Please, check the audience and issuer.")
            raise AuthError({"code": "invalid_claims",
                            "description": "Incorrect claims. Please, check the audience and issuer."}, 401)
        except Exception as e:
            logger.error(f"Error decoding token: {str(e)}")
            raise AuthError({"code": "invalid_token", # Corrected from invalid_header
                            "description": "Unable to parse authentication token."}, 401) # Corrected status code

    logger.warning("Unable to find the appropriate key.")
    raise AuthError({"code": "invalid_header",
                    "description": "Unable to find the appropriate key."}, 400)

def requires_auth(permission=''):
    """Decorator for Auth0 authentication."""
    def requires_auth_decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                token = get_token_auth_header()
                payload = verify_decode_jwt(token)
                _request_ctx_stack.top.current_user = payload
                
                # Store user info in request for easy access
                request.current_user = payload
                
                return f(*args, **kwargs)
            except AuthError as e:
                raise e
            except Exception as e:
                raise AuthError({
                    "code": "invalid_token",
                    "description": "Unable to validate token"
                }, 401)
                
        return decorated
    return requires_auth_decorator