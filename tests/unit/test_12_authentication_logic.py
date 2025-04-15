"""Tests for authentication functionality."""

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import patch

import flask
import pytest
from flask import Response, g

from flask_synapse_token_register.auth_session import (
    generate_admin_token,
    get_auth_secret,
    verify_admin_token_with_payload,
)
from flask_synapse_token_register.db.admin import (
    create_admin_user,
    update_admin_password,
    verify_admin_credentials,
)


def test_admin_token_generation_and_verification(app):
    """Test admin token generation and verification."""
    with app.app_context():
        # Generate a token
        username = "testadmin"
        token = generate_admin_token(username)

        # Verify token - extracting just the username from the result tuple
        result_username, _ = verify_admin_token_with_payload(token)
        assert result_username == username


def test_admin_token_complete_verification(app):
    """Test that admin token verification returns both username and payload."""
    with app.app_context():
        # Generate a token
        username = "testadmin"
        token = generate_admin_token(username)

        # Verify complete token with payload
        result_username, payload = verify_admin_token_with_payload(token)

        # Check basic verification
        assert result_username == username

        # Check payload contents
        assert payload is not None
        assert payload["username"] == username
        assert payload["type"] == "admin_auth"
        assert payload["exp"] > time.time()  # Expiration is in the future


def test_admin_token_expiration(app):
    """Test admin token expiration."""
    with app.app_context():
        # Generate a token
        username = "testadmin"
        token = generate_admin_token(username)

        # Mock time to be in the future
        with patch("time.time") as mock_time:
            # Move forward 25 hours (token valid for 24 hours)
            mock_time.return_value = time.time() + (25 * 60 * 60)
            result = verify_admin_token_with_payload(token)
            assert result == (None, None)


def test_invalid_admin_tokens(app):
    """Test invalid admin tokens are rejected."""
    with app.app_context():
        # Invalid format
        assert verify_admin_token_with_payload("not-a-valid-token") == (None, None)

        # Empty token
        assert verify_admin_token_with_payload("") == (None, None)

        # None token
        assert verify_admin_token_with_payload(None) == (None, None)


def test_malformed_token_payload(app):
    """Test verification of tokens with malformed payload."""
    with app.app_context():
        # Create a token with invalid base64 in payload
        invalid_base64_token = "invalid!base64.signature"
        assert verify_admin_token_with_payload(invalid_base64_token) == (None, None)

        # Create a token with valid base64 but invalid JSON
        invalid_json = base64.urlsafe_b64encode(b"not-valid-json").decode().rstrip("=")
        invalid_json_token = f"{invalid_json}.signature"
        assert verify_admin_token_with_payload(invalid_json_token) == (None, None)


