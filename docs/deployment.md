# Installing Neocarbon

This guide is for the IT team that installs and runs Neocarbon on its own servers. It covers two ways to install: **containers** (Docker or Podman with Compose, recommended) and **native** (system services on Linux, no containers). Both run the same code and need no internet access on the server.

## What runs

| Part | Role | Container install | Native install |
|---|---|---|---|
| nginx | HTTPS, serves the web interface, forwards `/api` to the API | `web` container | OS package |
| API | Flask application under gunicorn | `app` container | `neocarbon` systemd service |
| PostgreSQL 16 | all data | `db` container | OS package or an existing database server |
| Redis 7 | sign-in and request rate-limit counters (nothing to back up) | `redis` container | OS package |

The browser talks only to nginx, on one address (for example `https://neocarbon.sonatrach.dz`). The web interface and the API share that address, so no cross-site requests are made.

## Server requirements

- Linux on x86_64, 4 CPU cores, 8 GB RAM, 50 GB disk to start (more for backups).
- A DNS name for the application and a TLS certificate for it (PEM: certificate chain and private key).
- Containers: Docker Engine 24+ with the Compose plugin, or Podman 4+ with `podman compose`.
- Native: Python 3.11 (with `venv`), PostgreSQL 16 (server, or client tools if the database is elsewhere), Redis 7, nginx 1.25+, `envsubst` (package `gettext`), systemd.
- Inbound: TCP 443 (and 80, which only redirects to 443). No outbound internet access is needed.

## The release bundle

Each release is one file, `neocarbon-<version>.tar.gz`. Check it and unpack it:

```bash
tar -xzf neocarbon-1.0.0.tar.gz
cd neocarbon-1.0.0
sha256sum -c SHA256SUMS
```

| Path | Used by |
|---|---|
| `images/neocarbon-images.tar` | containers (app, web, postgres, redis images) |
| `compose.yml`, `.env.example` | containers |
| `native/`, `server/`, `spa/`, `wheels/` | native install |
| `deployment.md` | this guide |

## Option A: containers

1. **Load the images** (no registry or internet needed):
   ```bash
   docker load -i images/neocarbon-images.tar
   ```
2. **Settings.** Copy the example and fill in at least `SERVER_NAME`, `SECRET_KEY`, `POSTGRES_PASSWORD`, and the four admin account values:
   ```bash
   cp .env.example .env && chmod 600 .env
   openssl rand -hex 32   # a value for SECRET_KEY
   openssl rand -hex 24   # a value for POSTGRES_PASSWORD
   ```
3. **Certificate.** Put the certificate chain and key in `certs/` (or set `TLS_DIR`):
   ```bash
   mkdir -p certs && cp /path/to/fullchain.pem /path/to/privkey.pem certs/
   ```
4. **Start:**
   ```bash
   docker compose up -d
   docker compose ps          # all four services "Up", app "healthy"
   ```
   The API applies database migrations on every start.
5. **Create the administrator accounts** (first install only; uses `ADMIN_*` and `IT_ADMIN_*` from `.env`):
   ```bash
   docker compose run --rm app seed-admin
   ```
   Afterwards, remove `ADMIN_PASSWORD` and `IT_ADMIN_PASSWORD` from `.env`. Running it again leaves existing accounts unchanged.
6. **Check:** open `https://<SERVER_NAME>/` and sign in with the admin account. `https://<SERVER_NAME>/api/health/ready` should answer `"status":"ready"`.

Useful commands:

```bash
docker compose logs -f app                 # API logs
docker compose exec app neocarbon-entrypoint backup
docker compose exec app sh                 # a shell in the API container
docker compose down                        # stop (data stays in the volumes)
```

Data lives in two Docker volumes: `neocarbon_pgdata` (database) and `neocarbon_appdata` (backups and upload job status).

## Option B: native install

1. Install the OS packages listed under *Server requirements*, create the database and a database user:
   ```bash
   sudo -u postgres createuser --pwprompt neocarbon
   sudo -u postgres createdb --owner neocarbon neocarbon
   ```
2. Run the installer from the unpacked bundle. The first run creates `/etc/neocarbon/neocarbon.env` and stops:
   ```bash
   sudo ./native/install.sh
   ```
