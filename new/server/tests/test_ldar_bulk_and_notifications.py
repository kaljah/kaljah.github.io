import pytest
from app import app
from models import db, User, Facility, ComponentInventory, FugitiveSurvey, Notification


@pytest.fixture
def test_setup():
    with app.app_context():
        # Facility
        fac = Facility.query.filter_by(name="LDAR Test Facility").first()
        if not fac:
            fac = Facility(name="LDAR Test Facility", location="Basra", country="Iraq")
            db.session.add(fac)
            db.session.commit()

        # Admin user
        admin = User.query.filter_by(email="admin_ldar@test.com").first()
        if not admin:
            admin = User(
                email="admin_ldar@test.com",
                fullName="LDAR Admin",
                orgName="Energy Corp",
                sector="Oil & Gas",
                role="admin",
            )
            admin.set_password("Password123!")
            db.session.add(admin)

        # Regular operator user
        operator = User.query.filter_by(email="op_ldar@test.com").first()
        if not operator:
            operator = User(
                email="op_ldar@test.com",
                fullName="LDAR Operator",
                orgName="Energy Corp",
                sector="Oil & Gas",
                role="user",
                location="Basra",
            )
            operator.set_password("Password123!")
            db.session.add(operator)
        else:
            operator.location = "Basra"

        # IT user
        it_user = User.query.filter_by(email="it_ldar@test.com").first()
        if not it_user:
            it_user = User(
                email="it_ldar@test.com",
                fullName="LDAR IT",
                orgName="Energy Corp",
                sector="Oil & Gas",
                role="it_admin",
            )
            it_user.set_password("Password123!")
            db.session.add(it_user)

        db.session.commit()
        db.session.remove()
        return {
            "facility_id": fac.id,
            "admin_email": "admin_ldar@test.com",
            "op_email": "op_ldar@test.com",
            "it_email": "it_ldar@test.com",
        }


def test_add_broken_component_triggers_notification(client, test_setup):
    client.post("/api/auth/login", json={"email": test_setup["op_email"], "password": "Password123!"})

    # Create active component -> No notification
    res1 = client.post(
        "/api/ldar/components",
        json={
            "facility_id": test_setup["facility_id"],
            "equipment_type": "Valves",
            "component_type": "Gate Valve",
            "service_type": "Gas",
            "quantity": 1,
            "operating_hours": 8760,
            "status": "Active",
        },
    )
    assert res1.status_code == 201
    active_comp_id = res1.get_json()["component"]["id"]

    with app.app_context():
        db.session.remove()
        notif_active = Notification.query.filter(
            Notification.metadata_json.like(f"%\"component_id\": {active_comp_id}%")
        ).first()
        assert notif_active is None

    # Create broken component -> Notification triggered
    res2 = client.post(
        "/api/ldar/components",
        json={
            "facility_id": test_setup["facility_id"],
            "equipment_type": "Pumps",
            "component_type": "Reciprocating Pump",
            "service_type": "Light Liquid",
            "quantity": 1,
            "operating_hours": 4000,
            "status": "Broken",
        },
    )
    assert res2.status_code == 201
    broken_comp_id = res2.get_json()["component"]["id"]

    with app.app_context():
        db.session.remove()
        notif = Notification.query.filter(
            Notification.metadata_json.like(f"%\"component_id\": {broken_comp_id}%")
        ).first()
        assert notif is not None
        assert "Broken Component" in notif.title
        assert notif.type == "warning"
        assert "Reciprocating Pump" in notif.message


def test_update_component_to_broken_triggers_notification(client, test_setup):
    client.post("/api/auth/login", json={"email": test_setup["op_email"], "password": "Password123!"})

    # Create active component
    res = client.post(
        "/api/ldar/components",
        json={
            "facility_id": test_setup["facility_id"],
            "equipment_type": "Flanges",
            "component_type": "Weld Neck Flange",
            "service_type": "Gas",
            "quantity": 5,
            "status": "Active",
        },
    )
    assert res.status_code == 201
    comp_id = res.get_json()["component"]["id"]

    # Update component to "Leaking"
    res_up = client.put(f"/api/ldar/components/{comp_id}", json={"status": "Leaking"})
    assert res_up.status_code == 200

    with app.app_context():
        db.session.remove()
        notif = Notification.query.filter(
            Notification.metadata_json.like(f"%\"component_id\": {comp_id}%")
        ).first()
        assert notif is not None
        assert "Component Marked Broken" in notif.title
        assert notif.type == "warning"


