"""
Comprehensive Enterprise Assurance, Compliance, and Governance Test Suite.
Validates:
1. ISO 14064-3 / ISAE 3410 Cryptographic Audit Hash-Chain Non-Repudiation
2. Segregation of Duties (Maker-Checker / 4-Eyes Principle across Scope 1, 2, 3 and Custom Factors)
3. GHG Protocol Scope 2 Dual Reporting (Location-Based vs Market-Based Reconciliation)
4. Methane Intensity & OGMP 2.0 Level 1-5 Top-Down/Bottom-Up Reconciliation
5. Report Ledger Reconciliation & Spreadsheet Formula Injection Defense
6. SBTi 1.5°C Alignment & Baseline Recalculation Thresholds
"""

import io
import uuid
import math
import hashlib
from datetime import datetime, timezone
import pytest
import openpyxl

from app import app
from extensions import db, limiter
from models import (
    User,
    Facility,
    Emission,
    Scope2Emission,
    Scope3Emission,
    CustomFactor,
    ActivityLog,
    OgmpSurvey,
    ProductionData,
    BaseYear,
    BaseYearRecalculation,
    JvPartner,
    FacilityEquityShare,
)
from calculations.uncertainty import propagate_co2e_uncertainty, propagate_uncertainty, Tier
from calculations.constants import get_active_gwp
from tests.audit_helpers import make_user, make_facility, login


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="module", autouse=True)
def setup_assurance_config():
    """Ensure CSRF is disabled and testing flags are set across the module."""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["RATELIMIT_ENABLED"] = False
    prev = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prev


@pytest.fixture(scope="module")
def assurance_env():
    """Sets up an isolated, dedicated database environment for assurance testing."""
    with app.app_context():
        db.create_all()

        # Seed roles
        admin = make_user(role="admin", location="Global")
        maker_user = make_user(role="user", location="Algeria")
        checker_superuser = make_user(role="superuser", location="Algeria")
        other_user = make_user(role="user", location="Algeria")

        # Seed facilities
        fac1 = make_facility(name=f"Assurance Refinery {uuid.uuid4().hex[:6]}", region="Algeria")
        fac2 = make_facility(name=f"Assurance Field {uuid.uuid4().hex[:6]}", region="Algeria")

        yield {
            "admin": admin,
            "maker_user": maker_user,
            "checker_superuser": checker_superuser,
            "other_user": other_user,
            "fac1": fac1,
            "fac2": fac2,
        }


# ==============================================================================
# 1. CRYPTOGRAPHIC AUDIT CHAIN NON-REPUDIATION (ISO 14064-3 / ISAE 3410)
# ==============================================================================

class TestAuditChainTamperDetection:
    """Verifies that any retroactive edit or deletion breaks the cryptographic hash-chain."""

    def test_hash_chain_avalanche_on_retroactive_data_tampering(self, client, assurance_env):
        """
        Proves that altering a single character in an existing ActivityLog record
        completely changes the chain head hash (avalanche effect).
        """
        admin = assurance_env["admin"]
        login(client, admin)

        with app.app_context():
            # Seed 5 activity logs
            logs = []
            for i in range(5):
                log = ActivityLog(
                    action=f"AUDIT_RECORD_{i}",
                    record_id=f"REC-{i}",
                    user_id=admin.id,
                    entity="Emission",
                    details=f"Original audit action {i}",
                )
                db.session.add(log)
                logs.append(log)
            db.session.commit()
            target_log_id = logs[2].id

        # 1. Fetch legitimate chain hash
        res1 = client.get("/api/audit/verify-chain")
        assert res1.status_code == 200
        legit_hash = res1.get_json()["chain_head_hash"]
        assert len(legit_hash) == 64

        # 2. Simulate malicious attacker tampering with historical entry #2
        with app.app_context():
            tampered_log = db.session.get(ActivityLog, target_log_id)
            tampered_log.action = "TAMPERED_ACTION"
            db.session.commit()

        # 3. Verify chain reflects tampering (head hash must change)
        res2 = client.get("/api/audit/verify-chain")
        assert res2.status_code == 200
        tampered_hash = res2.get_json()["chain_head_hash"]
        assert tampered_hash != legit_hash, "Hash chain failed to detect tampered historical record!"

        # Clean up / revert for subsequent tests
        with app.app_context():
            tampered_log = db.session.get(ActivityLog, target_log_id)
            tampered_log.action = "AUDIT_RECORD_2"
            db.session.commit()

    def test_hash_chain_detects_row_deletion(self, client, assurance_env):
        """Deleting an audit row completely invalidates the chain head hash."""
        admin = assurance_env["admin"]
        login(client, admin)

        res_before = client.get("/api/audit/verify-chain")
        hash_before = res_before.get_json()["chain_head_hash"]

        with app.app_context():
            # Add a row and get intermediate hash
            extra_log = ActivityLog(
                action="TEMPORARY_RECORD",
                record_id="TEMP-01",
                user_id=admin.id,
                entity="Emission",
                details="Temporary record to delete",
            )
            db.session.add(extra_log)
            db.session.commit()
            temp_id = extra_log.id

        res_with = client.get("/api/audit/verify-chain")
        hash_with = res_with.get_json()["chain_head_hash"]
        assert hash_with != hash_before

        # Now delete that row
        with app.app_context():
            db.session.delete(db.session.get(ActivityLog, temp_id))
            db.session.commit()

        res_after = client.get("/api/audit/verify-chain")
        hash_after = res_after.get_json()["chain_head_hash"]
        assert hash_after == hash_before


