"""Tests for database migration functions."""

from unittest.mock import MagicMock, patch

from flask_synapse_token_register.db.migration import (
    apply_migration,
    get_applied_migrations,
    get_migration_files,
    init_migrations_table,
    run_migrations,
)


def test_get_migration_files():
    """Test retrieving migration files."""
    # Mock the os.listdir to return some fake migration files
    mock_files = [
        "_001_initial_schema.py",
        "_002_add_tokens_table.py",
        "_003_add_admin_users.py",
        "__init__.py",  # Should be ignored
        "not_a_migration.py",  # Should be ignored
    ]

    with patch("os.listdir", return_value=mock_files), patch(
        "os.path.dirname", return_value="/fake/path"
    ), patch("os.path.abspath", return_value="/fake/path/module.py"):
        migrations = get_migration_files()

        # Should have 3 migrations
        assert len(migrations) == 3

        # Check sorting and extraction
        assert migrations[0][0] == 1  # First migration number
        assert migrations[0][1] == "initial_schema"  # First migration name
        assert migrations[1][0] == 2  # Second migration number
        assert migrations[2][0] == 3  # Third migration number


def test_init_migrations_table():
    """Test initializing migration table."""
    # Mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Call the function
    init_migrations_table(mock_conn)

    # Verify correct SQL was executed
    mock_cursor.execute.assert_called_once()
    sql = mock_cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS migrations" in sql
    assert "migration_id INTEGER UNIQUE NOT NULL" in sql
    mock_conn.commit.assert_called_once()


def test_get_applied_migrations():
    """Test getting already applied migrations."""
    # Mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock fetchall to return some applied migrations
    mock_cursor.fetchall.return_value = [
        {"migration_id": 1},
        {"migration_id": 2},
    ]

    # Get applied migrations
    applied = get_applied_migrations(mock_conn)

    # Verify result
    assert applied == {1, 2}
    mock_cursor.execute.assert_called_once_with(
        "SELECT migration_id FROM migrations ORDER BY migration_id"
    )


def test_apply_migration_success():
    """Test successful application of a migration."""
    # Mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Create a mock migration module
    mock_module = MagicMock()
    mock_module.migration_name = "Test Migration"
    mock_module.apply_migration = MagicMock()

    # Mock importlib.import_module to return our mock module
    with patch("importlib.import_module", return_value=mock_module):
        # Apply the migration
        result = apply_migration(mock_conn, 5, "test_migration", "fake.module.path")

        # Verify success
        assert result is True
        mock_module.apply_migration.assert_called_once_with(mock_conn)
        mock_cursor.execute.assert_called_once()

        # Check SQL and parameter structure but not exact timestamp value
        assert "INSERT INTO migrations" in mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        assert params[0] == 5  # migration_id
        assert isinstance(params[1], (int, float))  # timestamp is a number
        assert params[2] == "Test Migration"  # name

        mock_conn.commit.assert_called_once()


def test_apply_migration_failure():
    """Test handling of migration failure."""
    # Mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Create a mock module that raises an exception
    mock_module = MagicMock()
    mock_module.apply_migration = MagicMock(side_effect=Exception("Migration failed"))

    # Mock print to suppress output
    with patch("importlib.import_module", return_value=mock_module), patch(
        "builtins.print"
    ), patch("traceback.print_exc"):
        # Apply the migration
        result = apply_migration(mock_conn, 5, "test_migration", "fake.module.path")

        # Verify failure
        assert result is False
        mock_conn.rollback.assert_called_once()
        # Verify the migration wasn't recorded
        assert not mock_cursor.execute.called


def test_run_migrations():
    """Test the complete migration process."""
    # Mock dependencies
    mock_conn = MagicMock()

    # Mock the list of available migrations
    mock_migrations = [
        (1, "first_migration", "module.path.001", "/path/to/001_first_migration.py"),
        (2, "second_migration", "module.path.002", "/path/to/002_second_migration.py"),
        (3, "third_migration", "module.path.003", "/path/to/003_third_migration.py"),
    ]

    # Mock applied migrations (only the first is already applied)
    mock_applied = {1}

    with patch(
        "flask_synapse_token_register.db.migration.get_db_connection",
        return_value=mock_conn,
    ), patch(
        "flask_synapse_token_register.db.migration.init_migrations_table"
    ) as mock_init, patch(
        "flask_synapse_token_register.db.migration.get_applied_migrations",
        return_value=mock_applied,
    ) as mock_get_applied, patch(
        "flask_synapse_token_register.db.migration.get_migration_files",
        return_value=mock_migrations,
    ) as mock_get_files, patch(
        "flask_synapse_token_register.db.migration.apply_migration", return_value=True
    ) as mock_apply, patch("builtins.print"):
        # Run migrations
        run_migrations()

        # Verify the right methods were called in sequence
        mock_init.assert_called_once_with(mock_conn)
        mock_get_applied.assert_called_once_with(mock_conn)
        mock_get_files.assert_called_once()

        # Verify only migrations 2 and 3 were applied (1 was already applied)
        assert mock_apply.call_count == 2
        mock_apply.assert_any_call(mock_conn, 2, "second_migration", "module.path.002")
        mock_apply.assert_any_call(mock_conn, 3, "third_migration", "module.path.003")

        # Verify connection was closed
        mock_conn.close.assert_called_once()


def test_run_migrations_with_failure():
    """Test migration process with a failing migration."""
    # Mock dependencies
    mock_conn = MagicMock()

    # Mock the list of available migrations
    mock_migrations = [
        (1, "first_migration", "module.path.001", "/path/to/001_first_migration.py"),
        (
            2,
            "failing_migration",
            "module.path.002",
            "/path/to/002_failing_migration.py",
        ),
    ]

    # No applied migrations yet
    mock_applied = set()

    with patch(
        "flask_synapse_token_register.db.migration.get_db_connection",
        return_value=mock_conn,
    ), patch("flask_synapse_token_register.db.migration.init_migrations_table"), patch(
        "flask_synapse_token_register.db.migration.get_applied_migrations",
        return_value=mock_applied,
    ), patch(
        "flask_synapse_token_register.db.migration.get_migration_files",
        return_value=mock_migrations,
    ), patch(
        "flask_synapse_token_register.db.migration.apply_migration"
    ) as mock_apply, patch("builtins.print"), patch("sys.exit") as mock_exit:
        # Make the first migration succeed, but the second fail
        mock_apply.side_effect = [True, False]

        # Run migrations
        run_migrations()

        # Verify we attempted both migrations
        assert mock_apply.call_count == 2

        # Verify we exited after the failure
        mock_exit.assert_called_once_with(1)
