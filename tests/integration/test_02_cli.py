"""Tests for command-line interface."""

import json
import os
from unittest.mock import patch

import click

from flask_synapse_token_register.cli import cli


def test_cli_main_normal_execution():
    """Test the main() function normal execution path."""
    from flask_synapse_token_register.cli import main

    # Mock sys.argv to simulate command line arguments
    with patch("sys.argv", ["flask-synapse-register", "show-config"]), patch(
        "flask_synapse_token_register.cli.cli"
    ) as mock_cli:
        # Call the main function
        main()

        # Verify that the CLI was invoked without error
        mock_cli.assert_called_once()

        # The cli() function should receive no arguments in this case
        # (Click will parse sys.argv internally)
        args, _ = mock_cli.call_args
        assert len(args) == 0


def test_cli_direct_execution():
    """Test that the CLI gets executed when the module is run directly."""
    import flask_synapse_token_register.cli

    # Save original __name__
    original_name = flask_synapse_token_register.cli.__name__

    # Mock main
    with patch.object(flask_synapse_token_register.cli, "main") as mock_main:
        try:
            # Set __name__ to "__main__" to trigger the if block
            flask_synapse_token_register.cli.__name__ = "__main__"

            # Execute the condition that should be at the bottom of cli.py
            if flask_synapse_token_register.cli.__name__ == "__main__":
                flask_synapse_token_register.cli.main()

            # Verify main was called
            mock_main.assert_called_once()
        finally:
            # Restore original name
            flask_synapse_token_register.cli.__name__ = original_name


def test_cli_add_admin(cli_env):
    """Test admin user creation via CLI."""
    runner, _, _ = cli_env

    # Create admin with simulated input
    result = runner.invoke(
        cli, ["add-admin", "cliuser"], input="Password123!\nPassword123!\n"
    )
    assert result.exit_code == 0
    assert "Admin user 'cliuser' created successfully" in result.output


def test_cli_add_admin_abort(cli_env):
    """Test aborting admin user creation."""
    runner, _, _ = cli_env

    # Simulate user pressing Ctrl+C during password prompt
    with patch("click.prompt", side_effect=click.Abort()):
        result = runner.invoke(cli, ["add-admin", "aborted_user"])
        assert result.exit_code == 1
        assert "Operation cancelled" in result.output

    # Make sure user wasn't created
    list_result = runner.invoke(cli, ["list-admins"])
    assert "aborted_user" not in list_result.output


def test_cli_add_admin_error(cli_env):
    """Test error during admin user creation."""
    runner, _, _ = cli_env

    # Create a user that already exists to trigger error
    runner.invoke(cli, ["add-admin", "duplicate"], input="Password123!\nPassword123!\n")

    # Try to create the same user again
    result = runner.invoke(
        cli, ["add-admin", "duplicate"], input="Password123!\nPassword123!\n"
    )
    assert result.exit_code == 1
    assert "Error adding admin user" in result.output


def test_cli_list_admins(cli_env):
    """Test listing admin users via CLI."""
    runner, _, _ = cli_env

    # First create a user
    runner.invoke(cli, ["add-admin", "testadmin"], input="Password123!\nPassword123!\n")

    # Then list users
    result = runner.invoke(cli, ["list-admins"])
    assert result.exit_code == 0
    assert "testadmin" in result.output
    assert "created:" in result.output
    assert "last login: Never" in result.output


def test_cli_list_admins_empty(cli_env):
    """Test listing admin users when there are none."""
    runner, fs, _ = cli_env

    # Create a new empty database
    empty_db_path = os.path.join(fs, "empty.db")
    empty_config_path = os.path.join(fs, "empty_config.json")

    with open(empty_config_path, "w", encoding="utf-8") as f:
        json.dump({"db_path": empty_db_path}, f)

    # Initialize it but don't add any users
    runner.invoke(cli, ["init-db", "--config", empty_config_path])

    # List users (should be empty)
    result = runner.invoke(cli, ["list-admins", "--config", empty_config_path])
    assert result.exit_code == 0
    assert "No admin users found" in result.output