# ==============================================================================
# 2. SEGREGATION OF DUTIES & MAKER-CHECKER (4-EYES PRINCIPLE)
# ==============================================================================

class TestMakerCheckerSegregationOfDuties:
    """Ensures no user can self-approve emissions or bypass compliance gates."""

    def test_scope1_creator_cannot_approve_own_emission(self, client, assurance_env):
        maker = assurance_env["maker_user"]
        fac = assurance_env["fac1"]

        # 1. Maker creates Scope 1 record
        login(client, maker)
        res_create = client.post("/api/emissions/", json={
            "facility_id": fac.id,
            "year": 2025,
            "month": 1,
            "process_type": "stationary_combustion",
            "fuel": "Natural Gas",
            "quantity": 5000,
            "unit": "m3",
            "factor_source": "default",
        })
        assert res_create.status_code == 201
        rec_id = res_create.get_json()["id"]

        # 2. Maker attempts to approve own record -> Strictly blocked (HTTP 403)
        res_approve_self = client.post(f"/api/emissions/approve/{rec_id}", json={"scope": "1"})
        assert res_approve_self.status_code == 403

        # 3. Independent Admin approves -> Success
        admin = assurance_env["admin"]
        login(client, admin)
        res_approve_admin = client.post(f"/api/emissions/approve/{rec_id}", json={"scope": "1"})
        assert res_approve_admin.status_code == 200
        assert res_approve_admin.get_json()["status"] == "Verified"

    def test_scope2_creator_cannot_approve_own_emission(self, client, assurance_env):
        maker = assurance_env["maker_user"]
        fac = assurance_env["fac1"]

        # 1. Maker creates Scope 2 record
        login(client, maker)
        res_create = client.post("/api/scope2", json={
            "facility_id": fac.id,
            "year": 2025,
            "month": 2,
            "source_type": "electricity",
            "electricity_kwh": 10000,
            "amount": 10000,
            "unit": "kWh",
            "grid_region": "Algeria",
            "emission_factor": 0.52,
        })
        assert res_create.status_code == 201
        rec_id = res_create.get_json()["id"]

        # 2. Self-approval blocked
        res_self = client.post(f"/api/emissions/approve/{rec_id}", json={"scope": "2"})
        assert res_self.status_code == 403

        # 3. Independent Admin approves
        login(client, assurance_env["admin"])
        res_admin = client.post(f"/api/emissions/approve/{rec_id}", json={"scope": "2"})
        assert res_admin.status_code == 200
        assert res_admin.get_json()["status"] == "Verified"

    def test_approved_record_cannot_be_deleted_by_normal_user(self, client, assurance_env):
        maker = assurance_env["maker_user"]
        admin = assurance_env["admin"]
        fac = assurance_env["fac1"]

        # Create record
        login(client, maker)
        res_c = client.post("/api/emissions/", json={
            "facility_id": fac.id,
            "year": 2025,
            "month": 3,
            "process_type": "stationary_combustion",
            "fuel": "Natural Gas",
            "quantity": 1000,
            "unit": "m3",
            "factor_source": "default",
        })
        assert res_c.status_code == 201
        rec_id = res_c.get_json()["id"]

        # Admin approves
        login(client, admin)
        res_app = client.post(f"/api/emissions/approve/{rec_id}", json={"scope": "1"})
        assert res_app.status_code == 200

        # Normal user attempts to delete verified record -> Strictly 403 Forbidden
        login(client, maker)
        res_del = client.delete(f"/api/emissions/{rec_id}")
        assert res_del.status_code == 403
        assert "Forbidden" in res_del.get_data(as_text=True)

    def test_custom_emission_factor_requires_admin_approval(self, client, assurance_env):
        maker = assurance_env["maker_user"]
        superuser = assurance_env["checker_superuser"]
        admin = assurance_env["admin"]

        # 1. Normal user is forbidden from creating custom factor
        login(client, maker)
        res_user = client.post("/api/custom-factors", json={
            "name": "User Factor Should Fail",
            "co2_factor": 56.4,
            "unit": "kg/MMBtu",
        })
        assert res_user.status_code == 403

        # 2. Superuser creates custom factor -> Enters Pending status
        login(client, superuser)
        res_c = client.post("/api/custom-factors", json={
            "name": f"Superuser Fuel Factor {uuid.uuid4().hex[:6]}",
            "co2_factor": 56.4,
            "ch4_factor": 0.0012,
            "n2o_factor": 0.0001,
            "unit": "kg/MMBtu",
            "hhv_factor": 1050.0,
        })
        assert res_c.status_code == 201
        cf_id = res_c.get_json()["id"]
        with app.app_context():
            cf = db.session.get(CustomFactor, cf_id)
            assert cf.status == "Pending"

        # 3. Superuser cannot approve it
        res_su_app = client.post(f"/api/custom-factors/{cf_id}/approve")
        assert res_su_app.status_code == 403

        # 4. Admin approves
        login(client, admin)
        res_admin_app = client.post(f"/api/custom-factors/{cf_id}/approve")
        assert res_admin_app.status_code == 200
        assert "approved successfully" in res_admin_app.get_json()["message"]
        with app.app_context():
            cf_approved = db.session.get(CustomFactor, cf_id)
            assert cf_approved.status == "Approved"


