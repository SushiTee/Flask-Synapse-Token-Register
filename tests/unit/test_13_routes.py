"""Unit tests for application routes."""

import subprocess
from unittest.mock import patch

from flask import Blueprint

import flask_synapse_token_register.routes
from flask_synapse_token_register.routes.admin import bp as admin_bp


class TestPublicRoutes:
    """Tests for public routes."""

    def test_register_no_token_redirects_to_login(self, client):
        """Test registration with no token redirects to login page."""
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_register_with_invalid_token(self, client):
        """Test registration with invalid token returns 403."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists",
            return_value=False,
        ):
            response = client.get("/?token=invalid")
            assert response.status_code == 403

    def test_register_with_used_token(self, client):
        """Test registration with used token returns 403."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists", return_value=True
        ), patch(
            "flask_synapse_token_register.routes.public.is_token_used",
            return_value=True,
        ):
            response = client.get("/?token=used_token")
            assert response.status_code == 403

    def test_register_form_with_valid_token(self, client):
        """Test registration form displays with valid token."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists", return_value=True
        ), patch(
            "flask_synapse_token_register.routes.public.is_token_used",
            return_value=False,
        ):
            response = client.get("/?token=valid_token")
            assert response.status_code == 200
            assert b"Register for matrix.example.com Matrix" in response.data

    def test_register_submission_invalid_username(self, client):
        """Test registration with invalid username."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists", return_value=True
        ), patch(
            "flask_synapse_token_register.routes.public.is_token_used",
            return_value=False,
        ):
            response = client.post(
                "/?token=valid_token",
                data={
                    "token": "valid_token",
                    "username": "INVALID!@#",
                    "password": "Password123!",
                    "confirm_password": "Password123!",
                },
            )

            assert response.status_code == 200
            assert b"Invalid username" in response.data

    def test_register_submission_password_mismatch(self, client):
        """Test registration with mismatched passwords."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists", return_value=True
        ), patch(
            "flask_synapse_token_register.routes.public.is_token_used",
            return_value=False,
        ):
            response = client.post(
                "/?token=valid_token",
                data={
                    "token": "valid_token",
                    "username": "validuser",
                    "password": "Password123!",
                    "confirm_password": "DifferentPassword123!",
                },
            )

            assert response.status_code == 200
            assert b"Passwords do not match" in response.data

    def test_register_submission_weak_password(self, client):
        """Test registration with weak password."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists", return_value=True
        ), patch(
            "flask_synapse_token_register.routes.public.is_token_used",
            return_value=False,
        ), patch(
            "flask_synapse_token_register.routes.public.is_strong_password",
            return_value=False,
        ):
            response = client.post(
                "/?token=valid_token",
                data={
                    "token": "valid_token",
                    "username": "validuser",
                    "password": "weak",
                    "confirm_password": "weak",
                },
            )

            assert response.status_code == 200
            assert b"Password must be at least" in response.data

    def test_register_submission_success(self, client):
        """Test successful registration flow."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists", return_value=True
        ), patch(
            "flask_synapse_token_register.routes.public.is_token_used",
            return_value=False,
        ), patch(
            "flask_synapse_token_register.routes.public.is_strong_password",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.public.validate_username",
            return_value=True,
        ), patch("flask_synapse_token_register.routes.public.subprocess.run"), patch(
            "flask_synapse_token_register.routes.public.mark_token_used"
        ) as mock_mark_used, patch(
            "flask_synapse_token_register.routes.public.generate_success_token",
            return_value="success123",
        ):
            response = client.post(
                "/?token=valid_token",
                data={
                    "token": "valid_token",
                    "username": "newuser",
                    "password": "StrongPass123!",
                    "confirm_password": "StrongPass123!",
                },
                follow_redirects=False,
            )

            # Should redirect to success page
            assert response.status_code == 302
            assert "/success" in response.headers["Location"]
            assert "username=newuser" in response.headers["Location"]
            assert "token=success123" in response.headers["Location"]

            # Should mark token as used
            mock_mark_used.assert_called_once_with("valid_token", username="newuser")

    def test_register_submission_missing_fields(self, client):
        """Test registration with missing form fields."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists", return_value=True
        ), patch(
            "flask_synapse_token_register.routes.public.is_token_used",
            return_value=False,
        ):
            # Test with missing password
            response = client.post(
                "/?token=valid_token",
                data={
                    "token": "valid_token",
                    "username": "validuser",
                    # Missing password and confirm_password
                },
            )

            assert response.status_code == 200
            assert b"Username and both password fields are required" in response.data

    def test_register_admin_redirects_to_manage_tokens(self, client):
        """Test that admin users accessing registration page get redirected to token management."""
        with patch(
            "flask_synapse_token_register.routes.public.get_admin_user",
            return_value="admin",
        ):
            response = client.get("/")
            assert response.status_code == 302
            assert "/manage-tokens" in response.headers["Location"]

    def test_register_subprocess_failure(self, client):
        """Test registration failure due to subprocess error."""
        with patch(
            "flask_synapse_token_register.routes.public.token_exists", return_value=True
        ), patch(
            "flask_synapse_token_register.routes.public.is_token_used",
            return_value=False,
        ), patch(
            "flask_synapse_token_register.routes.public.is_strong_password",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.public.validate_username",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.public.current_app.config.get",
            # Override the TESTING flag only for this specific call
            side_effect=lambda key, default=None: False
            if key == "TESTING"
            else default,
        ), patch(
            "flask_synapse_token_register.routes.public.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "cmd"),
        ):
            response = client.post(
                "/?token=valid_token",
                data={
                    "token": "valid_token",
                    "username": "existinguser",
                    "password": "StrongPass123!",
                    "confirm_password": "StrongPass123!",
                },
            )

            assert response.status_code == 200
            assert (
                b"Failed to register: The user existinguser already exists"
                in response.data
            )


