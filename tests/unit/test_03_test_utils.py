"""Tests for utility functions."""

from flask_synapse_token_register.utils import format_timestamp


def test_format_timestamp_none():
    """Test formatting None timestamp."""
    assert format_timestamp(None) is None


def test_format_timestamp_valid(app):
    """Test formatting valid timestamp with Flask app context."""
    # Test with a known timestamp (2022-01-01 01:00:00 UTC)
    timestamp = 1640995200

    with app.app_context():
        # Test with default UTC timezone
        app.config["timezone"] = "UTC"
        formatted = format_timestamp(timestamp)
        assert "2022-01-01" in formatted
        assert "00:00:00" in formatted

        # Also test with a specific timezone (Berlin is UTC+1)
        app.config["timezone"] = "Europe/Berlin"
        formatted_berlin = format_timestamp(timestamp)
        assert "2022-01-01" in formatted_berlin
        assert "01:00:00" in formatted_berlin
