"""The Copernicus / Sentinel-5P integration was removed (owner decision 2026-10-09).

Its routes are gone, and settings an older database still holds (credentials included) are never
loaded, stored or returned. OGMP 2.0 site-level surveys of type "Satellite" stay: operators record
those themselves.
"""
import json

import pytest

from extensions import db
from models import SystemSetting, User
from tests.audit_helpers import login, make_user


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield
        db.session.rollback()


@pytest.mark.parametrize("url", [
    "/api/satellite/sentinel5p/layer-config",
    "/api/satellite/sentinel5p/query",
    "/api/satellite/sentinel5p/export-to-ogmp",
])
def test_satellite_routes_are_gone(app, ctx, url):
    with app.test_client() as c:
        login(c, make_user("admin"))
        assert c.get(url).status_code == 404


def test_stored_copernicus_credentials_are_never_returned(app, ctx):
    from routes.auth import load_settings_from_db, _app_settings

    previous = db.session.get(SystemSetting, "copernicus_password")
    previous = previous.value if previous else None
    db.session.merge(SystemSetting(key="copernicus_password", value=json.dumps("old-secret")))
    db.session.commit()
    admin = make_user("admin")
    admin.preferences = json.dumps({"copernicus_client_secret": "pref-secret", "theme": "light"})
    db.session.commit()
    try:
        load_settings_from_db()
        assert "copernicus_password" not in _app_settings
        with app.test_client() as c:
            login(c, admin)
            body = c.get("/api/auth/settings").get_json()
            assert not any(k.startswith("copernicus_") for k in body)
            saved = c.put("/api/auth/settings", json={"copernicus_password": "new", "theme": "light"}).get_json()
            assert not any(k.startswith("copernicus_") for k in saved["settings"])
        db.session.expire_all()
        prefs = json.loads(db.session.get(User, admin.id).preferences)
        assert not any(k.startswith("copernicus_") for k in prefs)
    finally:
        row = db.session.get(SystemSetting, "copernicus_password")
        if previous is None:
            db.session.delete(row)
        else:
            row.value = previous
        db.session.commit()
