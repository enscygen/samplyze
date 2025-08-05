from functools import wraps
from flask import abort
from flask_login import current_user

def permission_required(permission):
    """
    A decorator that checks if the current user has the required permission.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.can(permission):
                abort(403)  # Forbidden error
            return f(*args, **kwargs)
        return decorated_function
    return decorator
