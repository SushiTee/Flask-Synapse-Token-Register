"""Tests for database token functions."""

from unittest.mock import MagicMock, patch

from flask_synapse_token_register.db.connection import (
    get_db_connection,
)
from flask_synapse_token_register.db.tokens import (
    delete_token,
    get_all_tokens,
    get_filtered_tokens,
    get_token_stats,
    get_unused_tokens,
    is_token_used,
    mark_token_used,
    save_token,
    token_exists,
)
from flask_synapse_token_register.utils import format_timestamp


def test_token_save_and_retrieval(app):
    """Test saving and retrieving tokens."""
    with app.app_context():
        # Save a token
        test_token = "test_token_save_retrieve"
        save_token(test_token, used=False)

        # Verify it exists
        assert token_exists(test_token)

        # Verify it's not used
        assert not is_token_used(test_token)

        # Mark as used
        mark_token_used(test_token, username="testuser")

        # Verify it's now used
        assert is_token_used(test_token)


def test_save_token_with_ip(app):
    """Test saving token with IP address."""
    with app.app_context():
        # Save a token with IP
        test_token = "test_token_with_ip"
        save_token(test_token, used=False, ip_address="192.168.1.1")

        # Verify it exists
        assert token_exists(test_token)

        # Verify IP was stored if schema supports it
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if ip_address column exists
        cursor.execute("PRAGMA table_info(tokens)")
        columns = {col["name"] for col in cursor.fetchall()}

        if "ip_address" in columns:
            cursor.execute(
                "SELECT ip_address FROM tokens WHERE token = ?", (test_token,)
            )
            result = cursor.fetchone()
            assert result["ip_address"] == "192.168.1.1"

        conn.close()


def test_save_token_without_ip_column(app):
    """Test saving token when IP column doesn't exist."""
    with app.app_context():
        # Create a test connection that will simulate not having ip_address column
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchall to return columns without ip_address
        mock_cursor.fetchall.return_value = [
            {"name": "id"},
            {"name": "token"},
            {"name": "used"},
            {"name": "created_at"},
        ]

        # Mock get_db_connection to return our test connection
        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Call save_token
            save_token("test_token", False)

            # Verify correct SQL was executed (without ip_address)
            mock_cursor.execute.assert_any_call(
                "INSERT INTO tokens (token, used, created_at) VALUES (?, ?, ?)",
                ("test_token", 0, mock_cursor.execute.call_args_list[1][0][1][2]),
            )


def test_is_token_used_nonexistent(app):
    """Test is_token_used with non-existent token."""
    with app.app_context():
        # Non-existent tokens should return True (treat as used)
        assert is_token_used("nonexistent_token") is True


def test_get_token_stats(app):
    """Test token statistics function."""
    with app.app_context():
        # Clear existing tokens
        conn = get_db_connection()
        conn.execute("DELETE FROM tokens")
        conn.commit()

        # Add some tokens
        for i in range(5):
            save_token(f"unused_token_{i}", used=False)

        for i in range(3):
            save_token(f"used_token_{i}", used=True)

        # Get stats
        stats = get_token_stats()

        # Verify counts
        assert stats["unused"] == 5
        assert stats["used"] == 3
        assert stats["total"] == 8


def test_get_unused_tokens(app):
    """Test retrieving unused tokens."""
    with app.app_context():
        # Clear existing tokens
        conn = get_db_connection()
        conn.execute("DELETE FROM tokens")
        conn.commit()

        # Add some unused tokens
        expected_tokens = []
        for i in range(3):
            token = f"unused_token_{i}"
            expected_tokens.append(token)
            save_token(token, used=False)

        # Add a used token
        save_token("used_token", used=True)

        # Get unused tokens
        unused = get_unused_tokens()

        # Verify they match
        assert len(unused) == 3
        for token, _ in unused:
            assert token in expected_tokens


