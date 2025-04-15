"""Database connection handling for the registration page."""

import os
import sqlite3

from flask import current_app


def dict_factory(cursor, row):
    """Convert row to dictionary for easier access."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db_path():
    """Get the database path from configuration or use default."""
    if current_app:
        # If within Flask app context, use the configured path
        return current_app.config.get("db_path")

    # Otherwise, use a default path in the current directory
    return os.path.join(os.getcwd(), "flask-synapse-token-register.db")


def get_db_connection():
    """Create a connection to the SQLite database."""
    # Get path from config or use default
    db_path = get_db_path()

    # Create the directory if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    return conn