def test_survey_leak_detection_triggers_notification(client, test_setup):
    client.post("/api/auth/login", json={"email": test_setup["op_email"], "password": "Password123!"})

    res = client.post(
        "/api/ldar/surveys",
        json={
            "facility_id": test_setup["facility_id"],
            "survey_method": "Method 21",
            "screening_value_ppm": 3200,
            "leak_status": "Leaking",
            "surveyor_name": "Test Surveyor",
        },
    )
    assert res.status_code == 201
    survey_id = res.get_json()["survey"]["id"]

    with app.app_context():
        db.session.remove()
        notif = Notification.query.filter(
            Notification.metadata_json.like(f"%\"survey_id\": {survey_id}%")
        ).first()
        assert notif is not None
        assert "Leak Detected in Survey" in notif.title
        assert notif.type == "warning"


def test_components_bulk_update_and_delete(client, test_setup):
    client.post("/api/auth/login", json={"email": test_setup["admin_email"], "password": "Password123!"})

    # Create 3 components
    comp_ids = []
    for i in range(3):
        res = client.post(
            "/api/ldar/components",
            json={
                "facility_id": test_setup["facility_id"],
                "equipment_type": "Valves",
                "component_type": f"Ball Valve {i}",
                "service_type": "Gas",
                "quantity": 1,
                "operating_hours": 8760,
                "status": "Active",
            },
        )
        assert res.status_code == 201
        comp_ids.append(res.get_json()["component"]["id"])

    # Bulk update to Broken
    res_bulk = client.post(
        "/api/ldar/components/bulk-update",
        json={
            "ids": comp_ids,
            "status": "Broken",
            "operating_hours": 5000,
        },
    )
    assert res_bulk.status_code == 200
    assert res_bulk.get_json()["updated_count"] == 3

    # Check notification created
    with app.app_context():
        db.session.remove()
        notif = Notification.query.filter(
            Notification.title == "LDAR Alert: Components Marked Broken"
        ).order_by(Notification.id.desc()).first()
        assert notif is not None
        assert notif.type == "warning"
        # Verify in DB
        comps = ComponentInventory.query.filter(ComponentInventory.id.in_(comp_ids)).all()
        for c in comps:
            assert c.status == "Broken"
            assert c.operating_hours == 5000.0

    # Bulk delete
    res_del = client.post(
        "/api/ldar/components/bulk-delete",
        json={"ids": comp_ids},
    )
    assert res_del.status_code == 200
    assert res_del.get_json()["deleted_count"] == 3

    # Verify deleted
    with app.app_context():
        remaining = ComponentInventory.query.filter(ComponentInventory.id.in_(comp_ids)).count()
        assert remaining == 0


def test_surveys_bulk_update_and_delete(client, test_setup):
    client.post("/api/auth/login", json={"email": test_setup["admin_email"], "password": "Password123!"})

    # Create 2 leaking surveys
    survey_ids = []
    for i in range(2):
        res = client.post(
            "/api/ldar/surveys",
            json={
                "facility_id": test_setup["facility_id"],
                "survey_method": "OGI",
                "screening_value_ppm": 1200,
                "leak_status": "Leaking",
                "notes": f"Initial leak {i}",
            },
        )
        assert res.status_code == 201
        survey_ids.append(res.get_json()["survey"]["id"])

    # Bulk mark repaired
    res_bulk = client.post(
        "/api/ldar/surveys/bulk-update",
        json={
            "ids": survey_ids,
            "leak_status": "Repaired",
            "repair_date": "2026-10-13",
            "notes": "Bulk repaired by maintenance team",
        },
    )
    assert res_bulk.status_code == 200
    assert res_bulk.get_json()["updated_count"] == 2

    # Verify in DB
    with app.app_context():
        surveys = FugitiveSurvey.query.filter(FugitiveSurvey.id.in_(survey_ids)).all()
        for s in surveys:
            assert s.leak_status == "Repaired"
            assert s.repair_date == "2026-10-13"
            assert "Bulk repaired by maintenance team" in s.notes

    # Bulk delete
    res_del = client.post(
        "/api/ldar/surveys/bulk-delete",
        json={"ids": survey_ids},
    )
    assert res_del.status_code == 200
    assert res_del.get_json()["deleted_count"] == 2

    with app.app_context():
        remaining = FugitiveSurvey.query.filter(FugitiveSurvey.id.in_(survey_ids)).count()
        assert remaining == 0


def test_it_and_unauthorized_rbac(client, test_setup):
    # IT user is forbidden from LDAR operations
    client.post("/api/auth/login", json={"email": test_setup["it_email"], "password": "Password123!"})
    res_comp = client.post(
        "/api/ldar/components/bulk-update",
        json={"ids": [1], "status": "Active"},
    )
    assert res_comp.status_code == 403

    res_survey = client.post(
        "/api/ldar/surveys/bulk-update",
        json={"ids": [1], "leak_status": "Repaired"},
    )
    assert res_survey.status_code == 403

    # Regular user cannot bulk delete
    client.post("/api/auth/login", json={"email": test_setup["op_email"], "password": "Password123!"})
    res_del = client.post(
        "/api/ldar/components/bulk-delete",
        json={"ids": [1]},
    )
    assert res_del.status_code == 403
