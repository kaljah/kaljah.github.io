import sys
import os

# Add server directory to sys.path for test discovery
server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

import pytest
from extensions import limiter


@pytest.fixture(autouse=True)
def disable_limiter_for_tests():
    """Ensure Flask-Limiter does not throttle authentication endpoints across large test suites."""
    prev = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prev

