"""Tests for database connection functions."""

import os
from unittest.mock import patch

from flask_synapse_token_register.db.connection import (
    get_db_connection,
    get_db_path,
)


def test_get_db_path_in_app_context(app):
    """Test getting DB path when in Flask app context."""
    with app.app_context():
        # Should use the path from app config
        path = get_db_path()
        assert path == app.config["db_path"]


def test_get_db_path_outside_app_context():
    """Test getting DB path when not in Flask app context."""
    # Mock current_app to be None to simulate being outside app context
    with patch("flask_synapse_token_register.db.connection.current_app", None):
        path = get_db_path()
        # Should fall back to default path
        assert path == os.path.join(os.getcwd(), "flask-synapse-token-register.db")


def test_get_db_connection_creates_directory():
    """Test that get_db_connection creates directory if it doesn't exist."""
    # Create a path to a non-existent directory
    test_dir = os.path.join(os.getcwd(), "test_db_dir")
    test_path = os.path.join(test_dir, "test.db")

    # Make sure directory doesn't exist initially
    if os.path.exists(test_dir):
        os.rmdir(test_dir)

    try:
        # Mock get_db_path to return our test path
        with patch(
            "flask_synapse_token_register.db.connection.get_db_path",
            return_value=test_path,
        ):
            # Call get_db_connection which should create the directory
            conn = get_db_connection()

            # Verify directory was created
            assert os.path.exists(test_dir)

            # Close connection
            conn.close()
    finally:
        # Clean up
        if os.path.exists(test_path):
            os.remove(test_path)
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
