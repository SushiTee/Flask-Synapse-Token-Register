"""Tests for test mode functionality."""

import logging
from unittest.mock import patch


def test_registration_skips_user_creation_in_test_mode(
    app, client, generate_token, caplog
):
    """Test that user creation is skipped in test mode."""
    caplog.set_level(logging.INFO)

    # Make sure TESTING is True
    assert app.config["TESTING"] is True

    # Mock subprocess to verify it's not called
    with patch("subprocess.run") as mock_run:
        # Submit registration
        response = client.post(
            "/",
            data={
                "token": generate_token,
                "username": "testuser",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            follow_redirects=True,
        )

        # Check success
        assert response.status_code == 200
        assert b"Account Successfully Created" in response.data

        # Verify subprocess was NOT called
        mock_run.assert_not_called()

        # Verify we got the test mode log message
        assert "Test mode: Would have created Matrix user: testuser" in caplog.text
