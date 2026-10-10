"""LOG_FILE: where app.py writes its rotating warning log (deployment package, 2026-10-10).

A native install keeps the code folder read-only for the service account, so an unwritable log
path must not stop the app; an empty LOG_FILE keeps logs on the console. Each case imports app.py
in a fresh subprocess against its own SQLite file (development mode migrates it on import).
"""
import os
import subprocess
import sys

SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_PROBE = (
    "import dotenv; dotenv.load_dotenv = lambda *a, **k: False\n"
    "import logging.handlers, app\n"
    "files = [h.baseFilename for h in app.app.logger.handlers\n"
    "         if isinstance(h, logging.handlers.RotatingFileHandler)]\n"
    "print('FILES=' + repr(files))\n"
)


def _import_app(tmp_path, log_file):
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTEST_CURRENT_TEST", "DATABASE_URL", "LOG_FILE", "FLASK_ENV")}
    env.update(FLASK_ENV="testing", DB_TYPE="sqlite", SEED_ADMIN="false",
               DATABASE_URL=f"sqlite:///{tmp_path / 'log_probe.db'}", UPLOAD_JOB_DIR=str(tmp_path / "jobs"))
    if log_file is not None:
        env["LOG_FILE"] = log_file
    return subprocess.run([sys.executable, "-c", _PROBE], cwd=SERVER, env=env,
                          capture_output=True, text=True, timeout=180)


def test_log_file_path_is_used(tmp_path):
    target = tmp_path / "neocarbon.log"
    p = _import_app(tmp_path, str(target))
    assert p.returncode == 0, p.stderr[-2000:]
    assert f"FILES=['{target}']" in p.stdout


def test_empty_log_file_means_console_only(tmp_path):
    p = _import_app(tmp_path, "")
    assert p.returncode == 0, p.stderr[-2000:]
    assert "FILES=[]" in p.stdout


def test_unwritable_log_file_warns_instead_of_failing(tmp_path):
    p = _import_app(tmp_path, str(tmp_path / "missing-folder" / "trace.log"))
    assert p.returncode == 0, p.stderr[-2000:]
    assert "FILES=[]" in p.stdout
    assert "not writable" in p.stderr
