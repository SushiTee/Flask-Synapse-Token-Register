"""Database operations for managing tokens."""

import time

from flask_synapse_token_register.db.connection import get_db_connection
from flask_synapse_token_register.utils import format_timestamp


def save_token(token, used=False, ip_address=None):
    """Save a new token to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if we have the IP column in our schema
    cursor.execute("PRAGMA table_info(tokens)")
    columns = {col["name"] for col in cursor.fetchall()}

    if "ip_address" in columns:
        cursor.execute(
            "INSERT INTO tokens (token, used, created_at, ip_address) VALUES (?, ?, ?, ?)",
            (token, 1 if used else 0, int(time.time()), ip_address),
        )
    else:
        cursor.execute(
            "INSERT INTO tokens (token, used, created_at) VALUES (?, ?, ?)",
            (token, 1 if used else 0, int(time.time())),
        )

    conn.commit()
    conn.close()


def mark_token_used(token, username=None):
    """Mark a token as used."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tokens SET used = 1, used_at = ?, used_by = ? WHERE token = ?",
        (int(time.time()), username, token),
    )

    conn.commit()
    conn.close()


def token_exists(token):
    """Check if a token exists in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM tokens WHERE token = ?", (token,))
    exists = cursor.fetchone() is not None

    conn.close()
    return exists


def is_token_used(token):
    """Check if a token has been used."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT used FROM tokens WHERE token = ?", (token,))
    row = cursor.fetchone()

    conn.close()
    return bool(row["used"]) if row else True  # Default to True if token doesn't exist


def get_all_tokens():
    """Get all tokens from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, token, used, created_at, used_at, used_by
        FROM tokens
        ORDER BY created_at DESC
        """
    )

    tokens = cursor.fetchall()
    conn.close()

    # Add formatted timestamps and truncated token representation
    for token in tokens:
        token["created_at_formatted"] = format_timestamp(token["created_at"])
        token["used_at_formatted"] = (
            format_timestamp(token["used_at"]) if token["used_at"] else "Unknown"
        )
        # Add abbreviated token for display but keep original for data attribute
        full_token = token["token"]
        if full_token and len(full_token) > 16:
            token["token_short"] = f"{full_token[:8]}...{full_token[-8:]}"
        else:
            token["token_short"] = full_token

    return tokens


def get_filtered_tokens(used=None):
    """Get tokens filtered by used status."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if used is not None:
        cursor.execute(
            """
            SELECT id, token, used, created_at, used_at, used_by
            FROM tokens
            WHERE used = ?
            ORDER BY created_at DESC
            """,
            (1 if used else 0,),
        )
    else:
        cursor.execute(
            """
            SELECT id, token, used, created_at, used_at, used_by
            FROM tokens
            ORDER BY created_at DESC
            """
        )

    tokens = cursor.fetchall()
    conn.close()

    # Add formatted timestamps and truncated token representation
    for token in tokens:
        token["created_at_formatted"] = format_timestamp(token["created_at"])
        token["used_at_formatted"] = (
            format_timestamp(token["used_at"]) if token["used_at"] else "Unknown"
        )
        # Add abbreviated token for display
        full_token = token["token"]
        if full_token and len(full_token) > 16:
            token["token_short"] = f"{full_token[:8]}...{full_token[-8:]}"
        else:
            token["token_short"] = full_token

    return tokens


def delete_token(token_id):
    """Delete a token from the database by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM tokens WHERE id = ?", (token_id,))
        success = cursor.rowcount > 0
        conn.commit()
        return success
    except Exception:  # pylint: disable=broad-except
        conn.rollback()
        return False
    finally:
        conn.close()


def get_unused_tokens():
    """Get a list of all unused tokens."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT token, created_at FROM tokens WHERE used = 0 ORDER BY created_at"
    )
    tokens = [(row["token"], row["created_at"]) for row in cursor.fetchall()]

    conn.close()
    return tokens


def get_token_stats():
    """Get statistics about tokens."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM tokens")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as unused FROM tokens WHERE used = 0")
    unused = cursor.fetchone()["unused"]

    conn.close()
    return {"total": total, "unused": unused, "used": total - unused}
