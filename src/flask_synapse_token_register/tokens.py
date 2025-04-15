"""Token generation and validation functions."""

import base64
import hashlib
import hmac
import time

from flask import current_app

from flask_synapse_token_register.db.secrets import get_secret


def get_secret_key():
    """Get a secret key for token signing."""
    db_secret = get_secret("SECRET_KEY")
    return db_secret


def generate_success_token(username):
    """Generate a time-limited token for accessing the success page."""
    # Get secret key
    secret_key = get_secret_key()

    timestamp = int(time.time())
    # Create payload with username and timestamp
    payload = f"{username}:{timestamp}"

    # Create signature using HMAC-SHA256
    signature = hmac.new(
        secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).digest()

    # Base64 encode the signature and payload
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    # Return the token
    return f"{payload_b64}.{signature_b64}"


def verify_success_token(token):
    """Verify a success token and extract username if valid."""
    # Get secret key and token max age
    secret_key = get_secret_key()
    max_age = current_app.config.get("SUCCESS_TOKEN_MAX_AGE", 300)

    try:
        # Split token into parts
        if not token or "." not in token:
            return None

        payload_b64, signature_b64 = token.split(".", 1)

        # Add back any stripped padding
        payload_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
        signature_b64 = signature_b64 + "=" * (-len(signature_b64) % 4)

        # Decode payload
        payload = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        username, timestamp_str = payload.split(":", 1)
        timestamp = int(timestamp_str)

        # Check if token is expired
        if time.time() - timestamp > max_age:
            return None

        # Verify signature
        expected_signature = hmac.new(
            secret_key.encode(), payload.encode(), hashlib.sha256
        ).digest()

        actual_signature = base64.urlsafe_b64decode(signature_b64.encode())

        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        return username
    except (ValueError, TypeError, AttributeError):
        return None
