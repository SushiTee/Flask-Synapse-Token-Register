"""Flask application factory."""

from flask import Flask

from flask_synapse_token_register.config import load_config
from flask_synapse_token_register.routes import register_blueprints


def create_app(config_path=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    config = load_config(config_path)
    app.config.update(config)

    # Set application constants
    app.config["SUCCESS_TOKEN_MAX_AGE"] = 300  # 5 minutes expiration

    # Set application root and URL scheme
    register_url_prefix = config.get("register_url_prefix", "/register")
    app.config["APPLICATION_ROOT"] = register_url_prefix
    app.config["PREFERRED_URL_SCHEME"] = config.get("url_scheme", "https")

    # Register blueprints/routes
    register_blueprints(app)

    return app
