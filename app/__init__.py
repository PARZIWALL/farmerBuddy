from flask import Flask
from typing import Optional


def create_app(config_object: Optional[str] = None) -> Flask:
    """Application factory for creating Flask app instances.

    Registers blueprints and loads configuration.
    """
    app = Flask(__name__)

    # Load configuration
    if config_object:
        app.config.from_object(config_object)
    else:
        app.config.from_object("config.Config")

    # Import and register blueprints
    from .controllers.health_controller import health_bp
    from .controllers.user_controller import user_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(user_bp, url_prefix="/api/users")

    return app


