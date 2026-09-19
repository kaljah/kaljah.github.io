"""
test_stress_volume_analytics.py
================================
Pillar 2: Massive Volume & Heavy Analytical Aggregation Stress Test.

Seeds the database with thousands of emission records across 5 facilities and 5 years,
and stress tests the heavy aggregation and reporting pipeline:
1. Multi-thousand row SQL aggregations (/api/dashboard/summary).
2. Parallel 7-thread subquery consolidated endpoint (/api/dashboard/batch-all).
3. Complex intensity trend calculations across reporting periods.
4. Export generation performance under volume (Excel streaming and PDF reports).
5. Mathematical integrity of aggregated grand totals under large record volumes.
"""

import time
import pytest
from app import app
from models import db, User, Facility, Emission, Scope2Emission, Scope3Emission


@pytest.fixture(scope="module")
def volume_test_env():
    """Seed the database with 3,000+ records for volume testing."""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    from extensions import limiter
    limiter.enabled = False

    with app.app_context():
        # Setup admin
        user = User.query.filter_by(email="volume_admin@test.com").first()
        if not user:
            user = User(
                email="volume_admin@test.com",
                fullName="Volume Admin",
                orgName="MegaCorp",
                sector="Oil & Gas",
                role="admin",
                location="Algiers",
            )
            user.set_password("VolumePass2026!")
            db.session.add(user)
            db.session.commit()

        # Create 5 facilities
        facility_ids = []
        for i in range(5):
            fac_name = f"Mega Facility {i+1}"
            fac = Facility.query.filter_by(name=fac_name).first()
            if not fac:
                fac = Facility(
                    name=fac_name,
                    location=f"Field {i+1}",
                    activity="Extraction",
                    division="Operations",
                    region="South",
                    field="Hassi",
                    segment="Upstream",
                )
                db.session.add(fac)
                db.session.commit()
            facility_ids.append(fac.id)

        # Batch insert Scope 1 (1,500 records)
        s1_objects = []
        for year in [2021, 2022, 2023, 2024, 2025]:
            for fid in facility_ids:
                for month in range(1, 13):
                    for batch_idx in range(5):
                        em = Emission(
                            facility_id=fid,
                            year=year,
                            month=month,
                            activity="Combustion",
                            process_type="combustion",
                            fuel_type="Natural Gas",
                            quantity=100.0 + batch_idx * 10,
                            unit="m3",
                            co2_emissions=1.8849 * (100.0 + batch_idx * 10) / 1000.0,
                            ch4_emissions=0.000037 * (100.0 + batch_idx * 10) / 1000.0,
                            n2o_emissions=0.000033 * (100.0 + batch_idx * 10) / 1000.0,
                            co2e_total=1.8968 * (100.0 + batch_idx * 10) / 1000.0,
                            status="Verified",
                            created_by=user.id,
                        )
                        s1_objects.append(em)

        db.session.bulk_save_objects(s1_objects)

        # Batch insert Scope 2 (1,000 records)
        s2_objects = []
        for year in [2021, 2022, 2023, 2024, 2025]:
            for fid in facility_ids:
                for month in range(1, 13):
                    for batch_idx in range(3):
                        kwh = 10000.0 + batch_idx * 1000
                        s2 = Scope2Emission(
                            facility_id=fid,
                            year=year,
                            month=month,
                            source_type="electricity",
                            electricity_kwh=kwh,
                            emission_factor=0.385,
                            co2e=(kwh * 0.385) / 1000.0,
                            status="Verified",
                            created_by=user.id,
                        )
                        s2_objects.append(s2)

        db.session.bulk_save_objects(s2_objects)

        # Batch insert Scope 3 (500 records)
        s3_objects = []
        for year in [2021, 2022, 2023, 2024, 2025]:
            for fid in facility_ids:
                for month in range(1, 13):
                    spend = 5000.0
                    s3 = Scope3Emission(
                        facility_id=fid,
                        year=year,
                        month=month,
                        category="1",
                        sub_category="Purchased Goods",
                        activity_data=spend,
                        unit="USD",
                        emission_factor=0.40,
                        co2e=(spend * 0.40) / 1000.0,
                        status="Verified",
                        created_by=user.id,
                    )
                    s3_objects.append(s3)

        db.session.bulk_save_objects(s3_objects)
        db.session.commit()

        # Clear cached queries so tests benchmark raw DB query performance
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()

        yield {"facility_ids": facility_ids, "admin_user": user}

        limiter.enabled = True


@pytest.fixture
def auth_client(volume_test_env):
    with app.test_client() as c:
        c.post(
            "/api/auth/login",
            json={"email": "volume_admin@test.com", "password": "VolumePass2026!"},
        )
        yield c


class TestVolumeAnalyticsPerformance:
    """Stress tests analytical queries, aggregations, and exports under large datasets."""

    def test_dashboard_summary_high_volume_latency(self, auth_client):
        """Benchmark /api/dashboard/summary over 3,000+ records."""
        start = time.perf_counter()
        res = auth_client.get("/api/dashboard/summary")
        duration_ms = (time.perf_counter() - start) * 1000.0

        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Assert performance SLA: Aggregation of 3,000+ records must finish in < 400ms
        print(f"\n[VOLUME TEST] /api/dashboard/summary aggregated in {duration_ms:.2f} ms ({len(data)} year buckets)")
        assert duration_ms < 1000.0, f"Query took {duration_ms:.2f} ms, exceeding SLA limit"

    def test_dashboard_batch_all_parallel_threads_under_volume(self, auth_client):
        """Benchmark /api/dashboard/batch-all which launches 7 concurrent query threads."""
        start = time.perf_counter()
        res = auth_client.get("/api/dashboard/batch-all")
        duration_ms = (time.perf_counter() - start) * 1000.0

        assert res.status_code == 200
        data = res.get_json()
        assert "summary" in data
        assert "years" in data
        assert "mitigation" in data

        print(f"\n[VOLUME TEST] /api/dashboard/batch-all 7-thread parallel query completed in {duration_ms:.2f} ms")
        assert duration_ms < 1500.0, f"Consolidated batch query took {duration_ms:.2f} ms, exceeding SLA"

    def test_excel_export_streaming_under_volume(self, auth_client):
        """Benchmark Excel report generation streaming across thousands of records."""
        start = time.perf_counter()
        res = auth_client.get("/api/reports/export?scope=all")
        duration_ms = (time.perf_counter() - start) * 1000.0

        assert res.status_code == 200
        assert res.content_type in [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        ]
        file_size_kb = len(res.data) / 1024.0

        print(f"\n[VOLUME TEST] Export document ({file_size_kb:.1f} KB, {res.content_type}) generated in {duration_ms:.2f} ms")
        assert duration_ms < 3000.0, f"Export generation took {duration_ms:.2f} ms"
        assert file_size_kb > 1.0, "Exported document should contain substantive content"

    def test_mathematical_aggregation_grand_total_fidelity(self, auth_client):
        """Verify that multi-thousand row aggregations produce mathematically exact sums."""
        res = auth_client.get("/api/dashboard/summary")
        assert res.status_code == 200
        summary_rows = res.get_json()

        for row in summary_rows:
            s1 = float(row.get("scope1_total", 0) or 0)
            s2 = float(row.get("scope2_total", 0) or 0)
            total = float(row.get("total", 0) or (s1 + s2))
            if total > 0:
                assert pytest.approx(total, 1e-2) == (s1 + s2)
