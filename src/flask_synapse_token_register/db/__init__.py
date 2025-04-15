"""
Database package for the Synapse registration page.
This module handles all database operations and migrations.

The database package provides:
1. Token management - creation, validation, and tracking
2. Admin user authentication and management
3. Application secrets storage
4. Database migration utilities
"""

# Admin user management
from flask_synapse_token_register.db.admin import (
    create_admin_user,
    delete_admin_user,
    list_admin_users,
    update_last_login,
    verify_admin_credentials,
)
from flask_synapse_token_register.db.connection import (
    get_db_connection,
    get_db_path,
)

# Migration utilities
from flask_synapse_token_register.db.migration import (
    get_migration_files,
    run_migrations,
)

# Application secrets management
from flask_synapse_token_register.db.secrets import (
    generate_secret_key,
    get_secret,
    set_secret,
)
from flask_synapse_token_register.db.tokens import (
    delete_token,
    get_all_tokens,
    get_filtered_tokens,
    get_token_stats,
    get_unused_tokens,
    is_token_used,
    mark_token_used,
    save_token,
    token_exists,
)
from flask_synapse_token_register.utils import format_timestamp

__all__ = [
    # Connection and token functions
    "get_db_connection",
    "get_db_path",
    "save_token",
    "mark_token_used",
    "token_exists",
    "is_token_used",
    "get_unused_tokens",
    "get_token_stats",
    "get_all_tokens",
    "get_filtered_tokens",
    "delete_token",
    # Migration functions
    "run_migrations",
    "get_migration_files",
    # Admin user functions
    "create_admin_user",
    "verify_admin_credentials",
    "update_last_login",
    "list_admin_users",
    "delete_admin_user",
    # Secret functions
    "get_secret",
    "set_secret",
    "generate_secret_key",
]
