#!/usr/bin/env bash
# First install on a Linux server, from an unpacked bundle:  sudo ./deploy/install.sh
# Needs: root, python3 (same minor version as the bundle), systemd, and a reachable PostgreSQL database.
# Does not need the internet. Safe to re-run: it never overwrites /etc/ghg/ghg.env or an existing nginx site.
set -euo pipefail

BUNDLE="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/ghg
DATA=/var/lib/ghg
ETC=/etc/ghg
PYTHON="${PYTHON:-python3}"

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }

want="$(cat "$BUNDLE/PYTHON_VERSION")"
have="$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
[ "$want" = "$have" ] || { echo "The bundle was built for Python $want but $PYTHON is $have. Set PYTHON=/path/to/python$want or ask for a bundle built for $have." >&2; exit 1; }
"$PYTHON" -c 'import venv, ensurepip' 2>/dev/null || { echo "Python venv support is missing (install the python3-venv package)." >&2; exit 1; }

echo "==> Service account and folders"
id ghg >/dev/null 2>&1 || useradd --system --home-dir "$DATA" --shell /usr/sbin/nologin ghg
mkdir -p "$APP" "$DATA/instance" "$DATA/upload_jobs" "$DATA/backups" "$ETC"
chown -R ghg:ghg "$DATA"

echo "==> Files"
rm -rf "$APP/server" "$APP/web.new"
cp -r "$BUNDLE/server" "$APP/server"
cp -r "$BUNDLE/web" "$APP/web.new"
rm -rf "$APP/web" && mv "$APP/web.new" "$APP/web"
cp "$BUNDLE/VERSION" "$APP/VERSION"
# Writable folders live in /var/lib/ghg so the code folder can stay read-only.
rm -rf "$APP/server/instance" "$APP/server/upload_jobs" "$APP/server/backups"
ln -s "$DATA/instance" "$APP/server/instance"
ln -s "$DATA/upload_jobs" "$APP/server/upload_jobs"
ln -s "$DATA/backups" "$APP/server/backups"
chown -R root:root "$APP"

echo "==> Python packages (offline)"
[ -d "$APP/venv" ] || "$PYTHON" -m venv "$APP/venv"
"$APP/venv/bin/pip" install --no-index --find-links "$BUNDLE/wheels" -r "$BUNDLE/requirements-runtime.txt"

echo "==> Configuration"
if [ ! -f "$ETC/ghg.env" ]; then
    install -m 640 -o root -g ghg "$BUNDLE/deploy/ghg.env.example" "$ETC/ghg.env"
    key="$("$PYTHON" -c 'import secrets; print(secrets.token_hex(32))')"
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$key|" "$ETC/ghg.env"
    echo "Created $ETC/ghg.env. EDIT IT NOW: DATABASE_URL and ALLOWED_ORIGINS, then run this script again."
    exit 0
fi
if grep -q 'CHANGE_ME\|example.local' "$ETC/ghg.env"; then
    echo "$ETC/ghg.env still has placeholder values (CHANGE_ME / example.local). Edit it first." >&2
    exit 1
fi

run_as_ghg() {
    runuser -u ghg -- bash -c "set -a; . $ETC/ghg.env; set +a; export FLASK_APP=app.py; cd $APP/server; $*"
}

echo "==> Database schema"
run_as_ghg "$APP/venv/bin/flask db upgrade"

echo "==> Service"
install -m 644 "$BUNDLE/deploy/ghg.service" /etc/systemd/system/ghg.service
systemctl daemon-reload
systemctl enable ghg
systemctl restart ghg

if [ -d /etc/nginx/conf.d ] && [ ! -f /etc/nginx/conf.d/ghg.conf ]; then
    install -m 644 "$BUNDLE/deploy/nginx-ghg.conf" /etc/nginx/conf.d/ghg.conf
    echo "Installed /etc/nginx/conf.d/ghg.conf. Edit the host name and certificate paths, then: nginx -t && systemctl reload nginx"
fi

echo "==> Health check"
for _ in $(seq 1 20); do
    if curl -fsS http://127.0.0.1:5000/api/health >/dev/null 2>&1; then
        echo "Application is up: $(curl -fsS http://127.0.0.1:5000/api/health)"
        echo
        echo "Next: create the first administrator (see INSTALL.md, section 'First administrator')."
        exit 0
    fi
    sleep 1
done
echo "The application did not answer. Look at: journalctl -u ghg -n 100" >&2
exit 1
