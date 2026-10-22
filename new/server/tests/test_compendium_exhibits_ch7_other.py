"""API Compendium 2021 worked examples, Section 7.5 / 7.6: wastewater (Exhibits 7-6, 7-7), refrigerant HFC (7-8)
and electrical-equipment SF6 (7-9). Each test runs the exhibit's own inputs through ``compute_emissions`` (the path
POST /api/emissions takes) and compares with the number the exhibit prints; "PDF line" is the line of the exhibit in
``pdftotext -layout`` output of API-GHG-Compendium-110921.pdf.

Equations 7-22 / 7-27 are printed with the opposite sign of Equation 7-23 (see calculations/fugitive_other.py), so the
mass-balance cases below that are not exhibits use hand-worked numbers.
"""
import pytest

from calculations.constants import GWP_AR4, GWP_AR5, GWP_AR6
from calculations.fugitive_other import ElectricalEquipmentCalculator, RefrigerantCalculator, WastewaterCalculator, fgas_gwp

from compendium_exhibits_support import assert_printed, run_scope1


def _scope1(app, process, **inputs):
    return run_scope1(app, {"process_type": process, "factor_source": "specific", "amount": inputs.pop("amount", 1),
                            "quantity": 1, "unit": inputs.pop("unit", "m3"), **inputs})


def test_exhibit_7_6_aerobic_wastewater_co2(app):
    """PDF line 28685. 5e6 gal/day, 365 days, BOD5 120 mg/L, Equation 7-19: 1,628 tonnes CO2/yr."""
    em = _scope1(app, "wastewater", wastewater_method="aerobic", amount=5e6, unit="gal/day", bod5_mg_l=120)
    assert_printed(em["co2"], "1,628", what="CO2")
    assert em["ch4"] == 0 and em["n2o"] == 0
    assert_printed(em["totalCo2e"], "1,628", what="CO2e")


def test_exhibit_7_7_anaerobic_wastewater_epa_ch4(app):
    """PDF line 28746. 870,000 ft3/day, 10 % anaerobic, 0.3 lb BOD5/ft3, Equation 7-20: 950.7 tonnes CH4/yr."""
    em = _scope1(app, "wastewater", wastewater_method="anaerobic_epa", amount=870_000, unit="ft3/day",
                 bod5_lb_ft3=0.3, fad_pct=10)
    assert_printed(em["ch4"], "950.7", slack=1.0, what="CH4")
    assert em["co2"] == 0
    assert em["totalCo2e"] == pytest.approx(950.7 * 28.0, rel=1e-3)


def test_exhibit_7_7_anaerobic_wastewater_ipcc_ch4(app):
    """PDF line 28746. The same plant by Equation 7-17: 87,000 ft3/day anaerobic, 1 kg COD/m3 (refinery default),
    shallow lagoon MCF 0.2 (Table 7-82), B 0.25: 44.96 tonnes CH4/yr."""
    em = _scope1(app, "wastewater", wastewater_method="ipcc", amount=870_000 * 0.1, unit="ft3/day",
                 cod_kg_m3=1.0, treatment_type="anaerobic_shallow_lagoon")
    assert_printed(em["ch4"], "44.96", what="CH4")


def test_wastewater_n2o_equation_7_18():
    """Eq 7-18 by hand: 100,000 m3/yr x 0.05 kg N/m3 x 0.005 kg N2O-N/kg N x 44/28 x 0.001 = 0.03929 tonnes N2O."""
    res = WastewaterCalculator().calculate("aerobic", {"flow": 100_000, "flow_unit": "m3/yr", "bod5_mg_l": 0,
                                                       "n_effluent_kg_m3": 0.05}, gwp_dict=GWP_AR5)
    assert res["results"]["n2o"]["value"] == pytest.approx(100_000 * 0.05 * 0.005 * 44 / 28 * 0.001, rel=1e-12)
    assert res["total_co2e"] == pytest.approx(0.039285714 * 265.0, rel=1e-6)


