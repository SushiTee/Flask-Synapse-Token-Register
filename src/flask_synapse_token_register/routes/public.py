"""Public routes for registration."""

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
    # Check if there's an admin token
    admin_user = get_admin_user()
    if admin_user:
        # If admin is logged in, redirect to token management
        return redirect(url_for("admin.manage_tokens"))

    # Check if a registration token is provided
    token = request.args.get("token") or request.form.get("token")
    if not token:
        # No token, show admin login
        return redirect(url_for("admin.login"))

    # Validate token
    if not token_exists(token):
        abort(403, description="Invalid registration token")

    if is_token_used(token):
        abort(403, description="This registration token has already been used")

    # Token is valid, handle registration
    error = None
    success_message = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not password or not confirm_password:
            error = "Username and both password fields are required."
            return render_template(
                "register.html", error=error, success=success_message, token=token
            )

        if not validate_username(username):
            error = (
                "Invalid username. Usernames can only contain lowercase letters, "
                "numbers, and the characters -_.=/"
            )
            return render_template(
                "register.html", error=error, success=success_message, token=token
            )

        if password != confirm_password:
            error = "Passwords do not match."
            return render_template(
                "register.html", error=error, success=success_message, token=token
            )

        # Check if the password is strong
        if not is_strong_password(password):
            error = (
                "Password must be at least 8 characters long, include a number, "
                "and contain at least one special character."
            )
            return render_template(
                "register.html", error=error, success=success_message, token=token
            )

        try:
            # Only create the user if we're not in test mode
            if not current_app.config.get("TESTING", False):
                # Create the user account
                subprocess.run(
                    [
                        "register_new_matrix_user",
                        "--no-admin",
                        "-c",
                        "/etc/synapse/homeserver.yaml",
                        "-u",
                        username,
                        "-p",
                        password,
                        "http://127.0.0.1:8008",
                    ],
                    check=True,
                )
            else:
                # In test mode, just log the action
                current_app.logger.info(
                    f"Test mode: Would have created Matrix user: {username}"
                )

            # Mark token as used in the database
            mark_token_used(token, username=username)

            # Generate success token and redirect
            success_token = generate_success_token(username)
            return redirect(
                url_for("success.show_success", username=username, token=success_token)
            )

        except subprocess.CalledProcessError:
            error = (
                f"Failed to register: The user {username} already exists "
                f"or there is another error."
            )

    return render_template(
        "register.html", error=error, success=success_message, token=token
    )
