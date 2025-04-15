"""Common test fixtures and configuration."""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from flask_synapse_token_register.app import create_app
from flask_synapse_token_register.cli import cli
from flask_synapse_token_register.db.admin import create_admin_user
from flask_synapse_token_register.db.connection import get_db_connection
from flask_synapse_token_register.db.secrets import set_secret


@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()

    # Create a temporary config file for the application
    config_fd, config_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(config_fd, "w") as config_file:
        test_config = {
            "TESTING": True,
            "db_path": db_path,
            "timezone": "UTC",
            "register_url_prefix": "",  # No prefix for tests
            "url_scheme": "http",
            "site_name": "Test Matrix Server",
            "matrix_url": "matrix.example.com",
        }
        json.dump(test_config, config_file)

    # Create the app with the test configuration file
    app_instance = create_app(config_path)

    # Setup the database
    with app_instance.app_context():
        # Create tables
        conn = get_db_connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                used BOOLEAN NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                used_at INTEGER,
                used_by TEXT,
                ip_address TEXT
            );

            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_login INTEGER
            );

            CREATE TABLE IF NOT EXISTS app_secrets (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
        """
        )

        # Add a test secret key
        set_secret("SECRET_KEY", "test_secret_key_for_unit_tests")

        # Create a test admin user
        create_admin_user("testadmin", "Password123!", commit=True)

        conn.commit()
        conn.close()

    # Provide the app for testing
    yield app_instance

    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)
    os.unlink(config_path)  # Clean up the config file too


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a CLI test runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def auth(client):
    """Authentication fixture to log in and out."""

    class AuthActions:
        def login(self, username="testadmin", password="Password123!"):
            response = client.post(
                "/login",
                data={"username": username, "password": password},
                follow_redirects=True,
            )
            return response

        def logout(self):
            return client.get("/logout", follow_redirects=True)

    return AuthActions()


@pytest.fixture
def generate_token(app):
    """Create a test token."""
    with app.app_context():
        token = "test_token_123"
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tokens (token, used, created_at) VALUES (?, ?, ?)",
            (token, 0, 1617293655),  # April 1, 2021
        )
        conn.commit()
        conn.close()
        return token


@pytest.fixture
def cli_env():
    """Create an isolated CLI test environment."""
    runner = CliRunner()

    with runner.isolated_filesystem() as fs:
        # Create a test database and config
        config_path = os.path.join(fs, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            test_config = {
                "TESTING": True,
                "db_path": os.path.join(fs, "test.db"),
                "register_url_prefix": "",
                "url_scheme": "http",
                "site_name": "Test CLI Matrix Server",
                "matrix_url": "matrix.example.com",
            }
            json.dump(test_config, f)

        # Make sure FLASK_CONFIG environment variable points to our config
        os.environ["FLASK_CONFIG"] = config_path

        # Initialize database
        runner.invoke(cli, ["init-db"])

        yield runner, fs, config_path

        # Cleanup environment variable
        if "FLASK_CONFIG" in os.environ:
            del os.environ["FLASK_CONFIG"]
