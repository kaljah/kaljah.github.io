"""GB HBNS / El Merk RY 2022 validation, fix batches 3 to 7 (Scope 2 grid factors, intensity and NGSI, flaring
split, CSV import, JV partners).

Findings and decisions: docs/validation-gb-ry2022-fix-plan.md (D3 / D4 Scope 2, D5 intensity basis, D7 NGSI gas,
D9 JV partners). Expected values are worked by hand from the report and the cited standards.
"""
import uuid
from types import SimpleNamespace

import pytest

from app import app as flask_app
from calculations.constants import GWP_AR4
from extensions import db
from models import Facility, GridFactor, JvPartner, ProductionData, User

PW = "GbRy2022Fixes1!"


def _user(role):
    email = f"gb37_{role}_{uuid.uuid4().hex[:6]}@example.com"
    with flask_app.app_context():
        u = User(email=email, fullName=f"GB {role}", orgName="GB", sector="Oil & Gas", role=role, location="Global")
        u.set_password(PW)
        db.session.add(u)
        db.session.commit()
    return email


def _login(client, email):
    assert client.post("/api/auth/login", json={"email": email, "password": PW}).status_code == 200


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def ctx():
    with flask_app.app_context():
        yield


# ---------------------------------------------------------------- GB-003 / GB-021 (D3 / D4)
def test_algeria_2022_uses_the_iea_2019_grid_average(ctx):
    """GHG Protocol Scope 2 Table 6.2: the most recent grid average at or before the reporting year. HBNS 2022:
    136,270 MWh x (0.419 + 8.0e-6 x 25 + 1.005e-6 x 298) kg/kWh = 57,165.2 t CO2e (report 57,165.28)."""
    from electricity_factors import grid_entry_for_year, grid_factor_kg_co2e_per_kwh

    _, e2022 = grid_entry_for_year("Algerian National Grid", 2022)
    assert e2022["co2"] == pytest.approx(0.419)
    assert 136_270e3 * grid_factor_kg_co2e_per_kwh(e2022, gwp=GWP_AR4) / 1000 == pytest.approx(57_165.28, rel=1e-4)
    assert grid_entry_for_year("Algerian National Grid", 2025)[1]["co2"] == pytest.approx(0.4974)
    assert grid_entry_for_year("Algerian National Grid", None)[1]["co2"] == pytest.approx(0.4974)


def test_pick_vintage_rule():
    from electricity_factors import pick_vintage

    rows = [(2019, "a"), (2024, "b")]
    assert pick_vintage(rows, 2018) == (2019, "a")  # nothing earlier: the earliest later one
    assert pick_vintage(rows, 2023) == (2019, "a")
    assert pick_vintage(rows, 2024) == (2024, "b")
    assert pick_vintage(rows, None) == (2024, "b")


def test_grid_factor_maker_checker_and_resolution(client):
    name = f"GB Test Grid {uuid.uuid4().hex[:6]}"
    _login(client, _user("superuser"))
    body = {"name": name, "country": "Testland", "level": "national", "year": 2020, "co2": 0.5, "ch4": 1e-5,
            "n2o": 1e-6, "source": "National statistics 2020"}
    r = client.post("/api/grid-factors", json=body)
    assert r.status_code == 201 and r.get_json()["status"] == "Pending"
    gid = r.get_json()["id"]
    assert client.post(f"/api/grid-factors/{gid}/approve").status_code == 403  # not by its author
    with flask_app.app_context():
        from electricity_factors import clear_grid_cache, grid_entry_for_year
        clear_grid_cache()
        assert grid_entry_for_year(name, 2022)[1] is None  # pending: not used
    _login(client, _user("admin"))
    assert client.post(f"/api/grid-factors/{gid}/approve").status_code == 200
    with flask_app.app_context():
        from electricity_factors import grid_entry_for_year
        canonical, entry = grid_entry_for_year(name, 2022)
        assert canonical == name and entry["co2"] == pytest.approx(0.5)
        # the country's national average when the record names no known grid
        _, by_country = grid_entry_for_year(None, 2022, country="Testland")
        assert by_country["co2"] == pytest.approx(0.5)
        db.session.delete(db.session.get(GridFactor, gid))
        db.session.commit()
        clear_grid_cache()


