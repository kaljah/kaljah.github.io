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


def test_chart_process_overview_dollar_math_safe():
    """Facility names containing unescaped '$' must not trigger Matplotlib mathtext parser crashes."""
    import services.master_report_charts as charts

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "pfd_dollar.png")
        charts.generate_process_overview_diagram(
            r"Fac $\unknown$ <tag> & CO2",
            out,
            language="en",
            use_cache=False,
        )
        assert os.path.exists(out) and os.path.getsize(out) > 5_000
        assert plt.get_fignums() == []


def test_master_report_skips_unused_empty_facility_pfds_and_scales_fast(monkeypatch):
    """Master report PDF must skip rendering PFDs for empty facilities and bulk-query without N+1 bottlenecks."""
    import uuid

    import services.master_report_charts as charts
    import services.master_report_engine as engine
    from models import EmissionSource

    charts.clear_chart_cache()
    tenant_id = f"perf_b_{uuid.uuid4().hex[:8]}"
    created_fac_ids = []

    with app.app_context():
        active_fac = Facility(
            name="Perf Active CPF",
            code=f"PERF-ACT-{tenant_id}",
            region="Basin Alpha",
            segment="Upstream",
            tenant_id=tenant_id,
        )
        db.session.add(active_fac)
        db.session.flush()
        created_fac_ids.append(active_fac.id)

        db.session.add(
            EmissionSource(
                facility_id=active_fac.id,
                name="Turbine A",
                type="stationary_combustion",
                equipment_id="TURB-A",
            )
        )
        db.session.add(
            Emission(
                facility_id=active_fac.id,
                year=2024,
                month=6,
                process_type="stationary_combustion",
                equipment_id="TURB-A",
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
                facility_id=active_fac.id,
                year=2024,
                month=6,
                gross_gas_mmsm3=10.0,
                crude_oil_mmboe=0.1,
                total_production_mmboe=0.15,
            )
        )

        empties = [
            Facility(
                name=f"Perf Empty Fac {i}",
                code=f"PERF-EMP-{tenant_id}-{i}",
                region="Basin Alpha",
                segment="Upstream",
                tenant_id=tenant_id,
            )
            for i in range(120)
        ]
        db.session.add_all(empties)
        db.session.flush()
        created_fac_ids.extend([f.id for f in empties])
        db.session.commit()

    pfd_calls = []
    orig_pfd = engine.generate_process_overview_diagram

    def _spy_pfd(facility_name, out_path, *args, **kwargs):
        pfd_calls.append(facility_name)
        return orig_pfd(facility_name, out_path, *args, **kwargs)

    monkeypatch.setattr(engine, "generate_process_overview_diagram", _spy_pfd)

    try:
        with app.app_context():
            t0 = time.perf_counter()
            buf = engine.generate_master_publication_pdf(
                mode="national",
                region_key=None,
                start_year=2024,
                end_year=2024,
                gwp_standard="AR5",
                language="en",
                tenant_id=tenant_id,
            )
            elapsed = time.perf_counter() - t0
            assert buf.getvalue().startswith(b"%PDF")
            assert pfd_calls == ["Perf Active CPF"], (
                f"Expected PFD rendering only for active facility, got {len(pfd_calls)} calls"
            )
            assert elapsed < 10.0, f"121-facility master report took {elapsed:.2f}s (expected < 10s)"
    finally:
        with app.app_context():
            EmissionSource.query.filter(EmissionSource.facility_id.in_(created_fac_ids)).delete(synchronize_session=False)
            Emission.query.filter(Emission.facility_id.in_(created_fac_ids)).delete(synchronize_session=False)
            ProductionData.query.filter(ProductionData.facility_id.in_(created_fac_ids)).delete(synchronize_session=False)
            Facility.query.filter(Facility.id.in_(created_fac_ids)).delete(synchronize_session=False)
            db.session.commit()


