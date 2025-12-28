from functools import wraps
from flask import request, jsonify, current_app, g
from typing import Callable

from core.services.auth_service import _get_user_by_api_key


def require_api_key(f: Callable):
    @wraps(f)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"error": "missing_api_key"}), 401
        user = _get_user_by_api_key(api_key)
        if not user:
            return jsonify({"error": "invalid_api_key"}), 401
        if user.status.value != "active":
            return jsonify({"error": f"user_{user.status.value}"}), 403
        g.user = user
        return f(*args, **kwargs)
    return wrapper


def require_admin_key(f: Callable):
    @wraps(f)
    def wrapper(*args, **kwargs):
        admin_key = request.headers.get("X-Admin-Key")
        expected = current_app.config.get("ADMIN_API_KEY")
        if not expected:
            return jsonify({"error": "admin_key_not_configured"}), 500
        if not admin_key or admin_key != expected:
            return jsonify({"error": "forbidden"}), 403
        return f(*args, **kwargs)
    return wrapper
