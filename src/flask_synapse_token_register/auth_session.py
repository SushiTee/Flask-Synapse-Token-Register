"""Session-based authentication handling."""

import base64
import hashlib
import hmac
import json
import time
from functools import wraps

from flask import (
    g,
    redirect,
    request,
    url_for,
)

from flask_synapse_token_register.db.secrets import get_secret


def get_auth_secret():
    """Get the secret used for signing auth tokens."""
    return get_secret("SECRET_KEY")


def generate_admin_token(username):
    """Generate an admin authentication token."""
    # Create payload with username and expiration time (24 hours from now)
    expiry = int(time.time()) + (24 * 60 * 60)
    payload = {"username": username, "exp": expiry, "type": "admin_auth"}

    # Convert payload to JSON and base64 encode
    payload_json = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")

    # Create signature
    secret = get_auth_secret()
    signature = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

    # Return token as payload.signature
    return f"{payload_b64}.{signature_b64}"


def verify_admin_token_with_payload(token):
    """Verify an admin authentication token and return username and payload."""
    try:
        if not token or "." not in token:
            return None, None

        # Split token into parts
        payload_b64, signature_b64 = token.split(".", 1)

        # Store original (unpadded) payload for signature verification
        original_payload_b64 = payload_b64

        # Add padding if necessary for decoding
        payload_b64_padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        signature_b64_padded = signature_b64 + "=" * (-len(signature_b64) % 4)

        # Decode payload
        try:
            payload_json = base64.urlsafe_b64decode(
                payload_b64_padded.encode()
            ).decode()
            payload = json.loads(payload_json)
        except (ValueError, json.JSONDecodeError):
            return None, None

        # Check token type and expiry
        if payload.get("type") != "admin_auth":
            return None, None

        if payload.get("exp", 0) < time.time():
            return None, None

        # Verify signature - using ORIGINAL unpadded payload
        secret = get_auth_secret()
        expected_sig = hmac.new(
            secret.encode(), original_payload_b64.encode(), hashlib.sha256
        ).digest()

        actual_sig = base64.urlsafe_b64decode(signature_b64_padded.encode())
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None, None

        return payload.get("username"), payload

    except Exception:  # pylint: disable=broad-except
        return None, None


def set_admin_cookie(response, username):
    """Set the admin authentication cookie on a response."""
    token = generate_admin_token(username)

    # Calculate an explicit expires datetime instead of using max_age
    # This is more compatible across browsers
    expires = time.time() + (24 * 60 * 60)  # 24 hours from now

    # Check if we're running in a secure environment
    secure = request.environ.get("HTTPS", "off") == "on"
    if request.host.startswith("localhost") or request.host.startswith("127.0.0.1"):
        secure = False  # Don't require HTTPS for local development

    # Set secure, httponly cookie
    response.set_cookie(
        "admin_auth",
        token,
        expires=expires,  # Use explicit expires instead of max_age
        httponly=True,
        secure=secure,
        samesite="Lax",
        path="/",  # Ensure cookie is available for all paths
    )
    return response


def clear_admin_cookie(response):
    """Remove the admin authentication cookie."""
    response.set_cookie("admin_auth", "", expires=0)
    # Also explicitly remove from g if it exists
    if hasattr(g, "admin_user"):
        delattr(g, "admin_user")
    if hasattr(g, "renew_admin_token"):
        delattr(g, "renew_admin_token")
    return response


def get_admin_user():
    """Get the admin username if authenticated."""
    # Check if we've already verified this request
    if hasattr(g, "admin_user"):
        return g.admin_user

    # Get token from cookie
    token = request.cookies.get("admin_auth")
    if not token:
        return None

    # Verify token
    username, payload = verify_admin_token_with_payload(token)
    if not username:
        return None

    # Store in Flask's g object for this request
    g.admin_user = username

    # Check if token needs renewal (less than 12 hours remaining)
    if payload and "exp" in payload:
        remaining = payload["exp"] - time.time()
        if remaining < (12 * 60 * 60):  # Less than 12 hours remaining
            # Set flag to renew token
            g.renew_admin_token = True
            # Store original expiration for logging
            g.token_expiry_hours = round(remaining / 3600, 1)

    return username


def login_required(f):
    """Decorator that requires admin login."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_user = get_admin_user()
        if not admin_user:
            return redirect(url_for("admin.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function
