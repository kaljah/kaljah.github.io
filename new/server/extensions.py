import os
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

# Rate limiting extension
# Default to memory:// in dev/test, switch to redis:// via RATELIMIT_STORAGE_URI in multi-worker production
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)