def test_grid_factor_needs_a_source_and_a_country_for_a_national_average(client):
    _login(client, _user("admin"))
    base = {"name": "X", "country": "Y", "level": "national", "year": 2020, "co2": 0.4, "source": "S"}
    assert client.post("/api/grid-factors", json={**base, "source": ""}).status_code == 400
    assert client.post("/api/grid-factors", json={**base, "country": ""}).status_code == 400
    assert client.post("/api/grid-factors", json={**base, "co2": 5}).status_code == 400


# ---------------------------------------------------------------- GB-004 / GB-024 (D7)
@pytest.mark.parametrize("site", ["HBNS", "El Merk"])
def test_ngsi_with_the_facility_gas_reproduces_the_report(site):
    """NGSI with the facility's own CH4 content and HHV (D7) gives the report's 0.141 % / 0.176 %."""
    from gb_ry2022_cases import EMK_GAS, HBNS_GAS, PRODUCTION
    from services.methane_intensity import ngsi_parts

    key = "HBNS" if site == "HBNS" else "El Merk"
    prod = next(v for k, v in PRODUCTION.items() if key.lower().replace(" ", "") in str(k).lower().replace(" ", ""))
    ch4 = 2_628.66 if site == "HBNS" else 4_627.02
    c1 = HBNS_GAS["c1"] if site == "HBNS" else EMK_GAS["fuel"]["c1"]
    fac = SimpleNamespace(segment="Upstream", activity="Oil and gas production", gas_ch4_mol_pct=c1 * 100,  # a fraction in the cases
                          gas_hhv_btu_scf=prod["hhv"])
    num, den = ngsi_parts({"gas_m3": prod["gas_no_inj_sm3"], "ch4": ch4, "oil_bbl": prod["liquids_boe"]},
                           "upstream", fac)
    assert num / den * 100 == pytest.approx(prod["ngsi_pct"], abs=6e-4)


def test_ngsi_without_facility_gas_uses_the_ngsi_defaults():
    from services.methane_intensity import NGSI_GAS_MMBTU_PER_MCF, facility_gas, gas_ratio

    assert facility_gas(SimpleNamespace(gas_ch4_mol_pct=None, gas_hhv_btu_scf=None)) == (None, None)
    r_default = gas_ratio("production", 1e6, 1000)
    r_own = gas_ratio("production", 1e6, 1000, NGSI_GAS_MMBTU_PER_MCF * 1000)
    assert r_default == pytest.approx(r_own)


def test_facility_api_stores_the_gas_fields(client):
    _login(client, _user("admin"))
    r = client.post("/api/facilities", json={"name": f"GB D7 {uuid.uuid4().hex[:6]}", "region": "Berkine",
                                             "activity": "EP", "division": "DP", "gas_ch4_mol_pct": 68.4,
                                             "gas_hhv_btu_scf": 1362.97})
    assert r.status_code in (200, 201), r.get_json()
    fid = (r.get_json().get("facility") or r.get_json()).get("id")
    with flask_app.app_context():
        f = db.session.get(Facility, fid)
        assert f.gas_ch4_mol_pct == pytest.approx(68.4) and f.gas_hhv_btu_scf == pytest.approx(1362.97)
    assert client.put(f"/api/facilities/{fid}", json={"gas_ch4_mol_pct": 150}).status_code in (400, 422)


# ---------------------------------------------------------------- GB-005 / GB-025 (D5)
def test_equity_basis_divides_by_saleable_production(ctx, monkeypatch):
    """Equity share: the denominator is the equity share of saleable production (API 2023), here 50 % of 6e5 BOE."""
    import services.consolidation as cons
    from services.intensity import _apply_boundary, _blank

    fac = Facility(name=f"GB D5 {uuid.uuid4().hex[:6]}", equity_share_pct=50.0, operator_status="operated")
    db.session.add(fac)
    db.session.flush()
    monkeypatch.setattr(cons, "current_approach", lambda: "equity_share")
    cell = _blank()
    cell.update(boe=1e6, saleable_boe=6e5, s1=100.0)
    cells = {(fac.id, None): cell}
    _apply_boundary(cells)
    assert cells[(fac.id, None)]["boe"] == pytest.approx(3e5)
    assert cells[(fac.id, None)]["s1"] == pytest.approx(50.0)
    db.session.rollback()


