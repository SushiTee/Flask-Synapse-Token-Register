"""Tests for token functionality."""

import base64
import time
from unittest.mock import patch

from flask_synapse_token_register.tokens import (
    generate_success_token,
    verify_success_token,
)


def test_success_token_generation_and_verification(app):
    """Test generation and verification of success tokens."""
    with app.app_context():
        # Generate a token
        username = "testuser"
        token = generate_success_token(username)

        # Should be a string with a dot separator
        assert isinstance(token, str)
        assert "." in token

        # Should verify correctly
        assert verify_success_token(token) == username


def test_expired_token_fails(app):
    """Test that expired tokens are rejected."""
    with app.app_context():
        # Generate a token
        username = "testuser"
        token = generate_success_token(username)

        # Mock time to be in the future (token expired)
        with patch("time.time") as mock_time:
            # Move time forward 6 minutes (tokens valid for 5 minutes)
            mock_time.return_value = time.time() + 360
            assert verify_success_token(token) is None


def test_invalid_tokens(app):
    """Test that invalid tokens are rejected."""
    with app.app_context():
        # Invalid format
        assert verify_success_token("not-a-valid-token") is None

        # Empty token
        assert verify_success_token("") is None

        # None token
        assert verify_success_token(None) is None


def test_token_expiration_boundary(app):
    """Test token expiration at the boundary conditions."""
    with app.app_context():
        # Generate a token
        username = "testuser"
        token = generate_success_token(username)

        # Get the token components to extract the timestamp
        payload_b64, _ = token.split(".", 1)
        payload_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        _, timestamp_str = payload.split(":", 1)
        token_timestamp = int(timestamp_str)

        # Test with token just within expiration window
        with patch("time.time") as mock_time:
            # Token is created at token_timestamp
            # Default max_age is 300 seconds (5 minutes)
            # Set current time to be at token_timestamp + 299 (just within limit)
            mock_time.return_value = token_timestamp + 299
            assert verify_success_token(token) == username

        # Test with token exactly at expiration limit
        with patch("time.time") as mock_time:
            # Set current time to be at token_timestamp + 300 (exactly at limit)
            mock_time.return_value = token_timestamp + 300
            assert verify_success_token(token) == username

        # Test with token just past expiration
        with patch("time.time") as mock_time:
            # Set current time to be at token_timestamp + 301 (just past limit)
            mock_time.return_value = token_timestamp + 301
            assert verify_success_token(token) is None


def test_token_with_custom_max_age(app):
    """Test token validation with a custom max_age setting."""
    with app.app_context():
        # Generate a token
        username = "testuser"
        token = generate_success_token(username)

        # Get the token timestamp
        payload_b64, _ = token.split(".", 1)
        payload_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        _, timestamp_str = payload.split(":", 1)
        token_timestamp = int(timestamp_str)

        # Save original config value
        original_max_age = app.config.get("SUCCESS_TOKEN_MAX_AGE", 300)

        try:
            # Set a custom max_age directly in the app config
            app.config["SUCCESS_TOKEN_MAX_AGE"] = 600  # 10 minutes

            # Test at 8 minutes (within 10 minute window)
            with patch("time.time") as mock_time:
                mock_time.return_value = token_timestamp + 480  # 8 minutes
                assert verify_success_token(token) == username

            # Test at 11 minutes (past 10 minute window)
            with patch("time.time") as mock_time:
                mock_time.return_value = token_timestamp + 660  # 11 minutes
                assert verify_success_token(token) is None
        finally:
            # Restore original value
            if original_max_age == 300:  # Was default
                app.config.pop("SUCCESS_TOKEN_MAX_AGE", None)
            else:
                app.config["SUCCESS_TOKEN_MAX_AGE"] = original_max_age


def test_tampered_token_signature(app):
    """Test that tokens with invalid signatures are rejected."""
    with app.app_context():
        # Generate a valid token
        username = "testuser"
        token = generate_success_token(username)

        # Split the token into parts
        payload_b64, signature_b64 = token.split(".", 1)

        # Create a tampered signature (modify a character)
        if signature_b64[0] == "a":
            # Change first character to 'b' if it's 'a'
            tampered_signature = "b" + signature_b64[1:]
        else:
            # Otherwise change it to 'a'
            tampered_signature = "a" + signature_b64[1:]

        # Reassemble token with tampered signature
        tampered_token = f"{payload_b64}.{tampered_signature}"

        # Verify it's rejected
        assert verify_success_token(tampered_token) is None

        # As a control, verify the original token is still valid
        assert verify_success_token(token) == username
