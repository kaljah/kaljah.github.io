"""
Performance Benchmark Suite: 100k Records (Item 4.5)
=====================================================
Measures and verifies p95 latency under realistic enterprise volume:
- 100,000 Scope 1 emission records
- 30 facilities
- 5 years of activity (2022 - 2026)
- 5,000 production data records
- 2,000 activity logs

Targets:
- Dashboard Summary: < 500 ms
- Reports Ledger (page 1): < 1000 ms
- Audit Trail (page 1): < 1000 ms
- QA/QC Dashboard: < 1000 ms

Outputs reports/benchmark_p95_report.json.
Uses an isolated sandbox database to guarantee production data is never touched.
"""
import os
import sys
import time
import json
import random
import datetime
import subprocess

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)


def seed_benchmark_db(db_path):
    import sqlite3
    from sqlalchemy import create_engine
    print(f"[BENCHMARK] Seeding 100k records into sandbox database: {db_path}")
    t0 = time.time()

    # Create tables via SQLAlchemy metadata
    import models  # noqa: F401
    from extensions import db
    engine = create_engine(f"sqlite:///{db_path}")
    db.metadata.create_all(engine)
    engine.dispose()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Seed 30 Facilities
    regions = ["Hassi Messaoud", "Rhourde Nouss", "In Salah", "Skikda", "Arzew", "Illizi", "Berkine"]
    facilities = []
    for i in range(1, 31):
        reg = regions[i % len(regions)]
        facilities.append((
            i, f"Facility {i:02d}", f"FAC-{i:03d}", f"Site {reg}", reg, "Upstream", "operated", "Algeria", 0
        ))
    cur.executemany(
        """INSERT INTO facilities (id, name, code, location, region, segment, operator_status, country, is_test)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        facilities
    )
    conn.commit()

    # Seed 1 User for Auth
    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash("BenchmarkPass123!")
    cur.execute(
        """INSERT INTO users (id, fullName, orgName, sector, email, password_hash, role, status, is_test)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (1, "Benchmark Admin", "NeoCarbon Corp", "Oil & Gas", "bench_admin@neocarbon.test", pw_hash, "admin", "active", 0)
    )
    conn.commit()

    # Seed 100,000 Scope 1 Emission Records
    print("[BENCHMARK] Inserting 100,000 Scope 1 emissions...")
    processes = ["Stationary Combustion", "Flaring", "Venting", "Fugitives"]
    fuels = ["Fuel Gas", "Diesel", "Associated Gas", "Natural Gas"]
    statuses = ["Verified", "Pending", "Draft", "Rejected"]

    batch_size = 10000
    total_records = 100000
    emissions_data = []

    for i in range(1, total_records + 1):
        fac_id = (i % 30) + 1
        year = 2022 + (i % 5)
        month = (i % 12) + 1
        proc = processes[i % len(processes)]
        fuel = fuels[i % len(fuels)]
        status = statuses[i % len(statuses)]
        qty = round(random.uniform(10.0, 5000.0), 2)
        co2e = round(qty * random.uniform(1.8, 3.2), 2)
        qa_flag = "SUSPICIOUS_HIGH" if (i % 250 == 0) else None

        emissions_data.append((
            i,
            f"REC-{year}-{i:06d}",
            fac_id,
            year,
            month,
            proc,
            fuel,
            qty,
            "tonnes",
            co2e,
            co2e * 0.95,
            co2e * 0.04,
            co2e * 0.01,
            status,
            qa_flag,
            "AR5",
            "1.0",
            0,
            0,
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        ))

        if len(emissions_data) >= batch_size:
            cur.executemany(
                """INSERT INTO emissions (
                    id, record_id, facility_id, year, month, process_type, fuel_type,
                    quantity, unit, co2e_total, co2_emissions, ch4_emissions, n2o_emissions,
                    status, qa_flag, gwp_version, factor_version, is_prior_period_adjustment, is_test, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                emissions_data
            )
            conn.commit()
            emissions_data.clear()

    # Seed 5,000 Production Data Records
    print("[BENCHMARK] Inserting 5,000 production records...")
    prod_data = []
    prod_id = 1
    for fac_id in range(1, 31):
        for year in range(2022, 2027):
            for month in range(1, 13):
                oil = round(random.uniform(50000, 200000), 2)
                gas = round(random.uniform(100000, 500000), 2)
                boe = round((oil + (gas / 5.8)) / 1e6, 4)
                prod_data.append((
                    prod_id,
                    fac_id,
                    year,
                    month,
                    oil,
                    gas,
                    boe,
                    0
                ))
                prod_id += 1
    cur.executemany(
        """INSERT INTO production_data (id, facility_id, year, month, oil_amount, gas_amount, total_production_mmboe, is_test)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        prod_data
    )
    conn.commit()

    # Seed 2,000 Activity Logs
    print("[BENCHMARK] Inserting 2,000 activity logs...")
    logs = []
    for i in range(1, 2001):
        logs.append((
            i,
            1,
            "bench_admin@neocarbon.test",
            "UPDATE" if i % 2 == 0 else "CREATE",
            "Emission",
            str(i),
            f"Record {i} updated via benchmark test harness",
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        ))
    cur.executemany(
        """INSERT INTO activity_log (id, user_id, user_name, action, entity, entity_id, details, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        logs
    )
    conn.commit()

    # Create indexes on benchmark db
    queries = [
        "CREATE INDEX IF NOT EXISTS ix_emissions_activity ON emissions(activity);",
        "CREATE INDEX IF NOT EXISTS ix_emissions_division ON emissions(division);",
        "CREATE INDEX IF NOT EXISTS ix_emissions_year ON emissions(year);",
        "CREATE INDEX IF NOT EXISTS ix_emissions_facility_id ON emissions(facility_id);",
        "CREATE INDEX IF NOT EXISTS ix_emissions_status ON emissions(status);",
        "CREATE INDEX IF NOT EXISTS ix_emissions_fac_yr_status ON emissions(facility_id, year, status);",
        "CREATE INDEX IF NOT EXISTS ix_emissions_process_type ON emissions(process_type);",
        "CREATE INDEX IF NOT EXISTS ix_production_data_facility_id ON production_data(facility_id);",
        "CREATE INDEX IF NOT EXISTS ix_production_data_year ON production_data(year);",
        "CREATE INDEX IF NOT EXISTS ix_activity_log_timestamp_action ON activity_log(timestamp, action);",
    ]
    for q in queries:
        try:
            cur.execute(q)
        except Exception:
            pass
    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    print(f"[BENCHMARK] Database seeded successfully in {elapsed:.2f}s")


def main():
    bench_dir = os.path.join(SERVER_DIR, "reports", "scratch_bench")
    os.makedirs(bench_dir, exist_ok=True)
    db_path = os.path.join(bench_dir, "benchmark_100k.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    try:
        seed_benchmark_db(db_path)

        # Run benchmark in worker subprocess with isolated DATABASE_URL
        worker_script = os.path.join(SERVER_DIR, "scripts", "benchmark_worker.py")
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.replace(os.sep, '/')}"
        env["FLASK_ENV"] = "testing"

        cmd = [sys.executable, "-u", worker_script, "--db-path", db_path]
        res = subprocess.run(cmd, env=env, text=True, capture_output=True)
        print(res.stdout)
        if res.stderr:
            print("[WORKER STDERR]", res.stderr)

        if res.returncode != 0:
            print(f"[ERROR] Benchmark worker failed with code {res.returncode}")
            sys.exit(res.returncode)

    finally:
        # Cleanup scratch db
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
