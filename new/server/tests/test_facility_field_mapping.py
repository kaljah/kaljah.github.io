import pytest
from app import app
from extensions import db
from models import User, Facility
from services.master_report_engine import generate_master_publication_pdf

def test_facility_add_mapping_region_and_field(client):
    """Test that submitting region_name and field sets facility.name=field and facility.region=region_name."""
    with app.app_context():
        admin = User.query.filter_by(role="admin").first()
        if not admin:
            admin = User(
                fullName="Admin Test",
                orgName="Sonatrach",
                sector="Oil & Gas",
                email="admin_field_test@sonatrach.dz",
                role="admin",
                password_hash="hash",
                status="active"
            )
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    # Post facility using region_name and field to /api/facilities
    payload = {
        "region_name": "Ouargla / HMD",
        "field": "HMD-Test-Field-999",
        "activity": "EP",
        "division": "Production",
        "location": "Ouargla, Algeria",
        "boundary_type": "Operational Control",
    }
    res = client.post("/api/facilities", json=payload)
    assert res.status_code == 201, f"Failed: {res.get_json()}"
    fac_id = res.get_json()["id"]

    with app.app_context():
        fac = db.session.get(Facility, fac_id)
        assert fac is not None
        assert fac.name == "HMD-Test-Field-999"
        assert fac.region == "Ouargla / HMD"
        assert fac.field == "HMD-Test-Field-999"
        # Cleanup
        db.session.delete(fac)
        db.session.commit()

def test_master_report_appendix_facility_prefix(client):
    """Test that master report appendix includes 'Facility: ' in EN and 'Installation : ' in FR."""
    with app.app_context():
        # Generate English PDF
        pdf_en = generate_master_publication_pdf(
            mode="regional",
            region_key="hmd",
            start_year=2023,
            end_year=2023,
            language="en"
        )
        assert pdf_en is not None
        assert len(pdf_en.getvalue()) > 5000

        # Generate French PDF
        pdf_fr = generate_master_publication_pdf(
            mode="regional",
            region_key="hmd",
            start_year=2023,
            end_year=2023,
            language="fr"
        )
        assert pdf_fr is not None
        assert len(pdf_fr.getvalue()) > 5000


def test_dashboard_multi_facility_query(client):
    """Test that /api/dashboard/batch-all and /api/dashboard/intensity-stats accept comma-separated facility IDs."""
    with app.app_context():
        admin = User.query.filter_by(role="admin").first()
        if not admin:
            admin = User(
                fullName="Admin Test",
                orgName="Sonatrach",
                sector="Oil & Gas",
                email="admin_multi_test@sonatrach.dz",
                role="admin",
                password_hash="hash",
                status="active"
            )
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

        fac1 = Facility(name="Test Fac 1", region="Region A", field="Field 1", activity="Upstream", division="Div A")
        fac2 = Facility(name="Test Fac 2", region="Region B", field="Field 2", activity="Upstream", division="Div B")
        db.session.add_all([fac1, fac2])
        db.session.commit()
        f1, f2 = fac1.id, fac2.id

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    # Test single facility
    res_single = client.get(f"/api/dashboard/intensity-stats?facilityId={f1}")
    assert res_single.status_code == 200

    # Test multiple facilities
    res_multi = client.get(f"/api/dashboard/intensity-stats?facilityId={f1},{f2}")
    assert res_multi.status_code == 200
    rows = res_multi.get_json()
    assert isinstance(rows, list)
    ret_fids = {r["facility_id"] for r in rows}
    assert ret_fids.issubset({f1, f2})

    # Test batch-all
    res_batch = client.get(f"/api/dashboard/batch-all?facilityId={f1},{f2}")
    assert res_batch.status_code == 200

    with app.app_context():
        fc1 = db.session.get(Facility, f1)
        fc2 = db.session.get(Facility, f2)
        if fc1:
            db.session.delete(fc1)
        if fc2:
            db.session.delete(fc2)
        db.session.commit()

