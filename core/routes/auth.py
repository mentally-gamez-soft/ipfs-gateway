from flask import Blueprint, request, jsonify

from core.utils.decorators import require_api_key, require_admin_key
from core.services import auth_service

bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "missing_email"}), 400
    try:
        user, api_key = auth_service.register_user(email)
        return jsonify({"email": user.email, "api_key": api_key}), 201
    except ValueError as e:
        if str(e) == "user_exists":
            return jsonify({"error": "user_exists"}), 409
        return jsonify({"error": "unknown_error"}), 500


@bp.post("/status")
@require_api_key
def status():
    api_key = request.headers.get("X-API-Key")
    result = auth_service.status_for_api_key(api_key)
    if not result:
        return jsonify({"error": "invalid_api_key"}), 401
    return jsonify(result), 200


@bp.post("/revoke")
@require_admin_key
def revoke():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "missing_email"}), 400
    ok = auth_service.revoke_user(email)
    if not ok:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"status": "revoked"}), 200


@bp.post("/reactivate")
@require_admin_key
def reactivate():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "missing_email"}), 400
    ok = auth_service.reactivate_user(email)
    if not ok:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"status": "active"}), 200


@bp.post("/renew")
def renew():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "missing_email"}), 400
    api_key = auth_service.renew_api_key(email)
    if not api_key:
        return jsonify({"error": "not_allowed"}), 403
    # In production this should be emailed to the user.
    return jsonify({"email": email, "api_key": api_key}), 200