def test_wastewater_sludge_and_treatment_types():
    """Eq 7-17: (V x COD - S) x B x MCF x 0.001. 10,000 m3, 2 kg COD/m3, 4,000 kg COD to sludge, anaerobic reactor
    (MCF 0.8): (20,000 - 4,000) x 0.25 x 0.8 x 0.001 = 3.2 tonnes CH4; an aerobic plant (MCF 0) emits none."""
    calc = WastewaterCalculator()
    base = {"flow": 10_000, "flow_unit": "m3", "cod_kg_m3": 2.0, "sludge_cod_kg": 4000}
    anaerobic = calc.calculate("ipcc", {**base, "treatment_type": "anaerobic_reactor"}, gwp_dict=GWP_AR5)
    assert anaerobic["results"]["ch4"]["value"] == pytest.approx(3.2, rel=1e-12)
    assert calc.calculate("ipcc", {**base, "treatment_type": "aerobic_centralized"},
                          gwp_dict=GWP_AR5)["results"]["ch4"]["value"] == 0


@pytest.mark.parametrize("inputs, message", [
    ({"flow": 1, "flow_unit": "furlong", "bod5_mg_l": 100}, "Unknown wastewater flow unit"),
    ({"flow": 1, "flow_unit": "m3", "bod5_mg_l": None}, "BOD5"),
    ({"flow": -1, "flow_unit": "m3", "bod5_mg_l": 100}, "Wastewater flow"),
    ({"flow": 1, "flow_unit": "m3", "cod_kg_m3": 1}, "treatment type"),
])
def test_wastewater_refuses_missing_or_wrong_inputs(inputs, message):
    method = "ipcc" if "cod_kg_m3" in inputs else "aerobic"
    with pytest.raises(ValueError, match=message):
        WastewaterCalculator().calculate(method, inputs, gwp_dict=GWP_AR5)


def test_exhibit_7_8_air_conditioning_hfc_134a(app):
    """PDF line 28988. 680 vehicles x 1.5 kg x 20 %/yr = 0.204 tonnes HFC-134a; x GWP 1,300 = 265.2 tonnes CO2e."""
    em = _scope1(app, "refrigerant", refrigerant_method="charge", refrigerant="HFC-134a", equipment_count=680,
                 charge_kg=1.5, operating_rate_pct=20)
    assert_printed(em["totalCo2e"], "265.2", what="CO2e")
    f_gas = em["_full_api_res"]["results"]["f_gas"]
    assert f_gas["gas"] == "HFC-134a" and f_gas["gwp"] == 1300.0
    assert_printed(f_gas["value"], "0.204", what="tonnes HFC-134a")
    assert em["co2"] == 0 and em["ch4"] == 0 and em["n2o"] == 0


def test_refrigerant_equipment_type_uses_table_7_83_high_end():
    """Chillers: the high end of Table 7-83's 2 - 15 % range. 4 chillers x 500 kg x 15 % = 300 kg = 0.3 t of R-410A
    (Table 7-84 GWP 1,924) = 577.2 t CO2e."""
    res = RefrigerantCalculator().calculate("charge", {"refrigerant": "R-410A", "equipment_count": 4, "charge_kg": 500,
                                                       "equipment_type": "chillers"}, gwp_dict=GWP_AR5)
    assert res["results"]["f_gas"]["value"] == pytest.approx(0.3, rel=1e-12)
    assert res["total_co2e"] == pytest.approx(0.3 * 1924, rel=1e-12)


def test_refrigerant_mass_balance_follows_equation_7_23_signs():
    """(stock begin - stock end) + purchases - sales - capacity increase: begin 300 kg, end 250 kg, bought 120 kg,
    sold 20 kg, equipment capacity up 30 kg -> 50 + 120 - 20 - 30 = 120 kg."""
    res = RefrigerantCalculator().calculate("mass_balance", {"refrigerant": "HFC-134a", "stock_begin": 300,
                                                             "stock_end": 250, "purchases": 120, "sales": 20,
                                                             "capacity_increase": 30}, gwp_dict=GWP_AR5)
    assert res["results"]["f_gas"]["value"] == pytest.approx(0.120, rel=1e-12)
    assert res["total_co2e"] == pytest.approx(0.120 * 1300, rel=1e-12)


