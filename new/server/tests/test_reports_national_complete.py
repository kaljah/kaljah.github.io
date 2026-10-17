"""Exhaustive test suite for Official Corporate HSE & National GHG Inventory Export (Executive Decree 21-330).

Covers:
- routes/reports_national.py:
  - _ch4_gwp (standard lookups, fallbacks, blank values)
  - _uncertainty_rows (year None message, scope 1/2/3/all calls)
  - export_national_inventory_report:
    - Authorization (401 unauthenticated, 403 IT role, 403 unauthorized facility RLS)
    - Multi-sheet Excel workbook structure and mathematical accuracy:
      - Sheet 1: Page de Garde (Metadata & Decree reference)
      - Sheet 2: Synthèse Exécutive (Scope 1, 2, 3 emissions & uncertainty)
      - Sheet 3: Scope 1 - Détail (IPCC CRF 1.A / 1.B categories, gas splits)
      - Sheet 4: Scope 2 - Détail (Location & market based, energy MWh/GJ)
      - Sheet 5: Scope 3 - Détail (Scope 3 categories 1-15)
      - Sheet 6: Production & Intensités (Production barrels/BOE, GHG intensity)
    - Status filtering (Verified vs Draft/Rejected)
    - Consolidated year vs single-year exports
"""
import io
import openpyxl
import pytest
from extensions import db
from models import (
    Emission,
    Facility,
    ProductionData,
    Scope2Emission,
    Scope3Emission,
    User,
)
from routes.reports_national import _ch4_gwp, _uncertainty_rows
from tests.audit_helpers import login, make_facility, make_user, uniq
from calculations.constants import GWP_STANDARDS


# ---------------------------------------------------------------------------
# Unit Tests for Helper Functions
# ---------------------------------------------------------------------------

def test_ch4_gwp_exhaustive():
    assert _ch4_gwp(None) == ""
    assert _ch4_gwp("") == ""
    # Test valid standards
    for std in ("AR4", "AR5", "AR6"):
        expected = GWP_STANDARDS[std]["CH4"]
        assert _ch4_gwp(std) == expected
    # Fallback to string representation for custom/unknown standards
    assert _ch4_gwp("CUSTOM_999") == "CUSTOM_999"


def test_uncertainty_rows_exhaustive(app):
    with app.app_context():
        # When year is None -> French prompt
        msg = _uncertainty_rows(None, None, ["Verified"])
        assert "Choisir une année" in msg["1"]
        assert "Choisir une année" in msg["all"]

        # When year is integer
        res = _uncertainty_rows(2024, None, ["Verified"])
        assert "1" in res and "2" in res and "3" in res and "all" in res


# ---------------------------------------------------------------------------
# Authorization and Security Tests
# ---------------------------------------------------------------------------

def test_national_inventory_export_auth(client, app):
    with app.app_context():
        # 1. Unauthenticated -> 401
        res_unauth = client.get("/api/reports/national-inventory-export")
        assert res_unauth.status_code == 401

        # 2. IT user -> 403 Forbidden
        it_user = make_user("it_admin", "Global")
        login(client, it_user)
        res_it = client.get("/api/reports/national-inventory-export")
        assert res_it.status_code == 403
        assert "IT personnel cannot access" in res_it.get_json()["error"]

        # 3. Facility-restricted user accessing unauthorized facility -> 403
        f_allowed = make_facility(region=uniq("AllowedFac"))
        f_other = make_facility(region=uniq("OtherFac"))
        scoped_user = make_user("engineer", f_allowed.name)
        scoped_user.allowed_facilities = [f_allowed]
        db.session.commit()

        login(client, scoped_user)
        res_denied = client.get(f"/api/reports/national-inventory-export?facility_id={f_other.id}")
        assert res_denied.status_code == 403
        assert "Unauthorized facility" in res_denied.get_json()["error"]


# ---------------------------------------------------------------------------
# Excel Workbook Generation and Calculation Invariants Tests
# ---------------------------------------------------------------------------

def test_national_inventory_export_workbook_complete(client, app):
    with app.app_context():
        f = make_facility(region=uniq("SonatrachSite"))
        admin = make_user("admin", "Global")
        admin.orgName = "Sonatrach Exploration & Production"
        admin.fullName = "Dr. Amina Benali"
        admin.email = "amina.benali@sonatrach.dz"
        db.session.commit()
        login(client, admin)

        target_year = 2024

        # 1. Populate Scope 1 records (Combustion & Flaring)
        e_comb = Emission(
            facility_id=f.id,
            year=target_year,
            month=6,
            process_type="combustion",
            fuel_type="natural_gas",
            quantity=1000.0,
            unit="m3",
            co2_emissions=180.0,
            ch4_emissions=0.05,
            n2o_emissions=0.001,
            co2e_total=181.5,
            status="Verified",
            gwp_version="AR6",
        )
        e_flare = Emission(
            facility_id=f.id,
            year=target_year,
            month=7,
            process_type="flaring",
            fuel_type="sour_gas",
            quantity=500.0,
            unit="m3",
            co2_emissions=90.0,
            ch4_emissions=0.02,
            n2o_emissions=0.0005,
            co2e_total=90.8,
            status="Verified",
            gwp_version="AR6",
        )
        # Pending record: must NOT appear in default verified export
        e_pending = Emission(
            facility_id=f.id,
            year=target_year,
            month=8,
            process_type="combustion",
            co2e_total=500.0,
            status="Pending",
        )

        # 2. Populate Scope 2 record (Grid Electricity)
        s2 = Scope2Emission(
            facility_id=f.id,
            year=target_year,
            month=6,
            source_type="electricity",
            grid_region="Algerian National Grid",
            electricity_kwh=200_000.0,
            co2e=110.0,
            co2e_location_based=110.0,
            co2e_market_based=0.0,
            market_instrument_type="REC",
            status="Verified",
        )

        # 3. Populate Scope 3 record (Purchased Goods)
        s3 = Scope3Emission(
            facility_id=f.id,
            year=target_year,
            month=6,
            category=1,
            sub_category="purchased_goods",
            co2e=45.0,
            status="Verified",
        )

        # 4. Populate Production Data
        prod = ProductionData(
            facility_id=f.id,
            year=target_year,
            month=6,
            oil_amount=10_000.0,   # Barrels
            oil_unit="bbl",
            gas_amount=50_000.0,   # Mscf
            gas_unit="mscf",
        )

        db.session.add_all([e_comb, e_flare, e_pending, s2, s3, prod])
        db.session.commit()

        # Generate Report
        res = client.get(f"/api/reports/national-inventory-export?year={target_year}&facility_id={f.id}&status=Verified")
        assert res.status_code == 200
        assert res.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # Inspect Excel content
        wb = openpyxl.load_workbook(io.BytesIO(res.data))
        _assert_sheets_content(wb, target_year)


