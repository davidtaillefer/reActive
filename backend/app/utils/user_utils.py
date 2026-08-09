import uuid
from flask import request, session

def get_user_uuid():
    """Return the current user's numeric id.

    This prefers the Flask session `user_id`, then falls back to the
    `X-User-Id` header for compatibility. Returns an int or None.
    """
    print("Getting user UUID from session or header...")
    user_id = session.get('user_id') or request.headers.get("X-User-Id")
    print(f"User ID found: {user_id}")
    if not user_id:
        print("No valid user ID found.")
        return None
    try:
        return int(user_id)
    except Exception:
        return None