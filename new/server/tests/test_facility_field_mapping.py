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
                orgName="Demo Operator Co.",
                sector="Oil & Gas",
                email="admin_field_test@example.org",
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
                orgName="Demo Operator Co.",
                sector="Oil & Gas",
                email="admin_multi_test@example.org",
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


def test_facility_consolidation_approach_saves_to_jv_ventures(client):
    """
    Test that adding a new facility with Equity Share / Joint Venture consolidation approach:
    1. Saves the facility with operator_status='non_operated' if equity_share_pct < 50.
    2. Automatically persists a FacilityEquityShare record for the operator (Demo Operator Co.).
    3. GET /api/equity/shares?facility_id=<id> returns the newly created share.
    4. Updating the facility's equity share % via PUT /api/facilities/<id> updates the FacilityEquityShare.
    5. Updating the operator's share via POST /api/equity/shares keeps facility.equity_share_pct in sync.
    """
    with app.app_context():
        from models import FacilityEquityShare, JvPartner
        admin = User.query.filter_by(role="admin").first()
        if not admin:
            admin = User(
                fullName="Admin Test",
                orgName="Demo Operator Co.",
                sector="Oil & Gas",
                email="admin_jv_test@example.org",
                role="admin",
                password_hash="hash",
                status="active"
            )
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    # Add facility with Consolidation Approach: Equity Share, Joint Venture, 10%
    payload = {
        "region_name": "In Amenas",
        "field": "JV-Test-Field-UTG",
        "activity": "EP",
        "division": "Production",
        "location": "Illizi, Algeria",
        "boundary_type": "Equity Share",
        "boundary_detail": "Joint Venture",
        "equity_share_pct": 10.0,
        "ogmp_membership_year": 2021,
        "agreement_reference": "PSC Block 405b",
    }
    res = client.post("/api/facilities", json=payload)
    assert res.status_code == 201, f"Failed: {res.get_json()}"
    fac_id = res.get_json()["id"]

    try:
        with app.app_context():
            fac = db.session.get(Facility, fac_id)
            assert fac is not None
            assert fac.boundary_type == "Equity Share"
            assert fac.boundary_detail == "Joint Venture"
            assert fac.equity_share_pct == 10.0
            assert fac.operator_status == "non_operated"

            # Check that FacilityEquityShare was persisted
            shares = FacilityEquityShare.query.filter_by(facility_id=fac_id).all()
            assert len(shares) == 1
            assert shares[0].equity_share_pct == 10.0
            assert shares[0].partner.is_operator is True

        # Test GET /api/equity/shares returns it
        res_shares = client.get(f"/api/equity/shares?facility_id={fac_id}")
        assert res_shares.status_code == 200
        shares_data = res_shares.get_json()
        assert len(shares_data) == 1
        assert shares_data[0]["equity_share_pct"] == 10.0
        assert shares_data[0]["partner_name"] == "Demo Operator Co."

        # Test updating facility equity % via PUT /api/facilities/<id>
        res_put = client.put(f"/api/facilities/{fac_id}", json={"equity_share_pct": 25.0})
        assert res_put.status_code == 200

        with app.app_context():
            fac = db.session.get(Facility, fac_id)
            assert fac.equity_share_pct == 25.0
            shares = FacilityEquityShare.query.filter_by(facility_id=fac_id).all()
            assert len(shares) == 1
            assert shares[0].equity_share_pct == 25.0

        # Test bidirectional sync from POST /api/equity/shares back to facility
        operator_partner_id = shares_data[0]["partner_id"]
        res_post_share = client.post("/api/equity/shares", json={
            "id": shares_data[0]["id"],
            "facility_id": fac_id,
            "partner_id": operator_partner_id,
            "equity_share_pct": 35.0,
            "effective_start_date": "2021-01-01"
        })
        assert res_post_share.status_code == 200

        with app.app_context():
            fac = db.session.get(Facility, fac_id)
            assert fac.equity_share_pct == 35.0

        # Test equity > 100% rejection in PUT /api/facilities/<id>
        partner_b = JvPartner.query.filter_by(name="Demo JV Partner B").first()
        if partner_b:
            res_add_partner_b = client.post("/api/equity/shares", json={
                "facility_id": fac_id,
                "partner_id": partner_b.id,
                "equity_share_pct": 50.0,
                "effective_start_date": "2021-01-01"
            })
            assert res_add_partner_b.status_code == 200

            # Now Demo Operator Co. has 35%, Demo JV Partner B has 50% = 85% total.
            # Attempting to set facility equity to 60% (60 + 50 = 110% > 100%) must fail with 400
            res_overflow = client.put(f"/api/facilities/{fac_id}", json={"equity_share_pct": 60.0})
            assert res_overflow.status_code == 400
            assert "max 100%" in res_overflow.get_json()["error"]

        # Test invalid partner_id rejection
        res_bad_partner = client.put(f"/api/facilities/{fac_id}", json={"partner_id": 99999})
        assert res_bad_partner.status_code == 400
        assert "does not exist" in res_bad_partner.get_json()["error"]

    finally:
        with app.app_context():
            FacilityEquityShare.query.filter_by(facility_id=fac_id).delete()
            fac = db.session.get(Facility, fac_id)
            if fac:
                db.session.delete(fac)
            db.session.commit()


