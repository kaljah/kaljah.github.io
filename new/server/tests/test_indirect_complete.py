"""calculations/indirect.py: steam / heat (API Compendium 2021 section 8.1.5, Equation 8-1) and cogeneration
allocation (section 8.3). Fixed while testing: a steam mass was converted at an assumed 1,000 Btu/lb (the
Compendium needs the steam's enthalpy from steam tables; Exhibit 8.3's steam carries 1,170 Btu/lb), an unknown
heat or power unit was read as Btu / MMBtu, and an unknown allocation method as energy content.
"""
import pytest

from calculations.indirect import CogenAllocationCalculator, IndirectSteamCalculator, heat_to_mmbtu


@pytest.mark.parametrize("amount,unit,mmbtu", [
    (1e6, "Btu", 1.0), (10, "therms", 1.0), (1000, "MJ", 0.947817), (1, "GJ", 0.947817), (1000, "kWh", 3.412142),
    (1, "MWh", 3.412142), (2, "MMBtu", 2.0),
])
def test_energy_units(amount, unit, mmbtu):
    assert heat_to_mmbtu(amount, unit) == pytest.approx(mmbtu)


def test_steam_mass_equation_8_1_exhibit_8_3():
    # 15 million lb of 600 psig / 700 F steam: (1350 - 180) Btu/lb -> 1.755E10 Btu
    assert heat_to_mmbtu(15e6, "lb", steam_enthalpy_btu_lb=1170) == pytest.approx(17_550)
    assert heat_to_mmbtu(15_000, "klb", steam_enthalpy_btu_lb=1170) == pytest.approx(17_550)
    assert heat_to_mmbtu(1, "short_ton", steam_enthalpy_btu_lb=1000) == pytest.approx(2.0)
    assert heat_to_mmbtu(1, "tonne", steam_enthalpy_btu_lb=1000) == pytest.approx(2.20462262)
    assert heat_to_mmbtu(1000, "kg", steam_enthalpy_btu_lb=1000) == pytest.approx(2.20462262)
    assert heat_to_mmbtu(200, "short_ton", steam_enthalpy=2.75) == pytest.approx(550)              # MMBtu per unit


@pytest.mark.parametrize("unit,kw,match", [
    ("tonne", {}, "needs its enthalpy"), ("ton", {}, "ambiguous"), ("m3", {}, "Unknown unit"),
])
def test_heat_unit_refusals(unit, kw, match):
    with pytest.raises(ValueError, match=match):
        heat_to_mmbtu(1, unit, **kw)


def test_steam_calculator():
    calc = IndirectSteamCalculator()
    res = calc.calculate(17_550, 59.0, 0.92, 0.10, {}, heat_unit="mmbtu", ef_ch4=1.1e-3, ef_n2o=3e-4)
    fuel = 17_550 / (0.92 - 0.10)                                                 # Exhibit 8.3
    assert res["results"]["co2"]["value"] == pytest.approx(fuel * 0.059)
    assert (res["results"]["ch4"]["value"], res["results"]["n2o"]["value"]) == pytest.approx((fuel * 1.1e-6, fuel * 3e-7))
    mass = calc.calculate(15e6, 59.0, 0.92, None, {}, heat_unit="lb", steam_enthalpy_btu_lb=1170)
    assert mass["inputs"]["energy_btu"] == pytest.approx(1.755e10)
    default = calc.calculate(1e6, 50.0, None, None, {})                                           # Btu, 80 %
    assert default["results"]["co2"]["value"] == pytest.approx(1 / 0.8 * 0.05)
    with pytest.raises(ValueError, match="are fractions"):
        calc.calculate(100, 50.0, 80, 0, {}, heat_unit="mmbtu")
    with pytest.raises(ValueError, match="Net efficiency must be greater than 0"):
        calc.calculate(100, 50.0, 0.8, 1.0, {}, heat_unit="mmbtu")


def test_dispatcher_passes_the_steam_enthalpy():
    from calculations.dispatcher import CalculationDispatcher

    res = CalculationDispatcher().dispatch("indirect_steam", {
        "amount": 15e6, "unit": "lb", "boiler_eff": 92, "trans_loss": 10, "steam_enthalpy_btu_lb": 1170,
        "factor_source": "specific"}, {"co2": 59.0}, {})
    assert res["results"]["co2"]["value"] == pytest.approx(17_550 / (0.92 - 0.10) * 0.059)


def test_cogen_allocation():
    c = CogenAllocationCalculator()
    wri = c.calculate(100, 80, 35, heat_unit="mmbtu", power_unit="mmbtu")                           # 80 % / 35 %
    assert wri["metadata"]["allocated_heat_tonnes"] == pytest.approx(50.0)
    assert wri["metadata"]["allocated_power_tonnes"] == pytest.approx(50.0)
    energy = c.calculate(100, 1, 1, method="energy_content", heat_unit="GJ", power_unit="MWh")
    h, p = 0.947817, 3.412142
    assert energy["metadata"]["allocated_heat_tonnes"] == pytest.approx(100 * h / (h + p))
    eff = c.calculate(100, 50, 50, heat_efficiency=90, power_efficiency=0.30)
    assert eff["metadata"]["allocated_heat_tonnes"] == pytest.approx(100 * (50 / 0.9) / (50 / 0.9 + 50 / 0.3))
    none = c.calculate(100, 0, 0)
    assert none["metadata"]["allocated_heat_tonnes"] == 0 and none["metadata"]["allocated_power_tonnes"] == 0
    with pytest.raises(ValueError, match="between 0 and 100"):
        c.calculate(100, 1, 1, heat_efficiency=150)
    with pytest.raises(ValueError, match="Unknown cogeneration allocation method"):
        c.calculate(100, 1, 1, method="uk_ets")
    with pytest.raises(ValueError, match="Unknown unit"):
        c.calculate(100, 1, 1, power_unit="hp")


