"""UTC timezone enforcement.

This module sets the TZ environment variable to UTC to ensure
consistent datetime behavior across all environments.
"""

import os

# Set UTC timezone for the entire application
os.environ["TZ"] = "UTC"
