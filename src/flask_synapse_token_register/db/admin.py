"""Database operations for admin users."""

import time

import bcrypt

from flask_synapse_token_register.db.connection import get_db_connection


def create_admin_user(username, password, commit=True):
    """Create a new admin user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Hash the password using bcrypt
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode(
        "utf-8"
    )

    try:
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, int(time.time())),
        )

        if commit:
            conn.commit()

        return True
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        conn.close()


def verify_admin_credentials(username, password):
    """Verify admin username and password."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT password_hash FROM admin_users WHERE username = ?", (username,)
    )
    result = cursor.fetchone()
    conn.close()

    if not result:
        # No such user
        return False

    try:
        # Verify password using bcrypt
        return bcrypt.checkpw(
            password.encode("utf-8"), result["password_hash"].encode("utf-8")
        )
    except Exception:  # pylint: disable=broad-except
        # Any error means verification failed
        return False


def update_last_login(username):
    """Update the last login timestamp for an admin user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE admin_users SET last_login = ? WHERE username = ?",
        (int(time.time()), username),
    )

    conn.commit()
    conn.close()


def list_admin_users():
    """Get a list of all admin users."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username, created_at, last_login FROM admin_users ORDER BY username"
    )

    users = [
        {
            "username": row["username"],
            "created_at": row["created_at"],
            "last_login": row["last_login"],
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return users


def delete_admin_user(username):
    """Delete an admin user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM admin_users WHERE username = ?", (username,))
    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted


def update_admin_password(username, new_password):
    """Update an admin user's password.

    Args:
        username: The admin username
        new_password: The new password to set

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Hash the new password
        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

        # Update the database
        conn = get_db_connection()
        cursor = conn.execute(
            "UPDATE admin_users SET password_hash = ? WHERE username = ?",
            (password_hash, username),
        )
        conn.commit()

        # Check if the update was successful
        return cursor.rowcount > 0
    except Exception:  # pylint: disable=broad-except
        return False
