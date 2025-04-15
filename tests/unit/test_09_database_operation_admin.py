"""Tests for admin database operations."""

from unittest.mock import MagicMock, patch

import pytest

from flask_synapse_token_register.db.admin import (
    create_admin_user,
    delete_admin_user,
    list_admin_users,
    update_admin_password,
    update_last_login,
    verify_admin_credentials,
)
from flask_synapse_token_register.db.connection import get_db_connection


def test_create_admin_user(app):
    """Test creating an admin user."""
    with app.app_context():
        username = "test_admin_create"
        password = "SecurePass123!"

        # Delete user if it already exists from previous test
        delete_admin_user(username)

        # Create user
        result = create_admin_user(username, password)

        # Verify success
        assert result is True

        # Verify user exists in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        assert user is not None
        assert user["username"] == username

        # Clean up
        delete_admin_user(username)


def test_create_admin_user_exception_handling(app):
    """Test exception handling in create_admin_user."""
    with app.app_context():
        # Mock get_db_connection to return a connection with a cursor that raises exception
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB insertion error")

        with patch(
            "flask_synapse_token_register.db.admin.get_db_connection",
            return_value=mock_conn,
        ):
            # Attempt to create user with the mocked connection
            with pytest.raises(Exception) as exc_info:
                create_admin_user("exception_test", "Password123!")

            # Verify exception was raised
            assert "DB insertion error" in str(exc_info.value)

            # Verify rollback was called
            mock_conn.rollback.assert_called_once()


def test_verify_admin_credentials_valid(app):
    """Test successful verification of admin credentials."""
    with app.app_context():
        # Create a test user
        username = "verify_test_user"
        password = "TestPassword456!"
        create_admin_user(username, password)

        # Verify with correct credentials
        assert verify_admin_credentials(username, password) is True

        # Verify with incorrect password
        assert verify_admin_credentials(username, "WrongPassword") is False

        # Clean up
        delete_admin_user(username)


def test_verify_admin_credentials_nonexistent_user(app):
    """Test verification with a non-existent user."""
    with app.app_context():
        # Try to verify credentials for a non-existent user
        result = verify_admin_credentials("nonexistent_user", "any_password")

        # Should return False (user not found)
        assert result is False


def test_verify_admin_credentials_exception_handling(app):
    """Test exception handling in credential verification."""
    with app.app_context():
        # Create a test user first
        create_admin_user("exception_test_user", "Password123!")

        # Mock bcrypt.checkpw to raise an exception
        with patch("bcrypt.checkpw", side_effect=Exception("Test exception")):
            # Attempt to verify with the exception-throwing mock
            result = verify_admin_credentials("exception_test_user", "Password123!")

            # Should return False due to exception
            assert result is False

        # Clean up
        delete_admin_user("exception_test_user")


def test_update_last_login(app):
    """Test updating last login timestamp."""
    with app.app_context():
        # First create a test user
        test_user = "last_login_test"
        create_admin_user(test_user, "Password123!")

        # Mock time to have a predictable timestamp
        current_time = 1617000000  # A fixed timestamp for testing
        with patch("time.time", return_value=current_time):
            # Update last login
            update_last_login(test_user)

            # Verify last login was updated
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_login FROM admin_users WHERE username = ?", (test_user,)
            )
            result = cursor.fetchone()
            conn.close()

            assert result is not None
            assert result["last_login"] == current_time

        # Clean up
        delete_admin_user(test_user)


def test_update_last_login_nonexistent_user(app):
    """Test updating last login for non-existent user."""
    with app.app_context():
        # Should not raise an exception even if user doesn't exist
        update_last_login("nonexistent_last_login_user")

        # No assertion needed, we're just verifying no exception is raised


def test_list_admin_users(app):
    """Test listing all admin users."""
    with app.app_context():
        # Create test users with specific timestamps
        test_users = ["list_test1", "list_test2", "list_test3"]
        timestamps = [1610000000, 1620000000, 1630000000]

        # Clear any existing test users first
        for user in test_users:
            delete_admin_user(user)

        # Create the test users
        for i, user in enumerate(test_users):
            # Mock timestamp for creation
            with patch("time.time", return_value=timestamps[i]):
                create_admin_user(user, "Password123!")

        # List all users
        users = list_admin_users()

        # Verify our test users are in the list
        test_user_results = [u for u in users if u["username"] in test_users]
        assert len(test_user_results) == len(test_users)

        # Verify timestamps
        for i, user in enumerate(
            sorted([u for u in test_user_results], key=lambda x: x["username"])
        ):
            assert user["created_at"] == timestamps[i]
            assert user["last_login"] is None

        # Clean up
        for user in test_users:
            delete_admin_user(user)


def test_list_admin_users_empty(app):
    """Test listing admin users when there are none."""
    with app.app_context():
        # Create a temporary database with no users
        with patch(
            "flask_synapse_token_register.db.admin.get_db_connection"
        ) as mock_get_db:
            # Setup mock connection that returns empty list
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            mock_get_db.return_value = mock_conn

            # Call list_admin_users
            users = list_admin_users()

            # Verify it returns an empty list
            assert users == []

            # Verify SQL query was correct
            mock_cursor.execute.assert_called_once()
            assert (
                "SELECT username, created_at, last_login"
                in mock_cursor.execute.call_args[0][0]
            )
            assert "ORDER BY username" in mock_cursor.execute.call_args[0][0]


def test_delete_admin_user(app):
    """Test deleting an admin user."""
    with app.app_context():
        username = "delete_test_user"
        create_admin_user(username, "Password123!")

        # Verify user exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admin_users WHERE username = ?", (username,))
        assert cursor.fetchone() is not None
        conn.close()

        # Delete user
        result = delete_admin_user(username)
        assert result is True

        # Verify user is gone
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admin_users WHERE username = ?", (username,))
        assert cursor.fetchone() is None
        conn.close()


def test_delete_nonexistent_admin_user(app):
    """Test deleting a non-existent admin user."""
    with app.app_context():
        # Delete non-existent user should return False
        result = delete_admin_user("nonexistent_user_to_delete")
        assert result is False


def test_update_admin_password_success(app):
    """Test successful password update."""
    with app.app_context():
        # Create a test user
        username = "password_update_user"
        old_password = "OldPassword123!"
        create_admin_user(username, old_password)

        # Update password
        new_password = "NewPassword456!"
        result = update_admin_password(username, new_password)

        # Should return True for successful update
        assert result is True

        # Verify old password no longer works
        assert verify_admin_credentials(username, old_password) is False

        # Verify new password works
        assert verify_admin_credentials(username, new_password) is True

        # Clean up
        delete_admin_user(username)


def test_update_admin_password_nonexistent_user(app):
    """Test updating password for non-existent user."""
    with app.app_context():
        # Try to update password for a non-existent user
        result = update_admin_password("nonexistent_update_user", "NewPassword123!")

        # Should return False (no rows updated)
        assert result is False


def test_update_admin_password_exception_handling(app):
    """Test exception handling in password update."""
    with app.app_context():
        # Mock get_db_connection to raise an exception
        with patch(
            "flask_synapse_token_register.db.admin.get_db_connection",
            side_effect=Exception("Test DB exception"),
        ):
            # Attempt to update password with the exception-throwing mock
            result = update_admin_password("any_user", "NewPassword123!")

            # Should return False due to exception
            assert result is False
