"""Database migration system for the registration page."""

import importlib
import os
import re
import sys
import time

from flask_synapse_token_register.db.connection import get_db_connection


def get_migration_files():
    """Get all migration files in order."""
    migration_pattern = re.compile(r"^_(\d{3})_([a-z0-9_]+)\.py$")
    migrations = []

    # Get the schema directory
    schema_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema")

    # Find all python files matching our pattern
    for filename in os.listdir(schema_dir):
        match = migration_pattern.match(filename)
        if match and filename != "__init__.py":
            number = int(match.group(1))
            name = match.group(2)
            module_path = f"flask_synapse_token_register.db.schema.{os.path.splitext(filename)[0]}"
            file_path = os.path.join(schema_dir, filename)
            migrations.append((number, name, module_path, file_path))

    # Sort by migration number
    migrations.sort()
    return migrations


def init_migrations_table(conn):
    """Initialize the migrations tracking table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS migrations (
        id INTEGER PRIMARY KEY,
        migration_id INTEGER UNIQUE NOT NULL,
        applied_at INTEGER NOT NULL,
        name TEXT NOT NULL
    )
    """
    )
    conn.commit()


def get_applied_migrations(conn):
    """Get a set of migration IDs that have already been applied."""
    cursor = conn.cursor()
    cursor.execute("SELECT migration_id FROM migrations ORDER BY migration_id")
    return {row["migration_id"] for row in cursor.fetchall()}


def apply_migration(conn, migration_id, migration_name, module_path):
    """Apply a single migration module to the database."""
    try:
        # Import the migration module
        module = importlib.import_module(module_path)
        display_name = getattr(module, "migration_name", migration_name)

        print(f"Applying migration {migration_id:03d}: {display_name}")

        # Execute the migration function
        module.apply_migration(conn)

        # Record that this migration has been applied
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO migrations (migration_id, applied_at, name) VALUES (?, ?, ?)",
            (migration_id, int(time.time()), display_name),
        )
        conn.commit()
        print(f"Migration {migration_id:03d} applied successfully.")
        return True
    except Exception as e:  # pylint: disable=broad-except
        if hasattr(conn, "rollback"):
            conn.rollback()
        print(f"Error applying migration {migration_id:03d}: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_migrations():
    """Run all pending migrations in order."""
    conn = get_db_connection()
    init_migrations_table(conn)

    # Get set of migrations that have already been applied
    applied = get_applied_migrations(conn)

    # Get all migration files
    migrations = get_migration_files()

    # Apply any migrations that haven't been applied yet
    for migration_id, migration_name, module_path, _ in migrations:
        if migration_id not in applied:
            if not apply_migration(conn, migration_id, migration_name, module_path):
                print("Migration failed, aborting.")
                conn.close()
                sys.exit(1)

    conn.close()
    print("All migrations applied successfully.")
