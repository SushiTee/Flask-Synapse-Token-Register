"""Tests for application secrets functions."""

from unittest.mock import MagicMock, patch

from flask_synapse_token_register.db.secrets import (
    generate_secret_key,
    get_secret,
    set_secret,
)


def test_get_secret_existing(app):
    """Test retrieving an existing secret."""
    with app.app_context():
        # Mock database to return a secret
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"value": "test_secret_value"}

        with patch(
            "flask_synapse_token_register.db.secrets.get_db_connection",
            return_value=mock_conn,
        ):
            # Get the secret
            value = get_secret("test_key")

            # Verify correct value was returned
            assert value == "test_secret_value"

            # Verify correct SQL was executed
            mock_cursor.execute.assert_called_once_with(
                "SELECT value FROM app_secrets WHERE key = ?", ("test_key",)
            )


def test_get_secret_nonexistent(app):
    """Test retrieving a non-existent secret."""
    with app.app_context():
        # Mock database to return no secret
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch(
            "flask_synapse_token_register.db.secrets.get_db_connection",
            return_value=mock_conn,
        ):
            # Get a non-existent secret with default
            value = get_secret("missing_key", default="default_value")

            # Should return the default
            assert value == "default_value"

            # Without default, should return None
            value = get_secret("missing_key")
            assert value is None


def test_set_secret_new(app):
    """Test setting a new secret."""
    with app.app_context():
        # Mock database operations
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Secret doesn't exist yet
        mock_cursor.fetchone.return_value = None

        with patch(
            "flask_synapse_token_register.db.secrets.get_db_connection",
            return_value=mock_conn,
        ), patch("time.time", return_value=1000000):
            # Set a new secret
            value = set_secret("new_key", "new_value")

            # Should return the set value
            assert value == "new_value"

            # Verify correct SQL was executed
            assert mock_cursor.execute.call_count == 2  # Check existence + insert

            # Check existence query
            assert (
                mock_cursor.execute.call_args_list[0][0][0]
                == "SELECT 1 FROM app_secrets WHERE key = ?"
            )
            assert mock_cursor.execute.call_args_list[0][0][1] == ("new_key",)

            # Check insert query
            assert (
                "INSERT INTO app_secrets" in mock_cursor.execute.call_args_list[1][0][0]
            )
            assert mock_cursor.execute.call_args_list[1][0][1] == (
                "new_key",
                "new_value",
                1000000,
            )

            # Verify connection was committed
            mock_conn.commit.assert_called_once()


def test_set_secret_update(app):
    """Test updating an existing secret."""
    with app.app_context():
        # Mock database operations
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Secret exists
        mock_cursor.fetchone.return_value = {"value": "old_value"}

        with patch(
            "flask_synapse_token_register.db.secrets.get_db_connection",
            return_value=mock_conn,
        ):
            # Update existing secret
            value = set_secret("existing_key", "updated_value")

            # Should return the set value
            assert value == "updated_value"

            # Verify correct SQL was executed
            assert mock_cursor.execute.call_count == 2  # Check existence + update

            # Check update query
            assert (
                "UPDATE app_secrets SET value"
                in mock_cursor.execute.call_args_list[1][0][0]
            )
            assert mock_cursor.execute.call_args_list[1][0][1] == (
                "updated_value",
                "existing_key",
            )

            # Verify connection was committed
            mock_conn.commit.assert_called_once()


def test_generate_secret_key_not_existing(app):
    """Test generating a secret key when none exists."""
    with app.app_context():
        # Mock get_secret to return None (no existing key)
        with patch(
            "flask_synapse_token_register.db.secrets.get_secret", return_value=None
        ) as mock_get_secret, patch(
            "flask_synapse_token_register.db.secrets.set_secret"
        ) as mock_set_secret, patch(
            "secrets.token_hex", return_value="new_generated_secret"
        ) as mock_token_hex:
            # Generate key
            generate_secret_key()

            # Verify methods were called correctly
            mock_get_secret.assert_called_once_with("SECRET_KEY")
            mock_token_hex.assert_called_once_with(32)
            mock_set_secret.assert_called_once_with(
                "SECRET_KEY", "new_generated_secret"
            )


def test_generate_secret_key_existing(app):
    """Test generating a secret key when one already exists."""
    with app.app_context():
        # Mock get_secret to return an existing key
        with patch(
            "flask_synapse_token_register.db.secrets.get_secret",
            return_value="existing_secret",
        ) as mock_get_secret, patch(
            "flask_synapse_token_register.db.secrets.set_secret"
        ) as mock_set_secret, patch("secrets.token_hex") as mock_token_hex:
            # Try to generate key when one exists
            generate_secret_key()

            # Verify get_secret was called but not the others
            mock_get_secret.assert_called_once_with("SECRET_KEY")
            mock_token_hex.assert_not_called()
            mock_set_secret.assert_not_called()