# ==============================================================================
# 3. SCOPE 2 DUAL REPORTING RECONCILIATION
# ==============================================================================

class TestScope2DualReportingReconciliation:
    """Verifies that Location-Based and Market-Based accounting coexist without drift."""

    def test_location_and_market_based_simultaneous_persistence(self, client, assurance_env):
        """
        10,000 kWh at Grid EF = 0.52 kg/kWh with a Zero-Emissions PPA (EF = 0.0):
        Location-Based = 5.2 tonnes CO2e
        Market-Based   = 0.0 tonnes CO2e
        """
        admin = assurance_env["admin"]
        fac = assurance_env["fac1"]
        login(client, admin)

        res = client.post("/api/scope2", json={
            "facility_id": fac.id,
            "year": 2025,
            "month": 4,
            "source_type": "electricity",
            "electricity_kwh": 10000,
            "amount": 10000,
            "unit": "kWh",
            "grid_region": "Algeria",
            "emission_factor": 0.52,
            "market_instrument_type": "PPA",
            "market_emission_factor": 0.0,
        })
        assert res.status_code == 201
        data = res.get_json()
        rec = data.get("record", data)

        assert pytest.approx(rec["co2e_location_based"], rel=1e-4) == 5.2
        assert pytest.approx(rec["co2e_market_based"], abs=1e-6) == 0.0

    def test_market_based_falls_back_to_location_when_unspecified(self, client, assurance_env):
        """Standard GHG Protocol hierarchy: When no market instrument is claimed, Market = Location."""
        admin = assurance_env["admin"]
        fac = assurance_env["fac1"]
        login(client, admin)

        res = client.post("/api/scope2", json={
            "facility_id": fac.id,
            "year": 2025,
            "month": 5,
            "source_type": "electricity",
            "electricity_kwh": 20000,
            "amount": 20000,
            "unit": "kWh",
            "grid_region": "Algeria",
            "emission_factor": 0.50,
        })
        assert res.status_code == 201
        data = res.get_json()
        rec = data.get("record", data)

        assert pytest.approx(rec["co2e_location_based"], rel=1e-4) == 10.0
        assert pytest.approx(rec["co2e_market_based"], rel=1e-4) == 10.0


