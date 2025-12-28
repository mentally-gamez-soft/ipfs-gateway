from flask import Flask
from .config.settings import get_config
from .utils.logging import configure_logging, init_request_hooks


def create_app(env: str | None = None) -> Flask:
    app = Flask(__name__)

    # Load configuration
    config_class = get_config(env)
    app.config.from_object(config_class)

    # Logging
    configure_logging(app)
    init_request_hooks(app)

    # Register blueprints
    from .routes.health import bp as health_bp
    app.register_blueprint(health_bp)

    return app
