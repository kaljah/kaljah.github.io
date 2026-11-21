"""
Seed synthetic demonstration data for the GHG Platform:
- 3 synthetic facilities across 3 demo basins (Facility A-1, Facility B-2, Facility C-3)
- Multi-year monthly production data (2022-2026) in bbl and mscf
- Comprehensive Scope 1 emissions (Combustion, Flaring, Venting, Fugitive) with status='Verified'
- Scope 2 and Scope 3 verified emissions
- EU CBAM product exports
- OGMP 2.0 empirical top-down surveys
- Operational flaring streams and field-measured DRE %

The target is the SQLite database of DATABASE_URL when it names one (sqlite:///path), else new/server/ghg_app.db.
It always wrote to ghg_app.db, whatever DATABASE_URL said, so a run meant for a throw-away database changed the
local development database. A non-SQLite DATABASE_URL is refused: the demo seeder builds SQLite files only.
"""
import os
import sys

SERVER_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SERVER_DIR, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def target_db_path(database_url=None):
    """The SQLite file to seed: DATABASE_URL's when it is sqlite:///..., else ghg_app.db next to this script."""
    url = (database_url if database_url is not None else os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        return os.path.join(SERVER_DIR, "ghg_app.db")
    if not url.startswith("sqlite:///"):
        raise SystemExit(f"seed_showcase_data.py seeds SQLite only; DATABASE_URL is {url.split(':', 1)[0]}://...")
    path = url[len("sqlite:///"):]
    return path if os.path.isabs(path) else os.path.join(SERVER_DIR, path)


def seed():
    from scripts.seed_demo import seed_demo

    db_path = target_db_path()
    print(f"Seeding showcase data into {db_path}")
    seed_demo(db_path=db_path, recreate=False, reset_passwords=False)


if __name__ == "__main__":
    seed()