def test_appendices_skip_zero_activity_facilities_and_scale_fast():
    """Appendices B & C must skip empty zero-activity facilities even with 12 zero-filled monthly rows."""
    from reportlab.platypus import Paragraph
    from services.master_report_appendices import (
        build_facility_appendix_elements,
        build_subannual_timeseries_elements,
    )
    from services.master_report_engine import _build_styles

    def _q_rows(co2e: float, boe: float):
        return [
            {
                "quarter": f"Qtr{q}",
                "co2e": co2e,
                "co2": co2e * 0.9,
                "ch4": 0.1 if co2e else 0.0,
                "n2o": 0.01 if co2e else 0.0,
                "oil_bbl": boe * 0.5,
                "gas_mscf": boe * 0.5,
                "total_boe": boe,
                "intensity_co2e_boe": (co2e / boe) if boe else 0.0,
                "energy_hhv": boe * 1e6,
                "daily_avg_co2e": co2e / 90.0,
            }
            for q in range(1, 5)
        ]

    def _m_rows(co2e: float, boe: float):
        return [
            {
                "month": m,
                "co2e": co2e,
                "co2": co2e * 0.9,
                "ch4": 0.01 if co2e else 0.0,
                "n2o": 0.001 if co2e else 0.0,
                "oil_bbl": boe * 0.5,
                "gas_mscf": boe * 0.5,
                "total_boe": boe,
                "intensity_co2e_boe": (co2e / boe) if boe else 0.0,
                "energy_hhv": boe * 1e6,
                "daily_avg_co2e": co2e / 30.0,
            }
            for m in range(1, 13)
        ]

    def _zero_bd(i: int):
        return {
            "name": f"ZeroFac-{i}",
            "code": f"ZF-{i}",
            "region": "Basin Alpha",
            "timeline": [
                {
                    "year": 2024,
                    "gross_gas_mmsm3": 0.0,
                    "liquid_mmbbl": 0.0,
                    "total_mmboe": 0.0,
                    "scope1_t": 0.0,
                    "scope2_t": 0.0,
                    "total_ghg_t": 0.0,
                    "flaring_mmsm3": 0.0,
                    "routine_mmsm3": 0.0,
                    "flaring_intensity_pct": 0.0,
                    "carbon_intensity_kg_boe": 0.0,
                }
            ],
        }

    subannual = {
        "Active-CPF": {
            "has_monthly_data": False,
            "quarterly_rows": _q_rows(250.0, 1000.0),
            "monthly_rows": _m_rows(0.0, 0.0),
        }
    }
    breakdowns = [
        {
            "name": "Active-CPF",
            "code": "ACT-1",
            "region": "Basin Alpha",
            "timeline": [
                {
                    "year": 2024,
                    "gross_gas_mmsm3": 10.0,
                    "liquid_mmbbl": 1.0,
                    "total_mmboe": 2.0,
                    "scope1_t": 1000.0,
                    "scope2_t": 50.0,
                    "total_ghg_t": 1050.0,
                    "flaring_mmsm3": 0.05,
                    "routine_mmsm3": 0.01,
                    "flaring_intensity_pct": 0.5,
                    "carbon_intensity_kg_boe": 12.0,
                }
            ],
        }
    ]
    for i in range(350):
        subannual[f"ZeroFac-{i}"] = {
            "has_monthly_data": False,
            "quarterly_rows": _q_rows(0.0, 0.0),
            "monthly_rows": _m_rows(0.0, 0.0),
        }
        breakdowns.append(_zero_bd(i))

    styles = _build_styles()
    sub_elems = build_subannual_timeseries_elements({"subannual_time_series": subannual}, styles, lang="en")
    fac_elems = build_facility_appendix_elements({"facility_breakdowns": breakdowns}, styles, lang="en")

    sub_text = "\n".join(el.getPlainText() for el in sub_elems if isinstance(el, Paragraph))
    fac_text = "\n".join(el.getPlainText() for el in fac_elems if isinstance(el, Paragraph))

    assert "Active-CPF" in sub_text
    assert "ZeroFac-" not in sub_text
    assert len(sub_elems) < 20

    assert "Active-CPF" in fac_text
    assert "ZeroFac-" not in fac_text
    assert len(fac_elems) < 20

    zero_only_sub = {f"ZeroFac-{i}": subannual[f"ZeroFac-{i}"] for i in range(20)}
    zero_only_bd = [_zero_bd(i) for i in range(20)]
    assert build_subannual_timeseries_elements({"subannual_time_series": zero_only_sub}, styles, lang="en") == []
    assert build_facility_appendix_elements({"facility_breakdowns": zero_only_bd}, styles, lang="en") == []


