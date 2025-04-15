"""Tests for validation functions."""

import pytest

from flask_synapse_token_register.validation import (
    is_strong_password,
    validate_username,
)


def test_strong_password_validation():
    """Test password strength validation."""
    # Too short
    assert not is_strong_password("Abc123!")

    # No digits
    assert not is_strong_password("Abcdefgh!")

    # No special characters
    assert not is_strong_password("Abcdefg123")

    # Valid passwords
    assert is_strong_password("Abcdef123!")
    assert is_strong_password("SuperSecure123@")
    assert is_strong_password("another-valid.pass123")


@pytest.mark.parametrize(
    "username,is_valid",
    [
        ("", False),  # Empty
        ("User Name", False),  # Spaces
        ("USER", False),  # Uppercase
        ("user@domain", False),  # @ symbol
        ("user123", True),
        ("test_user", True),
        ("user-name", True),
        ("user.name", True),
        ("user=name", True),
        ("user/name", True),
    ],
)
def test_username_validation(username, is_valid):
    """Test username validation."""
    assert validate_username(username) == is_valid
