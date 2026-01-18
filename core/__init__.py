from flask import Flask
from dotenv import load_dotenv
from .config.settings import get_config
from .utils.logging import configure_logging, init_request_hooks
from .models.connection import init_db
from .swagger import init_swagger


def create_app(env: str | None = None) -> Flask:
    # Load .env early
    load_dotenv()
    app = Flask(__name__)

    # Load configuration
    config_class = get_config(env)
    app.config.from_object(config_class)

    # Refresh secrets from environment after .env is loaded
    import os
    app.config["FILEBASE_IPFS_API_KEY"] = os.getenv("FILEBASE_IPFS_API_KEY")
    app.config["FILEBASE_BUCKET"] = os.getenv("FILEBASE_BUCKET", "ipfs-gateway")
    app.config["S3_ACCESS_KEY"] = os.getenv("S3_ACCESS_KEY")
    app.config["S3_SECRET_ACCESS_KEY"] = os.getenv("S3_SECRET_ACCESS_KEY")

    # Logging
    configure_logging(app)
    init_request_hooks(app)

    # Database
    init_db(app)

    # Swagger/OpenAPI documentation (dev and staging only)
    app_env = app.config.get("APP_ENV", "development")
    init_swagger(app, env=app_env)

    # Register blueprints
    from .routes.health import bp as health_bp
    app.register_blueprint(health_bp)
    from .routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    from .routes.upload import bp as upload_bp
    app.register_blueprint(upload_bp)

    return app
