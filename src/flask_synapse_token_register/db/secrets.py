"""Database operations for application secrets."""

import secrets as py_secrets
import time

from flask_synapse_token_register.db.connection import get_db_connection


def get_secret(key, default=None):
    """Get a secret from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM app_secrets WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result["value"]
    return default


def set_secret(key, value):
    """Set a secret in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if key exists
    cursor.execute("SELECT 1 FROM app_secrets WHERE key = ?", (key,))
    exists = cursor.fetchone() is not None

    if exists:
        # Update existing key
        cursor.execute("UPDATE app_secrets SET value = ? WHERE key = ?", (value, key))
    else:
        # Insert new key
        cursor.execute(
            "INSERT INTO app_secrets (key, value, created_at) VALUES (?, ?, ?)",
            (key, value, int(time.time())),
        )

    conn.commit()
    conn.close()
    return value


def generate_secret_key():
    """Generate and store a new secret key if one doesn't exist."""
    existing_key = get_secret("SECRET_KEY")
    if existing_key:
        return

    # Generate a new key
    new_key = py_secrets.token_hex(32)
    set_secret("SECRET_KEY", new_key)
