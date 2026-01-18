from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from core.models.connection import engine
from core.swagger import HEALTH_DOCS, DB_CHECK_DOCS

bp = Blueprint("health", __name__)


@bp.route("/health", methods=["GET"]) 
def health():
    """
    ---
    tags:
      - Health
    summary: Check API health status
    responses:
      200:
        description: API is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
            app:
              type: string
              example: ipfs-gateway
            env:
              type: string
              example: staging
    """
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
    """
    ---
    tags:
      - Health
    summary: Check database connectivity
    responses:
      200:
        description: Database is connected
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
            database:
              type: string
              example: connected
            query_result:
              type: integer
              example: 1
      503:
        description: Database is unavailable
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            error:
              type: string
    """
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
