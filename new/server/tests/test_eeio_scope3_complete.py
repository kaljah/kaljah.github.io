"""Tests for emission_factors/eeio_factors.py, /api/scope3/eeio-* routes,
and background_processor._process_row_scope3_eeio (spend-based Scope 3 calculations).
"""
import uuid
import pytest
from app import app as flask_app
from extensions import db
from models import Facility, User, Scope3Emission
from emission_factors.eeio_factors import EEIO_FACTORS, get_eeio_factor, search_eeio_factors
from background_processor import _process_row_scope3_eeio


@pytest.fixture(scope="module")
def eeio_world():
    tag = uuid.uuid4().hex[:6]
    with flask_app.app_context():
        f = Facility(name=f"EEIO Fac {tag}", region=f"Reg{tag}", activity="EP", division="D",
                     field="F", segment="Upstream", code=f"EF{tag}")
        admin = User(email=f"eeio_admin_{tag}@test.com", fullName="EEIO Admin", orgName="Org",
                     sector="Energy", role="admin", location="Global Corporate Head Office")
        it_user = User(email=f"eeio_it_{tag}@test.com", fullName="EEIO IT", orgName="Org",
                       sector="Energy", role="it_admin", location="Global Corporate Head Office")
        user = User(email=f"eeio_user_{tag}@test.com", fullName="EEIO User", orgName="Org",
                    sector="Energy", role="user", location=f"Reg{tag}")
        for u in (admin, it_user, user):
            u.set_password("EeioPass123!")
        db.session.add_all([f, admin, it_user, user])
        db.session.commit()
        return {"fid": f.id, "fname": f.name, "admin_id": admin.id, "it_id": it_user.id,
                "user_id": user.id, "tag": tag}


