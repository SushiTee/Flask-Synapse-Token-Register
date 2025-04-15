"""Command-line interface for the application."""

import sys
import time

import click

from flask_synapse_token_register.app import create_app
from flask_synapse_token_register.db.admin import (
    create_admin_user,
    delete_admin_user,
    list_admin_users,
)
from flask_synapse_token_register.db.migration import run_migrations
from flask_synapse_token_register.db.secrets import generate_secret_key


@click.group()
def cli():
    """Flask Synapse Token Register CLI."""
    pass  # pylint: disable=unnecessary-pass


@cli.command("run")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=5000, type=int, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--config", help="Path to config file")
def run_command(host, port, debug, config):
    """Run the development server."""
    app = create_app(config)
    app.run(host=host, port=port, debug=debug)


@cli.command("init-db")
@click.option("--config", help="Path to config file")
def init_db_command(config):
    """Initialize the database."""
    print("Starting database initialization...")

    # Create app to ensure config is loaded
    app = create_app(config)

    # Show which database we're using
    db_path = app.config.get("db_path", "flask-synapse-token-register.db")
    print(f"Using database: {db_path}")

    # Run migrations
    with app.app_context():
        run_migrations()

        # Generate a secret key
        generate_secret_key()
        print("Secret key generated and stored in the database.")

    print("Database initialization complete. You can now run the application.")


@cli.command("add-admin")
@click.argument("username")
@click.option("--config", help="Path to config file")
def add_admin_command(username, config):
    """Add a new admin user."""
    try:
        # Securely prompt for password
        password = click.prompt(
            "Enter password", hide_input=True, confirmation_prompt=True
        )

        # Create app to ensure config is loaded and database is accessible
        app = create_app(config)

        with app.app_context():
            create_admin_user(username, password)

        print(f"Admin user '{username}' created successfully.")
    except click.Abort:
        print("Operation cancelled.")
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error adding admin user: {e}")
        sys.exit(1)


@cli.command("list-admins")
@click.option("--config", help="Path to config file")
def list_admins_command(config):
    """List all admin users."""
    try:
        # Create app to ensure config is loaded and database is accessible
        app = create_app(config)

        with app.app_context():
            users = list_admin_users()

        if not users:
            print("No admin users found.")
            return

        print(f"Found {len(users)} admin users:")
        for user in users:
            last_login = (
                "Never" if not user["last_login"] else time.ctime(user["last_login"])
            )
            print(
                f"- {user['username']} (created: {time.ctime(user['created_at'])}, last login: {last_login})"
            )

    except Exception as e:  # pylint: disable=broad-except
        print(f"Error listing admin users: {e}")
        sys.exit(1)


@cli.command("remove-admin")
@click.argument("username")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.option("--config", help="Path to config file")
def remove_admin_command(username, yes, config):
    """Remove an admin user."""
    try:
        # Create app to ensure config is loaded and database is accessible
        app = create_app(config)

        if not yes:
            confirm = click.confirm(
                f"Are you sure you want to delete admin user '{username}'?"
            )
            if not confirm:
                print("Operation cancelled.")
                return

        with app.app_context():
            success = delete_admin_user(username)

        if success:
            print(f"Admin user '{username}' removed successfully.")
        else:
            print(f"Admin user '{username}' not found.")
            sys.exit(1)

    except Exception as e:  # pylint: disable=broad-except
        print(f"Error removing admin user: {e}")
        sys.exit(1)


@cli.command("show-config")
@click.option("--config", help="Path to config file")
def show_config_command(config):
    """Show the current configuration."""
    app = create_app(config)

    # Print out configuration values (excluding any sensitive data)
    print("Current configuration:")
    print(f"  Database path:       {app.config.get('db_path')}")
    print(f"  Register URL prefix: {app.config.get('register_url_prefix')}")
    print(f"  URL scheme:          {app.config.get('url_scheme')}")
    print(f"  Site name:           {app.config.get('site_name')}")
    print(f"  Matrix URL:          {app.config.get('matrix_url')}")
    og_config = app.config.get("og", {})
    print("  Open Graph:")
    for key, value in og_config.items():
        print(f"    - {key}: {value}")


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:  # pylint: disable=broad-except
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()  # pragma: no cover
