from unittest.mock import patch


def test_wsgi_module_execution():
    """Test direct module execution via __name__ == '__main__' block in wsgi.py."""
    import os

    from flask_synapse_token_register import wsgi

    # Get the path to the WSGI module file
    wsgi_path = os.path.abspath(wsgi.__file__)

    # Mock the Flask app.run() method
    with patch("flask.Flask.run") as mock_run:
        # Use runpy to execute the module as a script
        import runpy

        # This will run the file as if it was executed directly
        runpy.run_path(wsgi_path, run_name="__main__")

        # Verify app.run() was called
        mock_run.assert_called_once()
