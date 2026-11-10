import pytest
import uuid
from app import app
from models import db, User, Facility, UserFacilityAccess, Emission, Scope2Emission, Scope3Emission, CustomFactor
from utils import get_allowed_facility_ids, facility_in_user_scope
from background_processor import _process_row, _process_row_scope2, _process_row_scope3, _dedupe, _scope1_key
from calculations import compute_emissions
from emission_factors import API_FACTORS

def _get_admin_user():
    admin = User.query.filter_by(role="admin").first()
    if not admin:
        admin = User(fullName="Admin", orgName="Demo Operator Co.", sector="Oil", email="adm_test_hardening@ghg.com", role="admin")
        admin.set_password("AuditPass!2026")
        db.session.add(admin)
        db.session.commit()
    return admin

@pytest.fixture(autouse=True)
def clean_db_session():
    yield
    with app.app_context():
        try:
            db.session.rollback()
            db.session.remove()
        except Exception:
            pass

def test_user_facility_access_scoping():
    """Verify that UserFacilityAccess takes priority over user.location string matching."""
    with app.app_context():
        # Create or fetch test facilities via db.session.get (SQLAlchemy 2.0 compliant)
        fac1 = db.session.get(Facility, 37) or Facility(id=37, name="Facility A-1", location="Basin Alpha Basin")
        fac2 = db.session.get(Facility, 38) or Facility(id=38, name="Facility B-2", location="Basin Alpha Basin")
        db.session.merge(fac1)
        db.session.merge(fac2)
        
        op = User.query.filter_by(email="op_test_hardening@ghg.com").first()
        if not op:
            op = User(fullName="Op", orgName="Demo Operator Co.", sector="Oil", email="op_test_hardening@ghg.com", role="user")
            op.set_password("AuditPass!2026")
            db.session.add(op)

        su = User.query.filter_by(email="su_test_hardening@ghg.com").first()
        if not su:
            su = User(fullName="Su", orgName="Demo Operator Co.", sector="Oil", email="su_test_hardening@ghg.com", role="superuser")
            su.set_password("AuditPass!2026")
            db.session.add(su)

        adm = User.query.filter_by(email="adm_test_hardening@ghg.com").first()
        if not adm:
            adm = User(fullName="Admin", orgName="Demo Operator Co.", sector="Oil", email="adm_test_hardening@ghg.com", role="admin")
            adm.set_password("AuditPass!2026")
            db.session.add(adm)

        db.session.commit()

        # Add explicit UserFacilityAccess for op and su to fac1 and fac2
        UserFacilityAccess.query.filter(UserFacilityAccess.user_id.in_([op.id, su.id])).delete(synchronize_session=False)
        acc1 = UserFacilityAccess(user_id=op.id, facility_id=37, access_level="operator")
        acc2 = UserFacilityAccess(user_id=op.id, facility_id=38, access_level="operator")
        acc3 = UserFacilityAccess(user_id=su.id, facility_id=37, access_level="verifier")
        acc4 = UserFacilityAccess(user_id=su.id, facility_id=38, access_level="verifier")
        db.session.add_all([acc1, acc2, acc3, acc4])
        db.session.commit()

        # Admin gets unrestricted global access (None)
        assert get_allowed_facility_ids(adm) is None

        # Operator and Superuser get explicit facilities [37, 38] from UserFacilityAccess
        op_allowed = get_allowed_facility_ids(op)
        su_allowed = get_allowed_facility_ids(su)

        assert 37 in op_allowed and 38 in op_allowed
        assert 37 in su_allowed and 38 in su_allowed

        # facility_in_user_scope returns True for granted facility_id even if user.location differs
        assert facility_in_user_scope(su, facility_id=37) is True

def test_dedupe_duplicate_actions():
    """Verify 3-way duplicate conflict handling in _dedupe."""
    batch_keys = {"facility_37_combustion": 12345}

    # 1. Overwrite in-place
    act_up, target_up = _dedupe(batch_keys, "facility_37_combustion", overwrite=True, describe="Test Row")
    assert act_up == "update"
    assert target_up == 12345

    act_up2, target_up2 = _dedupe(batch_keys, "facility_37_combustion", overwrite="overwrite", describe="Test Row")
    assert act_up2 == "update"
    assert target_up2 == 12345

    # 2. Skip duplicates
    act_skip, target_skip = _dedupe(batch_keys, "facility_37_combustion", overwrite="skip", describe="Test Row")
    assert act_skip == "skip"
    assert target_skip is None

    # 3. Create audited revision
    act_rev, target_rev = _dedupe(batch_keys, "facility_37_combustion", overwrite="revision", describe="Test Row")
    assert act_rev == "revision"
    assert target_rev == 12345

    # 4. Error on unhandled duplicate without overwrite
    act_err, msg = _dedupe(batch_keys, "facility_37_combustion", overwrite=False, describe="Test Row")
    assert act_err == "error"
    assert "Duplicate record" in msg