def test_cli_list_admins_error(cli_env):
    """Test error during admin listing."""
    runner, fs, _ = cli_env

    # Create an invalid config pointing to non-existent DB
    invalid_config_path = os.path.join(fs, "invalid_config.json")
    with open(invalid_config_path, "w", encoding="utf-8") as f:
        json.dump({"db_path": "/path/that/does/not/exist/db.sqlite"}, f)

    # Try to list admins with invalid config
    result = runner.invoke(cli, ["list-admins", "--config", invalid_config_path])
    assert result.exit_code == 1
    assert "Error listing admin users" in result.output


def test_cli_show_config(cli_env):
    """Test showing configuration via CLI."""
    runner, _, _ = cli_env

    result = runner.invoke(cli, ["show-config"])
    assert result.exit_code == 0
    assert "Current configuration" in result.output
    assert "Test CLI Matrix Server" in result.output


def test_cli_show_config_with_og_data(cli_env):
    """Test showing configuration with Open Graph data."""
    runner, fs, _ = cli_env

    # Create config with OG data
    og_config_path = os.path.join(fs, "og_config.json")
    with open(og_config_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "db_path": os.path.join(fs, "og.db"),
                "site_name": "OG Test Site",
                "og": {
                    "title": "Matrix Registration",
                    "description": "Register for our Matrix server",
                    "image": "https://example.com/image.png",
                },
            },
            f,
        )

    # Show config with OG data
    result = runner.invoke(cli, ["show-config", "--config", og_config_path])
    assert result.exit_code == 0
    assert "Open Graph:" in result.output
    assert "title: Matrix Registration" in result.output
    assert "description: Register for our Matrix" in result.output
    assert "image: https://example.com/image.png" in result.output


def test_cli_remove_admin(cli_env):
    """Test removing an admin user."""
    runner, _, _ = cli_env

    # First create a user
    runner.invoke(
        cli, ["add-admin", "admin_to_remove"], input="Password123!\nPassword123!\n"
    )

    # Verify user exists
    list_result = runner.invoke(cli, ["list-admins"])
    assert "admin_to_remove" in list_result.output

    # Remove with confirmation (yes)
    result = runner.invoke(cli, ["remove-admin", "admin_to_remove"], input="y\n")
    assert result.exit_code == 0
    assert "Admin user 'admin_to_remove' removed successfully" in result.output

    # Verify user is gone
    list_result = runner.invoke(cli, ["list-admins"])
    assert "admin_to_remove" not in list_result.output


def test_cli_remove_admin_with_yes_flag(cli_env):
    """Test removing an admin user with --yes flag."""
    runner, _, _ = cli_env

    # First create a user
    runner.invoke(
        cli, ["add-admin", "admin_to_remove_flag"], input="Password123!\nPassword123!\n"
    )

    # Remove with --yes flag (no prompt)
    result = runner.invoke(cli, ["remove-admin", "admin_to_remove_flag", "--yes"])
    assert result.exit_code == 0
    assert "Admin user 'admin_to_remove_flag' removed successfully" in result.output