class TestAdminRoutes:
    """Tests for admin routes."""

    def test_login_already_logged_in(self, client):
        """Test login redirects when already logged in."""
        with patch(
            "flask_synapse_token_register.routes.admin.get_admin_user",
            return_value="admin",
        ):
            response = client.get("/login")
            assert response.status_code == 302
            assert "/manage-tokens" in response.headers["Location"]

    def test_login_form_display(self, client):
        """Test login form displays correctly."""
        with patch(
            "flask_synapse_token_register.routes.admin.get_admin_user",
            return_value=None,
        ):
            response = client.get("/login")
            assert response.status_code == 200
            assert b"Admin Login" in response.data

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        with patch(
            "flask_synapse_token_register.routes.admin.get_admin_user",
            return_value=None,
        ):
            response = client.post(
                "/login",
                data={
                    "username": "admin",
                    "password": "",  # Missing password
                },
            )
            assert response.status_code == 200
            assert b"Username and password are required" in response.data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        with patch(
            "flask_synapse_token_register.routes.admin.get_admin_user",
            return_value=None,
        ), patch(
            "flask_synapse_token_register.routes.admin.verify_admin_credentials",
            return_value=False,
        ):
            response = client.post(
                "/login", data={"username": "admin", "password": "wrong"}
            )
            assert response.status_code == 200
            assert b"Invalid username or password" in response.data

    def test_login_success(self, client):
        """Test successful login."""
        with patch(
            "flask_synapse_token_register.routes.admin.get_admin_user",
            return_value=None,
        ), patch(
            "flask_synapse_token_register.routes.admin.verify_admin_credentials",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.admin.update_last_login"
        ) as mock_update_login, patch(
            "flask_synapse_token_register.routes.admin.set_admin_cookie"
        ) as mock_set_cookie:
            response = client.post(
                "/login", data={"username": "admin", "password": "correct"}
            )

            # Verify redirect
            assert response.status_code == 302
            assert "/manage-tokens" in response.headers["Location"]

            # Verify side effects
            mock_update_login.assert_called_once_with("admin")
            mock_set_cookie.assert_called_once()

    def test_logout(self, client):
        """Test logout functionality."""
        with patch(
            "flask_synapse_token_register.routes.admin.clear_admin_cookie"
        ) as mock_clear_cookie:
            response = client.get("/logout")

            # Verify redirect
            assert response.status_code == 302
            assert "/login" in response.headers["Location"]

            # Verify cookie cleared
            mock_clear_cookie.assert_called_once()

    def test_admin_token_renewal(self, client, app):
        """Test that admin token gets renewed if expiry is approaching."""

        # Create a test version of the after_request function that can be tested
        original_after_request = admin_bp.after_request_funcs[None][0]

        with patch(
            "flask_synapse_token_register.routes.admin.set_admin_cookie"
        ) as mock_set_cookie:
            # Create a Flask test request context
            with app.test_request_context("/manage-tokens"):
                # Set g values directly within the request context
                from flask import g

                g.admin_user = "admin"
                g.renew_admin_token = True
                g.token_expiry_hours = 2

                # Create a mock response to pass to the function
                mock_response = app.response_class()

                # Call the after_request function directly
                _ = original_after_request(mock_response)

                # Verify the token was renewed
                mock_set_cookie.assert_called_once_with(mock_response, "admin")

    def test_manage_tokens_requires_login(self, client):
        """Test manage tokens page requires login."""
        with patch(
            "flask_synapse_token_register.routes.admin.get_admin_user",
            return_value=None,
        ):
            response = client.get("/manage-tokens")
            assert response.status_code == 302
            assert "/login" in response.headers["Location"]

    def test_manage_tokens_shows_token_list(self, client):
        """Test manage tokens displays token list with different filters."""
        # Mock token data for testing
        mock_token = {
            "id": 10,
            "token": "abc1234-token",
            "used": 0,
            "created_at": 1000000,
            "used_at": None,
            "used_by": None,
            "created_at_formatted": "2025-01-01 01:00:00",
            "used_at_formatted": "Unknown",
            "token_short": "abc12...token",
        }

        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 2, "used": 3, "total": 5},
        ), patch(
            "flask_synapse_token_register.routes.admin.get_all_tokens",
            return_value=[mock_token],
        ):
            # Test default case (all tokens)
            response = client.get("/manage-tokens")

            assert response.status_code == 200
            assert b"Matrix Invitation Management" in response.data
            assert b"Manage Existing Tokens" in response.data
            assert b"abc12...token" in response.data
            assert b"2025-01-01 01:00:00" in response.data

        # Test unused tokens filter
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 2, "used": 3, "total": 5},
        ), patch(
            "flask_synapse_token_register.routes.admin.get_filtered_tokens",
            return_value=[mock_token],
        ) as mock_get_filtered:
            response = client.get("/manage-tokens?filter=unused")

            assert response.status_code == 200
            assert b"Filter tokens:" in response.data
            assert b"abc12...token" in response.data
            mock_get_filtered.assert_called_once_with(used=False)

        # Test used tokens filter
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 2, "used": 3, "total": 5},
        ), patch(
            "flask_synapse_token_register.routes.admin.get_filtered_tokens",
            return_value=[mock_token],
        ) as mock_get_filtered:
            response = client.get("/manage-tokens?filter=used")

            assert response.status_code == 200
            assert b"Filter tokens:" in response.data
            assert b"abc12...token" in response.data
            mock_get_filtered.assert_called_once_with(used=True)

    def test_manage_tokens_with_invalid_filter(self, client):
        """Test manage tokens handles invalid filter parameters correctly."""
        mock_token = {
            "id": 10,
            "token": "abc1234-token",
            "used": 0,
            "created_at": 1000000,
            "used_at": None,
            "used_by": None,
            "created_at_formatted": "2025-01-01 01:00:00",
            "used_at_formatted": "Unknown",
            "token_short": "abc12...token",
        }

        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 2, "used": 3, "total": 5},
        ), patch(
            "flask_synapse_token_register.routes.admin.get_all_tokens",
            return_value=[mock_token],
        ) as mock_get_all, patch(
            "flask_synapse_token_register.routes.admin.get_unused_tokens",
            return_value=[mock_token],
        ):
            # Test with an invalid filter parameter
            response = client.get("/manage-tokens?filter=invalid")

            assert response.status_code == 200
            assert mock_get_all.called, (
                "get_all_tokens should be called for invalid filters"
            )

            # Check that the "all" filter button has the active class
            assert b'href="/manage-tokens" class="filter-btn active"' in response.data

            # The other filter buttons should not have the active class
            assert (
                b'href="/manage-tokens?filter=unused" class="filter-btn "'
                in response.data
            )
            assert (
                b'href="/manage-tokens?filter=used" class="filter-btn "'
                in response.data
            )

    def test_manage_tokens_generate_token(self, client):
        """Test token generation."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 3, "used": 3, "total": 6},
        ), patch(
            "flask_synapse_token_register.routes.admin.get_all_tokens", return_value=[]
        ), patch(
            "flask_synapse_token_register.routes.admin.get_unused_tokens",
            return_value=[],
        ), patch("secrets.token_urlsafe", return_value="new_token_123"), patch(
            "flask_synapse_token_register.routes.admin.save_token"
        ) as mock_save_token:
            response = client.post("/manage-tokens", data={"action": "generate"})

            assert response.status_code == 200
            assert b"New token generated successfully" in response.data
            assert b"new_token_123" in response.data
            mock_save_token.assert_called_once_with(
                "new_token_123", used=False, ip_address="127.0.0.1"
            )

    def test_manage_tokens_delete_token(self, client):
        """Test token deletion with different filters."""
        mock_token = {
            "id": 10,
            "token": "abc1234-token",
            "used": 0,
            "created_at": 1000000,
            "used_at": None,
            "used_by": None,
            "created_at_formatted": "2025-01-01 01:00:00",
            "used_at_formatted": "Unknown",
            "token_short": "abc12...token",
        }

        # Test with "all" filter (default case)
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 1, "used": 3, "total": 4},
        ), patch(
            "flask_synapse_token_register.routes.admin.delete_token", return_value=True
        ) as mock_delete, patch(
            "flask_synapse_token_register.routes.admin.get_all_tokens",
            return_value=[mock_token],
        ) as mock_get_all:
            response = client.post(
                "/manage-tokens", data={"action": "delete", "token_id": "10"}
            )

            assert response.status_code == 200
            assert b"Token deleted successfully" in response.data
            mock_delete.assert_called_once_with("10")
            mock_get_all.assert_called_once()

        # Test with "unused" filter
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 1, "used": 3, "total": 4},
        ), patch(
            "flask_synapse_token_register.routes.admin.delete_token", return_value=True
        ) as mock_delete, patch(
            "flask_synapse_token_register.routes.admin.get_filtered_tokens",
            return_value=[mock_token],
        ) as mock_get_filtered:
            response = client.post(
                "/manage-tokens?filter=unused",
                data={"action": "delete", "token_id": "10"},
            )

            assert response.status_code == 200
            assert b"Token deleted successfully" in response.data
            mock_delete.assert_called_once_with("10")
            mock_get_filtered.assert_called_once_with(used=False)

        # Test with "used" filter
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 1, "used": 3, "total": 4},
        ), patch(
            "flask_synapse_token_register.routes.admin.delete_token", return_value=True
        ) as mock_delete, patch(
            "flask_synapse_token_register.routes.admin.get_filtered_tokens",
            return_value=[mock_token],
        ) as mock_get_filtered:
            response = client.post(
                "/manage-tokens?filter=used",
                data={"action": "delete", "token_id": "10"},
            )

            assert response.status_code == 200
            assert b"Token deleted successfully" in response.data
            mock_delete.assert_called_once_with("10")
            mock_get_filtered.assert_called_once_with(used=True)

    def test_manage_tokens_delete_token_failure(self, client):
        """Test token deletion failure."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.get_token_stats",
            return_value={"unused": 1, "used": 3, "total": 4},
        ), patch(
            "flask_synapse_token_register.routes.admin.delete_token", return_value=False
        ) as mock_delete, patch(
            "flask_synapse_token_register.routes.admin.get_all_tokens", return_value=[]
        ):
            response = client.post(
                "/manage-tokens", data={"action": "delete", "token_id": "999"}
            )

            assert response.status_code == 200
            assert b"Failed to delete token" in response.data
            mock_delete.assert_called_once_with("999")

    def test_change_password_requires_login(self, client):
        """Test change password page requires login."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value=None,
        ):
            response = client.get("/change-password")
            assert response.status_code == 302
            assert "/login" in response.headers["Location"]

    def test_change_password_displays_form(self, client):
        """Test change password form displays."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ):
            response = client.get("/change-password")
            assert response.status_code == 200
            assert b"Change Password" in response.data

    def test_change_password_incorrect_current_password(self, client):
        """Test change password with incorrect current password."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.verify_admin_credentials",
            return_value=False,
        ):
            response = client.post(
                "/change-password",
                data={
                    "current_password": "wrong",
                    "new_password": "NewPass123!",
                    "confirm_password": "NewPass123!",
                },
            )

            assert response.status_code == 200
            assert b"Current password is incorrect" in response.data

    def test_change_password_success(self, client):
        """Test successful password change."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.verify_admin_credentials",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.admin.is_strong_password",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.admin.update_admin_password",
            return_value=True,
        ) as mock_update:
            response = client.post(
                "/change-password",
                data={
                    "current_password": "Current123!",
                    "new_password": "NewPass123!",
                    "confirm_password": "NewPass123!",
                },
            )

            assert response.status_code == 200
            assert b"Password changed successfully" in response.data
            mock_update.assert_called_once_with(None, "NewPass123!")

    def test_change_password_missing_fields(self, client):
        """Test change password with missing fields."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ):
            response = client.post(
                "/change-password",
                data={
                    "current_password": "Current123!",
                    "new_password": "NewPass123!",
                    # Missing confirm_password
                },
            )

            assert response.status_code == 200
            assert b"All fields are required" in response.data

    def test_change_password_mismatch(self, client):
        """Test change password with mismatched new passwords."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.verify_admin_credentials",
            return_value=True,
        ):
            response = client.post(
                "/change-password",
                data={
                    "current_password": "Current123!",
                    "new_password": "NewPass123!",
                    "confirm_password": "DifferentPass123!",
                },
            )

            assert response.status_code == 200
            assert b"New passwords do not match" in response.data

    def test_change_password_weak_password(self, client):
        """Test change password with weak new password."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.verify_admin_credentials",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.admin.is_strong_password",
            return_value=False,
        ):
            response = client.post(
                "/change-password",
                data={
                    "current_password": "Current123!",
                    "new_password": "weak",
                    "confirm_password": "weak",
                },
            )

            assert response.status_code == 200
            assert b"New password does not meet strength requirements" in response.data

    def test_change_password_update_failure(self, client):
        """Test change password with database update failure."""
        with patch(
            "flask_synapse_token_register.auth_session.get_admin_user",
            return_value="admin",
        ), patch(
            "flask_synapse_token_register.routes.admin.verify_admin_credentials",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.admin.is_strong_password",
            return_value=True,
        ), patch(
            "flask_synapse_token_register.routes.admin.update_admin_password",
            return_value=False,
        ) as mock_update:
            response = client.post(
                "/change-password",
                data={
                    "current_password": "Current123!",
                    "new_password": "NewPass123!",
                    "confirm_password": "NewPass123!",
                },
            )

            assert response.status_code == 200
            assert b"Failed to update password" in response.data
            mock_update.assert_called_once_with(None, "NewPass123!")


class TestSuccessRoutes:
    """Tests for success routes."""

    def test_success_page_invalid_token(self, client):
        """Test success page with invalid token."""
        with patch(
            "flask_synapse_token_register.routes.success.verify_success_token",
            return_value=None,
        ):
            response = client.get("/success?username=user&token=invalid")
            assert response.status_code == 403

    def test_success_page_mismatched_username(self, client):
        """Test success page with username mismatch."""
        with patch(
            "flask_synapse_token_register.routes.success.verify_success_token",
            return_value="correct_user",
        ):
            response = client.get("/success?username=wrong_user&token=valid")
            assert response.status_code == 403

    def test_success_page_valid(self, client):
        """Test success page with valid token and username."""
        with patch(
            "flask_synapse_token_register.routes.success.verify_success_token",
            return_value="testuser",
        ):
            response = client.get("/success?username=testuser&token=valid")
            assert response.status_code == 200
            assert b"Account Successfully Created" in response.data
            assert b"testuser" in response.data


class TestErrorHandlers:
    """Tests for error handlers."""

    def test_403_handler(self, app, client):
        """Test 403 error handler."""

        @app.route("/test-403")
        def trigger_403():
            from flask import abort

            abort(403, "Test forbidden error")

        response = client.get("/test-403")
        assert response.status_code == 403
        assert b"Test forbidden error" in response.data

    def test_404_handler(self, app, client):
        """Test 404 error handler."""

        @app.route("/test-404")
        def trigger_404():
            from flask import abort

            abort(404, "Page not found")

        response = client.get("/test-404")
        assert response.status_code == 404
        assert b"Page not found" in response.data

        # also test with some really unknown route
        response = client.get("/unknown-route")
        assert response.status_code == 404
        # default flask error message
        assert b"The requested URL was not found on the server." in response.data

    def test_500_handler(self, app, client):
        """Test 500 error handler."""

        @app.route("/test-500")
        def trigger_500():
            from flask import abort

            abort(500, "Test server error")

        response = client.get("/test-500")
        assert response.status_code == 500
        assert b"Test server error" in response.data


class TestOgStaticRoutes:
    """Tests for OG static routes."""

    def setup_method(self, _):
        """Set up method to run before each test."""
        # Import here to avoid circular imports
        from flask_synapse_token_register.routes.og_static import serve_og_static

        self.serve_og_static = serve_og_static

    def test_og_static_not_configured(self, app, client):
        """Test og_static route when not configured."""
        # Create a separate blueprint for testing
        bp = Blueprint("test_og_static", __name__)
        bp.add_url_rule(
            "/og-static/<path:filename>", "serve_og_static", self.serve_og_static
        )
        app.register_blueprint(bp)

        with app.app_context():
            # Ensure og_static_dir is not configured
            app.config["og_static_dir"] = None

            # Add mock error handler
            @app.errorhandler(404)
            def mock_not_found(_):
                return "Not Found", 404

            response = client.get("/og-static/image.png")
            assert response.status_code == 404

    def test_og_static_directory_not_found(self, app, client):
        """Test og_static route when directory doesn't exist."""
        # Create a separate blueprint for testing
        bp = Blueprint("test_og_static", __name__)
        bp.add_url_rule(
            "/og-static/<path:filename>", "serve_og_static", self.serve_og_static
        )
        app.register_blueprint(bp)

        with app.app_context():
            # Configure a non-existent directory
            app.config["og_static_dir"] = "/path/that/does/not/exist"

            # Add mock error handler
            @app.errorhandler(404)
            def mock_not_found(_):
                return "Not Found", 404

            with patch("os.path.isdir", return_value=False):
                response = client.get("/og-static/image.png")
                assert response.status_code == 404

    def test_og_static_file_not_found(self, app, client):
        """Test og_static route when file doesn't exist in directory."""
        # Create a separate blueprint for testing
        bp = Blueprint("test_og_static", __name__)
        bp.add_url_rule(
            "/og-static/<path:filename>", "serve_og_static", self.serve_og_static
        )
        app.register_blueprint(bp)

        with app.app_context():
            # Configure a valid directory
            app.config["og_static_dir"] = "/valid/path"

            # Add mock error handler
            @app.errorhandler(404)
            def mock_not_found(_):
                return "Not Found", 404

            with patch("os.path.isdir", return_value=True), patch(
                "os.path.isfile", return_value=False
            ):
                response = client.get("/og-static/missing-image.png")
                assert response.status_code == 404

    def test_og_static_directory_traversal(self, app, client):
        """Test og_static route blocks directory traversal attempts."""
        # Create a separate blueprint for testing
        bp = Blueprint("test_og_static", __name__)
        bp.add_url_rule(
            "/og-static/<path:filename>", "serve_og_static", self.serve_og_static
        )
        app.register_blueprint(bp)

        with app.app_context():
            # Configure a valid directory
            app.config["og_static_dir"] = "/valid/path"

            # Add mock error handler
            @app.errorhandler(403)
            def mock_forbidden(_):
                return "Forbidden", 403

            with patch("os.path.isdir", return_value=True), patch(
                "os.path.abspath", side_effect=lambda p: p
            ):
                # Try a directory traversal attack
                response = client.get("/og-static/../../../etc/passwd")
                assert response.status_code == 403

    def test_og_static_valid_file(self, app, client):
        """Test og_static route serves valid files correctly."""
        # Create a separate blueprint for testing
        bp = Blueprint("test_og_static", __name__)
        bp.add_url_rule(
            "/og-static/<path:filename>", "serve_og_static", self.serve_og_static
        )
        app.register_blueprint(bp)

        test_file_content = b"test image data"

        with app.app_context():
            # Configure a valid directory
            app.config["og_static_dir"] = "/valid/path"

            with patch("os.path.isdir", return_value=True), patch(
                "os.path.isfile", return_value=True
            ), patch(
                "os.path.abspath", side_effect=lambda p: "/valid/path/valid-image.png"
            ), patch(
                "flask_synapse_token_register.routes.og_static.send_from_directory",
                return_value=test_file_content,
            ) as mock_send:
                response = client.get("/og-static/valid-image.png")

                # Verify send_from_directory was called with correct parameters
                mock_send.assert_called_once()
                args, _ = mock_send.call_args
                assert args[0] == "/valid/path"  # First arg is directory
                assert args[1] == "valid-image.png"  # Second arg is filename

                # The response should contain our test content
                assert response.data == test_file_content

    def test_blueprint_registration_with_og_static_dir(self):
        """Test that the og_static blueprint is registered when og_static_dir is configured."""
        # Create a test config with og_static_dir
        test_config = {
            "og_static_dir": "/some/path",
            "TESTING": True,
            "register_url_prefix": "",
            "url_scheme": "http",
        }

        # Patch config loading to use our test config
        with patch(
            "flask_synapse_token_register.app.load_config", return_value=test_config
        ):
            # Import inside patch to get fresh app with our config
            from flask_synapse_token_register.app import create_app

            app_with_og = create_app()

            # Check if og_static blueprint is registered
            assert "og_static" in app_with_og.blueprints

    def test_blueprint_registration_without_og_static_dir(self):
        """Test that the og_static blueprint is not registered when og_static_dir is not configured."""
        # Create a test config without og_static_dir
        test_config = {"TESTING": True, "register_url_prefix": "", "url_scheme": "http"}

        # Patch config loading to use our test config
        with patch(
            "flask_synapse_token_register.app.load_config", return_value=test_config
        ):
            # Import inside patch to get fresh app with our config
            from flask_synapse_token_register.app import create_app

            app_without_og = create_app()

            # Check that og_static blueprint is not registered
            assert "og_static" not in app_without_og.blueprints

    def test_template_context_without_og_static_dir(self):
        """Test that has_og_static_dir is correctly exposed as False when not configured."""
        # Create a test app without og_static_dir configured
        with patch(
            "flask_synapse_token_register.app.load_config",
            return_value={
                "TESTING": True,
                "register_url_prefix": "",
                "url_scheme": "http",
            },
        ):
            from flask_synapse_token_register.app import create_app

            test_app = create_app()
            test_client = test_app.test_client()

            # Add a test route
            @test_app.route("/test-og-context")
            def test_og_context():
                from flask import render_template_string

                return render_template_string("""
                    {% if has_og_static_dir %}
                    Has OG static: True
                    {% else %}
                    Has OG static: False
                    {% endif %}
                """)

            # Test with fresh app instance
            response = test_client.get("/test-og-context")
            assert b"Has OG static: False" in response.data

    def test_template_context_with_og_static_dir(self, app, client):
        """Test that has_og_static_dir is correctly exposed as True when configured."""
        # Create a test app with og_static_dir configured
        with patch(
            "flask_synapse_token_register.app.load_config",
            return_value={
                "og_static_dir": "/some/path",
                "TESTING": True,
                "register_url_prefix": "",
                "url_scheme": "http",
            },
        ):
            from flask_synapse_token_register.app import create_app

            test_app = create_app()
            test_client = test_app.test_client()

            # Add a test route
            @test_app.route("/test-og-context")
            def test_og_context():
                from flask import render_template_string

                return render_template_string("""
                    {% if has_og_static_dir %}
                    Has OG static: True
                    {% else %}
                    Has OG static: False
                    {% endif %}
                """)

            # Test with fresh app instance
            response = test_client.get("/test-og-context")
            assert b"Has OG static: True" in response.data


