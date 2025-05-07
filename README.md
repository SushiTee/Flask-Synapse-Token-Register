[![CI Status](https://github.com/SushiTee/Flask-Synapse-Token-Register/actions/workflows/python-tests.yml/badge.svg)](https://github.com/SushiTee/Flask-Synapse-Token-Register/actions/workflows/python-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

# Flask Synapse Token Register

A simple Flask web application for creating and managing Synapse/Matrix user accounts through invitation tokens.

## Overview

This application provides a user-friendly web interface for onboarding new users to a Matrix server using invitation tokens. It includes:

- Token-based registration system with one-time use tokens
- Advanced token management interface with filtering and status tracking
- _Strong_ password enforcement and username validation
- Responsive design for desktop and mobile devices
- Session-based admin authentication with secure cookies
- SQLite database for persistent storage
- Success page with helpful information for new users

## Screenshots

![Manage Tokens](/docs/screenshots/manage-tokens.png)
![Registration Form](/docs/screenshots/registration-form.png)
![Success Page](/docs/screenshots/success-page.png)
![Admin Login](/docs/screenshots/admin-login.png)

## Installation

### Prerequisites

- Python 3.8+
- Matrix Synapse server with `register_new_matrix_user` command available
- Web server with uWSGI support (e.g., Nginx) for production
- User with appropriate permissions to run `register_new_matrix_user`

### Setup

The following steps are an example of how to set up the application for the use with Nginx and uWSGI. You can also run the application in development mode using Flask's built-in server, but this is not recommended for production.

1. Install the application:
   ```bash
   git clone https://github.com/SushiTee/Flask-Synapse-Token-Register.git
   cd flask-synapse-token-register
   pip install .
   ```

   Alternatively install it directly using `pip`:
   ```bash
   pip install git+https://github.com/SushiTee/Flask-Synapse-Token-Register.git
   ```

2. Create a configuration file:
   ```bash
   cp config.json.example config.json
   ```

3. Edit the configuration file with your settings:
   
   If you use a relative path for `db_path`, the database will be stored in the working directory.

4. Set appropriate file permissions:

   Figure out which user shell run the application and set the permissions accordingly. It must have access to the command `register_new_matrix_user`.

5. Configure uWSGI:

   Make sure the webserver and the application have access to the socket.

   ```ini
   [uwsgi]
   module = flask_synapse_token_register.wsgi:app
   master = true
   processes = 4
   socket = <path_to_your_socket>/register-uwsgi.sock
   chmod-socket = 660
   vacuum = true
   die-on-term = true

   virtualenv = <path_to_your_virtualenv>
   chdir = <path_to_where_you_want_to_run_the_app>
   ```

6. Configure your Nginx web server:

   This is an example for running the application at the location `/register`:

   ```nginx
   location /register {
       rewrite ^/register$ /register/ permanent;
       rewrite ^/register/(.*) /$1 break;

       include uwsgi_params;
       uwsgi_param SCRIPT_NAME /register;
       uwsgi_pass unix:/run/synapse/register-uwsgi.sock;
   }
   ```

7. Initialize the database:
   ```bash
   flask-synapse-register init-db
   ```

8. Create an admin user:
   ```bash
   flask-synapse-register add-admin your_username
   # You'll be prompted to enter and confirm a password
   ```

9. Setup systemd service:

   If you want to run the application as a systemd service, you can use this example service file. Make sure to adjust the paths accordingly.

   ```ini
   [Unit]
   Description=uWSGI instance for Matrix register page
   After=network.target

   [Service]
   ExecStart=<path_to_your_virtualenv>/bin/uwsgi --ini <path_to_wsgi>/wsgi.ini
   Restart=always
   User=<your_user>
   Group=<your_group>
   WorkingDirectory=<path_to_where_you_want_to_run_the_app>

   [Install]
   WantedBy=multi-user.target
   ```

   Move the service file to `/etc/systemd/system/` and enable it:

   ```bash
   systemctl enable --now flask-synapse-register
   ```

## Usage

The usage of the website is straightforward. The next sections will describe the usage of the CLI commands and the configuration options.

### CLI Commands

The application provides a comprehensive command-line interface for management tasks:

```bash
# Run the development server
flask-synapse-register run [--host 127.0.0.1] [--port 5000] [--debug] [--config PATH]

# Initialize the database
flask-synapse-register init-db [--config PATH]

# Add an admin user
flask-synapse-register add-admin <username> [--config PATH]

# List all admin users
flask-synapse-register list-admins [--config PATH]

# Remove an admin user
flask-synapse-register remove-admin <username> [--yes] [--config PATH]

# Show current configuration
flask-synapse-register show-config [--config PATH]
```

**Command Details:**

- **`run`**: Start the development server
  - `--host`: Host address to bind to (default: 127.0.0.1)
  - `--port`: Port number to use (default: 5000)
  - `--debug`: Enable Flask debug mode
  - `--config`: Path to a custom configuration file

- **`init-db`**: Initialize the database and run migrations
  - `--config`: Path to a custom configuration file
  - Automatically generates a secure secret key

- **`add-admin`**: Create a new administrator user
  - `<username>`: Required username for the new admin
  - Will prompt securely for a password
  - `--config`: Path to a custom configuration file

- **`list-admins`**: Display all admin users
  - Shows usernames, creation dates, and last login times
  - `--config`: Path to a custom configuration file

- **`remove-admin`**: Delete an administrator account
  - `<username>`: Required username to remove
  - `--yes`: Skip confirmation prompt
  - `--config`: Path to a custom configuration file

- **`show-config`**: Display the current configuration
  - `--config`: Path to a custom configuration file to display

## Configuration Options

In the config.json file:

- `register_url_prefix`: URL prefix for the application (default: "/register"). You may set it to an empty string to run the application at the root URL.
- `url_scheme`: URL scheme for generated links (default: "https") 
- `site_name`: Name displayed in templates and page titles
- `matrix_url`: The Matrix server domain
- `db_path`: Path to SQLite database file. A relative path will be relative to the working directory. The default is `./flask-synapse-token-register.db`.
- `og_static_dir`: Directory for Open Graph images. If not set, the default static directory will be used. It is only used to server a custom image for Open Graph.
- `og`: Open Graph metadata for social media sharing
    - `title`: Title for Open Graph
    - `description`: Description for Open Graph
    - `image_name`: Image name for Open Graph
    - `image_width`: Width of the image for Open Graph
    - `image_height`: Height of the image for Open Graph
    - `url`: URL for Open Graph
- `register_cmd`: Command to register new users. The default is `register_new_matrix_user --no-admin -c /etc/synapse/homeserver.yaml -u {username} -p {password} http://127.0.0.1:8008`. The `{username}` and `{password}` placeholders will be replaced with the actual username and password. If your synapse server is running the _Matrix Authentication Service_ (MAS), you can use the command may look like this: `mas-cli manage register-user --config <path to MAS config.yaml> --ignore-password-complexity --username {username} --password {password} --no-admin --yes`
- `TESTING`: Set to `true` to enable testing mode. This will disable running the actual register command. This means the register form will redirect to the success page without actually creating a user on the Matrix server.

## Testing

This project uses `pytest` for testing. To run the tests:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage report
pytest --cov=flask_synapse_token_register --cov-report=term-missing

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/functional/
```

The tests are organized into:

- **Unit tests**: Tests for individual components and functions.
- **Integration tests**: Tests that check the interaction between components.
- **Functional tests**: Tests that check the overall functionality of the application.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