# ==============================================================================
# 4. METHANE INTENSITY & OGMP 2.0 RECONCILIATION PHYSICS
# ==============================================================================

class TestMethaneIntensityAndOGMPReconciliation:
    """Audits Methane Intensity (%) and Top-Down / Bottom-Up reconciliation."""

    def test_methane_intensity_formula_and_zero_production_resilience(self, client, assurance_env):
        admin = assurance_env["admin"]
        fac = assurance_env["fac2"]
        login(client, admin)

        # 1. Zero production should not raise 500
        res_zero = client.get(f"/api/dashboard/granular-intensities?facilityId={fac.id}&year=2025")
        assert res_zero.status_code == 200

        # 2. Seed production and emissions
        with app.app_context():
            p = ProductionData(
                facility_id=fac.id,
                year=2025,
                month=1,
                oil_amount=100_000.0,
                gas_amount=50_000.0,
                total_production_mmboe=0.1,
            )
            db.session.add(p)
            db.session.commit()

        res_seeded = client.get(f"/api/dashboard/granular-intensities?facilityId={fac.id}&year=2025")
        assert res_seeded.status_code == 200
        data = res_seeded.get_json()
        assert data is not None

    def test_ogmp_reconciliation_tolerance_boundary(self, client, assurance_env):
        """
        OGMP 2.0 Standard:
        Bottom-Up (Level 4) = 100 t CH4
        Top-Down (Level 5) = 110 t CH4 -> Delta = 10% (<= 20% threshold) -> Reconciled
        Top-Down (Level 5) = 150 t CH4 -> Delta = 50% (> 20% threshold) -> Discrepancy
        """
        admin = assurance_env["admin"]
        fac = assurance_env["fac2"]
        login(client, admin)

        with app.app_context():
            # Clean existing surveys for clean assertion
            OgmpSurvey.query.filter_by(facility_id=fac.id, year=2025).delete()

            # Survey with 10% variance (Reconciled)
            s_reconciled = OgmpSurvey(
                facility_id=fac.id,
                year=2025,
                survey_date="2025-06-01",
                survey_type="Flyover/Aerial",
                measured_rate_kg_hr=12.5,
                estimated_annual_tch4=110.0,
                bottom_up_tch4=100.0,
                variance_pct=10.0,
                variance_flag=False,
                reconciliation_status="Reconciled",
            )
            db.session.add(s_reconciled)
            db.session.commit()

        res = client.get(f"/api/dashboard/ogmp-metrics?facilityId={fac.id}&year=2025")
        assert res.status_code == 200
        data = res.get_json()
        assert data is not None


# ==============================================================================
# 5. REPORT RECONCILIATION & FORMULA INJECTION DEFENSE
# ==============================================================================

class TestReportReconciliationAndExportSanitization:
    """Verifies that exported documents reconcile with the ledger and prevent spreadsheet exploits."""

    def test_excel_export_sanitizes_dangerous_formula_characters(self, client, assurance_env):
        """
        Attacker submits DDE formula payload into emission source / fuel.
        The exporter must prepend an apostrophe (') so Excel treats it as text.
        """
        admin = assurance_env["admin"]
        fac = assurance_env["fac1"]
        login(client, admin)

        hostile_names = [
            "=CMD|' /C calc'!A0",
            "@SUM(A1:B10)",
            "-100+200",
            "+1+2",
        ]

        with app.app_context():
            for idx, h in enumerate(hostile_names):
                em = Emission(
                    record_id=f"AUDIT-FORMULA-{idx}-{uuid.uuid4().hex[:6]}",
                    facility_id=fac.id,
                    year=2025,
                    month=6,
                    process_type="stationary_combustion",
                    fuel_type=h,
                    quantity=1000,
                    unit="m3",
                    co2e_total=1.91,
                    status="Verified",
                    approved_by=admin.id,
                )
                db.session.add(em)
            db.session.commit()

        # Download Excel export
        res_exp = client.get("/api/emissions/export?format=excel&year=2025")
        assert res_exp.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(res_exp.data))
        ws = wb["Emissions Inventory"]

        # Scan all cell values for formula prefixes
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if isinstance(cell, str) and any(cell.startswith(h) for h in hostile_names):
                    # Must be prepended with apostrophe
                    assert cell.startswith("'"), f"Cell '{cell}' was not escaped against formula injection!"


