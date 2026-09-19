# Cleanup: Remove Unnecessary Files from the Workspace

## Background

The **new software** is the Flask + React/Vite app located entirely inside `h/new/`:
- **Backend**: `h/new/server/` (Python Flask, runs on port 5000)
- **Frontend**: `h/new/client/` (React + Vite, runs on port 5173)
- **Launcher**: `h/new/start_all.bat`

Everything at the **root of `h/`** belongs to the **old/legacy Node.js app** (the `server.js` + `public/` stack). Everything else is debug scripts, check scripts, test scripts, PDF references, and scratch files accumulated during development.

---

## User Review Required

> [!CAUTION]
> This plan proposes **permanent deletion** of many files. Please review each section carefully before approving. Deleted files cannot be recovered unless you have Git history.

> [!IMPORTANT]
> The `new/` folder is untouched. Only files **outside** `new/` will be deleted.

> [!WARNING]
> The **old software** (`server.js`, `public/`, etc.) will also be deleted. If you still need the old app, do NOT approve this plan.

---

## What Will Be KEPT (untouched)

Everything inside `h/new/` is kept as-is:
- `new/server/` — entire Python Flask backend
- `new/client/` — entire React/Vite frontend
- `new/start_all.bat` — launcher
- `new/setup.bat` — setup script

The following root-level files are also kept as they are **required for git, Docker, or build tooling**:
- `.git/` — version control
- `.gitignore`
- `.dockerignore`
- `Dockerfile`
- `docker-compose.yml`
- `package.json` + `package-lock.json` + `node_modules/` — **still needed** if electron build or old server is used
- `icon.png` — referenced in `package.json` for Electron build
- `users_v2.db` — referenced in `package.json` electron build files list
- `ghg_shared.db`, `ghg_shared.db-shm`, `ghg_shared.db-wal` — main shared DB

---

## What Will Be DELETED

### 1. Old Legacy App Files (root level)
These belong to the old Node.js server, not the new software:
- `server.js` (old Node.js backend, replaced by `new/server/app.py`)
- `main.js` (Electron entry point for old app)
- `report_service.js`
- `pg-adapter.js`
- `db_config.js`
- `dummy.js`
- `temp_patch.js`
- `public/` (entire folder — old HTML/CSS/JS frontend, replaced by `new/client/`)

### 2. Debug / Check / Verify Scripts (root level — one-off dev tools)
- `check_2026.js`
- `check_577.py`
- `check_activities.js`
- `check_db.js`
- `check_db_contents.py`
- `check_db_emissions.js`
- `check_facility_links.py`
- `check_pg_db.js`
- `check_schema.js`
- `check_status_2024.py`
- `check_unmapped.js`
- `check_users.py`
- `check_yearly_totals.js`
- `check_years.js`
- `cleanup_db.js`
- `count_rows.js`
- `debug_2024.py`
- `debug_activities.js`
- `debug_api_simulation.js`
- `debug_audit.js`
- `debug_dashboard_error.py`
- `debug_dashboard_query.js`
- `debug_db.js`
- `debug_emissions_breakdown.js`
- `debug_emissions_logic.py`
- `debug_output.json`
- `debug_scope3_log.txt`
- `debug_status.py`
- `debug_union.py`
- `debug_years.py`
- `deep_diagnostic.py`
- `simple_debug.js`
- `verify_all_years.js`
- `verify_api_live.py`
- `verify_notifications.py`
- `verify_reports.py`
- `verify_scope2_data.js`
- `add_system_notification.py`
- `fix_emission_factors.py`

### 3. Test Scripts (root level)
- `test.py`
- `test.db`
- `test_2024_params.py`
- `test_api.py`
- `test_api_categorical.js`
- `test_backend.py`
- `test_compendium_examples.py`
- `test_count_api.js`
- `test_gas_calc.js`
- `test_logic_fixes.py`
- `test_params.py`
- `test_s3_probe.js`
- `test_stac_api.js`
- `test_summary_api.js`
- `test_unep_api.js`
- `test_unep_api_headers.js`
- `test_wms.js`
- `test_wms_time.js`
- `tests/` (root-level tests folder)

### 4. Seed / Migration Scripts (root level)
- `seed_ramzi.js`
- `seed_script.js`
- `seed_script_comprehensive.js`
- `seed_sonatrach_full.js`
- `seed_map_data.py`
- `seed_map_data_safe.py`
- `migrations/` (root-level — only contains one old Python migration unrelated to the new app's `new/server/migrations/`)

### 5. PDF References / Extract Text Files (research artifacts, not runtime)
- `2023-API-Guidance-2.pdf`
- `api_compendium_2021.pdf`
- `api_guidance_extract.txt`
- `compendium_dehydrator_extract.txt`
- `compendium_examples_extracted.txt`
- `compendium_flaring_eff.txt`
- `compendium_fugitive_extract.txt`
- `compendium_loading_extract.txt`
- `compendium_pneumatic_p412.txt`
- `compendium_pneumatic_tables.txt`
- `compendium_section5_extract.txt`
- `compendium_table_6_17.txt`
- `compendium_tank_flash_extract.txt`
- `extract_compendium_examples.py`
- `probe_pdf_examples.py`
- `repro_backend_logic.py`
- `search_results.txt`
- `query`

### 6. Old Databases (not used by new app)
- `data.db`
- `emissions.db`
- `ghg_reporting.db`

### 7. Utility/Setup Scripts for Old Stack
- `install_dependencies.bat`
- `start_local.bat`
- `start_postgres.bat`
- `start_python_service.bat`
- `setup_db_user.bat`
- `reset_pg_password.ps1`
- `python_service/` (old standalone Python service, replaced by `new/server/`)

### 8. Scratch Folder (root level)
- `scratch/` (two one-off check scripts)

### 9. Entire `_archive/` Folder
- Contains old debug HTMLs, old databases, old seed scripts — all replaced by new software.

### 10. `scripts/` Folder (root level)
- Contains duplicated seed/debug scripts.

---

## Verification Plan

After deletion:
1. `new/` folder is fully intact
2. Run `cd new && start_all.bat` to confirm the new app still starts
3. Verify `new/server/app.py` and `new/client/` are untouched

---

## Summary

| Category | Action |
|---|---|
| `new/` (entire folder) | ✅ KEPT |
| `.git/`, `.gitignore`, `.dockerignore` | ✅ KEPT |
| `Dockerfile`, `docker-compose.yml` | ✅ KEPT |
| `package.json`, `package-lock.json`, `node_modules/` | ✅ KEPT |
| `icon.png`, `users_v2.db` | ✅ KEPT |
| `ghg_shared.db*` | ✅ KEPT |
| Old Node.js app files (`server.js`, `main.js`, etc.) | ❌ DELETED |
| `public/` (old frontend) | ❌ DELETED |
| All `check_*.js/py`, `debug_*.js/py`, `verify_*.js/py` | ❌ DELETED |
| All `test_*.js/py`, `tests/` | ❌ DELETED |
| All `seed_*.js/py` | ❌ DELETED |
| PDFs, compendium text extracts | ❌ DELETED |
| Old `.db` files (`data.db`, `emissions.db`, `ghg_reporting.db`) | ❌ DELETED |
| `_archive/`, `scratch/`, `scripts/`, `migrations/` (root) | ❌ DELETED |
| `python_service/` | ❌ DELETED |
