from flask import Blueprint, request, jsonify

from core.utils.decorators import require_api_key, require_admin_key
from core.services import auth_service
from core.utils.errors import ErrorResponses

bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return ErrorResponses.missing_email()
    try:
        user, api_key = auth_service.register_user(email)
        return jsonify({"email": user.email, "api_key": api_key}), 201
    except ValueError as e:
        if str(e) == "user_exists":
            return ErrorResponses.user_exists()
        return ErrorResponses.internal_error()


@bp.post("/status")
@require_api_key
def status():
    api_key = request.headers.get("X-API-Key")
    result = auth_service.status_for_api_key(api_key)
    if not result:
        return ErrorResponses.invalid_api_key()
    return jsonify(result), 200


@bp.post("/revoke")
@require_admin_key
def revoke():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return ErrorResponses.missing_email()
    ok = auth_service.revoke_user(email)
    if not ok:
        return ErrorResponses.not_found("User")
    return jsonify({"status": "revoked"}), 200


@bp.post("/reactivate")
@require_admin_key
def reactivate():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return ErrorResponses.missing_email()
    ok = auth_service.reactivate_user(email)
    if not ok:
        return ErrorResponses.not_found("User")
    return jsonify({"status": "active"}), 200


@bp.post("/renew")
def renew():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return ErrorResponses.missing_email()
    api_key = auth_service.renew_api_key(email)
    if not api_key:
        return ErrorResponses.not_allowed()
    # In production this should be emailed to the user.
    return jsonify({"email": email, "api_key": api_key}), 200
