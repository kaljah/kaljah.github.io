#!/usr/bin/env bash
# Install or upgrade Neocarbon without containers, from an unpacked release bundle.
# Run as root from the bundle folder:   sudo ./native/install.sh
#
# Expects on the server (from the OS packages): Python 3.11 with venv, PostgreSQL 16 client tools
# (pg_dump, psql), nginx, systemd, envsubst (gettext). PostgreSQL 16 and Redis may run on this
# server or elsewhere (DATABASE_URL, REDIS_URL). Nothing is downloaded: Python packages come from
# the bundle's wheels/ folder.
#
# Variables:
#   PYTHON         Python 3.11 interpreter (default: python3.11)
#   SERVER_NAME    host name for the nginx site (asked for when unset)
#   TLS_CERT       certificate chain (default /etc/neocarbon/tls/fullchain.pem)
#   TLS_KEY        private key       (default /etc/neocarbon/tls/privkey.pem)
#   NGINX_SITE     where the nginx site goes (default /etc/nginx/conf.d/neocarbon.conf)
set -euo pipefail

BUNDLE="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3.11}"
PREFIX=/opt/neocarbon
TLS_CERT="${TLS_CERT:-/etc/neocarbon/tls/fullchain.pem}"
TLS_KEY="${TLS_KEY:-/etc/neocarbon/tls/privkey.pem}"
NGINX_SITE="${NGINX_SITE:-/etc/nginx/conf.d/neocarbon.conf}"

[ "$(id -u)" -eq 0 ] || { echo "Run as root." >&2; exit 1; }
for f in "$BUNDLE/server/app.py" "$BUNDLE/spa/index.html" "$BUNDLE/wheels"; do
  [ -e "$f" ] || { echo "Missing $f: run from an unpacked release bundle." >&2; exit 1; }
done
command -v "$PYTHON" >/dev/null || { echo "$PYTHON not found (set PYTHON=...)." >&2; exit 1; }
command -v envsubst >/dev/null || { echo "envsubst not found (package gettext)." >&2; exit 1; }
command -v pg_dump >/dev/null || echo "Warning: pg_dump not found; backups need the PostgreSQL 16 client tools." >&2

echo "== Service account and folders"
id neocarbon >/dev/null 2>&1 || useradd --system --home-dir "$PREFIX" --shell /usr/sbin/nologin neocarbon
install -d -m 0755 "$PREFIX"
install -d -m 0750 -o neocarbon -g neocarbon /var/lib/neocarbon /var/lib/neocarbon/upload_jobs /var/backups/neocarbon
install -d -m 0750 -o root -g neocarbon /etc/neocarbon

echo "== Application files"
was_running=0
systemctl is-active --quiet neocarbon && was_running=1 && systemctl stop neocarbon
rm -rf "$PREFIX/server.new" && cp -r "$BUNDLE/server" "$PREFIX/server.new"
rm -rf "$PREFIX/server.old" && { [ -d "$PREFIX/server" ] && mv "$PREFIX/server" "$PREFIX/server.old" || true; }
mv "$PREFIX/server.new" "$PREFIX/server"
rm -rf "$PREFIX/spa" && cp -r "$BUNDLE/spa" "$PREFIX/spa"
cp "$BUNDLE/native/gunicorn.conf.py" "$PREFIX/gunicorn.conf.py"
chown -R root:root "$PREFIX/server" "$PREFIX/spa"
chmod -R a+rX "$PREFIX/server" "$PREFIX/spa"

echo "== Python environment (offline, from wheels/)"
[ -x "$PREFIX/venv/bin/python" ] || "$PYTHON" -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install --no-index --find-links "$BUNDLE/wheels" -r "$PREFIX/server/requirements.runtime.txt"

echo "== Settings"
if [ ! -f /etc/neocarbon/neocarbon.env ]; then
  install -m 0640 -o root -g neocarbon "$BUNDLE/native/neocarbon.env.example" /etc/neocarbon/neocarbon.env
  echo "Created /etc/neocarbon/neocarbon.env: fill in DATABASE_URL, SECRET_KEY and ALLOWED_ORIGINS, then run this script again."
  exit 0
fi
for key in DATABASE_URL SECRET_KEY ALLOWED_ORIGINS; do
  grep -qE "^$key=.+" /etc/neocarbon/neocarbon.env || { echo "Set $key in /etc/neocarbon/neocarbon.env first." >&2; exit 1; }
done

echo "== systemd units"
install -m 0644 "$BUNDLE/native/neocarbon.service" "$BUNDLE/native/neocarbon-backup.service" \
  "$BUNDLE/native/neocarbon-backup.timer" /etc/systemd/system/
cat > /usr/local/sbin/neocarbon-seed-admin <<'EOF'
#!/bin/sh
# Create the admin and IT admin accounts from ADMIN_* / IT_ADMIN_* in /etc/neocarbon/neocarbon.env
set -a; . /etc/neocarbon/neocarbon.env; set +a
cd /opt/neocarbon/server
runuser -u neocarbon -- /opt/neocarbon/venv/bin/flask db upgrade
exec runuser -u neocarbon -- /opt/neocarbon/venv/bin/python seed_admin.py "$@"
EOF
chmod 0750 /usr/local/sbin/neocarbon-seed-admin
systemctl daemon-reload

echo "== nginx site"
if [ -z "${SERVER_NAME:-}" ]; then read -r -p "Host name users type in the browser: " SERVER_NAME; fi
export SERVER_NAME TLS_CERT TLS_KEY APP_UPSTREAM=127.0.0.1:8000 SPA_ROOT="$PREFIX/spa" \
       CLIENT_MAX_BODY="${CLIENT_MAX_BODY:-55m}" CSP_IMG_SRC_EXTRA="${CSP_IMG_SRC_EXTRA:-}"
envsubst '${SERVER_NAME} ${APP_UPSTREAM} ${SPA_ROOT} ${TLS_CERT} ${TLS_KEY} ${CLIENT_MAX_BODY} ${CSP_IMG_SRC_EXTRA}' \
  < "$BUNDLE/native/neocarbon.conf.template" > "$NGINX_SITE"
# Debian / Ubuntu ship a default site that also takes port 80 (and listens on IPv6).
if [ -L /etc/nginx/sites-enabled/default ]; then
  rm /etc/nginx/sites-enabled/default && echo "Disabled the distribution's default nginx site."
fi
[ -f "$TLS_CERT" ] && [ -f "$TLS_KEY" ] || echo "Warning: put the certificate at $TLS_CERT and the key at $TLS_KEY before reloading nginx." >&2

echo "== Start"
systemctl enable --now neocarbon neocarbon-backup.timer
if nginx -t; then systemctl reload nginx || systemctl start nginx; fi
[ "$was_running" = 1 ] && echo "Upgraded (previous code kept in $PREFIX/server.old)."
systemctl --no-pager status neocarbon | head -5
echo "Done. First install: run neocarbon-seed-admin to create the admin accounts."