# ---------------------------------------------------------------- GB-054
def test_production_flared_split_feeds_the_flaring_summary(client):
    _login(client, _user("admin"))
    with flask_app.app_context():
        fac = Facility(name=f"GB54 {uuid.uuid4().hex[:6]}", segment="Upstream", activity="EP", division="DP")
        db.session.add(fac)
        db.session.flush()
        db.session.add(ProductionData(facility_id=fac.id, year=2033, month=1, gross_gas_mmsm3=100.0,
                                      routine_flared_mmsm3=23.107, non_routine_flared_mmsm3=33.061,
                                      safety_flared_mmsm3=11.977))
        db.session.commit()
        fid = fac.id
    try:
        r = client.get(f"/api/dashboard/flaring-summary?year=2033&facility_id={fid}")
        assert r.status_code == 200, r.get_json()
        d = r.get_json()
        assert d["routine_flaring"]["volume_m3"] == pytest.approx(23.107e6)
        assert d["non_routine_flaring"]["volume_m3"] == pytest.approx(33.061e6)
        assert d["safety_flaring"]["volume_m3"] == pytest.approx(11.977e6)
    finally:
        with flask_app.app_context():
            ProductionData.query.filter_by(facility_id=fid).delete()
            db.session.delete(db.session.get(Facility, fid))
            db.session.commit()


# ---------------------------------------------------------------- GB-055
def test_fire_suppressant_is_an_other_source():
    from services.dashboard_filters import source_category
    assert source_category("fire_suppression") == "other"


# ---------------------------------------------------------------- GB-029
def test_skip_reasons_keep_formulas_and_do_not_read_method_errors_as_facility_errors():
    from services.import_feedback import _normalise, classify

    assert "CH4" in _normalise("CH4 content 85.5 % above Table 6-39")
    assert "Table 6-39" in _normalise("CH4 content 85.5 % above Table 6-39")
    title = classify("Missing required field: facility_type (oil_production, gas_production or gas_processing) "
                     "for facility-level fugitives")[1]
    assert title != "Facility not found or not allowed"
    assert classify("Region 'Nowhere' not found. Check the name")[1] == "Facility not found or not allowed"


# ---------------------------------------------------------------- GB-031
def test_template_offers_the_columns_that_work():
    from services.scope1_template import PROCESSES, columns_for

    keys = {c.key for c in columns_for("auto")}
    for k in ("combustion_method", "equipment_type", "activity_key", "agent_type", "wastewater_method", "bod5_mg_l",
              "cod_kg_m3", "n_effluent_mg_l", "ch4_factor", "n2o_factor", "n2o_factor_unit", "facility_type"):
        assert k in keys, k
    for p in ("fire_suppression", "wastewater", "refrigerant", "electrical_equipment"):
        assert p in PROCESSES


# ---------------------------------------------------------------- GB-028 (D9)
def test_admin_manages_jv_partners_and_archived_ones_take_no_share(client):
    _login(client, _user("admin"))
    code = f"GB{uuid.uuid4().hex[:5].upper()}"
    r = client.post("/api/equity/partners", json={"name": f"Partner {code}", "code": code, "country": "Algeria"})
    assert r.status_code == 201
    pid = r.get_json()["id"]
    assert client.post("/api/equity/partners", json={"name": f"Other {code}", "code": code}).status_code == 409
    assert client.put(f"/api/equity/partners/{pid}", json={"name": f"Renamed {code}"}).get_json()["name"] == f"Renamed {code}"
    assert client.post(f"/api/equity/partners/{pid}/archive").get_json()["is_archived"] is True
    listed = [p["id"] for p in client.get("/api/equity/partners").get_json()]
    assert pid not in listed
    assert pid in [p["id"] for p in client.get("/api/equity/partners?include_archived=1").get_json()]
    with flask_app.app_context():
        fac = Facility(name=f"GB28 {code}", activity="EP", division="DP")
        db.session.add(fac)
        db.session.commit()
        fid = fac.id
    r = client.post("/api/equity/shares", json={"facility_id": fid, "partner_id": pid, "equity_share_pct": 10,
                                                "effective_start_date": "2022-01-01"})
    assert r.status_code == 409
    with flask_app.app_context():
        db.session.delete(db.session.get(Facility, fid))
        db.session.delete(db.session.get(JvPartner, pid))
        db.session.commit()


