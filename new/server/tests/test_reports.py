import io
import pytest
import openpyxl
from app import app
from extensions import db, limiter
from models import User, Facility, Emission, Scope2Emission, Scope3Emission


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
def test_setup():
    with app.app_context():
        # Admin
        admin = User.query.filter_by(email="admin_rep@test.com").first()
        if not admin:
            admin = User(
                email="admin_rep@test.com",
                fullName="Admin Reporter",
                orgName="Sonatrach Test",
                sector="Energy",
                role="admin",
                location="Hassi Messaoud",
            )
            admin.set_password("password123")
            db.session.add(admin)
            db.session.commit()
        else:
            admin.role = "admin"
            admin.set_password("password123")
            db.session.commit()

        # IT Admin
        it_admin = User.query.filter_by(email="it_rep@test.com").first()
        if not it_admin:
            it_admin = User(
                email="it_rep@test.com",
                fullName="IT Admin Reporter",
                orgName="Sonatrach Test",
                sector="IT",
                role="it_admin",
                location="Algiers",
            )
            it_admin.set_password("password123")
            db.session.add(it_admin)
            db.session.commit()
        else:
            it_admin.role = "it_admin"
            it_admin.set_password("password123")
            db.session.commit()

        # Regular user
        user = User.query.filter_by(email="user_rep@test.com").first()
        if not user:
            user = User(
                email="user_rep@test.com",
                fullName="Regular Reporter",
                orgName="Sonatrach Test",
                sector="Energy",
                role="user",
                location="Hassi Messaoud",
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
        else:
            user.role = "user"
            user.set_password("password123")
            db.session.commit()

        # Facility
        fac = Facility.query.filter_by(name="Report Test Facility").first()
        if not fac:
            fac = Facility(
                name="Report Test Facility",
                location="Hassi Messaoud",
                activity="Extraction",
                division="Production",
                region="Hassi Messaoud",
                field="Hassi",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.commit()

        # Clean existing test records for this facility
        Emission.query.filter_by(facility_id=fac.id).delete()
        Scope2Emission.query.filter_by(facility_id=fac.id).delete()
        Scope3Emission.query.filter_by(facility_id=fac.id).delete()
        db.session.commit()

        # Add verified Scope 1 record
        e1 = Emission(
            record_id="rep-test-s1-001",
            facility_id=fac.id,
            year=2024,
            month=5,
            process_type="combustion",
            fuel_type="Natural Gas",
            quantity=1500.0,
            unit="m3",
            co2_emissions=300.0,
            ch4_emissions=1.5,
            n2o_emissions=0.05,
            co2e_total=340.0,
            status="Verified",
            activity="Flaring",
        )
        db.session.add(e1)

        # Add verified Scope 2 record
        e2 = Scope2Emission(
            facility_id=fac.id,
            created_by=admin.id,
            year=2024,
            month=5,
            source_type="electricity",
            electricity_kwh=8000.0,
            emission_factor=0.04,
            co2e=320.0,
            status="Verified",
            grid_region="Algiers",
        )
        db.session.add(e2)

        # Add verified Scope 3 record
        e3 = Scope3Emission(
            facility_id=fac.id,
            created_by=admin.id,
            year=2024,
            month=5,
            category="Purchased Goods and Services",
            sub_category="Chemicals",
            activity_data=4000.0,
            unit="kg",
            emission_factor=0.045,
            co2e=180.0,
            status="Verified",
        )
        db.session.add(e3)

        # Add injection test Scope 1 record
        e_inj = Emission(
            record_id="rep-test-s1-inj",
            facility_id=fac.id,
            year=2024,
            month=6,
            process_type="=cmd|'/C calc'!A0",
            fuel_type="+SUM(1,1)",
            quantity=100.0,
            unit="m3",
            co2_emissions=20.0,
            ch4_emissions=0.1,
            n2o_emissions=0.01,
            co2e_total=22.8,
            status="Verified",
            activity="@malicious",
        )
        db.session.add(e_inj)

        db.session.commit()

        return {
            "admin_email": "admin_rep@test.com",
            "it_email": "it_rep@test.com",
            "user_email": "user_rep@test.com",
            "facility_id": fac.id,
            "facility_name": fac.name,
        }


def test_reports_unauthenticated(client):
    """Ensure unauthenticated access to report endpoints returns 401."""
    assert client.get("/api/reports/export").status_code == 401
    assert client.post("/api/reports/generate", json={}).status_code == 401
    assert client.get("/api/reports/ogmp-export").status_code == 401
    assert client.get("/api/emissions/export?format=excel").status_code == 401


def test_reports_it_admin_forbidden(client, test_setup):
    """Ensure IT Admin is blocked with 403 Forbidden from operational emission reports."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": test_setup["it_email"], "password": "password123"},
    )
    assert login_res.status_code == 200

    assert client.get("/api/reports/export").status_code == 403
    assert client.post("/api/reports/generate", json={}).status_code == 403
    assert client.get("/api/reports/ogmp-export").status_code == 403
    assert client.get("/api/emissions/export?format=excel").status_code == 403


def test_emissions_excel_export_multi_scope(client, test_setup):
    """Validate genuine OpenPyXL Excel generation with Scope 1, 2, and 3 across sheets."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": test_setup["admin_email"], "password": "password123"},
    )
    assert login_res.status_code == 200

    # 1. Fetch full Excel export
    res = client.get("/api/emissions/export?format=excel&year=2024")
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.content_type
    assert "attachment" in res.headers.get("Content-Disposition", "")
    assert ".xlsx" in res.headers.get("Content-Disposition", "")

    wb = openpyxl.load_workbook(io.BytesIO(res.data))
    assert "Emissions Inventory" in wb.sheetnames
    assert "Executive Summary" in wb.sheetnames

    # Check sheet 1: Emissions Inventory (headers start on row 4)
    ws_inv = wb["Emissions Inventory"]
    headers = [cell.value for cell in ws_inv[4]]
    assert "Record ID" in headers
    assert "Scope" in headers
    assert "Year" in headers
    assert "Month" in headers
    assert "Facility" in headers
    assert "Category / Process" in headers
    assert "Total CO₂e (t)" in headers

    # Verify rows contain Scope 1, Scope 2, Scope 3 (Scope is in column index 1)
    scopes_found = set()
    for row in ws_inv.iter_rows(min_row=5, values_only=True):
        if len(row) > 1 and row[1] in ("Scope 1", "Scope 2", "Scope 3"):
            scopes_found.add(row[1])
    assert "Scope 1" in scopes_found
    assert "Scope 2" in scopes_found
    assert "Scope 3" in scopes_found

    # Check sheet 2: Executive Summary
    ws_sum = wb["Executive Summary"]
    summary_text = [str(cell) for row in ws_sum.iter_rows(values_only=True) for cell in row if cell is not None]
    assert any("Scope 1" in t for t in summary_text)
    assert any("Scope 2" in t for t in summary_text)
    assert any("Scope 3" in t for t in summary_text)
    assert any("Grand Total" in t for t in summary_text)


