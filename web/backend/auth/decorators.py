"""
Auth0 decorators for Flask routes.
"""

from functools import wraps
from flask import request
from .middleware import requires_auth

def auth_required(f):
    """Simple auth decorator for routes."""
    @wraps(f)
    @requires_auth()
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function
