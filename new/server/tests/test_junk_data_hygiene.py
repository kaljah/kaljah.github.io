import pytest
from tests.audit_helpers import make_user, make_facility, login, uniq
from models import Facility, EmissionSource, CustomFactor, MitigationProject, Emission
from services.dashboard_filters import apply_scope
from extensions import db


def test_required_name_validation(client, app):
    """Item 1.9: Names cannot be empty or 'None' across entities."""
    with app.app_context():
        admin = make_user("admin")
        fac = make_facility(name=uniq("FAC_VALID"))
        login(client, admin)

        # 1. Facility name cannot be "None" or empty
        res = client.post("/api/facilities", json={"name": "None", "code": uniq("C_NONE")})
        assert res.status_code == 400

        res2 = client.post("/api/facilities", json={"name": "   ", "code": uniq("C_EMPTY")})
        assert res2.status_code == 400

        # 2. Emission source name cannot be "None" or empty
        res_src = client.post("/api/sources", json={"facility_id": fac.id, "name": "None", "type": "combustion"})
        assert res_src.status_code == 400

        res_src2 = client.post("/api/sources", json={"facility_id": fac.id, "name": "", "type": "combustion"})
        assert res_src2.status_code == 400

        # 3. Mitigation project name cannot be "None" or empty
        res_mit = client.post("/api/mitigation", json={"facility_id": fac.id, "name": "None", "year": 2026})
        assert res_mit.status_code == 400

        # 4. Custom factor name cannot be "None" or empty
        res_cf = client.post("/api/custom-factors", json={"name": "None", "unit": "kg/m3", "co2_factor": 1.5})
        assert res_cf.status_code == 400


def test_is_test_flag_filtering(client, app):
    """Item 1.9: Test records flagged with is_test=True are excluded from scoped queries."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        # Create a production facility and a test facility
        prod_fac = make_facility(name=uniq("FAC_PROD"))
        test_fac = make_facility(name=uniq("FAC_TEST"))
        test_fac.is_test = True
        db.session.commit()

        # Emission on test facility
        em_test = Emission(
            facility_id=test_fac.id,
            year=2026,
            co2e_total=50000.0,
            status="Verified",
            is_test=True,
        )
        # Emission on prod facility
        em_prod = Emission(
            facility_id=prod_fac.id,
            year=2026,
            co2e_total=12000.0,
            status="Verified",
            is_test=False,
        )
        db.session.add_all([em_test, em_prod])
        db.session.commit()

        # Query with apply_scope (include_test=False by default)
        q = apply_scope(Emission.query, Emission)
        results = q.filter(Emission.facility_id.in_([prod_fac.id, test_fac.id])).all()

        # Must only return em_prod; em_test must be excluded
        assert len(results) == 1
        assert results[0].id == em_prod.id
