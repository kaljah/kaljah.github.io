"""BUG-087: 5xx responses never carry exception text."""
from extensions import db
from tests.audit_helpers import login, make_facility, make_user


def test_internal_error_body_is_generic(app):
    from utils import internal_error

    with app.test_request_context():
        resp, status = internal_error(RuntimeError("secret sqlite path /srv/db"), "Failed to add source")
        assert status == 500
        assert resp.get_json() == {"error": "Failed to add source"}
        resp, _ = internal_error(RuntimeError("x"), status_text="error")
        assert resp.get_json() == {"error": "Internal server error", "status": "error", "message": "Internal server error"}


def test_route_500_does_not_leak_exception(client, app, monkeypatch):
    with app.app_context():
        f = make_facility(region="West")
        db.session.commit()
        login(client, make_user("admin", "Global"))

        def boom(*a, **k):
            raise RuntimeError("OperationalError: /secret/ghg_app.db locked")

        monkeypatch.setattr(db.session, "commit", boom)
        r = client.post("/api/sources", json={"facility_id": f.id, "name": "S1", "type": "Boiler"})
        monkeypatch.undo()
        assert r.status_code == 500
        assert "secret" not in r.get_data(as_text=True)
        assert "OperationalError" not in r.get_data(as_text=True)
