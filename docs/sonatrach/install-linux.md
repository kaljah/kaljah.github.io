# Install guide: Linux server, no containers, no internet

For Sonatrach IT. The platform runs as one systemd service (gunicorn) behind nginx, against a PostgreSQL database that Sonatrach provides. The server needs no internet access: the bundle contains the web app, the code and every Python package.

Status: this guide and its scripts are written but have not yet been run on a real Linux server. The first install on a Sonatrach test server is the rehearsal; please report anything that does not match.

## 1. What the server needs
| Item | Requirement |
|------|-------------|
| OS | Linux with systemd (RHEL/Rocky 8 or 9, Ubuntu 22.04 or later), x86-64 |
| Python | 3.11, with the `venv` module (`python3-venv` on Debian/Ubuntu). The bundle is built for one Python minor version; tell us yours if it is not 3.11. |
| Web server | nginx, with a TLS certificate and key for the hostname |
| Database | PostgreSQL 13 or later provided by Sonatrach: an empty database and a user that can create tables |
| PostgreSQL client | `pg_dump` on the application server (used for the backup before each upgrade) |
| Memory and disk | 4 CPU, 8 GB RAM, 50 GB disk to start; uploads and reports live under `/var/lib/ghg` |
| Network | Users reach it on 443. The server must reach the database. No outbound access needed. |

## 2. Build the bundle (once per release, on a machine with internet)
On Linux, WSL or Git Bash, from a clean checkout of the release tag:
```bash
PY_VERSION=3.11 ./deploy/native/build-bundle.sh
```
Result: `dist/ghg-platform-<version>.tar.gz` and a `.sha256` file. Copy both to the server and check:
```bash
sha256sum -c ghg-platform-<version>.tar.gz.sha256
tar xzf ghg-platform-<version>.tar.gz
cd ghg-platform-<version>
```

## 3. Install
```bash
sudo ./deploy/install.sh
```
The first run creates the `ghg` service account, installs the files under `/opt/ghg`, installs the Python packages offline, writes `/etc/ghg/ghg.env`, and stops. Edit that file:

| Setting | Meaning |
|---------|---------|
| `DATABASE_URL` | `postgresql://USER:PASSWORD@HOST:5432/DBNAME` (percent-encode special characters in the password) |
| `ALLOWED_ORIGINS` | The address users type, for example `https://ghg.sonatrach.dz` |
| `GUNICORN_WORKERS` | 1 unless Redis is installed; see the comments in the file |

`SECRET_KEY` is generated for you; do not share or reuse it. Then run `sudo ./deploy/install.sh` again. It applies the database schema, starts the service and checks `http://127.0.0.1:5000/api/health`.

## 4. nginx and TLS
The installer copies `/etc/nginx/conf.d/ghg.conf` if none exists. Edit the host name and the two certificate paths in it, then:
```bash
sudo nginx -t && sudo systemctl reload nginx
```
nginx serves the web app and passes `/api` to the service, so users see one address and one origin.

## 5. First administrator
```bash
sudo runuser -u ghg -- bash -c 'set -a; . /etc/ghg/ghg.env; set +a; cd /opt/ghg/server; \
  ADMIN_EMAIL=admin@sonatrach.dz ADMIN_PASSWORD="<strong password>" \
  IT_ADMIN_EMAIL=itadmin@sonatrach.dz IT_ADMIN_PASSWORD="<strong password>" \
  /opt/ghg/venv/bin/python seed_admin.py'
```
Sign in at your address, then change both passwords from the account settings. Do not leave the passwords in shell history.

## 6. Check it works
- `curl -s https://<your address>/api/health` answers `{"status": "ok", ...}`.
- Sign in as the administrator and open the dashboard.
- `journalctl -u ghg -n 100` shows no errors.

## 7. Upgrade
Unpack the new bundle (after checking its checksum) and run from inside it:
```bash
sudo ./deploy/upgrade.sh
```
It backs up the database to `/var/lib/ghg/backups`, keeps the old files in `/opt/ghg/previous`, installs the new version, applies migrations and checks health. If a step fails it puts the old files back. A database change is not undone automatically: to go back after a migration, restore the backup taken just before (see section 8).

## 8. Backups and restore
`scripts/backup.py` writes a dump to `/var/lib/ghg/backups` and keeps the newest `BACKUP_RETAIN_COUNT` (default 14). To run it every night, add to root's crontab:
```
0 2 * * * runuser -u ghg -- bash -c 'set -a; . /etc/ghg/ghg.env; set +a; cd /opt/ghg/server; BACKUP_DIR=/var/lib/ghg/backups /opt/ghg/venv/bin/python scripts/backup.py'
```
Copy the backups off the server. Restore with `scripts/restore.py <file>` after stopping the service (`systemctl stop ghg`). A scheduled backup service, point-in-time recovery and a tested restore drill are planned (M3).

## 9. Where things are
| What | Where |
|------|-------|
| Code and web app | `/opt/ghg/server`, `/opt/ghg/web` (read-only for the service) |
| Settings and secret | `/etc/ghg/ghg.env` (readable by root and the `ghg` group) |
| Uploads, job state, backups | `/var/lib/ghg` |
| Service logs | `journalctl -u ghg` |
| Service control | `systemctl status|restart|stop ghg` |

## 10. Known limits of this first version
- The web page still asks Google Fonts for fonts and the Methane Explorer loads map tiles from the internet; with no internet the pages still work but use fallback fonts and the explorer map stays blank. Self-hosting these is task T2.1 and T2.2.
- The nginx security policy has not yet been tested in a browser on a real install; if a page loads blank, check the browser console and tell us which resource was blocked.
- One gunicorn worker is the default. Several workers need Redis for shared rate limits.
- Sign-in is local accounts only; single sign-on comes with M5.
