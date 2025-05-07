"""Public routes for registration."""

import shlex
import subprocess

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_synapse_token_register.auth_session import (
    get_admin_user,
)
from flask_synapse_token_register.db.tokens import (
    is_token_used,
    mark_token_used,
    token_exists,
)
from flask_synapse_token_register.tokens import generate_success_token
from flask_synapse_token_register.validation import (
    is_strong_password,
    validate_username,
)

bp = Blueprint("public", __name__)


@bp.route("/", methods=["GET", "POST"])
def register():
    """Main route - either shows admin login or registration form."""
    # Check if admin is logged in
    if get_admin_user():
        return redirect(url_for("admin.manage_tokens"))

    # Check if a registration token is provided
    token = request.args.get("token") or request.form.get("token")
    if not token:
        return redirect(url_for("admin.login"))

    # Validate token
    if not token_exists(token):
        abort(403, description="Invalid registration token")
    if is_token_used(token):
        abort(403, description="This registration token has already been used")

    # Handle GET request - show registration form
    if request.method == "GET":
        return render_template("register.html", token=token)

    # Handle POST request - process registration
    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    # Validate form inputs
    if not username or not password or not confirm_password:
        error = "Username and both password fields are required."
        return render_template("register.html", error=error, token=token)

    if not validate_username(username):
        error = (
            "Invalid username. Usernames can only contain lowercase letters, "
            "numbers, and the characters -_.=/"
        )
        return render_template("register.html", error=error, token=token)

    if password != confirm_password:
        error = "Passwords do not match."
        return render_template("register.html", error=error, token=token)

    if not is_strong_password(password):
        error = (
            "Password must be at least 8 characters long, include a number, "
            "and contain at least one special character."
        )
        return render_template("register.html", error=error, token=token)

    # Create the Matrix user
    try:
        if not current_app.config.get("TESTING", False):
            # Get command template from config
            register_cmd_template = current_app.config.get(
                "register_cmd",
                (
                    "register_new_matrix_user --no-admin -c /etc/synapse/homeserver.yaml "
                    "-u {username} -p {password} http://127.0.0.1:8008"
                ),
            )

            # Format command with proper escaping
            register_cmd = register_cmd_template.format(
                username=shlex.quote(username), password=shlex.quote(password)
            )

            # Execute command securely
            cmd_parts = shlex.split(register_cmd)
            subprocess.run(
                cmd_parts,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        else:
            # Log instead of executing in test mode
            current_app.logger.info(
                f"Test mode: Would have created Matrix user: {username}"
            )

        # Mark token as used and redirect to success page
        mark_token_used(token, username=username)
        success_token = generate_success_token(username)
        return redirect(
            url_for("success.show_success", username=username, token=success_token)
        )

    except subprocess.CalledProcessError as e:
        # Log error details
        current_app.logger.error(f"Registration command failed: {e}")
        if hasattr(e, "stdout"):
            current_app.logger.error(f"Command stdout: {e.stdout}")
        if hasattr(e, "stderr"):
            current_app.logger.error(f"Command stderr: {e.stderr}")

        # User-friendly error message
        error = (
            f"Failed to register: The user {username} may already exist or there "
            "was a server error."
        )
        return render_template("register.html", error=error, token=token)
