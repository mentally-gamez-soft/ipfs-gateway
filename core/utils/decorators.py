from functools import wraps
from flask import request, jsonify, current_app, g
from typing import Callable

from core.services.auth_service import _get_user_by_api_key
from core.utils.errors import ErrorResponses


def require_api_key(f: Callable):
    @wraps(f)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return ErrorResponses.missing_api_key()
        user = _get_user_by_api_key(api_key)
        if not user:
            return ErrorResponses.invalid_api_key()
        if user.status.value == "inactive":
            return ErrorResponses.user_inactive()
        if user.status.value == "revoked":
            return ErrorResponses.user_revoked()
        if user.status.value != "active":
            return ErrorResponses.forbidden()
        g.user = user
        return f(*args, **kwargs)
    return wrapper


def require_admin_key(f: Callable):
    @wraps(f)
    def wrapper(*args, **kwargs):
        admin_key = request.headers.get("X-Admin-Key")
        expected = current_app.config.get("ADMIN_API_KEY")
        if not expected:
            return ErrorResponses.admin_key_not_configured()
        if not admin_key or admin_key != expected:
            return ErrorResponses.forbidden()
        return f(*args, **kwargs)
    return wrapper
