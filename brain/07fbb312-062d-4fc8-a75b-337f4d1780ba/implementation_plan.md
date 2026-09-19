# Workspace Cleanup Plan

To ensure the `h` folder only contains the new software and essential reference materials, I will delete the legacy files and folders from the root directory. This is a destructive operation, so please review the lists below carefully.

## Files and Folders to KEEP

These items are essential for the new software or serve as important documentation/source control:
- `new/` (The new application directory)
- `.git/` and `.gitignore` (Source control)
- `.vscode/` (IDE settings)
- `2023-API-Guidance-2.pdf` and `api_compendium_2021.pdf` (Reference documents)
- All `api_guidance_extract.txt` and `compendium_*.txt` files (Reference extracts)

## Files and Folders to DELETE

Everything else in the root directory belongs to the legacy software or are temporary debugging scripts. They will be deleted:

**Legacy Directories:**
- `public/`
- `python_service/`
- `scripts/`
- `migrations/`
- `node_modules/`
- `tests/`
- `_archive/`

**Legacy Databases:**
- `data.db`, `emissions.db`, `ghg_reporting.db`, `ghg_shared.db*`, `test.db`, `users_v2.db`
*(Note: The new software uses its own database inside the `new/server` folder).*

**Legacy Source Code & Configs:**
- All root `.js` files (e.g., `server.js`, `main.js`, `check_*.js`, `seed_*.js`, `test_*.js`, `dummy.js`)
- All root `.py` files (e.g., `test_backend.py`, `seed_map_data.py`, `debug_*.py`, `verify_*.py`)
- All root `.bat` and `.ps1` files (e.g., `start_local.bat`, `start_postgres.bat`, `reset_pg_password.ps1`)
- `package.json` and `package-lock.json`
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- Miscellaneous files: `icon.png`, `query`, `search_results.txt`, `debug_output.json`, `debug_scope3_log.txt`

## User Review Required

> [!CAUTION]
> This action will permanently delete a large amount of legacy code and databases. Please confirm that you no longer need the old `server.js` backend, the old `public` frontend, or the old root-level `.db` files before approving this plan.

If you approve, I will run a script to carefully remove all the items listed in the "DELETE" section.