def test_exhibit_7_9_sf6_equipment_material_balance(app):
    """PDF line 29147. 79,878 lb recharged - 79,480 lb recovered = 398 lb = 0.18 tonnes SF6 (Eq 7-24); the exhibit
    multiplies the rounded 0.18 by 23,500 and prints 4,230 tonnes CO2e (exact: 398 / 2204.62 x 23,500 = 4,242)."""
    em = _scope1(app, "electrical_equipment", electrical_method="recharge", recharge=79_878, recovered=79_480,
                 mass_unit="lb")
    f_gas = em["_full_api_res"]["results"]["f_gas"]
    assert f_gas["gas"] == "SF6" and f_gas["gwp"] == 23500.0
    assert_printed(f_gas["value"], "0.18", what="tonnes SF6")
    assert em["totalCo2e"] == pytest.approx(398 / 2204.62 * 23500, rel=1e-9)
    assert_printed(em["totalCo2e"], "4,230", rel=4e-3, what="CO2e (the exhibit rounds SF6 to 0.18 first)")


def test_exhibit_7_9_sf6_transmission_mileage(app):
    """PDF line 29183. 135 mi x 0.226 kg SF6/mi-yr = 0.0305 t (printed 0.031); x 23,500 = 717.0 tonnes CO2e."""
    em = _scope1(app, "electrical_equipment", electrical_method="distance", distance=135, distance_unit="mi")
    assert_printed(em["_full_api_res"]["results"]["f_gas"]["value"], "0.031", what="tonnes SF6")
    assert_printed(em["totalCo2e"], "717.0", what="CO2e")


def test_sf6_usage_factor_and_distance_in_km():
    """Eq 7-25: net recharge 10 kg + 5,000 kg nameplate x 0.026 (closed pressure, Europe) = 140 kg; Table 7-86: 100 km
    x 1.40e-4 t/km-yr = 0.014 t."""
    calc = ElectricalEquipmentCalculator()
    usage = calc.calculate("usage_factor", {"recharge": 30, "recovered": 20, "nameplate_capacity": 5000,
                                            "equipment_type": "closed_pressure_europe"}, gwp_dict=GWP_AR5)
    assert usage["results"]["f_gas"]["value"] == pytest.approx(0.140, rel=1e-12)
    km = calc.calculate("distance", {"distance": 100, "distance_unit": "km"}, gwp_dict=GWP_AR5)
    assert km["results"]["f_gas"]["value"] == pytest.approx(0.014, rel=1e-12)


def test_sf6_mass_balance_matches_equation_7_23():
    """Decrease in inventory 40 kg + acquisitions 25 kg - disbursements 10 kg - capacity increase 15 kg = 40 kg."""
    res = ElectricalEquipmentCalculator().calculate("mass_balance", {"stock_begin": 100, "stock_end": 60,
                                                                     "purchases": 25, "sales": 10,
                                                                     "capacity_increase": 15}, gwp_dict=GWP_AR5)
    assert res["results"]["f_gas"]["value"] == pytest.approx(0.040, rel=1e-12)


@pytest.mark.parametrize("gwp_dict, gas, expected", [
    (GWP_AR4, "SF6", 22800.0), (GWP_AR5, "SF6", 23500.0), (GWP_AR6, "SF6", 25200.0),
    (GWP_AR4, "HFC-134a", 1430.0), (GWP_AR5, "R-134a", 1300.0), (GWP_AR6, "HFC-134a", 1530.0),
    (GWP_AR5, "R-404A", 3943.0), ({**GWP_AR5, "CH4": 84.0}, "SF6", 17500.0),
])
def test_fgas_gwp_follows_the_active_ipcc_report(gwp_dict, gas, expected):
    assert fgas_gwp(gas, gwp_dict) == expected


