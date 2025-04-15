"""Routes package for the application."""

from flask import current_app, render_template

from flask_synapse_token_register.auth_session import get_admin_user
from flask_synapse_token_register.routes.admin import bp as admin_bp
from flask_synapse_token_register.routes.og_static import bp as og_static_bp
from flask_synapse_token_register.routes.public import bp as public_bp
from flask_synapse_token_register.routes.success import bp as success_bp


def register_blueprints(app):
    """Register all blueprints with the app."""
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(success_bp)

    # Only register custom og static blueprint if the directory is configured
    if app.config.get("og_static_dir"):
        app.register_blueprint(og_static_bp)

    # Register template context processors
    @app.context_processor
    def inject_globals():
        """Inject global variables into templates."""
        # Check if admin is logged in
        admin_logged_in = get_admin_user() is not None

        # Add classes to body tag if admin is logged in
        body_classes = "has-admin-nav" if admin_logged_in else ""

        return dict(
            og_meta=current_app.config.get("og", {}),
            has_og_static_dir=bool(current_app.config.get("og_static_dir")),
            site_name=current_app.config.get("site_name", "Matrix Server"),
            matrix_url=current_app.config.get("matrix_url", ""),
            admin_logged_in=admin_logged_in,
            body_classes=body_classes,
        )

    # Register error handlers
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 errors."""
        error_message = getattr(error, "description", "Access denied")
        return render_template("error.html", error=error_message), 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        error_message = getattr(error, "description", "Page not found")
        return render_template("error.html", error=error_message), 404

    @app.errorhandler(500)
    def server_error(error):
        """Handle 500 errors."""
        error_message = getattr(error, "description", "Internal server error")
        return render_template("error.html", error=error_message), 500