def test_cold_pfds_and_large_appendix_tables_scale_within_budget():
    """Rendering 40 distinct cold PFDs + large Appendix A/B tables must complete fast without bloated Paragraph cells."""
    import io

    import services.master_report_charts as charts
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table
    from services.master_report_appendices import (
        build_granular_source_ledger_elements,
        build_subannual_timeseries_elements,
    )
    from services.master_report_engine import _build_styles

    # 1. Cold PFD scaling: 40 distinct facility names without disk cache must finish < 2.5s
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.perf_counter()
        sizes = []
        for i in range(40):
            out = os.path.join(tmp, f"pfd_{i}.png")
            charts.generate_process_overview_diagram(f"Scale Facility {i}", out, language="en", use_cache=False)
            sizes.append(os.path.getsize(out))
        pfd_elapsed = time.perf_counter() - t0

    assert all(sz > 50_000 for sz in sizes), f"Expected crisp >50KB PFD PNGs, min={min(sizes)}"
    assert plt.get_fignums() == []
    assert pfd_elapsed < 2.5, f"40 cold PFDs took {pfd_elapsed:.2f}s (expected < 2.5s)"

    # 2. Large Appendix A + B scaling: numeric cells must be plain strings rather than Paragraph objects
    rows = [
        {
            "facility_id": 1,
            "facility_name": "Scale Facility",
            "source_name": f"Turbine-{i}",
            "equipment_id": f"EQ-{i}",
            "module": "Stationary Combustion",
            "scope": "Scope 1",
            "quantity": 1000.0 + i,
            "unit": "m3",
            "co2": 200.0 + i,
            "ch4": 1.0,
            "n2o": 0.05,
            "co2e": 240.0 + i,
        }
        for i in range(1500)
    ]
    subannual = {
        f"SubFac-{i}": {
            "has_monthly_data": False,
            "quarterly_rows": [
                {
                    "quarter": f"Qtr{q}",
                    "co2e": 100.0,
                    "co2": 90.0,
                    "ch4": 0.2,
                    "n2o": 0.01,
                    "oil_bbl": 100.0,
                    "gas_mscf": 500.0,
                    "total_boe": 180.0,
                    "intensity_co2e_boe": 0.55,
                    "energy_hhv": 1e8,
                    "daily_avg_co2e": 1.1,
                }
                for q in range(1, 5)
            ],
            "monthly_rows": [{"co2e": 0.0, "total_boe": 0.0} for _ in range(12)],
        }
        for i in range(40)
    }

    styles = _build_styles()
    t1 = time.perf_counter()
    elems = []
    elems.extend(
        build_granular_source_ledger_elements(
            {"granular_source_ledger": {"total_sources_count": len(rows), "ledger_by_facility": {"Scale Facility": rows}}},
            styles,
            lang="en",
        )
    )
    elems.extend(build_subannual_timeseries_elements({"subannual_time_series": subannual}, styles, lang="en"))
    tables = [el for el in elems if isinstance(el, Table)]
    assert tables
    first_ledger_row = tables[0]._cellvalues[1]
    assert isinstance(first_ledger_row[0], str)
    assert isinstance(first_ledger_row[4], str)
    assert isinstance(first_ledger_row[9], str)
    first_sub_row = tables[1]._cellvalues[1]
    assert all(isinstance(cell, str) for cell in first_sub_row)

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4).build(elems)
    build_elapsed = time.perf_counter() - t1
    assert buf.getvalue().startswith(b"%PDF")
    assert build_elapsed < 4.5, f"Large Appendix A+B build took {build_elapsed:.2f}s (expected < 4.5s)"
