"""RC-1 authorization / facility-scope regressions (AUDIT_FINDINGS.md).

Each test names the BUG it guards. Expected values come from the audit's stated
expected behaviour, not from current output.
"""
import pytest

from extensions import db
from models import CustomFactor, Facility
from tests.audit_helpers import login, make_facility, make_user, uniq, upload


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ── BUG-001: bulk job endpoint must enforce the dedicated endpoints' roles ──────────

@pytest.mark.parametrize("role,location", [("user", "West"), ("it_admin", "Global"), ("it", "Global")])
def test_bug001_non_admin_cannot_bulk_import_facilities_or_factors(client, ctx, role, location):
    target = make_facility(region="Center")
    u = make_user(role, location)
    login(client, u)
    evil = uniq("EVIL")
    r1, _, _ = upload(client, f"name,location\n{target.name},HACKED\nNEW_{evil},X\n", "facilities")
    r2, _, _ = upload(client, f"name,co2_factor,unit\n{evil},999,scf\n", "custom_factors")
    assert r1.status_code == 403 and r2.status_code == 403
    db.session.expire_all()
    assert db.session.get(Facility, target.id).location == "Center"
    assert Facility.query.filter_by(name=f"NEW_{evil}").count() == 0
    assert CustomFactor.query.filter_by(name=evil).count() == 0


def test_bug001_it_roles_cannot_start_any_bulk_job(client, ctx):
    login(client, make_user("it_admin", "Global"))
    r, _, _ = upload(client, "date,facility_name,quantity\n2024-01,X,1\n", "1")
    assert r.status_code == 403


def test_bug001_regional_superuser_cannot_overwrite_or_reregion_other_region(client, ctx):
    center = make_facility(region="Center")
    west = make_facility(region="West")
    login(client, make_user("superuser", "West"))
    # overwrite a Center facility
    _, _, st = upload(client, f"name,location\n{center.name},HACKED\n", "facilities")
    # move own West facility to East through bulk overwrite
    _, _, st2 = upload(client, f"name,region\n{west.name},East\n", "facilities")
    db.session.expire_all()
    assert db.session.get(Facility, center.id).location == "Center"
    assert db.session.get(Facility, west.id).region == "West"


def test_bug001_admin_can_still_bulk_import_facilities(client, ctx):
    login(client, make_user("admin", "Global"))
    name = uniq("ADMINFAC")
    _, _, st = upload(client, f"name,location,region\n{name},Loc,East\n", "facilities")
    assert st["status"] == "completed", st
    assert Facility.query.filter_by(name=name).count() == 1


# ── BUG-093: PUT /api/facilities/<id> must keep the facility inside the caller's scope ──

def test_bug093_regional_superuser_cannot_move_facility_out_of_region(client, ctx):
    f = make_facility(region="West")
    login(client, make_user("superuser", "West"))
    r = client.put(f"/api/facilities/{f.id}", json={"region": "East", "location": "East"})
    assert r.status_code == 403
    db.session.expire_all()
    assert db.session.get(Facility, f.id).region == "West"
    # editing within the region still works
    assert client.put(f"/api/facilities/{f.id}", json={"description": "ok"}).status_code == 200


def test_bug093_admin_may_reregion(client, ctx):
    f = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    assert client.put(f"/api/facilities/{f.id}", json={"region": "East"}).status_code == 200


# ── BUG-029: facility name is required; NULL-name rows must not break bulk import ──

@pytest.mark.parametrize("payload", [{"region": "West"}, {"name": "", "region": "West"}, {"name": "   ", "region": "West"}])
def test_bug029_create_facility_requires_name(client, ctx, payload):
    login(client, make_user("admin", "Global"))
    before = Facility.query.count()
    r = client.post("/api/facilities", json=payload)
    assert r.status_code == 400
    assert Facility.query.count() == before


def test_bug029_bulk_import_survives_legacy_null_name_facility(client, ctx):
    legacy = Facility(name=None, region=None)
    db.session.add(legacy)
    db.session.commit()
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    csv = ("date,facility_name,process,fuel,quantity,unit,factor_type\n"
           f"2024-03,{fac.name},combustion,Natural Gas,100,MMBtu,default\n")
    _, _, st = upload(client, csv, "1")
    assert st["status"] == "completed", st
    assert not any("NoneType" in str(e) for e in st.get("errors", []))
    db.session.delete(legacy)
    db.session.commit()


# ── BUG-045: optional latitude/longitude ────────────────────────────────────────────

def test_bug045_blank_coordinates_are_accepted(client, ctx):
    login(client, make_user("admin", "Global"))
    r = client.post("/api/facilities", json={"name": uniq("F"), "region": "West", "latitude": "", "longitude": ""})
    assert r.status_code == 201, r.get_data(as_text=True)
    f = db.session.get(Facility, r.get_json()["id"])
    assert f.latitude is None and f.longitude is None


