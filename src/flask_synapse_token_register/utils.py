"""Utility functions for the Flask Synapse Token Register."""

from datetime import datetime

import pytz
from flask import current_app


def format_timestamp(timestamp):
    """Format a Unix timestamp into a readable string."""
    if not timestamp:
        return None

    # Get timezone from config or use UTC as default
    timezone_name = current_app.config.get("timezone", "UTC")
    timezone = pytz.timezone(timezone_name)

    # Convert timestamp to datetime in the specified timezone
    dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    localized_dt = dt.astimezone(timezone)

    return localized_dt.strftime("%Y-%m-%d %H:%M:%S")