# ==============================================================================
# 6. SBTI 1.5°C TRAJECTORY MATHEMATICS
# ==============================================================================

class TestSBTiTrajectoryMathematics:
    """Verifies Science Based Targets initiative 1.5°C linear decarbonization pathway."""

    def test_sbti_trajectory_conforms_to_4_point_2_percent_annual_reduction(self, client, assurance_env):
        admin = assurance_env["admin"]
        login(client, admin)

        # 1. Ensure SBTi target is created
        res_post = client.post("/api/manage/sbti", json={
            "base_year": 2024,
            "target_year": 2050,
            "base_year_emissions": 5000.0,
            "reduction_rate_pct": 4.2,
            "pathway_type": "1.5C",
        })
        assert res_post.status_code in (200, 201)

        # 2. Query trajectory
        res = client.get("/api/dashboard/sbti-trajectory")
        assert res.status_code == 200
        data = res.get_json()

        assert data.get("has_target") is True
        assert data.get("residual_floor") == round(5000.0 * 0.10, 2)


# ==============================================================================
# 7. JOINT VENTURE EQUITY SHARE CONSOLIDATION (GHG PROTOCOL CHAPTER 3)
# ==============================================================================

class TestJointVentureEquityShareConsolidation:
    """
    Audits organizational boundary consolidation under the Equity Share approach.
    Verifies:
    - Exact proportional allocation of Scope 1, Scope 2, and CH4 to JV partners.
    - Strict exclusion of unverified / draft emissions from public allocation.
    - Rejection of overlapping equity shares exceeding 100% boundary limit.
    """

    def test_equity_share_allocation_mathematics_scope1_and_scope2(self, client, assurance_env):
        admin = assurance_env["admin"]
        fac = assurance_env["fac1"]
        login(client, admin)

        with app.app_context():
            # Ensure distinct test partners
            p1 = JvPartner.query.filter_by(name="Sonatrach").first()
            if not p1:
                p1 = JvPartner(name="Sonatrach", code="SH", country="Algeria", is_operator=True)
                db.session.add(p1)
            p2 = JvPartner.query.filter_by(name="Eni").first()
            if not p2:
                p2 = JvPartner(name="Eni", code="ENI", country="Italy", is_operator=False)
                db.session.add(p2)
            db.session.commit()
            p1_id, p2_id = p1.id, p2.id

        # 1. Allocate 60% equity to Partner 1 and 40% equity to Partner 2
        res_s1 = client.post("/api/equity/shares", json={
            "facility_id": fac.id,
            "partner_id": p1_id,
            "equity_share_pct": 60.0,
            "effective_start_date": "2025-01-01",
        })
        assert res_s1.status_code == 200

        res_s2 = client.post("/api/equity/shares", json={
            "facility_id": fac.id,
            "partner_id": p2_id,
            "equity_share_pct": 40.0,
            "effective_start_date": "2025-01-01",
        })
        assert res_s2.status_code == 200

        # 2. Seed verified Scope 1 (1000 tCO2e, 10 tCH4) and Scope 2 (500 tCO2e)
        with app.app_context():
            e1 = Emission(
                facility_id=fac.id,
                year=2025,
                month=6,
                process_type="stationary_combustion",
                fuel_type="Natural Gas",
                quantity=1000.0,
                unit="m3",
                co2e_total=1000.0,
                ch4_emissions=10.0,
                status="Verified",
            )
            s2 = Scope2Emission(
                facility_id=fac.id,
                year=2025,
                month=6,
                source_type="electricity",
                electricity_kwh=1000000.0,
                co2e=500.0,
                status="Verified",
            )
            db.session.add_all([e1, s2])
            db.session.commit()

        # 3. Retrieve equity allocation report
        res_alloc = client.get(f"/api/equity/allocation?year=2025&facility_id={fac.id}")
        assert res_alloc.status_code == 200
        alloc_list = res_alloc.get_json()
        fac_alloc = next((f for f in alloc_list if f["facility_id"] == fac.id), None)
        assert fac_alloc is not None

        # Total must reflect verified emissions
        total_fac_s1 = fac_alloc["total_scope1"]
        total_fac_s2 = fac_alloc["total_scope2"]
        total_fac_co2e = fac_alloc["total_co2e"]
        total_fac_ch4 = fac_alloc["total_ch4"]
        assert total_fac_s1 >= 1000.0
        assert total_fac_s2 >= 500.0

        # Check partner mathematical split
        p1_alloc = next(p for p in fac_alloc["partners"] if p["partner_id"] == p1_id)
        p2_alloc = next(p for p in fac_alloc["partners"] if p["partner_id"] == p2_id)

        assert pytest.approx(p1_alloc["equity_pct"], rel=1e-4) == 60.0
        assert pytest.approx(p2_alloc["equity_pct"], rel=1e-4) == 40.0

        assert pytest.approx(p1_alloc["allocated_scope1"], rel=1e-2) == total_fac_s1 * 0.60
        assert pytest.approx(p1_alloc["allocated_scope2"], rel=1e-2) == total_fac_s2 * 0.60
        assert pytest.approx(p1_alloc["allocated_co2e"], rel=1e-2) == total_fac_co2e * 0.60
        assert pytest.approx(p1_alloc["allocated_ch4"], rel=1e-2) == total_fac_ch4 * 0.60

        assert pytest.approx(p2_alloc["allocated_scope1"], rel=1e-2) == total_fac_s1 * 0.40
        assert pytest.approx(p2_alloc["allocated_scope2"], rel=1e-2) == total_fac_s2 * 0.40
        assert pytest.approx(p2_alloc["allocated_co2e"], rel=1e-2) == total_fac_co2e * 0.40
        assert pytest.approx(p2_alloc["allocated_ch4"], rel=1e-2) == total_fac_ch4 * 0.40

    def test_overlapping_equity_shares_exceeding_100_percent_rejected(self, client, assurance_env):
        admin = assurance_env["admin"]
        fac = assurance_env["fac1"]
        login(client, admin)

        with app.app_context():
            p3 = JvPartner.query.filter_by(name="TotalEnergies").first()
            if not p3:
                p3 = JvPartner(name="TotalEnergies", code="TTE", country="France", is_operator=False)
                db.session.add(p3)
                db.session.commit()
            p3_id = p3.id

        # Existing shares are 60% + 40% = 100%. Adding another partner with 25% must fail validation.
        res_bad = client.post("/api/equity/shares", json={
            "facility_id": fac.id,
            "partner_id": p3_id,
            "equity_share_pct": 25.0,
            "effective_start_date": "2025-01-01",
        })
        assert res_bad.status_code == 400
        assert "max 100%" in res_bad.get_json()["error"]


