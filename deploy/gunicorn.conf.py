"""gunicorn settings for Neocarbon (container and native installs).

Every value can be overridden with the environment variable named next to it.
"""
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
# Bulk uploads run in a background thread of the worker that received them and report progress
# through files in UPLOAD_JOB_DIR, so any worker can answer a status request.
workers = int(os.environ.get("GUNICORN_WORKERS", "4"))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
# Large exports and report generation can take a while.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "300"))
graceful_timeout = 30
keepalive = 5
# Recycle workers now and then to bound memory growth from report libraries.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "2000"))
max_requests_jitter = 200
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
# Client addresses and the scheme come from nginx through X-Forwarded-*; the app trusts them only
# when TRUSTED_PROXIES is set (werkzeug ProxyFix), so gunicorn itself does not rewrite them.
forwarded_allow_ips = ""
# gunicorn 25+ opens a control socket under the user's home folder, which is read-only for the
# service account; Neocarbon does not use it (older versions ignore this setting).
control_socket_disable = True
