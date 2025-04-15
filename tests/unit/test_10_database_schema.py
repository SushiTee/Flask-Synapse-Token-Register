# Add this new test function to the migration test file

import importlib
import sqlite3
import time

from flask_synapse_token_register.db.migration import (
    get_migration_files,
    init_migrations_table,
)


def test_001_initial_schema_migration():
    """Test the 001_initial_schema migration applies correctly."""
    # Import the migration module
    from flask_synapse_token_register.db.schema import _001_initial_schema

    # Create temporary in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    try:
        # Apply the migration
        _001_initial_schema.apply_migration(conn)

        # Verify tables were created
        cursor = conn.cursor()

        # Check tokens table exists with correct structure
        cursor.execute("PRAGMA table_info(tokens)")
        columns = {col["name"] for col in cursor.fetchall()}
        expected_columns = {"id", "token", "used", "created_at", "used_at", "used_by"}
        assert expected_columns.issubset(columns)

        # Check admin_users table exists with correct structure
        cursor.execute("PRAGMA table_info(admin_users)")
        columns = {col["name"] for col in cursor.fetchall()}
        expected_columns = {
            "id",
            "username",
            "password_hash",
            "created_at",
            "last_login",
        }
        assert expected_columns.issubset(columns)

        # Check app_secrets table exists with correct structure
        cursor.execute("PRAGMA table_info(app_secrets)")
        columns = {col["name"] for col in cursor.fetchall()}
        expected_columns = {"key", "value", "created_at"}
        assert expected_columns.issubset(columns)

        # Check indexes were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {idx["name"] for idx in cursor.fetchall()}
        expected_indexes = {
            "idx_tokens_token",
            "idx_tokens_used_created_at",
            "idx_admin_username",
        }
        assert expected_indexes.issubset(indexes)

        # Test we can insert data into the tables
        # Test tokens table
        cursor.execute(
            "INSERT INTO tokens (token, used, created_at) VALUES (?, ?, ?)",
            ("test_token", 0, 1000000),
        )

        # Test admin_users table
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, created_at) VALUES (?, ?, ?)",
            ("test_admin", "hash_value", 1000000),
        )

        # Test app_secrets table
        cursor.execute(
            "INSERT INTO app_secrets (key, value, created_at) VALUES (?, ?, ?)",
            ("test_key", "test_value", 1000000),
        )

        # Verify data was inserted
        cursor.execute("SELECT COUNT(*) as count FROM tokens")
        assert cursor.fetchone()["count"] == 1

        cursor.execute("SELECT COUNT(*) as count FROM admin_users")
        assert cursor.fetchone()["count"] == 1

        cursor.execute("SELECT COUNT(*) as count FROM app_secrets")
        assert cursor.fetchone()["count"] == 1

    finally:
        # Always close the connection
        conn.close()


def test_all_migrations_in_sequence():
    """Test applying all migrations in sequence."""
    # Create temporary in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    try:
        # Get all migration files
        migrations = get_migration_files()

        # Initialize the migrations table
        init_migrations_table(conn)

        # Apply each migration in order
        for migration_id, migration_name, _, _ in migrations:
            # Import the migration module
            module_name = f"flask_synapse_token_register.db.schema._{migration_id:03d}_{migration_name}"
            module = importlib.import_module(module_name)

            # Apply the migration
            module.apply_migration(conn)

            # Record the migration
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO migrations (migration_id, applied_at, name) VALUES (?, ?, ?)",
                (migration_id, int(time.time()), module.migration_name),
            )
            conn.commit()

        # Verify final database state
        cursor = conn.cursor()

        # Check all expected tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {table["name"] for table in cursor.fetchall()}
        assert "tokens" in tables
        assert "admin_users" in tables
        assert "app_secrets" in tables
        assert "migrations" in tables

    finally:
        conn.close()
