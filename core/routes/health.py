from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from core.models.connection import engine

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


@bp.route("/db-check", methods=["GET"])
def db_check():
    """Check database connectivity by executing a simple SELECT 1 query."""
    try:
        if engine is None:
            return (
                jsonify({
                    "status": "error",
                    "message": "Database engine not initialized"
                }),
                503
            )
        
        # Execute a simple query to verify database connectivity
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
        return (
            jsonify({
                "status": "ok",
                "database": "connected",
                "query_result": row[0] if row else None
            }),
            200
        )
    except Exception as e:
        return (
            jsonify({
                "status": "error",
                "message": f"Database check failed: {str(e)}"
            }),
            503
        )
