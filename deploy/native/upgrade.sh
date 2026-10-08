#!/usr/bin/env bash
# Upgrade to a newer bundle:  sudo ./deploy/upgrade.sh   (run from the unpacked NEW bundle)
# Takes a database backup first, installs the new files, runs migrations, restarts, checks health.
# If anything fails after the backup, the old version's files are restored (see INSTALL.md for the database).
set -euo pipefail

BUNDLE="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/ghg
DATA=/var/lib/ghg
ETC=/etc/ghg

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }
[ -f "$ETC/ghg.env" ] || { echo "No $ETC/ghg.env: this server has no installation. Use install.sh." >&2; exit 1; }

old="$(cat "$APP/VERSION" 2>/dev/null || echo unknown)"
new="$(cat "$BUNDLE/VERSION")"
echo "==> Upgrading $old -> $new"

run_as_ghg() {
    runuser -u ghg -- bash -c "set -a; . $ETC/ghg.env; set +a; export FLASK_APP=app.py; cd $APP/server; $*"
}

echo "==> Database backup"
mkdir -p "$DATA/backups"
chown ghg:ghg "$DATA/backups"
command -v pg_dump >/dev/null || { echo "pg_dump is missing (install the PostgreSQL client package) so no backup can be taken." >&2; exit 1; }
run_as_ghg "BACKUP_DIR=$DATA/backups $APP/venv/bin/python scripts/backup.py"

echo "==> Keep the previous version for rollback"
rm -rf "$APP/previous"
mkdir -p "$APP/previous"
mv "$APP/server" "$APP/previous/server"
mv "$APP/web" "$APP/previous/web"
cp "$APP/VERSION" "$APP/previous/VERSION" 2>/dev/null || true

rollback() {
    echo "!! Upgrade failed; restoring the previous files" >&2
    rm -rf "$APP/server" "$APP/web"
    mv "$APP/previous/server" "$APP/server"
    mv "$APP/previous/web" "$APP/web"
    systemctl restart ghg || true
}
trap rollback ERR

cp -r "$BUNDLE/server" "$APP/server"
cp -r "$BUNDLE/web" "$APP/web"
cp "$BUNDLE/VERSION" "$APP/VERSION"
rm -rf "$APP/server/instance" "$APP/server/upload_jobs" "$APP/server/backups"
ln -s "$DATA/instance" "$APP/server/instance"
ln -s "$DATA/upload_jobs" "$APP/server/upload_jobs"
ln -s "$DATA/backups" "$APP/server/backups"
chown -R root:root "$APP/server" "$APP/web"

"$APP/venv/bin/pip" install --no-index --find-links "$BUNDLE/wheels" -r "$BUNDLE/requirements-runtime.txt"
run_as_ghg "$APP/venv/bin/flask db upgrade"
install -m 644 "$BUNDLE/deploy/ghg.service" /etc/systemd/system/ghg.service
systemctl daemon-reload
systemctl restart ghg

for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:5000/api/health >/dev/null 2>&1; then
        trap - ERR
        echo "Upgraded to $new. $(curl -fsS http://127.0.0.1:5000/api/health)"
        exit 0
    fi
    sleep 1
done
false
