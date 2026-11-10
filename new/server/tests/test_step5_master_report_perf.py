"""Step 5 Regression Tests: Master Report Performance, Agg Backend, 150 DPI,
Chart Caching, Merged Multi-Panel Figures, and Non-Blocking Background Jobs.
"""

import os
import tempfile
import time

import matplotlib
import matplotlib.pyplot as plt
import pytest
from app import app
from extensions import db, limiter
from models import Emission, Facility, ProductionData, User
from PIL import Image as PILImage


@pytest.fixture
def perf_client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test-secret-step5"
    app.config["RATELIMIT_ENABLED"] = False
    limiter.enabled = False

    with app.app_context():
        user = User.query.filter_by(email="step5_perf@example.org").first()
        if not user:
            user = User(
                email="step5_perf@example.org",
                fullName="Step 5 Perf Admin",
                orgName="Demo Operator Co.",
                sector="Energy",
                role="admin",
                location="Basin Alpha",
            )
            user.set_password("Step5PerfPass!1")
            db.session.add(user)

        fac = Facility.query.filter_by(code="STEP5-FAC-A1").first()
        if not fac:
            fac = Facility(
                name="Facility A-1 Step5",
                code="STEP5-FAC-A1",
                region="Basin Alpha",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.flush()
            db.session.add(
                Emission(
                    facility_id=fac.id,
                    year=2024,
                    month=6,
                    process_type="stationary_combustion",
                    fuel_type="Natural Gas",
                    quantity=1000.0,
                    unit="m3",
                    co2_emissions=200.0,
                    ch4_emissions=1.0,
                    n2o_emissions=0.05,
                    co2e_total=240.0,
                    status="Verified",
                )
            )
            db.session.add(
                ProductionData(
                    facility_id=fac.id,
                    year=2024,
                    month=6,
                    gross_gas_mmsm3=10.0,
                    crude_oil_mmboe=0.1,
                    total_production_mmboe=0.15,
                )
            )
        db.session.commit()

    with app.test_client() as client:
        resp = client.post(
            "/api/auth/login",
            json={"email": "step5_perf@example.org", "password": "Step5PerfPass!1"},
        )
        assert resp.status_code == 200
        yield client


def test_matplotlib_agg_backend_150_dpi_and_figure_cleanup_on_error():
    import services.master_report_charts as charts

    assert matplotlib.get_backend().lower() == "agg"
    assert charts.CHART_DPI == 150

    with pytest.raises(OSError):
        charts.generate_production_chart(
            [2024],
            [10.0],
            [0.5],
            out_path="/nonexistent_step5_dir_xyz/subdir/bad.png",
            language="en",
            use_cache=False,
        )
    assert plt.get_fignums() == [], "Matplotlib figure leaked after error"


def test_charts_render_150_dpi_and_cache_reuses_png():
    import services.master_report_charts as charts

    charts.clear_chart_cache()
    with tempfile.TemporaryDirectory() as tmp:
        out1 = os.path.join(tmp, "prod_1.png")
        out2 = os.path.join(tmp, "prod_2.png")

        charts.generate_production_chart([2023, 2024], [10.0, 12.0], [0.5, 0.6], out1, language="en")
        with PILImage.open(out1) as img:
            # 7.2 inches * 150 DPI = 1080px (300 DPI would be 2160px)
            assert img.width == 1080
            assert img.height == 480

        stats_before = charts.get_chart_cache_stats()
        charts.generate_production_chart([2023, 2024], [10.0, 12.0], [0.5, 0.6], out2, language="en")
        stats_after = charts.get_chart_cache_stats()

        assert stats_after["hits"] > stats_before["hits"]
        with open(out1, "rb") as f1, open(out2, "rb") as f2:
            assert f1.read() == f2.read()
        assert plt.get_fignums() == []


def test_consolidated_multi_panel_charts_render_cleanly():
    import services.master_report_charts as charts

    with tempfile.TemporaryDirectory() as tmp:
        p1 = os.path.join(tmp, "em_sangea.png")
        p2 = os.path.join(tmp, "int_poll.png")
        p3 = os.path.join(tmp, "glide_jv.png")

        charts.generate_emissions_sangea_panel_chart(
            years=[2023, 2024],
            s1_mmt=[0.4, 0.38],
            s2_mmt=[0.05, 0.04],
            combustion_t=[250000.0, 240000.0],
            flaring_t=[80000.0, 60000.0],
            fugitives_t=[40000.0, 35000.0],
            venting_t=[30000.0, 25000.0],
            out_path=p1,
            language="en",
        )
        charts.generate_intensities_pollutants_panel_chart(
            years=[2023, 2024],
            carbon_intensity_kg_boe=[18.5, 17.2],
            methane_intensity_pct=[0.18, 0.16],
            nox_t=[120.0, 110.0],
            co_t=[200.0, 185.0],
            so2_t=[15.0, 12.0],
            voc_t=[40.0, 35.0],
            out_path=p2,
            language="en",
        )
        charts.generate_glidepath_jv_panel_chart(
            target_projection={
                "historical_years": [2023, 2024],
                "historical_ghg_mmt": [0.45, 0.42],
                "proj_years": [2024, 2030],
                "glidepath_mmt": [0.42, 0.25],
                "target_2030_ghg_mmt": 0.25,
            },
            jv_equity={
                "partners": [{"partner_code": "DO", "partner_name": "Demo Operator Co.", "equity_share_pct": 100.0}],
                "annual_equity_timeline": [{"year": 2024, "partner_emissions": {"DO": {"total_ghg_tco2e": 420000.0}}}],
            },
            out_path=p3,
            language="en",
        )

        for p in (p1, p2, p3):
            assert os.path.exists(p) and os.path.getsize(p) > 10_000
        assert plt.get_fignums() == []


def test_post_master_report_runs_as_background_job_with_status_and_download(perf_client):
    t0 = time.perf_counter()
    res = perf_client.post(
        "/api/reports/master-report",
        json={
            "mode": "national",
            "start_year": 2024,
            "end_year": 2024,
            "gwp_standard": "AR5",
            "language": "en",
        },
    )
    post_elapsed = time.perf_counter() - t0

    assert res.status_code == 202, f"Expected 202 Accepted background job, got {res.status_code}"
    assert post_elapsed < 1.5, f"POST handler blocked HTTP request for {post_elapsed:.2f}s"

    payload = res.get_json()
    assert payload["job_id"]
    assert payload["status"] in ("queued", "running", "completed")
    assert payload["status_url"].startswith("/api/reports/master-report/jobs/")
    assert payload["download_url"].endswith("/download")

    # Poll status until completion
    deadline = time.perf_counter() + 30.0
    job_state = None
    while time.perf_counter() < deadline:
        st = perf_client.get(payload["status_url"])
        assert st.status_code == 200
        job_state = st.get_json()
        if job_state["status"] == "completed":
            break
        assert job_state["status"] != "failed", f"Job failed: {job_state}"
        time.sleep(0.1)

    assert job_state is not None and job_state["status"] == "completed"
    total_elapsed = time.perf_counter() - t0
    assert total_elapsed < 30.0, f"Master report exceeded 30s target: {total_elapsed:.2f}s"

    dl = perf_client.get(job_state["download_url"])
    assert dl.status_code == 200
    assert dl.content_type == "application/pdf"
    assert dl.data.startswith(b"%PDF")
    assert len(dl.data) > 50_000
    assert len(dl.headers.get("X-Report-SHA256", "")) == 64
    assert plt.get_fignums() == []