3. Fill in `/etc/neocarbon/neocarbon.env`: `DATABASE_URL` (`postgresql://neocarbon:PASSWORD@127.0.0.1:5432/neocarbon`), `SECRET_KEY`, `ALLOWED_ORIGINS` (`https://<host name>`), and the admin account values.
4. Put the certificate at `/etc/neocarbon/tls/fullchain.pem` and the key at `/etc/neocarbon/tls/privkey.pem` (or set `TLS_CERT` and `TLS_KEY` when running the installer). Then run the installer again:
   ```bash
   sudo SERVER_NAME=neocarbon.sonatrach.dz ./native/install.sh
   sudo neocarbon-seed-admin       # first install only
   ```

The installer puts the code in `/opt/neocarbon`, installs Python packages from `wheels/` without downloading anything, writes the nginx site to `/etc/nginx/conf.d/neocarbon.conf`, and enables the `neocarbon` service and the daily `neocarbon-backup.timer`. Logs: `journalctl -u neocarbon`.

## Backups and restore

Backups are full PostgreSQL dumps (`pg_dump --clean`, gzip). The newest `BACKUP_RETAIN_COUNT` (14) are kept. **Copy them off the server** (backup storage, another site): a backup on the same disk does not survive the loss of that disk.

- Containers: schedule on the host, for example in root's crontab:
  ```
  15 2 * * * cd /opt/neocarbon && docker compose exec -T app neocarbon-entrypoint backup >> /var/log/neocarbon-backup.log 2>&1
  ```
  The files are in the `neocarbon_appdata` volume under `backups/` (`docker volume inspect neocarbon_appdata` shows the folder on the host).
- Native: `neocarbon-backup.timer` runs every night at 02:15 into `/var/backups/neocarbon`. Run one now with `sudo systemctl start neocarbon-backup`.

Restore (stops at the first error and changes nothing on failure). Without `--apply` it only checks the file:

```bash
# containers
docker compose exec app neocarbon-entrypoint restore /data/backups/<file>.sql.gz
docker compose exec app neocarbon-entrypoint restore /data/backups/<file>.sql.gz --apply
# native
sudo -u neocarbon sh -c 'set -a; . /etc/neocarbon/neocarbon.env; cd /opt/neocarbon/server && /opt/neocarbon/venv/bin/python scripts/restore.py <file> --apply'
```

**Restore drill:** before go-live, restore a backup on a test server, sign in, compare the dashboard totals and run *Verify integrity* on the Audit Trail page. Record how long it took.

## Upgrades and rollback

Take a backup first. Then:

- Containers: `docker load -i images/neocarbon-images.tar` from the new bundle, set `NEOCARBON_VERSION` in `.env` to the new version, `docker compose up -d`. Migrations run on start.
- Native: run the new bundle's `native/install.sh`. The previous code is kept in `/opt/neocarbon/server.old`.