def _login(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid


# =============================================================================
# 1. Unit Tests for emission_factors/eeio_factors.py
# =============================================================================

def test_eeio_factors_dataset_loaded():
    assert len(EEIO_FACTORS) >= 1000
    # Spot check known NAICS code
    assert "331110" in EEIO_FACTORS
    entry = EEIO_FACTORS["331110"]
    assert "iron and steel" in entry["name"].lower()
    assert entry["kg_co2e_per_usd"] > 0
    assert entry["kg_co2e_per_1000_usd"] == pytest.approx(entry["kg_co2e_per_usd"] * 1000.0)


def test_get_eeio_factor_exact_and_trimmed():
    f1 = get_eeio_factor("331110")
    f2 = get_eeio_factor("  331110  ")
    assert f1 == f2
    assert f1["name"] == "Iron and Steel Mills and Ferroalloy Manufacturing"


@pytest.mark.parametrize("bad_code,match", [
    ("", "must be a six-digit 2017 NAICS code"),
    ("ABC", "must be a six-digit 2017 NAICS code"),
    ("331", "must be a six-digit 2017 NAICS code"),
    ("33111", "must be a six-digit 2017 NAICS code"),
    ("3311100", "must be a six-digit 2017 NAICS code"),
    ("999999", "is not in the EPA supply chain factor dataset"),
])
def test_get_eeio_factor_refusals(bad_code, match):
    with pytest.raises(LookupError, match=match):
        get_eeio_factor(bad_code)


def test_search_eeio_factors_prefix_and_title():
    prefix_hits = search_eeio_factors("3311")
    assert len(prefix_hits) > 0
    assert all(h["naics"].startswith("3311") for h in prefix_hits)

    title_hits = search_eeio_factors("petroleum")
    assert len(title_hits) > 0
    assert any("petroleum" in h["name"].lower() for h in title_hits)

    empty = search_eeio_factors("")
    assert empty == []

    limited = search_eeio_factors("a", limit=5)
    assert len(limited) <= 5


# =============================================================================
# 2. API Routes: /api/scope3/eeio-calculate and /api/scope3/eeio-factors
# =============================================================================

def test_eeio_calculate_requires_auth(client):
    res = client.post("/api/scope3/eeio-calculate", json={"spend_usd": 1000, "naics_code": "331110"})
    assert res.status_code == 401


def test_eeio_calculate_refuses_it_role(client, eeio_world):
    _login(client, eeio_world["it_id"])
    res = client.post("/api/scope3/eeio-calculate", json={"spend_usd": 1000, "naics_code": "331110"})
    assert res.status_code == 403


def test_eeio_calculate_zero_and_negative_spend(client, eeio_world):
    _login(client, eeio_world["user_id"])
    res_zero = client.post("/api/scope3/eeio-calculate", json={"spend_usd": 0, "naics_code": "331110"})
    assert res_zero.status_code == 200
    assert res_zero.get_json()["co2e"] == 0

    res_empty = client.post("/api/scope3/eeio-calculate", json={})
    assert res_empty.status_code == 400


def test_eeio_calculate_unknown_naics(client, eeio_world):
    _login(client, eeio_world["user_id"])
    res = client.post("/api/scope3/eeio-calculate", json={"spend_usd": 5000, "naics_code": "999999"})
    assert res.status_code == 422
    assert "field" in res.get_json() and res.get_json()["field"] == "naics_code"


def test_eeio_calculate_valid_precision(client, eeio_world):
    _login(client, eeio_world["user_id"])
    factor_data = get_eeio_factor("331110")
    spend = 125000.0  # $125,000
    res = client.post("/api/scope3/eeio-calculate", json={"spend_usd": spend, "naics_code": "331110"})
    assert res.status_code == 200
    body = res.get_json()

    expected_kg = (spend / 1000.0) * factor_data["kg_co2e_per_1000_usd"]
    expected_t = expected_kg / 1000.0
    assert body["co2e"] == pytest.approx(expected_t)
    assert body["emission_factor"] == pytest.approx(factor_data["kg_co2e_per_1000_usd"])
    assert body["naics_code"] == "331110"


def test_eeio_factors_search_route(client, eeio_world):
    _login(client, eeio_world["user_id"])
    res = client.get("/api/scope3/eeio-factors?q=iron")
    assert res.status_code == 200
    items = res.get_json()
    assert isinstance(items, list)
    assert any("iron" in item["name"].lower() for item in items)


# =============================================================================
# 3. Pipeline Import Processing: background_processor._process_row_scope3_eeio
# =============================================================================

def test_process_row_scope3_eeio_success(eeio_world):
    fac = db.session.get(Facility, eeio_world["fid"])
    fac_name_map = {fac.name.lower(): fac}
    fac_id_map = {str(fac.id): fac}

    row = {
        "date": "2025-03",
        "facility_name": fac.name,
        "naics_code": "331110",
        "spend_usd": "25000",
        "notes": "Steel purchasing Q1",
    }
    batch_keys = {}
    record, errors = _process_row_scope3_eeio(row, eeio_world["admin_id"], fac_name_map, fac_id_map,
                                             "job_1", 1, batch_keys=batch_keys)
    assert not errors
    assert record is not None
    assert record.facility_id == fac.id
    assert record.year == 2025 and record.month == 3
    assert record.category == "Category 1"
    assert "331110" in record.sub_category
    assert record.activity_data == 25000.0
    assert record.unit == "USD"
    factor = get_eeio_factor("331110")["kg_co2e_per_1000_usd"]
    assert record.co2e == pytest.approx(25.0 * factor / 1000.0)


def test_process_row_scope3_eeio_excel_float_code(eeio_world):
    fac = db.session.get(Facility, eeio_world["fid"])
    fac_name_map = {fac.name.lower(): fac}
    fac_id_map = {str(fac.id): fac}

    row = {
        "date": "2025-04",
        "facility_name": fac.name,
        "naics_code": "331110.0",  # Excel formatted number
        "spend_usd": "10000",
    }
    record, errors = _process_row_scope3_eeio(row, eeio_world["admin_id"], fac_name_map, fac_id_map,
                                             "job_1", 2, batch_keys={})
    assert not errors
    assert record is not None
    assert "331110" in record.sub_category
    # the Excel code "331110.0" resolves to the same factor as "331110": 10,000 USD at the NAICS factor per 1,000 USD
    factor = get_eeio_factor("331110")["kg_co2e_per_1000_usd"]
    assert record.co2e == pytest.approx(10.0 * factor / 1000.0)


def test_process_row_scope3_eeio_validation_refusals(eeio_world):
    fac = db.session.get(Facility, eeio_world["fid"])
    fac_name_map = {fac.name.lower(): fac}
    fac_id_map = {str(fac.id): fac}

    # Missing facility
    r1, err1 = _process_row_scope3_eeio({"date": "2025-01", "spend_usd": "100", "naics_code": "331110"},
                                       eeio_world["admin_id"], fac_name_map, fac_id_map, "j", 1)
    assert "not found" in err1[0]

    # Negative / unreadable spend
    r2, err2 = _process_row_scope3_eeio({"date": "2025-01", "facility_name": fac.name, "spend_usd": "-500",
                                        "naics_code": "331110"},
                                       eeio_world["admin_id"], fac_name_map, fac_id_map, "j", 2)
    assert "greater than zero" in err2[0]

    # Unknown NAICS code
    r3, err3 = _process_row_scope3_eeio({"date": "2025-01", "facility_name": fac.name, "spend_usd": "500",
                                        "naics_code": "999999"},
                                       eeio_world["admin_id"], fac_name_map, fac_id_map, "j", 3)
    assert "not in the EPA supply chain" in err3[0]
