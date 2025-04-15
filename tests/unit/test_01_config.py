"""Tests for configuration handling."""

import json
import os
import tempfile
from unittest.mock import patch

from flask_synapse_token_register.config import load_config


def test_load_config_default():
    """Test loading default configuration."""
    # Test with non-existent path, should use defaults
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_path = os.path.join(temp_dir, "does_not_exist.json")

        # Make sure no config files exist in standard locations either
        with patch("os.path.exists", return_value=False):
            config = load_config(non_existent_path)

        # Check default values are used
        assert config["register_url_prefix"] == "/register"
        assert config["site_name"] == "Matrix Server"
        # Default db_path should be converted to absolute path
        assert os.path.isabs(config["db_path"])
        assert config["db_path"].endswith("flask-synapse-token-register.db")


def test_load_config_from_fallback_paths():
    """Test loading configuration from fallback paths."""
    # Create a test config file
    test_config = {
        "site_name": "Fallback Config Test",
        "matrix_url": "fallback.example.com",
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a non-existent primary config path
        non_existent_path = os.path.join(temp_dir, "does_not_exist.json")

        # Create a fallback config file in the current directory
        fallback_path = os.path.join(os.getcwd(), "config.json")

        # Patch the exists check to return True only for our fallback path
        def mock_exists(path):
            return path == fallback_path

        # Patch open to return our test config when the fallback path is opened
        def mock_open(*args, **kwargs):
            if args[0] == fallback_path:
                file_mock = tempfile.TemporaryFile(mode="w+")
                json.dump(test_config, file_mock)
                file_mock.seek(0)
                return file_mock
            return open(*args, **kwargs, encoding="utf-8")  # pragma: no cover

        # Apply our patches
        with patch("os.path.exists", side_effect=mock_exists), patch(
            "builtins.open", side_effect=mock_open
        ):
            config = load_config(non_existent_path)

            # Check our fallback config was used
            assert config["site_name"] == "Fallback Config Test"
            assert config["matrix_url"] == "fallback.example.com"
            # Default values should still be present
            assert config["register_url_prefix"] == "/register"


def test_load_config_home_directory_fallback():
    """Test loading configuration from ~/.config directory."""
    # Create a test config
    test_config = {"site_name": "Home Config Test", "matrix_url": "home.example.com"}

    # Define the home directory path
    home_path = os.path.expanduser("~/.config/flask-synapse-token-register/config.json")

    # Patch exists to return True only for home path
    def mock_exists(path):
        return path == home_path

    # Patch open to return our test config when the home path is opened
    def mock_open(*args, **kwargs):
        if args[0] == home_path:
            file_mock = tempfile.TemporaryFile(mode="w+")
            json.dump(test_config, file_mock)
            file_mock.seek(0)
            return file_mock
        return open(*args, **kwargs, encoding="utf-8")  # pragma: no cover

    # Apply our patches
    with patch("os.path.exists", side_effect=mock_exists), patch(
        "builtins.open", side_effect=mock_open
    ):
        config = load_config()

        # Check our home config was used
        assert config["site_name"] == "Home Config Test"
        assert config["matrix_url"] == "home.example.com"


def test_load_config_system_directory_fallback():
    """Test loading configuration from /etc directory."""
    # Create a test config
    test_config = {
        "site_name": "System Config Test",
        "matrix_url": "system.example.com",
    }

    # Define the system directory path
    system_path = "/etc/flask-synapse-token-register/config.json"

    # Patch exists to return True only for system path
    def mock_exists(path):
        return path == system_path

    # Patch open to return our test config when the system path is opened
    def mock_open(*args, **kwargs):
        if args[0] == system_path:
            file_mock = tempfile.TemporaryFile(mode="w+")
            json.dump(test_config, file_mock)
            file_mock.seek(0)
            return file_mock
        return open(*args, **kwargs, encoding="utf-8")  # pragma: no cover

    # Apply our patches
    with patch("os.path.exists", side_effect=mock_exists), patch(
        "builtins.open", side_effect=mock_open
    ):
        config = load_config()

        # Check our system config was used
        assert config["site_name"] == "System Config Test"
        assert config["matrix_url"] == "system.example.com"


def test_relative_db_path():
    """Test that relative db_path is converted to absolute."""
    # Create a test config with relative db_path
    test_config = {"db_path": "relative/path/to/db.sqlite"}

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as temp_file:
        # Write config to temp file
        json.dump(test_config, temp_file)
        temp_file.flush()

        # Load the config
        config = load_config(temp_file.name)

        # Check that db_path was converted to absolute
        assert os.path.isabs(config["db_path"])
        assert config["db_path"].endswith("relative/path/to/db.sqlite")
        assert os.getcwd() in config["db_path"]


def test_none_db_path():
    """Test handling of None db_path."""
    # Create a test config with db_path set to None
    test_config = {"db_path": None}

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as temp_file:
        # Write config to temp file
        json.dump(test_config, temp_file)
        temp_file.flush()

        # Load the config
        config = load_config(temp_file.name)

        # Check that db_path is still None
        assert config["db_path"] is None


def test_absolute_db_path():
    """Test that absolute db_path remains unchanged."""
    # Create absolute path
    absolute_path = os.path.abspath("/tmp/absolute_db_path.sqlite")

    # Create a test config with absolute db_path
    test_config = {"db_path": absolute_path}

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as temp_file:
        # Write config to temp file
        json.dump(test_config, temp_file)
        temp_file.flush()

        # Load the config
        config = load_config(temp_file.name)

        # Check that db_path remains unchanged
        assert config["db_path"] == absolute_path