def test_get_all_tokens_formatting(app):
    """Test that get_all_tokens formats tokens correctly."""
    with app.app_context():
        # Create mock tokens that require formatting
        mock_tokens = [
            {
                "id": 1,
                "token": "abcdefghijklmnopqrstuvwxyz12345678",  # Long token
                "used": 1,
                "created_at": 1617000000,
                "used_at": 1617001000,
                "used_by": "testuser",
            },
            {
                "id": 2,
                "token": "short",  # Short token
                "used": 0,
                "created_at": 1617002000,
                "used_at": None,
                "used_by": None,
            },
        ]

        # Mock the database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = mock_tokens

        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Get tokens
            tokens = get_all_tokens()

            # Check long token formatting
            assert tokens[0]["token_short"] == "abcdefgh...12345678"

            # Check short token formatting
            assert tokens[1]["token_short"] == "short"


def test_get_filtered_tokens_used(app):
    """Test getting filtered tokens with used=True."""
    with app.app_context():
        # Mock database response
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Get used tokens
            get_filtered_tokens(used=True)

            # Verify correct SQL was executed with WHERE used = 1
            sql = mock_cursor.execute.call_args[0][0]
            params = mock_cursor.execute.call_args[0][1]
            assert "WHERE used = ?" in sql
            assert params == (1,)


def test_get_filtered_tokens_unused(app):
    """Test getting filtered tokens with used=False."""
    with app.app_context():
        # Mock database response
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Get unused tokens
            get_filtered_tokens(used=False)

            # Verify correct SQL was executed with WHERE used = 0
            sql = mock_cursor.execute.call_args[0][0]
            params = mock_cursor.execute.call_args[0][1]
            assert "WHERE used = ?" in sql
            assert params == (0,)


def test_get_filtered_tokens_all(app):
    """Test getting all tokens without filtering."""
    with app.app_context():
        # Mock database response
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Get all tokens
            get_filtered_tokens(used=None)

            # Verify correct SQL was executed without WHERE clause
            sql = mock_cursor.execute.call_args[0][0]
            assert "WHERE used" not in sql


def test_get_filtered_tokens_formatting(app):
    """Test that get_filtered_tokens formats tokens correctly."""
    with app.app_context():
        # Create mock tokens that require formatting
        mock_tokens = [
            {
                "id": 1,
                "token": "abcdefghijklmnopqrstuvwxyz12345678",  # Long token
                "used": 1,
                "created_at": 1617000000,
                "used_at": 1617001000,
                "used_by": "testuser",
            },
            {
                "id": 2,
                "token": "short",  # Short token
                "used": 0,
                "created_at": 1617002000,
                "used_at": None,
                "used_by": None,
            },
        ]

        # Mock the database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = mock_tokens

        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Get tokens
            tokens = get_filtered_tokens()

            # Check formatted timestamps
            assert tokens[0]["created_at_formatted"] == format_timestamp(1617000000)
            assert tokens[0]["used_at_formatted"] == format_timestamp(1617001000)
            assert tokens[1]["used_at_formatted"] == "Unknown"

            # Check token shortening
            assert tokens[0]["token_short"] == "abcdefgh...12345678"
            assert tokens[1]["token_short"] == "short"


def test_delete_token_success(app):
    """Test successful token deletion."""
    with app.app_context():
        # Mock successful deletion
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1

        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Delete token
            result = delete_token(1)

            # Verify success
            assert result is True
            mock_conn.commit.assert_called_once()


def test_delete_token_not_found(app):
    """Test deletion when token is not found."""
    with app.app_context():
        # Mock token not found
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 0

        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Delete non-existent token
            result = delete_token(999)

            # Verify failure
            assert result is False
            mock_conn.commit.assert_called_once()


def test_delete_token_exception(app):
    """Test exception handling during token deletion."""
    with app.app_context():
        # Mock exception during deletion
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB error")

        with patch(
            "flask_synapse_token_register.db.tokens.get_db_connection",
            return_value=mock_conn,
        ):
            # Delete token with exception
            result = delete_token(1)

            # Verify failure
            assert result is False
            mock_conn.rollback.assert_called_once()
            mock_conn.close.assert_called_once()