class TestTemplateContext:
    """Tests for the global template context processor."""

    def test_context_processor(self, app, client, monkeypatch):
        """Test the global template context processor."""

        # Setup a simple test route that uses the template context
        @app.route("/test-context")
        def test_context():
            from flask import render_template_string

            return render_template_string("""
                Site: {{ site_name }}
                Logged in: {{ admin_logged_in }}
                Body classes: {{ body_classes }}
                OG title: {{ og_meta.title if og_meta else 'None' }}
            """)

        # Test without admin login
        monkeypatch.setattr(
            flask_synapse_token_register.routes, "get_admin_user", lambda: None
        )
        response = client.get("/test-context")
        assert b"Site: Test Matrix Server" in response.data
        assert b"Logged in: False" in response.data
        assert b"Body classes: " in response.data  # Empty

        # Test with admin login
        monkeypatch.setattr(
            flask_synapse_token_register.routes, "get_admin_user", lambda: "admin"
        )
        response = client.get("/test-context")
        assert b"Site: Test Matrix Server" in response.data
        assert b"Logged in: True" in response.data
        assert b"Body classes: has-admin-nav" in response.data

        # Test with custom site name and OG data
        with app.app_context():
            app.config["site_name"] = "Custom Matrix"
            app.config["og"] = {"title": "Custom OG Title"}

            # Need to reapply the patch in this context
            monkeypatch.setattr(
                flask_synapse_token_register.routes, "get_admin_user", lambda: None
            )
            response = client.get("/test-context")
            assert b"Site: Custom Matrix" in response.data
            assert b"OG title: Custom OG Title" in response.data
