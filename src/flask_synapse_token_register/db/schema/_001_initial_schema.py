"""Initial database schema for tokens, admin users, and application secrets."""

migration_name = "Initial Schema"


def apply_migration(conn):
    """Apply the initial schema migration."""
    cursor = conn.cursor()

    # Create the tokens table
    cursor.execute(
        """
    CREATE TABLE tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        used BOOLEAN NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL,
        used_at INTEGER NULL,
        used_by TEXT NULL
    )
    """
    )

    # Create index for faster token lookups
    cursor.execute("CREATE INDEX idx_tokens_token ON tokens(token)")

    # Create index for finding unused tokens
    cursor.execute(
        "CREATE INDEX idx_tokens_used_created_at ON tokens(used, created_at)"
    )

    # Create the admin users table
    cursor.execute(
        """
    CREATE TABLE admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        last_login INTEGER NULL
    )
    """
    )

    # Create index for faster username lookup
    cursor.execute("CREATE INDEX idx_admin_username ON admin_users(username)")

    # Create the application secrets table
    cursor.execute(
        """
    CREATE TABLE app_secrets (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at INTEGER NOT NULL
    )
    """
    )

    conn.commit()