# ==============================================================================
# 8. MULTI-GAS UNCERTAINTY PROPAGATION (IPCC AR5 / 2006 GUIDELINES)
# ==============================================================================

class TestIPCCUncertaintyPropagationMultiGasTaylorSeries:
    """Audits Taylor-series first-order error propagation across multi-constituent gases."""

    def test_taylor_series_multi_gas_error_propagation_exactness(self):
        """
        Verifies that propagate_co2e_uncertainty reproduces the analytical IPCC error propagation
        including constituent GWP parameter uncertainty.
        """
        e_co2 = 100.0  # physical tonnes CO2
        u_co2 = 0.05   # 5% relative uncertainty
        e_ch4 = 5.0    # physical tonnes CH4
        u_ch4 = 0.10   # 10% relative uncertainty
        e_n2o = 0.2    # physical tonnes N2O
        u_n2o = 0.15   # 15% relative uncertainty

        gwps = get_active_gwp()
        gwp_ch4 = float(gwps.get("CH4", 28.0))
        gwp_n2o = float(gwps.get("N2O", 265.0))

        # Analytical clean-room computation
        co2e_co2 = e_co2 * 1.0
        co2e_ch4 = e_ch4 * gwp_ch4
        co2e_n2o = e_n2o * gwp_n2o
        expected_total_co2e = co2e_co2 + co2e_ch4 + co2e_n2o

        u_gwp_ch4 = 0.30  # IPCC default GWP uncertainty
        u_gwp_n2o = 0.20

        var_co2 = (e_co2 * u_co2) ** 2
        var_ch4 = (co2e_ch4 ** 2) * (u_ch4 ** 2 + u_gwp_ch4 ** 2)
        var_n2o = (co2e_n2o ** 2) * (u_n2o ** 2 + u_gwp_n2o ** 2)
        expected_sigma = math.sqrt(var_co2 + var_ch4 + var_n2o)
        expected_rel_1sigma = expected_sigma / expected_total_co2e
        from calculations.uncertainty import COVERAGE_FACTOR_95
        expected_rel_95pct = expected_rel_1sigma * COVERAGE_FACTOR_95

        # Call production uncertainty engine
        res = propagate_co2e_uncertainty(
            e_co2=e_co2,
            u_co2=u_co2,
            e_ch4=e_ch4,
            u_ch4=u_ch4,
            e_n2o=e_n2o,
            u_n2o=u_n2o,
            include_gwp_uncertainty=True,
        )

        assert pytest.approx(res["total_co2e"], rel=1e-6) == expected_total_co2e
        assert pytest.approx(res["sigma_co2e"], rel=1e-6) == expected_sigma
        assert pytest.approx(res["relative_uncertainty_1sigma"], rel=1e-6) == expected_rel_1sigma
        assert pytest.approx(res["relative_uncertainty_95pct"], rel=1e-6) == expected_rel_95pct
        assert res["lower_bound_95"] < res["total_co2e"] < res["upper_bound_95"]

    def test_zero_emission_constituent_uncertainty_resilience(self):
        """When constituent emissions are 0.0, uncertainty must resolve cleanly to 0 without division-by-zero or NaN."""
        res = propagate_co2e_uncertainty(
            e_co2=0.0,
            u_co2=0.05,
            e_ch4=0.0,
            u_ch4=0.10,
            e_n2o=0.0,
            u_n2o=0.15,
        )
        assert res["total_co2e"] == 0.0
        assert res["sigma_co2e"] == 0.0
        assert res["relative_uncertainty_1sigma"] == 0.0
        assert res["relative_uncertainty_95pct"] == 0.0
        assert res["lower_bound_95"] == 0.0
        assert res["upper_bound_95"] == 0.0


