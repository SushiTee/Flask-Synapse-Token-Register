"""Validation utilities for user input."""

import re


def is_strong_password(password):
    """Check if the password is strong: at least 8 characters,
    one number, and one special character."""
    if len(password) < 8:
        return False
    if not re.search(r"\d", password):  # Check for at least one digit
        return False
    if not re.search(
        r"[-_!@#$%^&*(),.?\":{}|<>\[\]+]", password
    ):  # Check for special character
        return False
    return True


def validate_username(username):
    """Validate a Matrix username.

    - Must be between 1-255 characters
    - Must contain only a-z, 0-9, -, _, =, ., /
    """
    if not username or len(username) > 255:
        return False

    # Matrix usernames can only contain certain characters
    return bool(re.match(r"^[a-z0-9\-_.=/]+$", username))
