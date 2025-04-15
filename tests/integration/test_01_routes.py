"""Integration tests for application routes."""

from unittest.mock import patch


def test_register_page_requires_token(client):
    """Test that the registration page requires a token."""
    # Access the home page without a token
    response = client.get("/")

    # Should redirect to login
    assert response.status_code == 302
    assert "/login" in response.location


def test_register_page_with_token(client, generate_token):
    """Test accessing registration page with a valid token."""
    response = client.get(f"/?token={generate_token}")

    # Should show the registration page
    assert response.status_code == 200
    assert b"Register for matrix.example.com Matrix" in response.data


def test_token_already_used(client, app, generate_token):
    """Test accessing with an already used token."""
    # Mark the token as used
    with app.app_context():
        from flask_synapse_token_register.db.tokens import mark_token_used

        mark_token_used(generate_token, username="existinguser")

    # Try to access with this token
    response = client.get(f"/?token={generate_token}", follow_redirects=True)

    # Should get an error page
    assert response.status_code == 403
    assert b"This registration token has already been used" in response.data


def test_invalid_token(client):
    """Test accessing with an invalid token."""
    response = client.get("/?token=invalid_token", follow_redirects=True)

    # Should get an error page
    assert response.status_code == 403
    assert b"Invalid registration token" in response.data


def test_admin_login_page(client):
    """Test admin login page."""
    response = client.get("/login")

    # Should show login form
    assert response.status_code == 200
    assert b"Admin Login" in response.data


def test_admin_login_success(client):
    """Test successful admin login."""
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "Password123!"},
        follow_redirects=True,
    )

    # Should redirect to token management page
    assert response.status_code == 200
    assert b"Matrix Invitation Management" in response.data

    # Check that the admin cookie was set (modern Flask test client approach)
    assert client.get_cookie("admin_auth") is not None


def test_admin_login_failure(client):
    """Test failed admin login."""
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "WrongPassword123!"},
        follow_redirects=True,
    )

    # Should show error
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_admin_logout(client, auth):
    """Test admin logout."""
    # Login first
    auth.login()

    # Verify we're logged in
    response = client.get("/manage-tokens")
    assert response.status_code == 200
    assert b"Matrix Invitation Management" in response.data

    # Then logout
    response = client.get("/logout")

    # Check that the response includes a Set-Cookie header that clears the auth cookie
    assert "Set-Cookie" in response.headers
    cookie_header = response.headers["Set-Cookie"]
    assert "admin_auth=" in cookie_header  # Cookie name
    assert (
        "Expires=" in cookie_header or "Max-Age=0" in cookie_header
    )  # Deletion marker

    # Try to access a protected page - with our improved client, the cookie should be gone
    response = client.get("/manage-tokens")

    # Should redirect to login
    assert response.status_code == 302
    assert "/login" in response.location


def test_manage_tokens_requires_auth(client):
    """Test that token management requires authentication."""
    response = client.get("/manage-tokens")

    # Should redirect to login
    assert response.status_code == 302
    assert "/login" in response.location


def test_manage_tokens_page(client, auth):
    """Test token management page when authenticated."""
    # Login
    auth.login()

    # Access token management
    response = client.get("/manage-tokens")

    # Should show token management interface
    assert response.status_code == 200
    assert b"Matrix Invitation Management" in response.data
    assert b"Generate New Token" in response.data


def test_successful_registration(client, generate_token):
    """Test successful user registration."""
    # Submit registration form
    response = client.post(
        "/",
        data={
            "token": generate_token,
            "username": "newuser",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True,
    )

    # Should redirect to success page
    assert response.status_code == 200
    assert b"Account Successfully Created" in response.data

    # Check token was marked as used
    response = client.get(f"/?token={generate_token}", follow_redirects=True)
    assert response.status_code == 403
    assert b"This registration token has already been used" in response.data


@patch("subprocess.run")
def test_registration_weak_password(mock_run, client, generate_token):
    """Test registration with weak password."""
    # Submit registration with weak password
    response = client.post(
        "/",
        data={
            "token": generate_token,
            "username": "newuser",
            "password": "password",  # Too weak
            "confirm_password": "password",
        },
    )

    # Should show password strength error
    assert response.status_code == 200
    assert b"Password must be at least 8 characters long" in response.data

    # Verify subprocess was NOT called
    mock_run.assert_not_called()


def test_change_password(client, auth):
    """Test changing admin password."""
    # Login first
    auth.login()

    # Access the change password page
    response = client.get("/change-password")
    assert response.status_code == 200
    assert b"Change Admin Password" in response.data

    # Try to change with incorrect current password
    response = client.post(
        "/change-password",
        data={
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )
    assert b"Current password is incorrect" in response.data

    # Try to change with password mismatch
    response = client.post(
        "/change-password",
        data={
            "current_password": "Password123!",
            "new_password": "NewPassword123!",
            "confirm_password": "DifferentPassword123!",
        },
    )
    assert b"New passwords do not match" in response.data

    # Try to change with weak password
    response = client.post(
        "/change-password",
        data={
            "current_password": "Password123!",
            "new_password": "weak",
            "confirm_password": "weak",
        },
    )
    assert b"New password does not meet strength requirements" in response.data

    # Successfully change password
    response = client.post(
        "/change-password",
        data={
            "current_password": "Password123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )
    assert b"Password changed successfully" in response.data

    # Verify we can still access protected pages (still logged in)
    response = client.get("/manage-tokens")
    assert response.status_code == 200

    # Logout
    response = client.get("/logout")
    assert response.status_code == 302
    response.set_cookie("admin_auth", "", expires=0)

    # Try logging in with old password
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "Password123!"},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data

    # Login with new password
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "NewPassword123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Matrix Invitation Management" in response.data

    # Verify we can access protected pages
    response = client.get("/manage-tokens")
    assert response.status_code == 200
