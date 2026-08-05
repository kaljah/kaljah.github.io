from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# SEC-08 FIX: replace in-memory rate limiter dict with flask-limiter
# Change storage_uri to "redis://localhost:6379/0" for multi-worker production
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://"  # Switch to redis:// for multi-worker production
)
