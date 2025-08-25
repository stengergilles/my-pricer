"""
Mock auth decorators for testing when Auth0 is not configured.
"""

from functools import wraps
import os

def auth_required(f=None):
    """
    Mock auth decorator that bypasses authentication for testing.
    In production, this would integrate with Auth0.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # In test/development mode, skip auth
            if os.getenv('FLASK_ENV') == 'testing' or os.getenv('SKIP_AUTH', 'false').lower() == 'true':
                return func(*args, **kwargs)
            
            # In production, this would validate Auth0 token
            # For now, just pass through
            return func(*args, **kwargs)
        return wrapper
    
    if f is None:
        return decorator
    else:
        return decorator(f)
