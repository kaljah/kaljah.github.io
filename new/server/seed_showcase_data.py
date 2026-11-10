"""
Seed synthetic demonstration data for the GHG Platform:
- 3 synthetic facilities across 3 demo basins (Facility A-1, Facility B-2, Facility C-3)
- Multi-year monthly production data (2022-2026) in bbl and mscf
- Comprehensive Scope 1 emissions (Combustion, Flaring, Venting, Fugitive) with status='Verified'
- Scope 2 and Scope 3 verified emissions
- EU CBAM product exports
- OGMP 2.0 empirical top-down surveys
- Operational flaring streams and field-measured DRE %
"""
import os
import sys

SERVER_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SERVER_DIR, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def seed():
    from scripts.seed_demo import seed_demo

    db_path = os.path.join(SERVER_DIR, "ghg_app.db")
    seed_demo(db_path=db_path, recreate=False, reset_passwords=False)


if __name__ == "__main__":
    seed()