def test_excel_formula_injection_defense(client, test_setup):
    """Ensure characters =, +, -, @ are sanitized with leading single-quote."""
    client.post(
        "/api/auth/login",
        json={"email": test_setup["admin_email"], "password": "password123"},
    )
    res = client.get("/api/emissions/export?format=excel&year=2024&month=6")
    assert res.status_code == 200

    wb = openpyxl.load_workbook(io.BytesIO(res.data))
    ws_inv = wb["Emissions Inventory"]
    
    # Check that injected formulas have been prepended with single quote
    injected_cells = []
    for row in ws_inv.iter_rows(min_row=2, values_only=True):
        for cell in row:
            val = str(cell) if cell is not None else ""
            if "cmd|" in val or "SUM(1,1)" in val or "@malicious" in val:
                injected_cells.append(val)
                # Must start with single quote to prevent DDE execution
                assert val.startswith("'"), f"Unsanitized formula injection found: {val}"
    assert len(injected_cells) > 0


def test_reports_pdf_export_get_and_post(client, test_setup):
    """Ensure both GET /api/reports/export and POST /api/reports/generate produce valid PDFs."""
    client.post(
        "/api/auth/login",
        json={"email": test_setup["admin_email"], "password": "password123"},
    )

    # 1. GET /api/reports/export
    res_get = client.get(
        f"/api/reports/export?year=2024&month=5&facility_id={test_setup['facility_id']}&scope=all"
    )
    assert res_get.status_code == 200
    assert res_get.content_type == "application/pdf"
    assert res_get.data.startswith(b"%PDF")
    assert "attachment" in res_get.headers.get("Content-Disposition", "")

    # 2. POST /api/reports/generate
    post_payload = {
        "filters": {
            "year": "2024",
            "month": "5",
            "facility_id": str(test_setup["facility_id"]),
            "scope": "all",
            "process_type": "all",
        }
    }
    res_post = client.post("/api/reports/generate", json=post_payload)
    assert res_post.status_code == 200
    assert res_post.content_type == "application/pdf"
    assert res_post.data.startswith(b"%PDF")


def test_reports_ogmp_excel_export(client, test_setup):
    """Ensure GET /api/reports/ogmp-export produces a multi-sheet OGMP 2.0 workbook."""
    client.post(
        "/api/auth/login",
        json={"email": test_setup["admin_email"], "password": "password123"},
    )
    res = client.get(f"/api/reports/ogmp-export?year=2024&facility_id={test_setup['facility_id']}")
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.content_type
    assert ".xlsx" in res.headers.get("Content-Disposition", "")

    wb = openpyxl.load_workbook(io.BytesIO(res.data))
    assert len(wb.sheetnames) >= 5
    assert "1. Executive Summary" in wb.sheetnames
    assert "2. Bottom-Up Inventory" in wb.sheetnames
    assert "3. Top-Down Surveys" in wb.sheetnames
    assert "4. Reconciliation Matrix" in wb.sheetnames
    assert "5. Gold Standard Roadmap" in wb.sheetnames
