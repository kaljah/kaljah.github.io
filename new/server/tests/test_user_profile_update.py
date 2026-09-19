import pytest
from app import app
from models import db, User


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def it_admin(client):
    with app.app_context():
        user = User.query.filter_by(email="it_admin_profile_test@domain.com").first()
        if not user:
            user = User(
                email="it_admin_profile_test@domain.com",
                fullName="IT Admin Tester",
                orgName="TestOrg",
                sector="Energy",
                role="it_admin",
            )
            user.set_password("AdminPass123!@#")
            db.session.add(user)
            db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
    return user_id


@pytest.fixture
def target_user(client):
    with app.app_context():
        leftover = User.query.filter_by(email="new_target_email@domain.com").first()
        if leftover:
            db.session.delete(leftover)
            db.session.commit()
        user = User.query.filter_by(email="target_user_edit@domain.com").first()
        if not user:
            user = User(
                email="target_user_edit@domain.com",
                fullName="Original Target User",
                orgName="TestOrg",
                sector="Energy",
                role="user",
                location="Algiers",
                department="Operations",
                jobTitle="Field Technician",
            )
            user.set_password("UserPass123!@#")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def existing_other_user(client):
    with app.app_context():
        user = User.query.filter_by(email="collision_target@domain.com").first()
        if not user:
            user = User(
                email="collision_target@domain.com",
                fullName="Collision Other User",
                orgName="TestOrg",
                sector="Energy",
                role="user",
            )
            user.set_password("UserPass123!@#")
            db.session.add(user)
            db.session.commit()
        return user.id


def test_update_user_profile_information(client, it_admin, target_user):
    payload = {
        "fullName": "Updated Target Name",
        "email": "new_target_email@domain.com",
        "department": "Renewables & Carbon",
        "jobTitle": "Lead Carbon Analyst",
        "role": "user",
        "location": "Algiers",
    }
    res = client.put(f"/api/auth/users/{target_user}", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "user" in data
    u = data["user"]
    assert u["fullName"] == "Updated Target Name"
    assert u["email"] == "new_target_email@domain.com"
    assert u["department"] == "Renewables & Carbon"
    assert u["jobTitle"] == "Lead Carbon Analyst"

    # Verify directly from DB
    with app.app_context():
        db_user = db.session.get(User, target_user)
        assert db_user.fullName == "Updated Target Name"
        assert db_user.email == "new_target_email@domain.com"
        assert db_user.department == "Renewables & Carbon"
        assert db_user.jobTitle == "Lead Carbon Analyst"


def test_update_user_email_collision_rejected(client, it_admin, target_user, existing_other_user):
    # Attempt to change target_user's email to collision_target@domain.com
    payload = {
        "email": "collision_target@domain.com",
        "fullName": "Some Name",
    }
    res = client.put(f"/api/auth/users/{target_user}", json=payload)
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data
    assert "already in use" in data["error"].lower()
