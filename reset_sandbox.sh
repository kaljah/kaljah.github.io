#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="${GHG_SANDBOX_SERVER_DIR:-$REPO_ROOT/new/server}"
DB_PATH="${GHG_DB_PATH:-$SERVER_DIR/ghg_app.db}"
TEMPLATE_PATH="${GHG_TEMPLATE_PATH:-$SERVER_DIR/instance/demo_template.db}"

if [ -z "${PYTHONEXE:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHONEXE="python3"
  else
    PYTHONEXE="python"
  fi
fi

RESET_PASSWORDS=0
for arg in "$@"; do
  if [ "$arg" = "--reset-passwords" ]; then
    RESET_PASSWORDS=1
  fi
done

echo "[Sandbox Reset] Server dir: $SERVER_DIR"

echo "[1/3] Removing SQLite WAL/SHM sidecars and restoring pristine template DB..."
rm -f "${DB_PATH}-wal" "${DB_PATH}-shm" "${DB_PATH}-journal"

if [ -f "$TEMPLATE_PATH" ]; then
  mkdir -p "$(dirname "$DB_PATH")"
  cp -f "$TEMPLATE_PATH" "$DB_PATH"
else
  echo "Template DB not found at $TEMPLATE_PATH; creating pristine template from scratch..."
  "$PYTHONEXE" "$REPO_ROOT/scripts/seed_demo.py" \
    --recreate --reset-passwords \
    --db "$DB_PATH" \
    --template "$TEMPLATE_PATH"
fi

echo "[2/3] Re-seeding demo database idempotently..."
if [ "$RESET_PASSWORDS" -eq 1 ]; then
  "$PYTHONEXE" "$REPO_ROOT/scripts/seed_demo.py" \
    --db "$DB_PATH" \
    --reset-passwords \
    --template "$TEMPLATE_PATH"
else
  "$PYTHONEXE" "$REPO_ROOT/scripts/seed_demo.py" \
    --db "$DB_PATH"
fi

rm -f "${DB_PATH}-wal" "${DB_PATH}-shm" "${DB_PATH}-journal"

echo "[3/3] Clearing sandbox upload staging, generated caches, and report job artifacts..."
for target_dir in \
  "$SERVER_DIR/upload_jobs" \
  "$SERVER_DIR/uploads" \
  "$SERVER_DIR/instance/uploads" \
  "$SERVER_DIR/instance/chart_cache" \
  "$SERVER_DIR/instance/master_report_jobs" \
  "$SERVER_DIR/report_jobs" \
  "$SERVER_DIR/tmp"; do
  if [ -d "$target_dir" ]; then
    find "$target_dir" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
  fi
done

echo "[OK] Sandbox reset complete."
