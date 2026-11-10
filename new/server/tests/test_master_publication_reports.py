"""
Master Publication Report Engine Integration Tests
==================================================
Tests the 3 reporting modes (National Corporate, Regional Asset, Cross-Basin Benchmark),
Excel benchmark exports, SHA-256 tamper-evident fingerprint headers, and authentication.
"""

import io
import pytest
import openpyxl
from app import app
from extensions import db, limiter
from models import User, Facility


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


def test_post_master_report_national(client, auth_headers):
    """Verifies generation of Consolidated Demo Operator Co. Corporate Master Report PDF."""
    res = client.post("/api/reports/master-report", json={
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
    res = client.post("/api/reports/master-report", json={
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
    res = client.post("/api/reports/master-report", json={
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
    res = client.post("/api/reports/master-report", json={
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
    res = client.post("/api/reports/master-report", json={
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



def test_master_report_advanced_chapters_and_base_year_recalculations(client, auth_headers):
    """Verifies that the Master Report includes Scope 3, OGMP 2.0, EU CBAM, and Base Year Recalculation."""
    import pypdfium2
    res = client.post("/api/reports/master-report", json={
        "mode": "regional",
        "region": "basin_alpha",
        "start_year": 2021,
        "end_year": 2025,
        "gwp_standard": "AR5",
        "language": "en"
    })
    assert res.status_code == 200
    pdf = pypdfium2.PdfDocument(res.data)
    assert len(pdf) >= 16
    all_text = " ".join([pdf[i].get_textpage().get_text_range() for i in range(len(pdf))])
    pdf.close()

    # Chapter 5: OGMP 2.0 & LDAR
    assert "OGMP 2.0 METHANE RECONCILIATION" in all_text
    assert "Level 4 Bottom-Up" in all_text or "Gold Standard" in all_text

    # Chapter 7: Scope 3 Value Chain
    assert "SCOPE 3 VALUE CHAIN EMISSIONS" in all_text
    assert "Category 1" in all_text or "GHG Protocol Category" in all_text

    # Chapter 10: EU CBAM & Decarbonization Economics
    assert "EU CBAM HYDROCARBON EXPORT EMBEDDINGS" in all_text
    assert "SEE Direct" in all_text or "Specific Embedded" in all_text

    # Chapter 12: Base Year Recalculation Audit Trail
    assert "Base Year Recalculation Audit Trail" in all_text or "Clause 6.4.1" in all_text
