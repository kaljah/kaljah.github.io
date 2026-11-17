"""
Master Publication Report Engine Integration Tests
==================================================
Tests the 3 reporting modes (National Corporate, Regional Asset, Cross-Basin Benchmark),
Excel benchmark exports, SHA-256 tamper-evident fingerprint headers, and authentication.
"""

import io
import time
import pytest
import openpyxl
from app import app
from extensions import db, limiter
from models import User, Facility


def _fetch_master_report_via_job(client, payload, timeout_s: float = 30.0):
    """Enqueues a Master Report background job (202), polls status until completed, and downloads the PDF."""
    post_res = client.post("/api/reports/master-report", json=payload)
    assert post_res.status_code == 202, f"Expected 202 Accepted job enqueue, got {post_res.status_code}"
    job = post_res.get_json()
    assert job["job_id"]
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        st = client.get(job["status_url"])
        assert st.status_code == 200
        st_data = st.get_json()
        if st_data["status"] == "completed":
            dl = client.get(st_data["download_url"])
            return dl
        assert st_data["status"] != "failed", f"Master report job failed: {st_data}"
        time.sleep(0.1)
    raise AssertionError(f"Master report job {job['job_id']} did not finish within {timeout_s}s")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["RATELIMIT_ENABLED"] = False
    limiter.enabled = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def auth_headers(client):
    with app.app_context():
        user = User.query.filter_by(email="admin_rep@test.com").first()
        if not user:
            user = User(
                email="admin_rep@test.com",
                fullName="Admin Reporter",
                orgName="Demo Operator Co. Test",
                sector="Energy",
                role="admin",
                location="Basin Alpha",
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

    resp = client.post("/api/auth/login", json={"email": "admin_rep@test.com", "password": "password123"})
    assert resp.status_code == 200


def test_get_master_report_regions(client, auth_headers):
    """Only regions that have facilities in the database are listed (plus "national"), each with its facility count."""
    codes = ("REGTEST-ALPHA", "REGTEST-BETA-A", "REGTEST-BETA-B", "REGTEST-COAST")
    with app.app_context():
        Facility.query.filter(Facility.code.in_(codes)).delete(synchronize_session=False)
        db.session.add_all([
            Facility(name="Facility A-1 Test", code="REGTEST-ALPHA", region="Basin Alpha", segment="Upstream"),
            Facility(name="Facility B-2 Test A", code="REGTEST-BETA-A", region="Basin Beta", segment="Upstream"),
            Facility(name="Facility B-2 Test B", code="REGTEST-BETA-B", region="Basin Beta", segment="Upstream"),
            Facility(name="Facility C-3 Test", code="REGTEST-COAST", region="Coastal Terminal", segment="Midstream"),
        ])
        db.session.commit()
    try:
        res = client.get("/api/reports/master-report/regions")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        by_key = {r["key"]: r for r in data["regions"]}
        assert {"national", "basin_alpha", "basin_beta", "coastal_terminal"} <= set(by_key)
        assert all("facility_count" in r for r in data["regions"])
        assert by_key["basin_alpha"]["facility_count"] >= 1 and "Facility A-1 Test" in by_key["basin_alpha"]["facility_names"]
        assert by_key["basin_beta"]["facility_count"] >= 2
        assert {"Facility B-2 Test A", "Facility B-2 Test B"} <= set(by_key["basin_beta"]["facility_names"])
        assert "Facility C-3 Test" in by_key["coastal_terminal"]["facility_names"]
        # every facility sits in the national roll-up
        assert by_key["national"]["facility_count"] >= 4
    finally:
        with app.app_context():
            Facility.query.filter(Facility.code.in_(codes)).delete(synchronize_session=False)
            db.session.commit()


def test_get_master_report_regions_no_duplicate_keys_on_location_match(client, auth_headers):
    """Facilities with region=None and location='Basin Alpha' must merge under basin_alpha with unique keys."""
    codes = ("REGLOC-ALPHA-1", "REGLOC-ALPHA-2")
    with app.app_context():
        Facility.query.filter(Facility.code.in_(codes)).delete(synchronize_session=False)
        db.session.add_all([
            Facility(name="Alpha Explicit Facility", code="REGLOC-ALPHA-1", region="Basin Alpha", segment="Upstream"),
            Facility(name="Alpha Location-Only Facility", code="REGLOC-ALPHA-2", region=None, location="Basin Alpha", segment="Upstream"),
        ])
        db.session.commit()
    try:
        res = client.get("/api/reports/master-report/regions")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        regions = data["regions"]
        keys = [r["key"] for r in regions]
        assert len(keys) == len(set(keys)), f"Duplicate region keys returned: {keys}"
        by_key = {r["key"]: r for r in regions}
        assert "basin_alpha" in by_key
        assert {"Alpha Explicit Facility", "Alpha Location-Only Facility"} <= set(by_key["basin_alpha"]["facility_names"])
        assert by_key["basin_alpha"]["facility_count"] >= 2
    finally:
        with app.app_context():
            Facility.query.filter(Facility.code.in_(codes)).delete(synchronize_session=False)
            db.session.commit()


def test_post_master_report_national(client, auth_headers):
    """Verifies generation of Consolidated Demo Operator Co. Corporate Master Report PDF."""
    res = _fetch_master_report_via_job(client, {
        "mode": "national",
        "start_year": 2023,
        "end_year": 2025,
        "gwp_standard": "AR5",
    })
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert "X-Report-SHA256" in res.headers
    assert len(res.headers["X-Report-SHA256"]) == 64
    assert res.data.startswith(b"%PDF")
    assert len(res.data) > 50000


def test_post_master_report_regional(client, auth_headers):
    """Verifies generation of Regional Asset Master Report PDF for Basin Alpha."""
    res = _fetch_master_report_via_job(client, {
        "mode": "regional",
        "region": "basin_alpha",
        "start_year": 2023,
        "end_year": 2025,
        "gwp_standard": "AR5",
    })
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert "X-Report-SHA256" in res.headers
    assert res.data.startswith(b"%PDF")


def test_post_master_report_comparison(client, auth_headers):
    """Verifies generation of Multi-Region Cross-Basin Benchmark PDF."""
    res = _fetch_master_report_via_job(client, {
        "mode": "comparison",
        "start_year": 2023,
        "end_year": 2025,
        "gwp_standard": "AR5",
    })
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert "X-Report-SHA256" in res.headers
    assert res.data.startswith(b"%PDF")


def test_post_benchmark_excel(client, auth_headers):
    """Verifies export of cross-basin benchmark Excel workbook."""
    res = client.post("/api/reports/master-report/benchmark-excel", json={
        "start_year": 2023,
        "end_year": 2025,
        "gwp_standard": "AR5",
    })
    assert res.status_code == 200
    assert "X-Report-SHA256" in res.headers

    wb = openpyxl.load_workbook(io.BytesIO(res.data))
    assert "Cross-Basin Benchmark" in wb.sheetnames
    ws = wb["Cross-Basin Benchmark"]
    assert "DEMO OPERATOR CO." in str(ws.cell(row=1, column=1).value)


def test_post_master_report_french_localization(client, auth_headers):
    """Verifies generation of French-localized Master Report PDF with verified terminology."""
    import pypdfium2
    res = _fetch_master_report_via_job(client, {
        "mode": "national",
        "language": "fr",
        "start_year": 2023,
        "end_year": 2025,
        "gwp_standard": "AR5",
    })
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert "Demo Operator Co._National_National_Master_Report_2023_2025_FR.pdf" in res.headers.get("Content-Disposition", "")
    assert res.data.startswith(b"%PDF")

    # Read extracted text from first page
    pdf = pypdfium2.PdfDocument(res.data)
    first_page_text = pdf[0].get_textpage().get_text_range()
    assert "RAPPORT MAÎTRE D'ENTREPRISE" in first_page_text or "CONSOLIDÉ" in first_page_text
    assert "Période de Déclaration" in first_page_text or "Norme Comptable" in first_page_text
    pdf.close()


def test_post_master_report_basin_alpha_tripartite_jv_and_glidepath(client, auth_headers):
    """Verifies that Basin Alpha asset report includes tripartite flaring, 2030 glidepath, and JV equity."""
    from models import db, Facility, Emission, FlaringDetail, JvPartner, FacilityEquityShare, ProductionData
    from datetime import date
    from routes.equity_routes import ensure_default_partners
    with app.app_context():
        ensure_default_partners()
        p1 = JvPartner.query.filter_by(name="Demo Operator Co.").first()
        p2 = JvPartner.query.filter_by(name="Demo JV Partner A").first()
        for code, fname in [("FA1-JV", "Facility A-1"), ("FB2-JV", "Facility B-2")]:
            fac = Facility.query.filter_by(name=fname).first()
            if not fac:
                fac = Facility(name=fname, code=code, region="Basin Alpha", segment="Upstream", equity_share_pct=60.0)
                db.session.add(fac)
                db.session.flush()
            if p1 and not FacilityEquityShare.query.filter_by(facility_id=fac.id, partner_id=p1.id).first():
                db.session.add(FacilityEquityShare(facility_id=fac.id, partner_id=p1.id, equity_share_pct=60.0, effective_start_date=date(2023, 1, 1)))
            if p2 and not FacilityEquityShare.query.filter_by(facility_id=fac.id, partner_id=p2.id).first():
                db.session.add(FacilityEquityShare(facility_id=fac.id, partner_id=p2.id, equity_share_pct=40.0, effective_start_date=date(2023, 1, 1)))
            for yr in (2023, 2024, 2025):
                if not Emission.query.filter_by(facility_id=fac.id, year=yr).first():
                    db.session.add(Emission(facility_id=fac.id, year=yr, month=6, process_type="flaring", fuel_type="Associated Gas", quantity=100.0, unit="mscf", co2_emissions=500.0, ch4_emissions=5.0, n2o_emissions=0.1, co2e_total=640.0, status="Verified"))
                if not FlaringDetail.query.filter_by(facility_id=fac.id, year=yr).first():
                    db.session.add(FlaringDetail(facility_id=fac.id, year=yr, month=6, routine_knm3=12.0, non_routine_knm3=4.0, safety_knm3=1.5, total_knm3=17.5, measured_dre_pct=98.5, status="Verified"))
                if not ProductionData.query.filter_by(facility_id=fac.id, year=yr).first():
                    db.session.add(ProductionData(facility_id=fac.id, year=yr, month=6, oil_amount=10000.0, gas_amount=25000.0, total_production_mmboe=0.15, saleable_production_mmboe=0.14))
        db.session.commit()

    import pypdfium2
    res = _fetch_master_report_via_job(client, {
        "mode": "regional",
        "region": "basin_alpha",
        "start_year": 2023,
        "end_year": 2025,
        "gwp_standard": "AR5",
    })
    assert res.status_code == 200
    assert res.content_type == "application/pdf"

    pdf = pypdfium2.PdfDocument(res.data)
    all_text = " ".join([pdf[i].get_textpage().get_text_range() for i in range(len(pdf))])
    pdf.close()

    # Feature 1: JV Partner Equity Allocation
    assert "JOINT VENTURE PARTNER EQUITY" in all_text
    assert "Demo Operator Co." in all_text
    assert "Demo JV Partner A" in all_text or "Demo JV Partner B" in all_text or "TotalEnergies" in all_text

    # Feature 2: Tripartite Flaring Breakdown
    assert "Routine" in all_text
    assert "Non-Routine" in all_text
    assert "Safety" in all_text

    # Feature 3: 2030 Target Glidepath
    assert "2030 DECARBONIZATION TARGET TRAJECTORY" in all_text
    assert "Zero Routine Flaring" in all_text

    # Feature 4: QA/QC Verification, Uncertainty & Statutory Regimes
    assert "QA/QC VERIFICATION, UNCERTAINTY" in all_text
    assert "Executive Decree 21-330" in all_text
    assert "Overall Inventory Uncertainty" in all_text or "Tier 3" in all_text

    # Feature 5: Facility-Level Disaggregated Appendix
    assert "DISAGGREGATED FACILITY-LEVEL" in all_text
    assert "Facility A-1" in all_text
    assert "Facility B-2" in all_text


def test_unauthenticated_guard(client):
    """Ensures unauthorized callers are blocked."""
    client.post("/api/auth/logout")
    res = client.post("/api/reports/master-report", json={"mode": "national"})
    assert res.status_code in (401, 302)



def test_master_report_advanced_chapters_and_base_year_recalculations(client):
    """Verifies honest empty states when Scope3/OGMP/CBAM/Recalc are unseeded AND real DB data when seeded."""
    import uuid
    import pypdfium2
    from models import (
        BaseYearRecalculation,
        CbamProductExport,
        Emission,
        OgmpSurvey,
        ProductionData,
        Scope3Emission,
    )

    tag = uuid.uuid4().hex[:8]
    tid = f"adv_{tag}"
    uid = None
    fac_id = None
    ogmp_id = None
    s3_id = None
    cbam_id = None
    recalc_id = None

    with app.app_context():
        user = User(
            email=f"adv_{tag}@test.com",
            fullName="Advanced Chapter Admin",
            orgName="Isolated Test Operator",
            sector="Energy",
            role="admin",
            status="active",
            location="Basin Alpha",
            tenant_id=tid,
        )
        user.set_password("AdvTestPass!123")
        db.session.add(user)
        db.session.flush()
        uid = user.id

        fac = Facility(
            name=f"Adv Ch Basin Alpha {tag}",
            code=f"ADV-BA-{tag}",
            region="Basin Alpha",
            segment="Upstream",
            equity_share_pct=100.0,
            tenant_id=tid,
        )
        db.session.add(fac)
        db.session.flush()
        fac_id = fac.id

        db.session.add(
            Emission(
                facility_id=fac.id,
                year=2024,
                month=6,
                process_type="stationary_combustion",
                fuel_type="Natural Gas",
                quantity=1000.0,
                unit="m3",
                co2_emissions=500.0,
                ch4_emissions=1.0,
                n2o_emissions=0.05,
                co2e_total=540.0,
                status="Verified",
                created_by=user.id,
                is_test=False,
            )
        )
        db.session.add(
            ProductionData(
                facility_id=fac.id,
                year=2024,
                month=6,
                oil_amount=5000.0,
                gas_amount=15000.0,
                gross_gas_mmsm3=5.0,
                total_production_mmboe=0.1,
            )
        )
        db.session.commit()

    login_res = client.post(
        "/api/auth/login",
        json={"email": f"adv_{tag}@test.com", "password": "AdvTestPass!123"},
    )
    assert login_res.status_code == 200

    try:
        # Part A: Unseeded tables -> honest empty-state disclosure, zero fabricated fallback values
        res_empty = _fetch_master_report_via_job(client, {
            "mode": "regional",
            "region": "basin_alpha",
            "start_year": 2021,
            "end_year": 2025,
            "gwp_standard": "AR5",
            "language": "en",
        })
        assert res_empty.status_code == 200
        pdf_e = pypdfium2.PdfDocument(res_empty.data)
        assert len(pdf_e) >= 14
        empty_text = " ".join(" ".join([pdf_e[i].get_textpage().get_text_range() for i in range(len(pdf_e))]).split())
        pdf_e.close()

        assert "OGMP 2.0 METHANE RECONCILIATION" in empty_text
        assert "SCOPE 3 VALUE CHAIN EMISSIONS" in empty_text
        assert "EU CBAM HYDROCARBON EXPORT EMBEDDINGS" in empty_text
        assert "Base Year Recalculation" in empty_text or "Clause 6.4.1" in empty_text
        assert "NO RECORDS / NOT APPLICABLE IN SCOPE" in empty_text or "No Verified Scope 3" in empty_text
        for fabricated in ("Aerial LiDAR", "Bridger Photonics", "483,084", "12,070", "Sahara Blend Export Crude", "309,500"):
            assert fabricated not in empty_text, f"Fabricated fallback leaked into unseeded report: {fabricated}"

        # Part B: Seed real DB records -> chapters dynamically render real values
        with app.app_context():
            ogmp = OgmpSurvey(
                facility_id=fac_id,
                year=2024,
                survey_date="2024-06-10",
                survey_type="Drone OGI",
                instrument_vendor=f"CleanSky-{tag}",
                measured_rate_kg_hr=2.5,
                estimated_annual_tch4=21.9,
                bottom_up_tch4=23.0,
                variance_pct=-4.8,
                reconciliation_status="Reconciled",
                status="reported",
            )
            s3 = Scope3Emission(
                facility_id=fac_id,
                year=2024,
                month=6,
                category="Category 1: Purchased Goods",
                sub_category=f"Pipeline Steel {tag}",
                activity_data=100.0,
                unit="tonnes",
                emission_factor=2.1,
                co2e=210.0,
                calculation_method="Supplier Primary Data (Tier 2)",
                data_quality="High",
                status="Verified",
            )
            cbam = CbamProductExport(
                facility_id=fac_id,
                year=2024,
                month=6,
                product_name=f"Methanol-{tag}",
                cn_code="2905 11 00",
                quantity_tonnes=5000.0,
                export_destination="EU-NL",
                quarter="Q2",
                specific_embedded_direct=0.45,
                specific_embedded_indirect=0.05,
                carbon_price_paid_eur=10.0,
            )
            recalc = BaseYearRecalculation(
                year=2021,
                reason=f"Boundary alignment audit {tag}",
                previous_emissions=100000.0,
                adjusted_emissions=104000.0,
                tenant_id=tid,
            )
            db.session.add_all([ogmp, s3, cbam, recalc])
            db.session.commit()
            ogmp_id, s3_id, cbam_id, recalc_id = ogmp.id, s3.id, cbam.id, recalc.id

        res_pop = _fetch_master_report_via_job(client, {
            "mode": "regional",
            "region": "basin_alpha",
            "start_year": 2021,
            "end_year": 2025,
            "gwp_standard": "AR5",
            "language": "en",
        })
        assert res_pop.status_code == 200
        pdf_p = pypdfium2.PdfDocument(res_pop.data)
        assert len(pdf_p) >= 14
        pop_text = " ".join(" ".join([pdf_p[i].get_textpage().get_text_range() for i in range(len(pdf_p))]).split())
        pdf_p.close()

        assert f"CleanSky-{tag}" in pop_text or "Drone OGI" in pop_text
        assert "Category 1" in pop_text and f"Pipeline Steel {tag}" in pop_text
        assert f"Methanol-{tag}" in pop_text
        assert "SEE Direct" in pop_text or "Specific Embedded" in pop_text
        assert f"Boundary alignment audit {tag}" in pop_text
    finally:
        client.post("/api/auth/logout")
        with app.app_context():
            db.session.rollback()
            if ogmp_id:
                OgmpSurvey.query.filter_by(id=ogmp_id).delete(synchronize_session=False)
            if s3_id:
                Scope3Emission.query.filter_by(id=s3_id).delete(synchronize_session=False)
            if cbam_id:
                CbamProductExport.query.filter_by(id=cbam_id).delete(synchronize_session=False)
            if recalc_id:
                BaseYearRecalculation.query.filter_by(id=recalc_id).delete(synchronize_session=False)
            if fac_id:
                Emission.query.filter_by(facility_id=fac_id).delete(synchronize_session=False)
                ProductionData.query.filter_by(facility_id=fac_id).delete(synchronize_session=False)
                Facility.query.filter_by(id=fac_id).delete(synchronize_session=False)
            if uid:
                User.query.filter_by(id=uid).delete(synchronize_session=False)
            db.session.commit()
