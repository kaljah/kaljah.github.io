"""
Step 8 Regression Tests — Dashboard Compound Performance Indexes & 50k Benchmark
================================================================================
Verifies:
1. Idempotent Alembic migration adds compound dashboard indexes on filter columns and runs ANALYZE.
2. EXPLAIN QUERY PLAN uses the compound indexes (no table SCAN / avoids TEMP B-TREE GROUP BY).
3. Dashboard endpoints (/api/dashboard/batch-all?year=2025 and all-years) on 50,000 records complete < 3.0s.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]

EXPECTED_COMPOUND_INDEXES = {
    "emissions": (
        "ix_emissions_dash_status_test_yr_proc_fac",
        "ix_emissions_fac_yr_status_test",
    ),
    "scope2_emissions": ("ix_scope2_dash_status_yr_fac",),
    "scope3_emissions": ("ix_scope3_dash_status_yr_fac_cat",),
    "production_data": ("ix_prod_dash_test_yr_fac",),
    "facilities": ("ix_facilities_dash_tenant_test_filters",),
    "ogmp_surveys": ("ix_ogmp_surveys_fac_yr",),
    "flaring_details": ("ix_flaring_details_status_yr_fac",),
    "mitigation_projects": ("ix_mitigation_projects_test_yr_fac",),
}


def _seed_50k_bench_db(db_path: Path) -> None:
    """Create a fresh migrated 50,000-record SQLite benchmark database via subprocess."""
    script = f"""
import os, sys, sqlite3
from pathlib import Path
SERVER = Path(r"{SERVER_DIR}")
DB = Path(r"{db_path}")
os.environ["DATABASE_URL"] = f"sqlite:///{{DB.as_posix()}}"
os.environ["FLASK_ENV"] = "development"
os.environ["SEED_ADMIN"] = "false"
os.environ["AUTO_MIGRATE"] = "true"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from app import app
from extensions import db
from models import Facility, User

with app.app_context():
    u = User(
        email="bench50k@example.org",
        fullName="Bench Admin",
        orgName="Demo Operator Co.",
        sector="Oil & Gas",
        role="admin",
        location="Global",
        status="active",
        tenant_id="default",
    )
    u.set_password("BenchPass123!")
    db.session.add(u)
    facs = []
    for i in range(20):
        f = Facility(
            name=f"Bench Facility {{i+1}}",
            code=f"BF-{{i+1:02d}}",
            location="Sector Alpha",
            region="Basin Alpha" if i % 2 == 0 else "Basin Beta",
            division="Production" if i % 2 == 0 else "Gas Processing",
            activity="EP" if i % 2 == 0 else "GP",
            segment="Upstream" if i % 2 == 0 else "Midstream",
            tenant_id="default",
        )
        db.session.add(f)
        facs.append(f)
    db.session.commit()
    fids = [f.id for f in facs]
    uid = u.id
    db.session.remove()
    db.engine.dispose()

