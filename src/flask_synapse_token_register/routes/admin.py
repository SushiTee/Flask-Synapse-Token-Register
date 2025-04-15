"""Admin routes for token management."""

import secrets

from flask import (
    Blueprint,
    current_app,
    g,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_synapse_token_register.auth_session import (
    clear_admin_cookie,
    get_admin_user,
    login_required,
    set_admin_cookie,
)
from flask_synapse_token_register.db.admin import (
    update_admin_password,
    update_last_login,
    verify_admin_credentials,
)
from flask_synapse_token_register.db.tokens import (
    delete_token,
    get_all_tokens,
    get_filtered_tokens,
    get_token_stats,
    get_unused_tokens,
    save_token,
)
from flask_synapse_token_register.validation import is_strong_password

bp = Blueprint("admin", __name__)


@bp.after_request
def check_token_renewal(response):
    """Check if the admin token needs renewal and update if needed."""
    if hasattr(g, "renew_admin_token") and g.renew_admin_token and g.admin_user:
        # Log the renewal for debugging
        hours = getattr(g, "token_expiry_hours", "unknown")
        current_app.logger.info(
            f"Renewing admin token for {g.admin_user} (was expiring in {hours} hours)"
        )

        # Set a fresh token with full expiration time
        response = set_admin_cookie(response, g.admin_user)
    return response


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Admin login page."""
    # If already logged in, redirect to token management
    if get_admin_user():
        return redirect(url_for("admin.manage_tokens"))

    error = None
    next_url = request.args.get("next") or url_for("admin.manage_tokens")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            error = "Username and password are required."
        elif verify_admin_credentials(username, password):
            # Update last login timestamp
            update_last_login(username)

            # Create response and set cookie
            response = make_response(redirect(next_url))
            set_admin_cookie(response, username)
            return response
        else:
            error = "Invalid username or password."

    return render_template("admin_login.html", error=error)


@bp.route("/logout")
def logout():
    """Admin logout handler."""
    response = make_response(redirect(url_for("admin.login")))
    clear_admin_cookie(response)
    return response


@bp.route("/manage-tokens", methods=["GET", "POST"])
@login_required
def manage_tokens():
    """Handle token management, generation, retrieval and deletion."""
    token = None
    full_link = None
    message = None
    message_type = None

    # Get filter parameter from URL query string
    filter_status = request.args.get("filter", "all")
    if filter_status not in ["unused", "used", "all"]:
        filter_status = "all"

    # Process form actions first
    if request.method == "POST":
        action = request.form.get("action")

        if action == "generate":
            # Generate a new token
            token = secrets.token_urlsafe(32)

            # Save token to database
            save_token(token, used=False, ip_address=request.remote_addr)

            # Success message
            message = "New token generated successfully."
            message_type = "success"

            # Generate full URL
            full_link = url_for("public.register", token=token, _external=True)

        elif action == "delete":
            # Delete a specific token
            token_to_delete = request.form.get("token_id")
            if token_to_delete:
                success = delete_token(token_to_delete)
                if success:
                    message = "Token deleted successfully."
                    message_type = "success"
                else:
                    message = "Failed to delete token. It might not exist."
                    message_type = "error"

    # Get token statistics
    token_stats = get_token_stats()

    # Get list of unused tokens for UI status
    unused_tokens = get_unused_tokens()
    has_unused_token = len(unused_tokens) > 0

    # Get tokens based on filter (only once, after any modifications)
    if filter_status == "unused":
        all_tokens = get_filtered_tokens(used=False)
    elif filter_status == "used":
        all_tokens = get_filtered_tokens(used=True)
    else:
        all_tokens = get_all_tokens()

    return render_template(
        "manage_tokens.html",
        token=token,
        full_link=full_link,
        has_unused_token=has_unused_token,
        unused_count=token_stats["unused"],
        used_count=token_stats["used"],
        total_count=token_stats["total"],
        all_tokens=all_tokens,
        message=message,
        message_type=message_type,
        admin_user=get_admin_user(),
        filter_status=filter_status,
    )


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Allow admin to change their password."""
    message = None
    message_type = None
    admin_username = get_admin_user()

    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            message = "All fields are required."
            message_type = "error"
        elif not verify_admin_credentials(admin_username, current_password):
            message = "Current password is incorrect."
            message_type = "error"
        elif new_password != confirm_password:
            message = "New passwords do not match."
            message_type = "error"
        elif not is_strong_password(new_password):
            message = "New password does not meet strength requirements."
            message_type = "error"
        else:
            # Update the password
            success = update_admin_password(admin_username, new_password)
            if success:
                message = "Password changed successfully."
                message_type = "success"
            else:
                message = "Failed to update password."
                message_type = "error"

    return render_template(
        "change_password.html", message=message, message_type=message_type
    )