Rollback: restore the backup taken before the upgrade, then start the previous version (containers: set `NEOCARBON_VERSION` back; native: run the previous bundle's installer). A database migrated by a newer version is not guaranteed to work with older code, which is why the backup is restored first.

## Monitoring

| Endpoint | Meaning |
|---|---|
| `GET /api/health/live` | the API process answers |
| `GET /api/health/ready` | the API reaches the database (`"database":"connected"`) |

Logs go to the console of the process: `docker compose logs` or `journalctl -u neocarbon`. Set `LOG_FILE` to also write warnings and errors to a rotating file.

## Settings reference

Container installs set these in `.env` (the compose file passes them on); native installs in `/etc/neocarbon/neocarbon.env`.

| Setting | Default | Meaning |
|---|---|---|
| `SERVER_NAME` | (required, containers) | host name in the browser; must match the certificate |
| `SECRET_KEY` | (required) | signs sessions and CSRF tokens; long random value; changing it signs everyone out |
| `DATABASE_URL` | (required, native; built from `POSTGRES_*` in containers) | `postgresql://user:password@host:5432/db` |
| `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB` | (required), `neocarbon`, `neocarbon` | containers: database credentials |
| `ALLOWED_ORIGINS` | (required, native; `https://SERVER_NAME` in containers) | the address users open; the app refuses to start in production without it |
| `REDIS_URL` | `redis://redis:6379/0` (containers) | shared rate-limit store; required in production |
| `TRUSTED_PROXIES` | `1` | number of reverse proxies in front of the app (nginx = 1). Needed for client addresses and for the CSRF check over HTTPS |
| `FLASK_ENV` | `production` | production mode: refuses unsafe settings at start |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME` | | compliance administrator created by `seed-admin` |
| `IT_ADMIN_EMAIL`, `IT_ADMIN_PASSWORD`, `IT_ADMIN_FULL_NAME` | | IT administrator (user accounts only) created by `seed-admin` |
| `BACKUP_DIR` | `/data/backups` (containers), `/var/backups/neocarbon` (native) | backup folder |
| `BACKUP_RETAIN_COUNT` | `14` | backups kept |
| `UPLOAD_JOB_DIR` | `/data/upload_jobs`, `/var/lib/neocarbon/upload_jobs` | status of running bulk uploads (shared by the API workers) |
| `MAX_CONTENT_LENGTH` | `52428800` (50 MB) | largest upload; keep `CLIENT_MAX_BODY` a little above it |
| `CLIENT_MAX_BODY` | `55m` | nginx upload limit (containers: in `.env`; native: when running the installer) |
| `MAX_CONCURRENT_UPLOADS_PER_USER` | `3` | bulk uploads one user may run at once |
| `LOGIN_RATE_LIMIT` | `50 per 15 minutes` | failed sign-ins allowed per client address |
| `LOGIN_ACCOUNT_LIMIT` | `10 per 15 minutes` | failed sign-ins per account (from any address) before it is locked for the rest of the window |
| `RATELIMIT_DEFAULT` | `200 per minute` | general request limit per client |
| `GUNICORN_WORKERS`, `GUNICORN_THREADS` | `4`, `4` | API processes and threads per process |
| `GUNICORN_TIMEOUT` | `300` | seconds before a request is cut (reports, exports) |
| `MAP_TILE_URL`, `MAP_TILE_ATTRIBUTION`, `MAP_TILE_SUBDOMAINS` | empty | internal map tile server for the Emissions Map; empty: the map shows facilities without a basemap |
| `CSP_IMG_SRC_EXTRA` | empty | containers: tile server origin allowed in the browser policy (for example `https://tiles.sonatrach.dz`) |
| `DISABLE_OUTBOUND_EMAIL` | `true` | `false` to send email (approval and password-reset notices) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `EMAIL_FROM` | `587`, `true` | mail relay |
| `WTF_CSRF_SSL_STRICT` | `true` | over HTTPS, a change must come from a page on the same address (`Referer`); `false` turns this check off |
| `SESSION_COOKIE_SAMESITE` | `Lax` | leave as is (web interface and API on one address) |
| `LOG_FILE` | empty | file for warnings and errors (rotating, 50 MB × 3); empty: console only |
| `AUTO_MIGRATE` | | `true` lets the app migrate the database itself on start (not needed: both installs run `flask db upgrade`) |
| `NEOCARBON_VERSION` | set by the bundle | containers: image version to run |
| `TLS_DIR`, `HTTP_PORT`, `HTTPS_PORT` | `./certs`, `80`, `443` | containers: certificate folder and published ports |

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The app container restarts; log says `FATAL: ...` | A required setting is missing or unsafe (`SECRET_KEY`, `DATABASE_URL`, `ALLOWED_ORIGINS`, `REDIS_URL`). The message names it. |
| `Database schema is at ..., expected ...` | Migrations did not run. Containers run them at start; native: `sudo systemctl restart neocarbon` (runs `flask db upgrade` first). |
| Saving anything shows "CSRF token missing or invalid" | Open the application by the address in `ALLOWED_ORIGINS`/`SERVER_NAME`, through nginx. Check `TRUSTED_PROXIES=1`. A proxy or browser extension that strips the `Referer` header breaks the HTTPS check (`WTF_CSRF_SSL_STRICT=false` turns it off). |
| Everyone is locked out of sign-in | Too many failed attempts from one address (`LOGIN_RATE_LIMIT`) or for one account (`LOGIN_ACCOUNT_LIMIT`); wait 15 minutes. |
| Uploads larger than a few MB fail with 413 | Raise `MAX_CONTENT_LENGTH` and nginx's `CLIENT_MAX_BODY` together. |
| Map without background | Expected without `MAP_TILE_URL`. |

## Building a release (vendor side)

On a machine with Docker and internet access, from the repository root:

```bash
deploy/release.sh 1.0.0
# or with an internal mirror of the base images:
REGISTRY=registry.example.dz/library deploy/release.sh 1.0.0
```

The bundle lands in `deploy/release/neocarbon-1.0.0.tar.gz`. `docker compose -f deploy/compose.yml build` builds the images for a local trial.