def test_token_with_wrong_type(app):
    """Test verification of tokens with incorrect 'type'."""
    with app.app_context():
        # Create token with wrong type
        wrong_type_payload = {
            "username": "testadmin",
            "exp": int(time.time()) + 3600,
            "type": "wrong_type",  # Should be "admin_auth"
        }

        # Encode payload
        payload_json = json.dumps(wrong_type_payload)
        payload_b64 = (
            base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
        )

        # Create signature using the same method as in generate_admin_token
        secret = get_auth_secret()
        signature = hmac.new(
            secret.encode(), payload_b64.encode(), hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        # Create the token
        token = f"{payload_b64}.{signature_b64}"

        # Verify it's rejected
        assert verify_admin_token_with_payload(token) == (None, None)


def test_expired_token(app):
    """Test verification of expired tokens."""
    with app.app_context():
        # Create an expired token (expired 1 hour ago)
        expired_payload = {
            "username": "testadmin",
            "exp": int(time.time()) - 3600,  # 1 hour in the past
            "type": "admin_auth",
        }

        # Encode payload
        payload_json = json.dumps(expired_payload)
        payload_b64 = (
            base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
        )

        # Create signature
        secret = get_auth_secret()
        signature = hmac.new(
            secret.encode(), payload_b64.encode(), hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        # Create the token
        token = f"{payload_b64}.{signature_b64}"

        # Verify the token is rejected as expired
        assert verify_admin_token_with_payload(token) == (None, None)


def test_token_signature_mismatch(app):
    """Test verification of tokens with incorrect signatures."""
    with app.app_context():
        # Create a valid payload
        valid_payload = {
            "username": "testadmin",
            "exp": int(time.time()) + 3600,
            "type": "admin_auth",
        }

        # Encode payload
        payload_json = json.dumps(valid_payload)
        payload_b64 = (
            base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
        )

        # Create an incorrect signature
        wrong_secret = "wrong_secret_key"
        wrong_signature = hmac.new(
            wrong_secret.encode(), payload_b64.encode(), hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(wrong_signature).decode().rstrip("=")

        # Create token with mismatched signature
        token = f"{payload_b64}.{signature_b64}"

        # Verify it's rejected due to signature mismatch
        assert verify_admin_token_with_payload(token) == (None, None)


def test_update_admin_password(app):
    """Test updating admin password."""
    with app.app_context():
        # Create a test user
        username = "password_change_test"
        old_password = "OldPassword123!"
        create_admin_user(username, old_password)

        # Verify original credentials work
        assert verify_admin_credentials(username, old_password) is True

        # Update password
        new_password = "NewPassword456!"
        result = update_admin_password(username, new_password)

        # Verify update was successful
        assert result is True

        # Verify old password no longer works
        assert verify_admin_credentials(username, old_password) is False

        # Verify new password works
        assert verify_admin_credentials(username, new_password) is True

        # Test updating non-existent user
        assert update_admin_password("nonexistent_user", "AnyPass123!") is False


def test_set_admin_cookie(app):
    """Test setting admin authentication cookie."""
    with app.app_context():
        from flask_synapse_token_register.auth_session import set_admin_cookie

        # Create mock response
        response = Response()

        # Test with localhost (insecure)
        with app.test_request_context():
            # We need to patch both the host and HTTPS environment variables
            with patch("flask.request.host", "localhost:5000"):
                # Set cookie for test user
                result = set_admin_cookie(response, "testadmin")

                # Verify response object was returned
                assert result is response

                # Verify cookie was set with correct parameters
                cookies = result.headers.getlist("Set-Cookie")
                assert any("admin_auth=" in cookie for cookie in cookies)
                assert any("HttpOnly" in cookie for cookie in cookies)
                assert all(
                    "Secure" not in cookie for cookie in cookies
                )  # Not secure for localhost
                assert any("SameSite=Lax" in cookie for cookie in cookies)

        # Test with IP 127.0.0.1 (should also be insecure)
        with app.test_request_context():
            response = Response()
            with patch("flask.request.host", "127.0.0.1:5000"):
                result = set_admin_cookie(response, "testadmin")
                cookies = result.headers.getlist("Set-Cookie")
                assert all(
                    "Secure" not in cookie for cookie in cookies
                )  # Not secure for 127.0.0.1

        # Test with a normal domain with HTTPS
        with app.test_request_context():
            response = Response()
            # Use a regular domain (not localhost/127.0.0.1) and set HTTPS on
            with patch("flask.request.host", "example.com"), patch.dict(
                "flask.request.environ", {"HTTPS": "on"}
            ):
                result = set_admin_cookie(response, "testadmin")

                # Verify secure flag is set for non-localhost with HTTPS
                cookies = result.headers.getlist("Set-Cookie")
                assert any("Secure" in cookie for cookie in cookies)

        # Test regular domain without HTTPS
        with app.test_request_context():
            response = Response()
            with patch("flask.request.host", "example.com"):
                # Not setting HTTPS environment variable
                result = set_admin_cookie(response, "testadmin")

                # Verify secure flag is not set
                cookies = result.headers.getlist("Set-Cookie")
                assert all("Secure" not in cookie for cookie in cookies)


def test_clear_admin_cookie(app):
    """Test clearing admin authentication cookie and g variables."""
    with app.app_context():
        from flask_synapse_token_register.auth_session import clear_admin_cookie

        # Create mock response
        response = Response()

        # Set values in g
        g.admin_user = "testadmin"
        g.renew_admin_token = True

        # Test clearing cookie and g
        result = clear_admin_cookie(response)

        # Verify response was returned
        assert result is response

        # Verify cookie was cleared (expires=0)
        cookies = result.headers.getlist("Set-Cookie")
        assert any(
            "admin_auth=" in cookie
            and ("expires" in cookie.lower() or "max-age=0" in cookie.lower())
            for cookie in cookies
        )

        # Verify g variables were deleted
        assert not hasattr(g, "admin_user")
        assert not hasattr(g, "renew_admin_token")


def test_get_admin_user_from_g(app):
    """Test getting admin user from g object."""
    with app.app_context():
        from flask_synapse_token_register.auth_session import get_admin_user

        # Set admin user in g
        g.admin_user = "testadmin"

        # Test getting from g
        result = get_admin_user()

        # Verify it returns the value from g
        assert result == "testadmin"

        # Clean up
        delattr(g, "admin_user")


def test_get_admin_user_token_needs_renewal(app):
    """Test token renewal detection in get_admin_user."""
    with app.app_context():
        from flask_synapse_token_register.auth_session import (
            get_admin_user,
        )

        # Create a token that's close to expiring (11 hours left)
        with patch("time.time") as mock_time:
            current_time = 1000000  # Arbitrary timestamp
            mock_time.return_value = current_time

            # Generate a token with 11 hours of validity left
            username = "testadmin"

            # Manually create payload with specific expiry
            expiry = current_time + (11 * 60 * 60)  # 11 hours from current_time
            import base64
            import hashlib
            import hmac
            import json

            from flask_synapse_token_register.auth_session import get_auth_secret

            payload = {"username": username, "exp": expiry, "type": "admin_auth"}
            payload_json = json.dumps(payload)
            payload_b64 = (
                base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
            )

            # Create signature
            secret = get_auth_secret()
            signature = hmac.new(
                secret.encode(), payload_b64.encode(), hashlib.sha256
            ).digest()
            signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

            token = f"{payload_b64}.{signature_b64}"

            # Setup request with the token as cookie
            with app.test_request_context():
                flask.request.cookies = {"admin_auth": token}

                # Get admin user - should detect renewal need
                result = get_admin_user()

                # Verify correct user is returned
                assert result == username

                # Verify renewal flag is set (less than 12 hours remaining)
                assert hasattr(g, "renew_admin_token")
                assert g.renew_admin_token is True
                assert hasattr(g, "token_expiry_hours")
                assert g.token_expiry_hours == pytest.approx(11.0)


def test_get_admin_user_token_no_renewal(app):
    """Test token with plenty of time left doesn't trigger renewal."""
    with app.app_context():
        from flask_synapse_token_register.auth_session import (
            get_admin_user,
        )

        # Create a token with plenty of time left (20 hours)
        with patch("time.time") as mock_time:
            current_time = 1000000  # Arbitrary timestamp
            mock_time.return_value = current_time

            # Generate a token with 20 hours of validity left
            username = "testadmin"

            # Manually create payload with specific expiry
            expiry = current_time + (20 * 60 * 60)  # 20 hours from current_time
            import base64
            import hashlib
            import hmac
            import json

            from flask_synapse_token_register.auth_session import get_auth_secret

            payload = {"username": username, "exp": expiry, "type": "admin_auth"}
            payload_json = json.dumps(payload)
            payload_b64 = (
                base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
            )

            # Create signature
            secret = get_auth_secret()
            signature = hmac.new(
                secret.encode(), payload_b64.encode(), hashlib.sha256
            ).digest()
            signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

            token = f"{payload_b64}.{signature_b64}"

            # Setup request with the token as cookie
            with app.test_request_context():
                flask.request.cookies = {"admin_auth": token}

                # Get admin user - should not detect renewal need
                result = get_admin_user()

                # Verify correct user is returned
                assert result == username

                # Verify renewal flag is NOT set (more than 12 hours remaining)
                assert not hasattr(g, "renew_admin_token")


def test_get_admin_user_with_invalid_token(app):
    """Test get_admin_user when token exists but is invalid."""
    with app.app_context():
        from flask_synapse_token_register.auth_session import get_admin_user

        # Create a test request with an invalid token in the cookie
        with app.test_request_context():
            # Set an invalid token in the request cookies
            flask.request.cookies = {"admin_auth": "invalid.token"}

            # Call get_admin_user - should verify token and return None
            result = get_admin_user()

            # Verify function returns None for invalid token
            assert result is None

            # Verify g.admin_user was not set
            assert not hasattr(g, "admin_user")

            # Verify renewal flags were not set
            assert not hasattr(g, "renew_admin_token")


def test_login_required_decorator(app):
    """Test login_required decorator."""
    with app.app_context():
        from flask_synapse_token_register.auth_session import login_required

        # Create a test route with login_required
        @login_required
        def test_route():
            return "Protected content"

        # Test without logged in user
        with app.test_request_context("/protected"):
            # No admin user
            response = test_route()
            # Should redirect to login
            assert response.status_code == 302
            assert "/login" in response.location

        # Test with logged in user
        with app.test_request_context("/protected"):
            # Set admin user in g
            g.admin_user = "testadmin"

            # Should allow access to the route
            response = test_route()
            assert response == "Protected content"
