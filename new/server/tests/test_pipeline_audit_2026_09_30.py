"""Whole-pipeline audit, 2026-09-30 (input -> calculation -> storage -> edit -> aggregation).

1. Scope 2 steam entered in MMBtu stored the amount as steam tonnage; any edit then recalculated
   it from that many short tons (2x), reset the boiler efficiency to 80 % and read metric tonnes
   as short tons.
2. Tier 3 flaring without a catalog factor had no N2O (an explicit 0 replaced the Table 5-3 default).
3. A custom kg/MMBtu factor of a liquid fuel (parent Diesel) was refused for gallons: its HHV was
   read per scf of gas.
4. Scope 3 method label "Scope 3 - Category Category 4".
"""
import pytest

from app import app as flask_app
from extensions import db
from models import CustomFactor, Emission, Facility, Scope2Emission, Scope3Emission, User

EMAIL = "pipeline_audit_0930@ghg.com"
PASSWORD = "PipelineAudit0930!"


@pytest.fixture
def admin(client):
    with flask_app.app_context():
        u = User.query.filter_by(email=EMAIL).first()
        if not u:
            u = User(email=EMAIL, fullName="Pipeline Audit", orgName="Audit", sector="Oil & Gas", role="admin",
                     location="Global")
            u.set_password(PASSWORD)
            db.session.add(u)
            db.session.commit()
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 200
    return client


@pytest.fixture
def facility(admin):
    with flask_app.app_context():
        f = Facility.query.filter_by(name="Pipeline Audit 0930").first()
        if not f:
            f = Facility(name="Pipeline Audit 0930", location="Skikda", country="Algeria", region="Skikda",
                         division="Refining", field="SK", segment="Downstream")
            db.session.add(f)
            db.session.commit()
        return f.id


def _steam(client, facility, **extra):
    r = client.post("/api/scope2", json=dict(facility_id=facility, year=2025, month=11, source_type="indirect_steam", **extra))
    assert r.status_code == 201, r.get_json()
    with flask_app.app_context():
        return Scope2Emission.query.order_by(Scope2Emission.id.desc()).first().id


def _get(rid):
    with flask_app.app_context():
        e = db.session.get(Scope2Emission, rid)
        return e.co2e, e.heat_mmbtu, e.steam_ton


@pytest.mark.parametrize("extra", [
    dict(amount=5000, unit="MMBtu", boiler_efficiency=0.8),
    dict(amount=5000, unit="MMBtu", boiler_efficiency=0.85),
    dict(amount=1000, unit="tonne", boiler_efficiency=0.8),
])
def test_steam_edit_keeps_value_and_scales(admin, facility, extra):
    rid = _steam(admin, facility, **extra)
    co2e, heat, tons = _get(rid)
    if extra["unit"] == "MMBtu":
        assert tons == 0  # 5,000 MMBtu is not 5,000 t of steam
    assert admin.put(f"/api/scope2/{rid}", json={"heat_mmbtu": heat}).status_code == 200
    assert _get(rid)[0] == pytest.approx(co2e, rel=1e-6)  # was 2x (MMBtu) or 0.907x (tonne)
    change = {"steam_ton": tons * 2} if tons else {"heat_mmbtu": heat * 2}
    assert admin.put(f"/api/scope2/{rid}", json=change).status_code == 200
    new_co2e, new_heat, _ = _get(rid)
    assert new_co2e == pytest.approx(2 * co2e, rel=1e-6)
    assert new_heat == pytest.approx(2 * heat, rel=1e-6)


def test_steam_edit_with_new_efficiency_recalculates(admin, facility):
    rid = _steam(admin, facility, amount=5000, unit="MMBtu", boiler_efficiency=0.8)
    co2e = _get(rid)[0]
    assert admin.put(f"/api/scope2/{rid}", json={"heat_mmbtu": 5000, "boiler_efficiency": 0.9}).status_code == 200
    assert _get(rid)[0] == pytest.approx(co2e * 0.8 / 0.9, rel=1e-6)


def test_tier3_flaring_has_n2o():
    from calculations.dispatcher import CalculationDispatcher

    res = CalculationDispatcher().dispatch(
        "flaring", dict(process_type="flaring", factor_source="specific", amount=50000, unit="m3", c1=85, c2=7, c3=3,
                        co2_mol=2, flare_type="elevated"), {}, {})["results"]
    # 50,000 m3 x 35.3147 scf/m3 x 1,020 Btu/scf = 1,801 MMBtu x 0.0001 kg/MMBtu (Table 5-3)
    assert res["n2o"]["value"] == pytest.approx(50000 * 35.314666721 * 1020 / 1e6 * 0.0001 / 1000, rel=1e-9)
    # carbon balance: 50,000 m3 x 1.08 C x 98.4 % + 2 % native CO2, at 44.01 / 23.685 kg/m3
    assert res["co2"]["value"] == pytest.approx((50000 * 1.08 * 0.965 + 50000 * 0.02) * (44.01 / 23.685) / 1000, rel=1e-6)


def test_custom_liquid_fuel_factor_on_energy_basis(admin, facility):
    with flask_app.app_context():
        cf = CustomFactor(name="Pipeline audit site diesel", co2_factor=74.0, ch4_factor=0.003, unit="kg/MMBtu",
                          hhv_factor=138000, parent_fuel="Diesel", usage="combustion")
        db.session.add(cf)
        db.session.commit()
        cid = cf.id
    r = admin.post("/api/emissions/", json=dict(year=2025, month=12, facility_id=facility, process_type="combustion",
                                                factor_source="custom", custom_factor_id=cid, fuel=str(cid),
                                                amount=1000, unit="gal"))
    assert r.status_code == 201, r.get_json()
    with flask_app.app_context():
        e = Emission.query.filter_by(facility_id=facility, month=12).order_by(Emission.id.desc()).first()
        assert e.co2_emissions == pytest.approx(1000 * 0.138 * 74.0 / 1000)


def test_scope3_method_label(admin, facility):
    r = admin.post("/api/scope3", json=dict(facility_id=facility, year=2025, month=3, category="4", sub_category="Truck",
                                            activity_data=100000, unit="tonne-km", emission_factor=0.1))
    assert r.status_code == 201, r.get_json()
    with flask_app.app_context():
        e = Scope3Emission.query.filter_by(facility_id=facility).order_by(Scope3Emission.id.desc()).first()
        assert e.calculation_method == "Scope 3 - Category 4"
        assert e.co2e == pytest.approx(10.0)
