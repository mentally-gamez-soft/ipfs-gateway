from flask import Blueprint, jsonify, current_app

bp = Blueprint("health", __name__)


@bp.route("/health", methods=["GET"]) 
def health():
    return (
        jsonify(
            {
                "status": "ok",
                "app": current_app.config.get("APP_NAME", "ipfs-gateway"),
                "env": current_app.config.get("APP_ENV", "development"),
            }
        ),
        200,
    )