@pytest.mark.parametrize("lat,lon", [("abc", 3), (91, 3), (10, 181)])
def test_bug045_invalid_coordinates_rejected_with_400(client, ctx, lat, lon):
    login(client, make_user("admin", "Global"))
    r = client.post("/api/facilities", json={"name": uniq("F"), "region": "West", "latitude": lat, "longitude": lon})
    assert r.status_code == 400


# ── Superuser audit 2026-10-09 (SU-1): location / name may not name another region's scope ──

def test_regional_superuser_cannot_put_facility_into_another_regions_scope(client, ctx):
    west, north = uniq("West"), uniq("North")
    make_facility(region=north)
    own = make_facility(region=west)
    login(client, make_user("superuser", west))
    # create: region blank, name = own region (in scope), location = another region
    r = client.post("/api/facilities/", json={"name": west, "location": north, "code": uniq("C")})
    assert r.status_code == 403
    r = client.post("/api/facilities/", json={"name": north, "region": west, "code": uniq("C")})
    assert r.status_code == 403
    # update: keep the region, point the location at another region
    assert client.put(f"/api/facilities/{own.id}", json={"location": north}).status_code == 403
    db.session.expire_all()
    assert db.session.get(Facility, own.id).location == west


def test_regional_superuser_can_still_edit_own_facility(client, ctx):
    west = uniq("West")
    own = make_facility(region=west, location="Shared town")
    make_facility(region=uniq("North"), location="Shared town")  # a location two regions share is not a scope key
    login(client, make_user("superuser", west))
    r = client.put(f"/api/facilities/{own.id}", json={"location": "Shared town", "name": uniq("Renamed")})
    assert r.status_code == 200, r.get_data(as_text=True)
    r = client.post("/api/facilities/", json={"name": uniq("NEW"), "region": west, "location": "Field camp",
                                              "code": uniq("C")})
    assert r.status_code == 201, r.get_data(as_text=True)


# ── SU-2: deleting a facility may not cascade-delete Verified records a superuser cannot delete ──

def test_superuser_cannot_delete_facility_with_verified_records(client, ctx):
    from models import Emission
    west = uniq("West")
    f = make_facility(region=west)
    db.session.add(Emission(facility_id=f.id, year=2026, month=1, process_type="combustion", co2e_total=1.0,
                            status="Verified"))
    db.session.commit()
    login(client, make_user("superuser", west))
    assert client.delete(f"/api/facilities/{f.id}").status_code == 403
    db.session.expire_all()
    assert db.session.get(Facility, f.id) is not None
    empty = make_facility(region=west)
    assert client.delete(f"/api/facilities/{empty.id}").status_code == 200
    login(client, make_user("admin", "Global"))
    assert client.delete(f"/api/facilities/{f.id}").status_code == 200


# ── SU-6 / OP-3: production data (the intensity denominator) ──

def test_production_rejects_negative_and_absurd_values(client, ctx):
    west = uniq("West")
    f = make_facility(region=west)
    login(client, make_user("superuser", west))
    base = {"facility_id": f.id, "year": 2025, "month": 12, "oil_amount": 1}
    for bad in ({"total_production_mmboe": -9}, {"oil_amount": 1e300}, {"saleable_production_mmboe": "nan"},
                {"gas_amount": -1}):
        assert client.post("/api/data/production", json={**base, **bad}).status_code == 400, bad
    assert client.post("/api/data/production", json={**base, "total_production_mmboe": 0.5}).status_code == 201


def test_operator_cannot_overwrite_or_delete_anothers_production(client, ctx):
    from models import ProductionData
    west = uniq("West")
    f = make_facility(region=west)
    login(client, make_user("user", west))
    assert client.post("/api/data/production",
                       json={"facility_id": f.id, "year": 2025, "month": 3, "oil_amount": 100}).status_code == 201
    login(client, make_user("user", west))
    r = client.post("/api/data/production", json={"facility_id": f.id, "year": 2025, "month": 3, "oil_amount": 1})
    assert r.status_code == 403
    rec = ProductionData.query.filter_by(facility_id=f.id, year=2025, month=3).first()
    assert client.delete(f"/api/data/production/{rec.id}").status_code == 403
    db.session.expire_all()
    assert db.session.get(ProductionData, rec.id).oil_amount == 100
    login(client, make_user("superuser", west))
    assert client.post("/api/data/production",
                       json={"facility_id": f.id, "year": 2025, "month": 3, "oil_amount": 2}).status_code == 201


def test_mitigation_rejects_bad_year_and_negative_quantity(client, ctx):
    west = uniq("West")
    f = make_facility(region=west)
    login(client, make_user("superuser", west))
    base = {"facility_id": f.id, "name": "x", "type": "CCUS", "status": "Active"}
    assert client.post("/api/mitigation", json={**base, "year": "abc", "quantity_tco2e": 5}).status_code == 400
    assert client.post("/api/mitigation", json={**base, "year": 2025, "quantity_tco2e": -5000}).status_code == 400
    assert client.post("/api/mitigation", json={**base, "year": 2025, "quantity_tco2e": 50}).status_code == 201