def test_superuser_cannot_manage_partners(client):
    _login(client, _user("superuser"))
    assert client.post("/api/equity/partners", json={"name": "N", "code": "C"}).status_code == 403


# ---------------------------------------------------------------- GB-053
def test_master_report_basins_do_not_offer_the_demo_group(client):
    _login(client, _user("admin"))
    r = client.get("/api/reports/master-report/regions")
    assert r.status_code == 200
    assert not any("demo operator" in str(x.get("name", "")).lower() for x in r.get_json().get("regions", []))


# ---------------------------------------------------------------- GB-045
@pytest.mark.parametrize("extra,gas,expected", [
    # 100 kg of CO2 released = 0.1 t CO2
    ({"process_type": "fire_suppression", "agent_type": "co2", "amount": 100, "unit": "kg"}, "co2", 0.1),
    # aerobic, Eq 7-19: 1,000 m3 x 1,000 L x 25 mg/L / 0.7 x 44 / 32 / 1e9 = 4.911e-2 t CO2
    ({"process_type": "wastewater", "wastewater_method": "aerobic", "bod5_mg_l": 25, "flow": 1000, "flow_unit": "m3",
      "amount": 1000, "unit": "m3"}, "co2", 1000 * 1000 * 25 / 0.7 * 44 / 32 / 1e9),
])
def test_other_sources_are_saved_as_the_form_sends_them(client, extra, gas, expected):
    _login(client, _user("admin"))
    with flask_app.app_context():
        fac = Facility(name=f"GB45 {uuid.uuid4().hex[:6]}", activity="EP", division="DP", segment="Upstream")
        db.session.add(fac)
        db.session.commit()
        fid = fac.id
    body = {"facility_id": fid, "year": 2022, "month": 6, "factor_source": "default", **extra,
            "calc_inputs": {extra["process_type"]: dict(extra)}}
    r = client.post("/api/emissions", json=body)
    assert r.status_code == 201, r.get_json()
    from models import Emission
    with flask_app.app_context():
        e = Emission.query.filter_by(facility_id=fid).one()
        assert float(getattr(e, f"{gas}_emissions")) == pytest.approx(expected, rel=1e-3)
        db.session.delete(e)
        db.session.delete(db.session.get(Facility, fid))
        db.session.commit()


# ---------------------------------------------------------------- GB-021 / D3: supplier gases, market-based
def test_supplier_gases_weighted_with_the_active_gwp(client):
    """A supplier disclosing 0.40 kg CO2, 1e-5 kg CH4 and 2e-6 kg N2O per kWh: market factor
    0.40 + 1e-5 x GWP_CH4 + 2e-6 x GWP_N2O (AR5 28 / 265) = 0.40081 kg CO2e/kWh; 1,000 MWh = 400.81 t."""
    _login(client, _user("admin"))
    with flask_app.app_context():
        fac = Facility(name=f"GB21 {uuid.uuid4().hex[:6]}", activity="EP", division="DP", country="Algeria")
        db.session.add(fac)
        db.session.commit()
        fid = fac.id
    r = client.post("/api/scope2", json={"facility_id": fid, "year": 2022, "month": 3, "source_type": "electricity",
                                         "amount": 1000, "unit": "MWh", "grid_region": "Algerian National Grid",
                                         "market_instrument_type": "supplier_specific", "market_co2_factor": 0.40,
                                         "market_ch4_factor": 1e-5, "market_n2o_factor": 2e-6})
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    from calculations.constants import get_active_gwp
    with flask_app.app_context():
        g = get_active_gwp()
        expected = 1000 * (0.40 + 1e-5 * g["CH4"] + 2e-6 * g["N2O"])
        from models import Scope2Emission
        rec = Scope2Emission.query.filter_by(facility_id=fid).one()
        assert rec.co2e_market_based == pytest.approx(expected, rel=1e-9)
        db.session.delete(rec)
        db.session.delete(db.session.get(Facility, fid))
        db.session.commit()
    assert body
