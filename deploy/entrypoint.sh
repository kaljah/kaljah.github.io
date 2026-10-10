#!/bin/sh
# Container entrypoint for the Neocarbon API image.
#   serve        apply database migrations, then start gunicorn (default)
#   migrate      apply database migrations only
#   seed-admin   create the admin and IT admin accounts (ADMIN_* / IT_ADMIN_* variables)
#   backup       write a database backup to $BACKUP_DIR
#   restore F    restore backup file F (add --apply to change the database)
#   anything else is run as a command (for example: sh)
set -e
cd /app

case "${1:-serve}" in
  serve)
    flask db upgrade
    exec gunicorn -c /etc/neocarbon/gunicorn.conf.py app:app
    ;;
  migrate)
    exec flask db upgrade
    ;;
  seed-admin)
    shift
    exec python seed_admin.py "$@"
    ;;
  backup)
    shift
    exec python scripts/backup.py "$@"
    ;;
  restore)
    shift
    exec python scripts/restore.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