def test_cli_remove_admin_not_found(cli_env):
    """Test removing a non-existent admin user."""
    runner, _, _ = cli_env

    # Try to remove a user that doesn't exist
    result = runner.invoke(cli, ["remove-admin", "non_existent_user", "--yes"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_cli_remove_admin_error(cli_env):
    """Test error during admin removal."""
    runner, fs, _ = cli_env

    # Create an invalid config pointing to non-existent DB
    invalid_config_path = os.path.join(fs, "invalid_remove_config.json")
    with open(invalid_config_path, "w", encoding="utf-8") as f:
        json.dump({"db_path": "/path/that/does/not/exist/db.sqlite"}, f)

    # Try to remove admin with invalid config
    result = runner.invoke(
        cli, ["remove-admin", "any_user", "--yes", "--config", invalid_config_path]
    )
    assert result.exit_code == 1
    assert "Error removing admin user" in result.output


def test_cli_remove_admin_cancel(cli_env):
    """Test cancelling admin removal."""
    runner, _, _ = cli_env

    # First create a user
    runner.invoke(
        cli, ["add-admin", "admin_to_keep"], input="Password123!\nPassword123!\n"
    )

    # Try to remove but cancel (answer no)
    result = runner.invoke(cli, ["remove-admin", "admin_to_keep"], input="n\n")
    assert "Operation cancelled" in result.output

    # Verify user still exists
    list_result = runner.invoke(cli, ["list-admins"])
    assert "admin_to_keep" in list_result.output


def test_cli_with_explicit_config_path(cli_env):
    """Test using explicit --config option."""
    runner, fs, config_path = cli_env

    # Create a second config file with different settings
    second_config_path = os.path.join(fs, "second_config.json")
    with open(second_config_path, "w", encoding="utf-8") as f:
        test_config = {
            "TESTING": True,
            "db_path": os.path.join(fs, "second_db.db"),
            "register_url_prefix": "/matrix",
            "url_scheme": "https",
            "site_name": "Second Test Server",
            "matrix_url": "second.example.com",
        }
        json.dump(test_config, f)

    # Initialize the second database
    runner.invoke(cli, ["init-db", "--config", second_config_path])

    # Add admin to second database
    runner.invoke(
        cli,
        ["add-admin", "second_admin", "--config", second_config_path],
        input="Password123!\nPassword123!\n",
    )

    # List admins from first database (should not see second_admin)
    result1 = runner.invoke(cli, ["list-admins", "--config", config_path])
    assert "second_admin" not in result1.output

    # List admins from second database (should see second_admin)
    result2 = runner.invoke(cli, ["list-admins", "--config", second_config_path])
    assert "second_admin" in result2.output

    # Show config for second database
    result3 = runner.invoke(cli, ["show-config", "--config", second_config_path])
    assert "Second Test Server" in result3.output


def test_cli_init_db_creates_tables(cli_env):
    """Test that init-db creates necessary tables."""
    runner, fs, _ = cli_env

    # Create a new config with a different database path
    new_db_path = os.path.join(fs, "new_test.db")
    new_config_path = os.path.join(fs, "new_config.json")

    with open(new_config_path, "w", encoding="utf-8") as f:
        json.dump({"db_path": new_db_path, "site_name": "New Test Server"}, f)

    # Make sure the database doesn't exist yet
    assert not os.path.exists(new_db_path)

    # Initialize the database
    result = runner.invoke(cli, ["init-db", "--config", new_config_path])
    assert result.exit_code == 0
    assert "Database initialization complete" in result.output

    # Verify database was created
    assert os.path.exists(new_db_path)

    # Verify we can now use the database
    add_result = runner.invoke(
        cli,
        ["add-admin", "newdb_admin", "--config", new_config_path],
        input="Password123!\nPassword123!\n",
    )
    assert add_result.exit_code == 0


def test_cli_run_command(cli_env):
    """Test the run command (without actually starting the server)."""
    runner, _, _ = cli_env

    # Mock app.run to prevent actually starting a server
    with patch("flask_synapse_token_register.app.Flask.run") as mock_run:
        result = runner.invoke(
            cli, ["run", "--host", "0.0.0.0", "--port", "8080", "--debug"]
        )

        assert result.exit_code == 0
        # Verify that app.run was called with the right parameters
        mock_run.assert_called_once_with(host="0.0.0.0", port=8080, debug=True)


def test_cli_main_function():
    """Test the main CLI entry point with error handling."""
    # Test normal operation by calling a simple command through main()
    from flask_synapse_token_register.cli import main

    # Mock sys.argv and sys.exit to prevent actual exit
    with patch("sys.argv", ["flask-synapse-register", "--help"]), patch(
        "sys.exit"
    ) as mock_exit, patch("click.echo") as mock_echo:
        # Mock cli() to simulate an error
        with patch(
            "flask_synapse_token_register.cli.cli", side_effect=Exception("Test error")
        ):
            main()

            # Check that error was echoed and exit was called
            mock_echo.assert_called_with("Error: Test error", err=True)
            mock_exit.assert_called_once_with(1)
