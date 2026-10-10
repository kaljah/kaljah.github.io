# Neocarbon images. Build from the repository root:
#   docker build -f deploy/Dockerfile --target app -t neocarbon-app:VERSION .
#   docker build -f deploy/Dockerfile --target web -t neocarbon-web:VERSION .
# deploy/release.sh builds both and packs them for an offline install.
#
# REGISTRY points at the registry holding the official base images (Docker Hub by default; an
# internal mirror works the same way, e.g. --build-arg REGISTRY=registry.example.dz/library).
ARG REGISTRY=docker.io/library

# ---- SPA build -----------------------------------------------------------------------------
FROM ${REGISTRY}/node:20-slim AS spa
WORKDIR /src
COPY new/client/package.json new/client/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY new/client/ ./
# Same origin: the browser calls /api on the address that served the page.
ENV VITE_API_URL=/api VITE_BASE_PATH=/
RUN npm run build

# ---- API (Flask + gunicorn) ----------------------------------------------------------------
FROM ${REGISTRY}/python:3.11-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# PostgreSQL 16 client tools (pg_dump / psql for scripts/backup.py and scripts/restore.py) from the
# PostgreSQL project's repository: Debian's own client is older than the server and pg_dump refuses
# to dump a newer server.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
 && install -d /usr/share/postgresql-common/pgdg \
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
 && . /etc/os-release \
 && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client-16 \
 && apt-get purge -y curl gnupg && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY new/server/requirements.txt ./requirements.txt
# Test-only packages are left out of the runtime image.
RUN grep -viE '^(pytest|pytest-timeout|pytest-benchmark|hypothesis)\b' requirements.txt > requirements.runtime.txt \
 && pip install -r requirements.runtime.txt
COPY new/server/ ./
RUN rm -rf tests instance upload_jobs backups *.db *.db-wal *.db-shm trace.log .hypothesis
COPY deploy/gunicorn.conf.py /etc/neocarbon/gunicorn.conf.py
COPY deploy/entrypoint.sh /usr/local/bin/neocarbon-entrypoint
RUN chmod 0755 /usr/local/bin/neocarbon-entrypoint \
 && useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin neocarbon \
 && install -d -o neocarbon -g neocarbon /data /data/upload_jobs /data/backups \
 && chown -R neocarbon:neocarbon /app
ENV FLASK_ENV=production \
    DB_TYPE=postgres \
    UPLOAD_JOB_DIR=/data/upload_jobs \
    BACKUP_DIR=/data/backups \
    LOG_FILE= \
    MPLCONFIGDIR=/tmp/matplotlib
USER neocarbon
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health/live', timeout=4).status == 200 else 1)"
ENTRYPOINT ["neocarbon-entrypoint"]
CMD ["serve"]

# ---- Web server (nginx: SPA + /api proxy on one address) -----------------------------------
FROM ${REGISTRY}/nginx:1.27-alpine AS web
RUN rm -f /etc/nginx/conf.d/default.conf
COPY deploy/nginx/neocarbon.conf.template /etc/nginx/templates/neocarbon.conf.template
COPY --from=spa /src/dist /usr/share/nginx/html
# Defaults for the template (the compose file sets SERVER_NAME).
ENV SERVER_NAME=localhost \
    APP_UPSTREAM=app:8000 \
    SPA_ROOT=/usr/share/nginx/html \
    TLS_CERT=/etc/nginx/certs/fullchain.pem \
    TLS_KEY=/etc/nginx/certs/privkey.pem \
    CLIENT_MAX_BODY=55m \
    CSP_IMG_SRC_EXTRA=""
EXPOSE 80 443
