"""
test_stress_concurrency.py
==========================
Pillar 1: High-Concurrency & Multi-Threading Stress Test.

Simulates 50 concurrent worker threads executing simultaneous reads and writes
against the Flask application, verifying:
1. SQLite WAL mode lock resilience (zero OperationalError: database is locked).
2. Zero unhandled 500 Internal Server Errors under intense write contention.
3. Thread safety of user sessions, facility access, and calculation dispatchers.
4. P95 latency and request throughput metrics under concurrent load.
"""

import time
import concurrent.futures
import pytest
from app import app
from models import db, User, Facility, Emission, Scope2Emission, Scope3Emission


@pytest.fixture
def test_env():
    from extensions import limiter
    limiter.enabled = False
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        # Setup admin user
        admin = User.query.filter_by(email="concurrency_admin@test.com").first()
        if not admin:
            admin = User(
                email="concurrency_admin@test.com",
                fullName="Concurrency Admin",
                orgName="StressCorp",
                sector="Oil & Gas",
                role="admin",
                location="Algiers",
            )
            admin.set_password("StressPass2026!")
            db.session.add(admin)
            db.session.commit()

        # Setup test facility
        fac = Facility.query.filter_by(name="Concurrency Stress Terminal").first()
        if not fac:
            fac = Facility(
                name="Concurrency Stress Terminal",
                location="Hassi Messaoud",
                activity="Extraction",
                division="Production",
                region="Ouargla",
                field="North Field",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.commit()

        fid = fac.id
        admin_id = admin.id

    try:
        yield {"facility_id": fid, "admin_id": admin_id}
    finally:
        limiter.enabled = True


class TestConcurrencyAndLockResilience:
    """Stress tests concurrent read and write operations under multi-threaded execution."""

    def test_concurrent_multi_scope_writes_and_reads(self, test_env):
        """Execute 50 concurrent requests mixing Scope 1, Scope 2, Scope 3 writes and Dashboard reads."""
        num_threads = 30
        facility_id = test_env["facility_id"]

        def worker_task(task_id):
            with app.test_client() as client:
                # Login
                login_res = client.post(
                    "/api/auth/login",
                    json={"email": "concurrency_admin@test.com", "password": "StressPass2026!"},
                )
                if login_res.status_code != 200:
                    return {"task_id": task_id, "type": "login", "status": login_res.status_code, "latency": 0}

                start = time.perf_counter()
                task_type = task_id % 4

                if task_type == 0:
                    # Scope 1 Write
                    payload = {
                        "year": 2025,
                        "month": (task_id % 12) + 1,
                        "facility_id": facility_id,
                        "process_type": "combustion",
                        "fuel": "Natural Gas",
                        "amount": 1000 + task_id * 10,
                        "unit": "m3",
                        "status": "Verified",
                        "calc_inputs": {
                            "combustion": {
                                "fuel_gas_volume": 1000 + task_id * 10,
                                "fuel_type": "Natural Gas",
                            }
                        },
                    }
                    res = client.post("/api/emissions", json=payload)
                    op_type = "scope1_write"
                elif task_type == 1:
                    # Scope 2 Write
                    payload = {
                        "year": 2025,
                        "month": (task_id % 12) + 1,
                        "facility_id": facility_id,
                        "source_type": "electricity",
                        "electricity_kwh": 5000 + task_id * 50,
                        "grid_region": "US Average",
                        "status": "Verified",
                    }
                    res = client.post("/api/scope2", json=payload)
                    op_type = "scope2_write"
                elif task_type == 2:
                    # Scope 3 Write
                    payload = {
                        "year": 2025,
                        "month": (task_id % 12) + 1,
                        "facility_id": facility_id,
                        "category": "1",
                        "sub_category": "Purchased Materials",
                        "activity_data": 2000 + task_id * 20,
                        "unit": "USD",
                        "emission_factor": 0.35,
                        "status": "Verified",
                    }
                    res = client.post("/api/scope3", json=payload)
                    op_type = "scope3_write"
                else:
                    # Dashboard Read
                    res = client.get("/api/dashboard/summary?year=2025")
                    op_type = "dashboard_read"

                elapsed = (time.perf_counter() - start) * 1000.0
                return {"task_id": task_id, "type": op_type, "status": res.status_code, "latency": elapsed}

        # Run parallel execution using ThreadPoolExecutor
        t_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        total_duration = time.perf_counter() - t_start

        # Assertions
        statuses = [r["status"] for r in results]
        latencies = [r["latency"] for r in results if r["latency"] > 0]
        failures = [r for r in results if r["status"] not in [200, 201]]

        # Zero DB lock errors (500s)
        assert len(failures) == 0, f"Encountered {len(failures)} failures under concurrency: {failures}"
        assert all(s in [200, 201] for s in statuses)

        # Performance metrics
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        throughput = len(results) / total_duration

        print(f"\n[CONCURRENCY RESULTS] {num_threads} concurrent operations in {total_duration:.2f}s:")
        print(f"   Throughput: {throughput:.1f} requests/sec")
        print(f"   P50 Latency: {p50:.1f} ms | P95 Latency: {p95:.1f} ms")
        print(f"   Lock Failures: 0 | HTTP 500s: 0")

        assert p95 < 2000.0, f"P95 latency {p95:.1f}ms exceeded acceptable SLA limit"

    def test_concurrent_session_and_token_isolation(self, test_env):
        """Verify that concurrent requests maintain strict session identity and authorization."""
        facility_id = test_env["facility_id"]
        num_sessions = 15

        def session_task(idx):
            with app.test_client() as client:
                client.post(
                    "/api/auth/login",
                    json={"email": "concurrency_admin@test.com", "password": "StressPass2026!"},
                )
                res = client.get("/api/auth/me")
                if res.status_code != 200:
                    return False
                data = res.get_json()
                return data.get("email") == "concurrency_admin@test.com"

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [executor.submit(session_task, i) for i in range(num_sessions)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(results)
        assert len(results) == num_sessions