def test_fgas_gwp_refuses_what_the_compendium_does_not_print():
    with pytest.raises(ValueError, match="AR5"):
        fgas_gwp("R-410A", GWP_AR6)          # Table 7-84 prints AR5 values only
    with pytest.raises(ValueError, match="No GWP"):
        fgas_gwp("R-409A", GWP_AR5)          # printed as "na"
    assert fgas_gwp("R-409A", GWP_AR5, override=1585) == 1585.0


def test_fgas_record_is_booked_with_the_scope1_gwp_standard(app):
    """The same 0.204 t of HFC-134a is 291.7 t CO2e under AR4 (GWP 1,430) and 312.1 t under AR6 (1,530)."""
    from calculations.legacy_engine import compute_emissions
    payload = {"process_type": "refrigerant", "factor_source": "specific", "amount": 1, "unit": "m3",
               "refrigerant_method": "charge", "refrigerant": "HFC-134a", "equipment_count": 680, "charge_kg": 1.5,
               "operating_rate_pct": 20}
    with app.app_context():
        ar4, _ = compute_emissions(dict(payload), {}, gwp_dict=GWP_AR4)
        ar6, _ = compute_emissions(dict(payload), {}, gwp_dict=GWP_AR6)
    assert_printed(ar4["totalCo2e"], "291.7", what="AR4 CO2e")
    assert_printed(ar6["totalCo2e"], "312.1", what="AR6 CO2e")


# ----------------------------------------------------------- through POST /api/emissions ----------------------------

@pytest.fixture
def route_client():
    from app import app as flask_app
    from extensions import db
    from models import Facility, User
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.test_client() as c:
        with flask_app.app_context():
            user = User.query.filter_by(email="ch7_other_admin@test.com").first()
            if not user:
                user = User(email="ch7_other_admin@test.com", fullName="Ch7 Admin", orgName="Audit Corp",
                            sector="Energy", role="admin", location="Algiers")
                user.set_password("AdminPass2026!")
                db.session.add(user)
            fac = Facility.query.filter_by(code="CH7-OTHER").first()
            if not fac:
                fac = Facility(name="Chapter 7 Other Sources", code="CH7-OTHER", region="Ouargla", segment="Upstream")
                db.session.add(fac)
            db.session.commit()
            assert c.post("/api/auth/login", json={"email": "ch7_other_admin@test.com",
                                                   "password": "AdminPass2026!"}).status_code == 200
            yield c, fac.id


@pytest.mark.parametrize("process, extra, co2e", [
    ("refrigerant", dict(refrigerant_method="charge", refrigerant="HFC-134a", equipment_count=680, charge_kg=1.5,
                         operating_rate_pct=20), 265.2),
    ("electrical_equipment", dict(electrical_method="distance", distance=135, distance_unit="mi"), 717.0),
])
def test_fluorinated_gas_record_is_stored_with_its_co2e(route_client, process, extra, co2e):
    """The record keeps CO2e even though HFC / SF6 have no gas column of their own, and the stored row agrees with
    the response (the CO2e must not be rebuilt from the CO2 / CH4 / N2O columns, which are zero)."""
    from extensions import db
    from models import Emission
    client, facility_id = route_client
    # records are monthly, so an annual leak rate covers the month; 365 operating days is the exhibits' whole year
    res = client.post("/api/emissions", json={"year": 2025, "month": 1, "facility_id": facility_id,
                                              "process_type": process, "factor_source": "specific", "amount": 1,
                                              "unit": "m3", "status": "Draft", "operating_days": 365,
                                              "calc_inputs": {process: extra}})
    assert res.status_code in (200, 201), res.get_json()
    data = res.get_json()
    assert_printed(data["emissions"]["totalCo2e"], str(co2e), what="CO2e in the response")
    row = db.session.get(Emission, data["id"])
    assert_printed(row.co2e_total, str(co2e), what="CO2e stored")