# ---------------------------------------------------------------- Scope 2 manual entry and file import
EMAIL, PASSWORD = "steam-enthalpy@example.test", "Steam-Enthalpy-1!"


@pytest.fixture
def steam_admin(client, app):
    from extensions import db
    from models import Facility, User

    with app.app_context():
        u = User.query.filter_by(email=EMAIL).first()
        if not u:
            u = User(email=EMAIL, fullName="Steam Test", orgName="T", sector="Oil & Gas", role="admin",
                     location="Global")
            u.set_password(PASSWORD)
            db.session.add(u)
        fac = Facility.query.filter_by(code="STEAM-H-T").first()
        if not fac:
            fac = Facility(name="Steam enthalpy plant T", code="STEAM-H-T", segment="Downstream")
            db.session.add(fac)
        db.session.commit()
        ids = (u.id, fac.id)
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 200
    return client, ids


def test_scope2_steam_mass_needs_its_enthalpy(steam_admin, app):
    from extensions import db
    from models import Scope2Emission

    client, (_, fac_id) = steam_admin
    base = dict(facility_id=fac_id, year=2025, month=3, source_type="indirect_steam", amount=1000, unit="klb",
                boiler_efficiency=0.8)
    r = client.post("/api/scope2", json=base)
    assert r.status_code == 400 and "enthalpy" in r.get_json()["error"]
    r = client.post("/api/scope2", json={**base, "calc_inputs": {"indirect_steam": {"steam_enthalpy_btu_lb": 1170}}})
    assert r.status_code == 201, r.get_json()
    with app.app_context():
        rec = db.session.get(Scope2Emission, r.get_json()["id"])
        assert rec.heat_mmbtu == pytest.approx(1170.0)                                              # 1E6 lb x 1170
        assert rec.steam_ton == 1000
    r = client.post("/api/scope2", json={**base, "unit": "furlong"})
    assert r.status_code == 400 and "Unknown unit" in r.get_json()["error"]


def test_scope2_import_reads_the_enthalpy_column(steam_admin, app):
    from background_processor import _process_row_scope2
    from models import Facility

    _, (user_id, fac_id) = steam_admin
    with app.app_context():
        fac = Facility.query.get(fac_id)
        maps = dict(fac_name_map={fac.name.lower(): fac}, fac_id_map={str(fac.id): fac}, GRID_FACTORS={},
                    job_id="steam-h", row_idx=2)
        row = {"date": "2025-04", "facility_name": fac.name, "source_type": "steam", "consumption": "15000",
               "unit": "klb", "boiler_eff": "92", "trans_loss": "10"}
        obj, errors = _process_row_scope2(row=row, user_id=user_id, **maps)
        assert obj is None and "enthalpy" in errors[0]
        obj, errors = _process_row_scope2(row={**row, "steam_enthalpy_btu_lb": "1170"}, user_id=user_id, **maps)
        assert errors == [] and obj.heat_mmbtu == pytest.approx(17_550)
        obj, errors = _process_row_scope2(row={**row, "steam_enthalpy_btu_lb": "hot"}, user_id=user_id, **maps)
        assert obj is None and "must be a positive number" in errors[0]


def test_negative_inputs_refused():
    calc = IndirectSteamCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        heat_to_mmbtu(-1, "mmbtu")
    with pytest.raises(ValueError, match="enthalpy cannot be negative"):
        heat_to_mmbtu(1, "lb", steam_enthalpy_btu_lb=-5)
    with pytest.raises(ValueError, match="enthalpy cannot be negative"):
        heat_to_mmbtu(1, "lb", steam_enthalpy=-5)
    for kw, gas in ((dict(ef_co2=-1), "CO2"), (dict(ef_co2=1, ef_ch4=-1), "CH4"), (dict(ef_co2=1, ef_n2o=-1), "N2O")):
        with pytest.raises(ValueError, match=f"{gas} emission factor cannot be negative"):
            calc.calculate(100, boiler_efficiency=0.8, transmission_loss=0, uncertainties={}, heat_unit="mmbtu", **kw)
    with pytest.raises(ValueError, match="total_emissions cannot be negative"):
        CogenAllocationCalculator().calculate("-5", 1, 1)


def test_percent_strings_for_steam_efficiencies():
    res = IndirectSteamCalculator().calculate(100, 50.0, "80%", "5 %", {}, heat_unit="mmbtu")
    assert res["results"]["co2"]["value"] == pytest.approx(100 / (0.8 - 0.05) * 0.05)
    assert IndirectSteamCalculator().calculate(100, 50.0, "-", "", {}, heat_unit="mmbtu")["results"]["co2"]["value"] \
        == pytest.approx(100 / 0.8 * 0.05)