conn = sqlite3.connect(str(DB))
cur = conn.cursor()
procs = ["combustion", "flaring", "venting", "fugitives", "mobile"]
fuels = ["Natural Gas", "Diesel", "Associated Gas", "Fuel Gas", "Condensate"]
s1 = [
    (
        f"S1-{{i:06d}}", 2018 + (i % 9), (i % 12) + 1, procs[i % 5], fuels[i % 5],
        100.0 + (i % 50), "m3", f"EQ-{{i % 200}}", 200.0, 2.5, 0.1, 270.8,
        "Default", fids[i % len(fids)], uid, "Verified" if i % 10 != 0 else "Pending", 0,
    )
    for i in range(42000)
]
cur.executemany(
    \"\"\"INSERT INTO emissions
    (record_id, year, month, process_type, fuel_type, quantity, unit, equipment_id,
     co2_emissions, ch4_emissions, n2o_emissions, co2e_total,
     factor_source, facility_id, created_by, status, is_test)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
    s1,
)
s2 = [
    (
        2018 + (i % 9), (i % 12) + 1, "electricity", 50000.0 + i,
        0.45, 22.5, 22.5, 22.5, "US Average", "US Average",
        fids[i % len(fids)], uid, "Verified" if i % 10 != 0 else "Pending",
    )
    for i in range(4000)
]
cur.executemany(
    \"\"\"INSERT INTO scope2_emissions
    (year, month, source_type, electricity_kwh, emission_factor, co2e,
     co2e_location_based, co2e_market_based, grid_region, location, facility_id, created_by, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
    s2,
)
s3 = [
    (
        2018 + (i % 9), (i % 12) + 1,
        "Category 11: Use of Sold Products" if i % 3 == 0 else "Category 1: Purchased Goods",
        f"Upstream Supply {{i}}", 1000.0 + i, "USD", 0.35, 350.0,
        "EEIO", fids[i % len(fids)], uid, "Verified" if i % 10 != 0 else "Pending",
    )
    for i in range(2000)
]
cur.executemany(
    \"\"\"INSERT INTO scope3_emissions
    (year, month, category, sub_category, activity_data, unit, emission_factor, co2e,
     calculation_method, facility_id, created_by, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
    s3,
)
prod = []
for i in range(2000):
    fid = fids[i % len(fids)]
    slot = i // len(fids)
    prod.append((2018 + (slot // 12), (slot % 12) + 1, 12000.0, "bbl", 3500000.0, "m3", fid, uid, 0))
cur.executemany(
    \"\"\"INSERT INTO production_data
    (year, month, oil_amount, oil_unit, gas_amount, gas_unit, facility_id, created_by, is_test)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
    prod,
)
cur.execute("ANALYZE")
conn.commit()
conn.close()
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(SERVER_DIR),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, f"50k DB creation failed: {proc.stderr}\n{proc.stdout}"


def test_compound_indexes_migration_idempotent_and_analyze(tmp_path: Path):
    """Alembic migration creates all compound dashboard indexes idempotently and populates sqlite_stat1."""
    db_path = tmp_path / "mig_step8.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    env["FLASK_ENV"] = "development"
    env["SEED_ADMIN"] = "false"
    env["AUTO_MIGRATE"] = "true"

    # Upgrade from clean DB to head, downgrade 1 step (verify drop), upgrade back,
    # and stamp back to h3d8e2a19f04 while indexes already exist -> upgrade again cleanly (idempotent check).
    mig_script = """
import sqlite3
from pathlib import Path
from app import app, migrate
from flask_migrate import downgrade, stamp, upgrade

with app.app_context():
    upgrade(directory=migrate.directory)
    downgrade(directory=migrate.directory, revision="-1")
    conn = sqlite3.connect(str(Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))))
    after_down = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    conn.close()
    assert "ix_emissions_dash_status_test_yr_proc_fac" not in after_down, "downgrade must drop compound index"
    upgrade(directory=migrate.directory)
    # Now indexes ALREADY exist; stamp back and upgrade to prove idempotency
    stamp(directory=migrate.directory, revision="h3d8e2a19f04")
    upgrade(directory=migrate.directory)
"""
    proc = subprocess.run(
        [sys.executable, "-c", mig_script],
        cwd=str(SERVER_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, f"Migration cycle failed: {proc.stderr}\n{proc.stdout}"

    conn = sqlite3.connect(str(db_path))
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    stat_rows = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sqlite_stat1'"
    ).fetchone()[0]
    conn.close()

    missing = [
        f"{tbl}.{idx}"
        for tbl, idxs in EXPECTED_COMPOUND_INDEXES.items()
        for idx in idxs
        if idx not in existing
    ]
    assert not missing, f"Missing compound dashboard indexes: {missing}"
    assert stat_rows == 1, "ANALYZE must be executed so sqlite_stat1 exists"


def test_explain_query_plan_and_50k_dashboard_under_3s(tmp_path: Path):
    """EXPLAIN QUERY PLAN uses compound indexes and 50k dashboard batch-all completes < 3.0s."""
    db_path = tmp_path / "bench50k_step8.db"
    _seed_50k_bench_db(db_path)

    conn = sqlite3.connect(str(db_path))
    existing = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    }
    for tbl, idxs in EXPECTED_COMPOUND_INDEXES.items():
        for idx in idxs:
            assert idx in existing, f"Compound index {tbl}.{idx} missing in migrated DB"

    plans = {
        "emissions_summary": [
            r[3]
            for r in conn.execute(
                """EXPLAIN QUERY PLAN
                SELECT year, process_type, SUM(co2_emissions), SUM(ch4_emissions), SUM(n2o_emissions), SUM(co2e_total)
                FROM emissions
                WHERE is_test = 0 AND status IN ('Verified') AND year = 2025
                GROUP BY year, process_type"""
            ).fetchall()
        ],
        "scope2_year": [
            r[3]
            for r in conn.execute(
                """EXPLAIN QUERY PLAN
                SELECT facility_id, SUM(co2e) FROM scope2_emissions
                WHERE status IN ('Verified') AND year = 2025
                GROUP BY facility_id"""
            ).fetchall()
        ],
        "scope3_year_fac": [
            r[3]
            for r in conn.execute(
                """EXPLAIN QUERY PLAN
                SELECT facility_id, year, category, SUM(co2e)
                FROM scope3_emissions
                WHERE status IN ('Verified') AND year = 2025
                GROUP BY facility_id, year, category"""
            ).fetchall()
        ],
        "production_year": [
            r[3]
            for r in conn.execute(
                """EXPLAIN QUERY PLAN
                SELECT * FROM production_data
                WHERE is_test = 0 AND year = 2025"""
            ).fetchall()
        ],
    }
    conn.close()

    assert any("ix_emissions_dash_status_test_yr_proc_fac" in step for step in plans["emissions_summary"]), (
        f"Expected emissions_summary to use compound index, got: {plans['emissions_summary']}"
    )
    assert not any("TEMP B-TREE FOR GROUP BY" in step for step in plans["emissions_summary"]), (
        f"Unexpected TEMP B-TREE FOR GROUP BY in emissions_summary: {plans['emissions_summary']}"
    )
    assert any("ix_scope2_dash_status_yr_fac" in step for step in plans["scope2_year"]), (
        f"Expected scope2_year to use compound index, got: {plans['scope2_year']}"
    )
    assert any("ix_scope3_dash_status_yr_fac_cat" in step for step in plans["scope3_year_fac"]), (
        f"Expected scope3_year_fac to use compound index, got: {plans['scope3_year_fac']}"
    )
    assert any("ix_prod_dash_test_yr_fac" in step for step in plans["production_year"]), (
        f"Expected production_year to use compound index, got: {plans['production_year']}"
    )

    # Measure cold-cache /api/dashboard/batch-all?year=2025 and /api/dashboard/batch-all on 50,000 records
    bench_script = f"""
import json, os, sys, time
from pathlib import Path
SERVER = Path(r"{SERVER_DIR}")
DB = Path(r"{db_path}")
os.environ["DATABASE_URL"] = f"sqlite:///{{DB.as_posix()}}"
os.environ["FLASK_ENV"] = "development"
os.environ["SEED_ADMIN"] = "false"
os.environ["AUTO_MIGRATE"] = "true"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from app import app
from extensions import limiter
from models import User
from routes.dashboard import clear_dashboard_cache

limiter.enabled = False
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False

with app.app_context():
    uid = User.query.filter_by(email="bench50k@example.org").first().id

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["role"] = "admin"
        sess["sv"] = 0
        sess["last_seen"] = time.time()

    clear_dashboard_cache()
    t0 = time.perf_counter()
    r1 = client.get("/api/dashboard/batch-all?year=2025")
    dt_year = time.perf_counter() - t0

    clear_dashboard_cache()
    t0 = time.perf_counter()
    r2 = client.get("/api/dashboard/batch-all")
    dt_all = time.perf_counter() - t0

    clear_dashboard_cache()
    t0 = time.perf_counter()
    r3 = client.get("/api/dashboard/summary?year=2025")
    dt_sum = time.perf_counter() - t0

print("BENCH_RESULT=" + json.dumps({{
    "status_year": r1.status_code,
    "dt_year": dt_year,
    "status_all": r2.status_code,
    "dt_all": dt_all,
    "status_sum": r3.status_code,
    "dt_sum": dt_sum,
}}))
"""
    proc = subprocess.run(
        [sys.executable, "-c", bench_script],
        cwd=str(SERVER_DIR),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, f"50k HTTP bench failed: {proc.stderr}\n{proc.stdout}"
    line = next(l for l in proc.stdout.splitlines() if l.startswith("BENCH_RESULT="))
    metrics = json.loads(line.split("=", 1)[1])
    assert metrics["status_year"] == 200
    assert metrics["status_all"] == 200
    assert metrics["status_sum"] == 200
    assert metrics["dt_year"] < 3.0, f"/api/dashboard/batch-all?year=2025 took {metrics['dt_year']:.3f}s (>= 3.0s)"
    assert metrics["dt_all"] < 3.0, f"/api/dashboard/batch-all (all years) took {metrics['dt_all']:.3f}s (>= 3.0s)"
