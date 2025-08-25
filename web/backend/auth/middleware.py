"""
Mock auth middleware for testing when Auth0 is not configured.
"""

class AuthError(Exception):
    """Auth error exception."""
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

def requires_auth(scopes=None):
    """
    Mock auth middleware that bypasses authentication for testing.
    In production, this would integrate with Auth0.
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            # In test/development mode, skip auth
            return f(*args, **kwargs)
        return wrapper
    return decorator
