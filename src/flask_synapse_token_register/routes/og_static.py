"""Blueprint for serving custom og static files from external directories."""

import os

from flask import Blueprint, abort, current_app, send_from_directory

# Create a blueprint without a static folder initially
# We'll set it dynamically when registering
bp = Blueprint("og_static", __name__)


@bp.route("/og-static/<path:filename>")
def serve_og_static(filename):
    """Serve a file from the custom og static directory."""
    og_static_dir = current_app.config.get("og_static_dir")

    if not og_static_dir or not os.path.isdir(og_static_dir):
        # If no custom og directory is configured or it doesn't exist, return 404
        abort(404)

    # Validate the file path to prevent directory traversal
    # This is an extra security measure on top of what send_from_directory does
    requested_path = os.path.realpath(os.path.join(og_static_dir, filename))
    if not requested_path.startswith(os.path.abspath(og_static_dir)):
        abort(403)  # Forbidden - attempted directory traversal

    return send_from_directory(og_static_dir, filename)
