import sys
import os

# Set testing environment variables before importing app
os.environ.setdefault("FLASK_ENV", "testing")
test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_app.db"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{test_db_path.replace(os.sep, '/')}")
os.environ.setdefault("SEED_ADMIN", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

# Add server directory to sys.path for test discovery
server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

# Add repo root to sys.path
repo_root = os.path.abspath(os.path.join(server_dir, "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import pytest
from extensions import db, limiter
from app import app as flask_app


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def disable_limiter_for_tests():
    """Ensure Flask-Limiter does not throttle endpoints during tests."""
    prev = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prev


@pytest.fixture
def app():
    return flask_app


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c
