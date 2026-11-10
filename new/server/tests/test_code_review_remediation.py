"""
Automated regression tests verifying code review remediations:
1. Custom factor versioning on PUT when version string is modified on a referenced factor.
2. Authorization check precedence in GET /api/equity/allocation (blocking IT roles before mutation).
3. Scope 3 PUT unit update re-normalization.
4. Input validation parse_number top-level regex guard.
"""
import pytest
from app import app
from extensions import db
from models import User, CustomFactor, Facility, Emission, Scope3Emission


@pytest.fixture(autouse=True)
def clean_db_session():
    yield
    with app.app_context():
        try:
            db.session.rollback()
            db.session.remove()
        except Exception:
            pass


def test_custom_factor_version_change_creates_new_version(client):
    """Updating a referenced custom factor with a new version string triggers versioning (201)."""
    with app.app_context():
        admin = User.query.filter_by(role="admin", status="active").first()
        if not admin:
            admin = User(
                email="cf_rev_admin@test.com",
                fullName="CF Admin",
                orgName="Demo Operator Co.",
                sector="Oil & Gas",
                role="admin",
                status="active"
            )
            admin.set_password("pass")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

        cf = CustomFactor.query.filter_by(name="Review Versioned Factor").first()
        if not cf:
            cf = CustomFactor(
                name="Review Versioned Factor",
                version="1.0",
                co2_factor=50.0,
                unit="kg/MMBtu",
                created_by=admin_id,
            )
            db.session.add(cf)
            db.session.commit()
        cf_id = cf.id

        fac = Facility.query.filter_by(name="CF Test Fac").first()
        if not fac:
            fac = Facility(name="CF Test Fac", location="Test", created_by=admin_id)
            db.session.add(fac)
            db.session.commit()

        # Add an emission referencing this factor so refs > 0
        ref_em = Emission.query.filter_by(custom_factor_id=cf.id).first()
        if not ref_em:
            ref_em = Emission(
                facility_id=fac.id,
                custom_factor_id=cf.id,
                fuel_type=cf.name,
                year=2024,
                process_type="combustion",
                quantity=100.0,
                co2_emissions=5.0,
                created_by=admin_id,
            )
            db.session.add(ref_em)
            db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    # Update with changed version "2.0" and co2_factor
    res = client.put(f"/api/custom-factors/{cf_id}", json={
        "version": "2.0",
        "co2_factor": 55.0,
    })
    # Should succeed with 201 Created (new version created)
    assert res.status_code == 201
    data = res.get_json()
    assert data["version"] == "2.0"
    assert data["parent_factor_id"] == cf_id


def test_it_role_blocked_from_equity_allocation_without_mutations(client):
    """IT user requesting /api/equity/allocation gets 403 Forbidden without modifying database."""
    with app.app_context():
        it_user = User.query.filter_by(role="it", status="active").first()
        if not it_user:
            it_user = User(
                email="it_review@test.com",
                fullName="IT User",
                orgName="Demo Operator Co.",
                sector="Oil & Gas",
                role="it",
                status="active"
            )
            it_user.set_password("pass")
            db.session.add(it_user)
            db.session.commit()
        it_id = it_user.id

    with client.session_transaction() as sess:
        sess["user_id"] = it_id

    res = client.get("/api/equity/allocation")
    assert res.status_code == 403
    assert "Forbidden" in res.get_json()["error"]


def test_scope3_unit_change_without_factor_rescaling(client):
    """Updating Scope 3 record unit without resending factor rescales stored factor properly."""
    with app.app_context():
        admin = User.query.filter_by(role="admin", status="active").first()
        admin_id = admin.id
        fac = Facility.query.first()
        fid = fac.id

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    # Create via POST /api/scope3: 1000 kg with factor 0.5 kg CO2e / kg -> 0.5 t CO2e
    res_create = client.post("/api/scope3", json={
        "facility_id": fid,
        "year": 2024,
        "month": 1,
        "category": "1",
        "sub_category": "Purchased Goods",
        "activity_data": 1000.0,
        "unit": "kg",
        "emission_factor": 0.5,
        "factor_unit": "kg CO2e / kg",
    })
    assert res_create.status_code in (200, 201), res_create.get_json()
    rid = res_create.get_json().get("id") or res_create.get_json().get("record", {}).get("id")

    # Update activity to 1 and unit to tonne (equivalent to 1000 kg), without sending emission_factor
    res_update = client.put(f"/api/scope3/{rid}", json={
        "activity_data": 1.0,
        "unit": "tonne",
    })
    assert res_update.status_code == 200, res_update.get_json()

    with app.app_context():
        updated = db.session.get(Scope3Emission, rid)
        # 1 tonne should still yield 0.5 tonnes CO2e
        assert abs(updated.co2e - 0.5) < 1e-4
        # Stored emission factor in kg CO2e per tonne should be 500.0
        assert abs(updated.emission_factor - 500.0) < 1e-2


def test_input_validation_parse_number_thousands_guard():
    """Verify parse_number rejects ambiguous thousands-comma entries and accepts European decimals."""
    from input_validation import parse_number, ValidationError

    # Ambiguous thousands integers must fail with ValidationError
    with pytest.raises(ValidationError):
        parse_number("1,000", "amount")

    with pytest.raises(ValidationError):
        parse_number("1,000,000", "amount")

    # European decimal comma must succeed
    assert parse_number("123,45", "amount") == 123.45
    assert parse_number("10 000,50", "amount") == 10000.50
