from functools import wraps
from flask import jsonify

from .user_utils import get_user_uuid


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_user_uuid()
        if not user_id:
            return jsonify({'error': 'authentication required'}), 401
        return fn(*args, **kwargs)
    return wrapper


def current_user_id():
    return get_user_uuid()
