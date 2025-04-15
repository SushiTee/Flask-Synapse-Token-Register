"""Functional tests for admin actions."""

from flask_synapse_token_register.db.connection import (
    get_db_connection,
)
from flask_synapse_token_register.db.tokens import (
    mark_token_used,
    save_token,
    token_exists,
)


def test_generate_token(client, auth):
    """Test token generation functionality."""
    # Login
    auth.login()

    # Generate a new token
    response = client.post(
        "/manage-tokens", data={"action": "generate"}, follow_redirects=True
    )

    # Should show success message
    assert response.status_code == 200
    assert b"New token generated successfully" in response.data
    assert b"Registration Link" in response.data


def test_delete_token(client, auth, app, generate_token):
    """Test token deletion."""
    # Login
    auth.login()

    # Get token ID
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT id FROM tokens WHERE token = ?", (generate_token,)
        )
        token_id = cursor.fetchone()["id"]

    # Delete the token
    response = client.post(
        "/manage-tokens",
        data={"action": "delete", "token_id": token_id},
        follow_redirects=True,
    )

    # Should show success message
    assert response.status_code == 200
    assert b"Token deleted successfully" in response.data

    # Verify token is gone
    with app.app_context():
        assert not token_exists(generate_token)


def test_filter_tokens(client, auth, app):
    """Test token filtering functionality."""
    # Login
    auth.login()

    # Add some tokens with very distinct names
    with app.app_context():
        save_token("abc_unused_token_xyz", used=False)
        save_token("123_used_token_789", used=False)
        mark_token_used("123_used_token_789", username="someuser")

    # Test unused filter
    response = client.get("/manage-tokens?filter=unused")
    assert response.status_code == 200
    assert b"abc_unused_token_xyz" in response.data
    assert b"123_used_token_789" not in response.data

    # Test used filter
    response = client.get("/manage-tokens?filter=used")
    assert response.status_code == 200
    assert b"123_used_token_789" in response.data
    assert b"abc_unused_token_xyz" not in response.data

    # Test all filter
    response = client.get("/manage-tokens?filter=all")
    assert response.status_code == 200
    assert b"abc_unused_token_xyz" in response.data
    assert b"123_used_token_789" in response.data
