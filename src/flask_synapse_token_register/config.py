"""Configuration handling."""

import json
import os

DEFAULT_CONFIG = {
    "register_url_prefix": "/register",
    "url_scheme": "https",
    "timezone": "UTC",
    "site_name": "Matrix Server",
    "og": {},
    "og_static_dir": None,
    "db_path": "flask-synapse-token-register.db",
}


def load_config(config_path=None):
    """Load configuration from file."""
    if config_path is None:
        # Default to config.json in current directory
        config_path = os.path.join(os.getcwd(), "config.json")

    # If config doesn't exist, check in default locations
    if not os.path.exists(config_path):
        possible_paths = [
            os.path.join(os.getcwd(), "config.json"),
            os.path.expanduser("~/.config/flask-synapse-token-register/config.json"),
            "/etc/flask-synapse-token-register/config.json",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break

    config = DEFAULT_CONFIG.copy()

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as config_file:
            config.update(json.load(config_file))

    # If db_path isn't absolute, make it relative to current working directory
    if config["db_path"] and not os.path.isabs(config["db_path"]):
        config["db_path"] = os.path.join(os.getcwd(), config["db_path"])

    return config