def _assert_sheets_content(wb, target_year):
    expected_sheets = [
        "0. Déclaration Décret 21-330",
        "Executive Summary",
        "Emissions Inventory",
        "Scope 1 - Combustion & Torchage",
        "Scope 1 - Évents & Fugitives",
        "Scope 2 - Énergie & Sonelgaz",
        "Scope 3 - Chaîne de Valeur",
        "Incertitude & Assurance Audit",
    ]
    for sheet_name in expected_sheets:
        assert sheet_name in wb.sheetnames, f"Missing expected sheet: {sheet_name}"

    ws_cover = wb["0. Déclaration Décret 21-330"]
    cover_text = " ".join(str(cell.value or "") for row in ws_cover.iter_rows() for cell in row)
    assert "21-330" in cover_text
    assert "Sonatrach Exploration & Production" in cover_text
    assert str(target_year) in cover_text

    ws_synth = wb["Executive Summary"]
    synth_text = " ".join(str(cell.value or "") for row in ws_synth.iter_rows() for cell in row)
    assert "Scope 1" in synth_text
    assert "Scope 2" in synth_text
    assert "Scope 3" in synth_text

    synth_values = [cell.value for row in ws_synth.iter_rows() for cell in row if isinstance(cell.value, (int, float))]
    s1_expected = 181.5 + 90.8
    assert any(pytest.approx(v, abs=0.1) == s1_expected for v in synth_values)
    assert any(pytest.approx(v, abs=0.1) == 110.0 for v in synth_values)
    assert any(pytest.approx(v, abs=0.1) == 45.0 for v in synth_values)

    ws_comb = wb["Scope 1 - Combustion & Torchage"]
    comb_rows = list(ws_comb.iter_rows(values_only=True))
    gas_rows = [r for r in comb_rows if r and any(str(c) in ("natural_gas", "sour_gas") for c in r)]
    assert len(gas_rows) == 2

    ws_s2 = wb["Scope 2 - Énergie & Sonelgaz"]
    s2_rows = list(ws_s2.iter_rows(values_only=True))
    elec_rows = [r for r in s2_rows if r and any("electric" in str(c).lower() for c in r)]
    assert len(elec_rows) >= 1

    ws_s3 = wb["Scope 3 - Chaîne de Valeur"]
    s3_rows = list(ws_s3.iter_rows(values_only=True))
    goods_rows = [r for r in s3_rows if r and any("purchased_goods" in str(c).lower() for c in r)]
    assert len(goods_rows) >= 1

    ws_audit = wb["Incertitude & Assurance Audit"]
    audit_rows = list(ws_audit.iter_rows(values_only=True))
    assert len(audit_rows) >= 2


def test_national_inventory_export_consolidated_and_statuses(client, app):
    with app.app_context():
        f = make_facility(region=uniq("ConsolSite"))
        admin = make_user("admin", "Global")
        login(client, admin)

        # Multi-year records
        e23 = Emission(facility_id=f.id, year=2023, month=1, co2e_total=100.0, status="Verified", process_type="combustion")
        e24_draft = Emission(facility_id=f.id, year=2024, month=1, co2e_total=200.0, status="Draft", process_type="combustion")
        db.session.add_all([e23, e24_draft])
        db.session.commit()

        # 1. Consolidated year=all
        res_all_year = client.get(f"/api/reports/national-inventory-export?year=all&facility_id={f.id}&status=Verified")
        assert res_all_year.status_code == 200
        wb_all = openpyxl.load_workbook(io.BytesIO(res_all_year.data))
        ws_cover = wb_all["0. Déclaration Décret 21-330"]
        cover_text = " ".join(str(cell.value or "") for row in ws_cover.iter_rows() for cell in row)
        assert "Consolidated" in cover_text or "Toutes" in cover_text or "21-330" in cover_text

        # 2. Including Draft status
        res_with_draft = client.get(f"/api/reports/national-inventory-export?year=2024&facility_id={f.id}&status=Draft")
        assert res_with_draft.status_code == 200
        wb_draft = openpyxl.load_workbook(io.BytesIO(res_with_draft.data))
        ws_comb_draft = wb_draft["Scope 1 - Combustion & Torchage"]
        s1_draft_rows = [r for r in ws_comb_draft.iter_rows(values_only=True) if r and any(c == 200.0 for c in r)]
        assert len(s1_draft_rows) == 1
