from flask import Blueprint, request, jsonify
import logging

from core.utils.decorators import require_api_key, require_admin_key
from core.services import auth_service
from core.utils.errors import ErrorResponses

bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        logger.warning("Register attempt without email")
        return ErrorResponses.missing_email()
    try:
        user, api_key = auth_service.register_user(email)
        logger.info(f"User successfully registered via API: {email}")
        return jsonify({"email": user.email, "api_key": api_key}), 201
    except ValueError as e:
        if str(e) == "user_exists":
            logger.warning(f"Register attempt for existing user: {email}")
            return ErrorResponses.user_exists()
        logger.error(f"Unexpected error during user registration for {email}: {str(e)}")
        return ErrorResponses.internal_error()


@bp.post("/status")
@require_api_key
def status():
    api_key = request.headers.get("X-API-Key")
    result = auth_service.status_for_api_key(api_key)
    if not result:
        logger.error(f"Status check failed for invalid API key")
        return ErrorResponses.invalid_api_key()
    logger.info(f"Status check successful for user: {result['email']}")
    return jsonify(result), 200


@bp.post("/revoke")
@require_admin_key
def revoke():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        logger.warning("Revoke attempt without email (admin)")
        return ErrorResponses.missing_email()
    ok = auth_service.revoke_user(email)
    if not ok:
        logger.warning(f"Revoke attempt for non-existent user (admin): {email}")
        return ErrorResponses.not_found("User")
    logger.warning(f"User revoked by admin: {email}")
    return jsonify({"status": "revoked"}), 200


@bp.post("/reactivate")
@require_admin_key
def reactivate():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        logger.warning("Reactivate attempt without email (admin)")
        return ErrorResponses.missing_email()
    ok = auth_service.reactivate_user(email)
    if not ok:
        logger.warning(f"Reactivate attempt for non-existent user (admin): {email}")
        return ErrorResponses.not_found("User")
    logger.info(f"User reactivated by admin: {email}")
    return jsonify({"status": "active"}), 200


@bp.post("/renew")
def renew():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        logger.warning("Renew attempt without email")
        return ErrorResponses.missing_email()
    api_key = auth_service.renew_api_key(email)
    if not api_key:
        logger.warning(f"Renew failed for user: {email}")
        return ErrorResponses.not_allowed()
    logger.info(f"API key renewed for user: {email}")
    # In production this should be emailed to the user.
    return jsonify({"email": email, "api_key": api_key}), 200