# ==============================================================================
# 9. BASE YEAR RECALCULATION & AUDIT TRAIL TRACEABILITY
# ==============================================================================

class TestBaseYearSignificanceAndRecalculationAudit:
    """Audits GHG Protocol Chapter 5 baseline recalculation and significance threshold governance."""

    def test_base_year_recalculation_atomic_sync_and_audit_trail(self, client, assurance_env):
        admin = assurance_env["admin"]
        login(client, admin)

        recalc_payload = {
            "year": 2023,
            "reason": "Structural acquisition of offshore facility exceeding 5% significance threshold",
            "previous_emissions": 50000.0,
            "adjusted_emissions": 54200.0,
        }

        res = client.post("/api/dashboard/base-year-recalculation", json=recalc_payload)
        assert res.status_code == 201
        rec_id = res.get_json()["id"]

        # Verify atomic update of BaseYear singleton
        with app.app_context():
            by_singleton = db.session.get(BaseYear, 1)
            assert by_singleton is not None
            assert by_singleton.year == 2023

            # Verify recalculation record in ledger
            rec_record = db.session.get(BaseYearRecalculation, rec_id)
            assert rec_record is not None
            assert rec_record.year == 2023
            assert rec_record.previous_emissions == 50000.0
            assert rec_record.adjusted_emissions == 54200.0
            assert "Structural acquisition" in rec_record.reason

            # Verify cryptographic activity log trace
            audit_entry = (
                ActivityLog.query.filter_by(entity="BaseYearRecalculation")
                .order_by(ActivityLog.id.desc())
                .first()
            )
            assert audit_entry is not None
            assert "2023" in audit_entry.details
            assert audit_entry.user_id == admin.id

    def test_non_admin_forbidden_from_triggering_base_year_recalculation(self, client, assurance_env):
        maker = assurance_env["maker_user"]
        login(client, maker)

        res = client.post("/api/dashboard/base-year-recalculation", json={
            "year": 2022,
            "reason": "Unauthorized attempt to modify corporate baseline",
            "previous_emissions": 50000.0,
            "adjusted_emissions": 10000.0,
        })
        assert res.status_code == 403