def test_audited_revision_supersedes_prior_scope1_record():
    """Verify that creating an audited revision sets prior record status to Superseded."""
    with app.app_context():
        fac = db.session.get(Facility, 37) or Facility(id=37, name="Facility A-1", location="Basin Alpha Basin")
        db.session.merge(fac)
        admin = _get_admin_user()

        # Existing record
        old_em = Emission(
            record_id=str(uuid.uuid4()),
            facility_id=37,
            year=2026,
            month=1,
            process_type="combustion",
            fuel_type="Diesel (No. 2 Fuel Oil)",
            co2_emissions=100.0,
            status="Verified",
            created_by=admin.id,
        )
        db.session.add(old_em)
        db.session.commit()

        # Build duplicate key matching _ImportRun.load_context()
        k = _scope1_key(old_em.facility_id, old_em.year, old_em.month, old_em.process_type, old_em.fuel_type, old_em.equipment_id, old_em.data_source_ref)
        batch_keys = {k: old_em.id}

        row = {
            "date": "2026-01-01",
            "facility_name": "Facility A-1",
            "process": "combustion",
            "fuel": "Diesel",
            "amount": "100",
            "unit": "gallons",
            "factor_type": "default",
        }
        fac_name_map = {"facility-a1": fac}
        fac_id_map = {37: fac}
        cf_name_map = {}

        # Process row with overwrite="revision"
        new_em, errs = _process_row(
            row, admin.id, fac_name_map, fac_id_map, cf_name_map,
            compute_emissions, API_FACTORS, "auto",
            batch_keys=batch_keys, overwrite_duplicates="revision"
        )
        assert len(errs) == 0, f"Unexpected errors: {errs}"
        assert new_em is not None
        assert "Audited Revision" in (new_em.qa_flag or "")

        # Verify old record was superseded
        assert old_em.status == "Superseded"
        assert "Superseded" in (old_em.qa_flag or "")

        # Cleanup
        db.session.delete(old_em)
        db.session.commit()

def test_hierarchical_custom_factor_scoping_and_status():
    """Verify custom factor auto-detection does not leak cross-facility or apply unapproved factors."""
    with app.app_context():
        fac1 = db.session.get(Facility, 37) or Facility(id=37, name="Facility A-1", location="Basin Alpha Basin")
        fac2 = db.session.get(Facility, 38) or Facility(id=38, name="Facility B-2", location="Basin Alpha Basin")
        db.session.merge(fac1)
        db.session.merge(fac2)
        admin = _get_admin_user()

        # Facility 38 custom factor: "Field Specific Gas"
        cf_fac2 = CustomFactor(
            name="Field Specific Gas",
            facility_id=38, # strictly facility 38
            status="Approved",
            co2_factor=55.0,
            unit="kg/MMBtu",
            created_by=admin.id
        )
        # Pending factor: "Unapproved Fuel"
        cf_pend = CustomFactor(
            name="Unapproved Fuel",
            facility_id=37,
            status="Pending", # not approved yet!
            co2_factor=45.0,
            unit="kg/MMBtu",
            created_by=admin.id
        )
        # Approved factor strictly for facility 37
        cf_fac1 = CustomFactor(
            name="Facility Specific Fuel",
            facility_id=37,
            status="Approved",
            co2_factor=50.0,
            unit="kg/MMBtu",
            created_by=admin.id
        )
        db.session.add_all([cf_fac2, cf_pend, cf_fac1])
        db.session.commit()

        fac_name_map = {"facility-a1": fac1, "facility b-2": fac2}
        fac_id_map = {37: fac1, 38: fac2}
        cf_name_map = {
            "field specific gas": cf_fac2,
            "unapproved fuel": cf_pend,
            "facility specific fuel": cf_fac1,
        }

        # 1. Row for Facility 37 using "Field Specific Gas" (which belongs to 38) should NOT auto-resolve to custom!
        row_fac1 = {
            "date": "2026-02-01",
            "facility_name": "Facility A-1",
            "process": "combustion",
            "fuel": "Field Specific Gas",
            "amount": "100",
            "unit": "MMBtu",
            "factor_type": "default",
        }
        _, errs1 = _process_row(
            row_fac1, admin.id, fac_name_map, fac_id_map, cf_name_map,
            compute_emissions, API_FACTORS, "auto",
            batch_keys={}, overwrite_duplicates=False
        )
        assert any("emission factor catalog" in e or "not in the" in e for e in errs1), f"Expected catalog error, got: {errs1}"

        # 2. Row using "Unapproved Fuel" (Pending) should NOT auto-resolve to custom!
        row_pend = {
            "date": "2026-02-01",
            "facility_name": "Facility A-1",
            "process": "combustion",
            "fuel": "Unapproved Fuel",
            "amount": "100",
            "unit": "MMBtu",
            "factor_type": "default",
        }
        _, errs2 = _process_row(
            row_pend, admin.id, fac_name_map, fac_id_map, cf_name_map,
            compute_emissions, API_FACTORS, "auto",
            batch_keys={}, overwrite_duplicates=False
        )
        assert any("emission factor catalog" in e or "not in the" in e for e in errs2), f"Expected catalog error, got: {errs2}"

        # 3. Row for Facility 37 using "Facility Specific Fuel" (Approved for 37) SHOULD auto-resolve to custom!
        row_approved = {
            "date": "2026-02-01",
            "facility_name": "Facility A-1",
            "process": "combustion",
            "fuel": "Facility Specific Fuel",
            "amount": "100",
            "unit": "MMBtu",
            "factor_type": "default",
        }
        em_approved, errs3 = _process_row(
            row_approved, admin.id, fac_name_map, fac_id_map, cf_name_map,
            compute_emissions, API_FACTORS, "auto",
            batch_keys={}, overwrite_duplicates=False
        )
        assert len(errs3) == 0, f"Expected clean custom factor resolution, got: {errs3}"
        assert em_approved is not None
        assert em_approved.factor_source == "custom"
        assert em_approved.custom_factor_id == cf_fac1.id

        # Cleanup
        db.session.delete(cf_fac2)
        db.session.delete(cf_pend)
        db.session.delete(cf_fac1)
        db.session.commit()
        db.session.commit()
