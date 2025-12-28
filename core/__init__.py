from flask import Flask
from dotenv import load_dotenv
from .config.settings import get_config
from .utils.logging import configure_logging, init_request_hooks
from .models.connection import init_db


def create_app(env: str | None = None) -> Flask:
    # Load .env early
    load_dotenv()
    app = Flask(__name__)

    # Load configuration
    config_class = get_config(env)
    app.config.from_object(config_class)

    # Logging
    configure_logging(app)
    init_request_hooks(app)

    # Database
    init_db(app)

    # Register blueprints
    from .routes.health import bp as health_bp
    app.register_blueprint(health_bp)
    from .routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    from .routes.upload import bp as upload_bp
    app.register_blueprint(upload_bp)

    return app
