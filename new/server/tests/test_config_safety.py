"""Production configuration safety (hardening plan, phase 2).

Each case imports ``config`` in a fresh subprocess because ``Config`` reads the environment
once, at class-body time. ``load_dotenv`` is stubbed so a developer's local .env cannot
change the result.
"""
import json
import os
import subprocess
import sys

SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD_SECRET = "regression-test-secret-key-that-is-long-enough-0123456789abcdef"
PG_URL = "postgresql://user:pass@localhost:5432/ghg"

_CLEARED = (
    "FLASK_ENV", "APP_ENV", "ENVIRONMENT", "SECRET_KEY", "DATABASE_URL", "DB_TYPE",
    "ALLOWED_ORIGINS", "CORS_STRICT", "REDIS_URL", "RATELIMIT_REDIS_URL",
    "RATELIMIT_STORAGE_URI", "ALLOW_MEMORY_LIMITER", "ALLOW_SQLITE_IN_PRODUCTION",
    "ALLOW_SQLITE_IN_PROD", "PYTEST_CURRENT_TEST",
)

_PROBE = (
    "import dotenv, json; dotenv.load_dotenv = lambda *a, **k: False\n"
    "from config import Config as C\n"
    "print(json.dumps({'prod': C.IS_PRODUCTION, 'origins': C.ALLOWED_ORIGINS, "
    "'limiter': C.RATELIMIT_STORAGE_URI}))\n"
)


def _load(**env_vars):
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED}
    env.update(env_vars)
    p = subprocess.run([sys.executable, "-c", _PROBE], cwd=SERVER, env=env,
                       capture_output=True, text=True, timeout=120)
    out = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else None
    return p, out


def _prod(**extra):
    base = dict(FLASK_ENV="production", SECRET_KEY=PROD_SECRET, DB_TYPE="postgres",
                DATABASE_URL=PG_URL, REDIS_URL="redis://localhost:6379/0")
    base.update(extra)
    return _load(**base)


# ── environment detection fails closed ──────────────────────────────────────────

def test_unknown_environment_name_is_treated_as_production():
    p, _ = _load(FLASK_ENV="live")
    assert p.returncode != 0
    assert "SECRET_KEY" in p.stderr


def test_known_development_names_are_not_production():
    for name in ("development", "dev", "local", "testing", "test"):
        p, out = _load(FLASK_ENV=name, SECRET_KEY="x" * 32)
        assert p.returncode == 0, (name, p.stderr[-500:])
        assert out["prod"] is False, name


def test_unset_environment_defaults_to_development():
    p, out = _load(SECRET_KEY="x" * 32)
    assert p.returncode == 0, p.stderr[-500:]
    assert out["prod"] is False


def test_development_without_secret_key_warns():
    p, out = _load(FLASK_ENV="development")
    assert p.returncode == 0, p.stderr[-500:]
    assert "SECRET_KEY is not set" in p.stderr


def test_production_rejects_the_dev_secret():
    p, _ = _prod(SECRET_KEY="dev-secret-key-change-in-prod-please")
    assert p.returncode != 0
    assert "SECRET_KEY" in p.stderr


# ── CORS ───────────────────────────────────────────────────────────────────────

def test_production_rejects_wildcard_origin():
    p, _ = _prod(ALLOWED_ORIGINS="*")
    assert p.returncode != 0
    assert "ALLOWED_ORIGINS" in p.stderr


def test_production_rejects_empty_origin_list():
    p, _ = _prod(ALLOWED_ORIGINS=" , ")
    assert p.returncode != 0
    assert "ALLOWED_ORIGINS" in p.stderr


def test_listed_origin_is_used_and_legacy_pages_origin_is_kept_with_warning():
    p, out = _prod(ALLOWED_ORIGINS="https://app.example.com")
    assert p.returncode == 0, p.stderr[-500:]
    assert out["origins"][0] == "https://app.example.com"
    assert "https://kaljah.github.io" in out["origins"]
    assert "CORS_STRICT" in p.stderr


def test_cors_strict_drops_the_legacy_pages_origin():
    p, out = _prod(ALLOWED_ORIGINS="https://app.example.com", CORS_STRICT="true")
    assert p.returncode == 0, p.stderr[-500:]
    assert out["origins"] == ["https://app.example.com"]


def test_cors_strict_keeps_an_explicitly_listed_pages_origin():
    p, out = _prod(ALLOWED_ORIGINS="https://kaljah.github.io", CORS_STRICT="true")
    assert p.returncode == 0, p.stderr[-500:]
    assert out["origins"] == ["https://kaljah.github.io"]


# ── rate-limit storage ─────────────────────────────────────────────────────────

def test_production_without_shared_limiter_store_refuses_to_start():
    p, _ = _prod(REDIS_URL="")
    assert p.returncode != 0
    assert "rate-limit" in p.stderr


def test_production_accepts_redis_for_the_limiter():
    p, out = _prod()
    assert p.returncode == 0, p.stderr[-500:]
    assert out["limiter"].startswith("redis://")


def test_single_worker_production_can_opt_into_memory_limiter():
    p, out = _prod(REDIS_URL="", ALLOW_MEMORY_LIMITER="true")
    assert p.returncode == 0, p.stderr[-500:]
    assert out["limiter"] == "memory://"


def test_development_uses_memory_limiter_without_opt_in():
    p, out = _load(FLASK_ENV="development", SECRET_KEY="x" * 32)
    assert p.returncode == 0, p.stderr[-500:]
    assert out["limiter"] == "memory://"
