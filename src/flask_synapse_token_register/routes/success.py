"""Success page routes."""

from flask import Blueprint, abort, render_template, request

from flask_synapse_token_register.tokens import verify_success_token

bp = Blueprint("success", __name__)


@bp.route("/success")
def show_success():
    """Render the success page."""
    token = request.args.get("token")
    username_from_token = verify_success_token(token)

    # Check if token is valid and username matches
    username = request.args.get("username")

    if not username_from_token or username_from_token != username:
        abort(403, description="Invalid or expired success token")

    return render_template("success.html", username=username)
