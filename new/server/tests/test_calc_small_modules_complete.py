"""The remaining branches of calculations/base.py, fugitive.py, stoichiometry.py, flare_defaults.py and
constants.py. Fixed while testing: an unknown fugitive component took the gas-valve factor and the component /
equipment calculators assumed 85 % CH4.
"""
import pytest

from calculations.base import BaseCalculator


# ---------------------------------------------------------------- base.validate_inputs
@pytest.mark.parametrize("value,match", [("nan", "NaN or Infinite"), ("inf", "NaN or Infinite"), ("-3", "negative"),
                                         (float("nan"), "NaN or Infinite"), (-1, "negative"), ("", "Missing")])
def test_validate_inputs_refuses(value, match):
    with pytest.raises(ValueError, match=match):
        BaseCalculator("x", "y").validate_inputs({"k": value}, ["k"])


@pytest.mark.parametrize("value", ["5", " 2.5 ", "scf", 0, 3.0])
def test_validate_inputs_accepts(value):
    assert BaseCalculator("x", "y").validate_inputs({"k": value}, ["k"]) is True


def test_uncertainty_bounds_never_negative():
    u = BaseCalculator("x", "y").calculate_uncertainty(1.0, 0.8)
    assert (u["lower_bound"], u["upper_bound"], u["abs_uncertainty_95"]) == pytest.approx((0.0, 2.6, 1.6))


# ---------------------------------------------------------------- fugitive.py
def test_component_calculator_rules():
    from calculations.fugitive import ComponentFugitiveCalculator

    c = ComponentFugitiveCalculator()
    res = c.calculate({"gas_valve": 10, "Open-Ended Line": 2}, 85, {})
    expected = (10 * 0.0045 + 2 * 0.002) * 0.85 * 8760 / 1000
    assert res["results"]["ch4"]["value"] == pytest.approx(expected)
    custom = c.calculate({"compressor_vent": {"count": 2, "ef": 0.01, "unit": "kg CH4/hr/component"}}, 0.85, {})
    assert custom["results"]["ch4"]["value"] == pytest.approx(2 * 0.01 * 8760 / 1000)       # CH4 factor: no scaling
    with pytest.raises(ValueError, match="Unknown component type"):
        c.calculate({"widget": 5}, 0.85, {})
    with pytest.raises(ValueError, match="ch4_content"):
        c.calculate({"valve": 5}, None, {})


def test_equipment_calculator_rules():
    from calculations.fugitive import EquipmentFugitiveCalculator

    e = EquipmentFugitiveCalculator()
    res = e.calculate(equipment_count=4, ef=0.1, ef_unit="kg TOC/hr/source", ch4_content=80, uncertainties={})
    assert res["results"]["ch4"]["value"] == pytest.approx(4 * 0.1 * 0.80 * 8760 / 1000)
    with pytest.raises(ValueError, match="ch4_content"):
        e.calculate(equipment_count=4, ef=0.1, uncertainties={})


def test_compressor_seal_segments_hours_and_measured():
    from calculations.fugitive import CompressorSealCalculator

    s = CompressorSealCalculator()
    storage = s.calculate(2, "reciprocating", segment="Underground Storage", hours=1000)
    assert storage["results"]["ch4"]["value"] == pytest.approx(2 * 4.72 * 1000 / 1000)          # T&S, Table 6-40
    processing = s.calculate(1, "centrifugal_dry", segment="gas processing")
    assert processing["results"]["ch4"]["value"] == pytest.approx(28.192)                        # Table 6-38
    measured = s.calculate(3, "reciprocating", measured_kg_hr=0.5, hours=None)
    assert measured["results"]["ch4"]["value"] == pytest.approx(3 * 0.5 * 8760 / 1000)
    with pytest.raises(ValueError, match="between 0 and 8784"):
        s.calculate(1, "reciprocating", hours=9000)
    with pytest.raises(ValueError, match="gives no centrifugal dry factor"):
        s.calculate(1, "centrifugal_dry", segment="production")


# ---------------------------------------------------------------- stoichiometry.py
def test_stoichiometry_percent_carbon_and_oxidation():
    from calculations.stoichiometry import StoichiometricCalculator

    s = StoichiometricCalculator()
    frac = s.calculate(1000, 0.85, oxidation_factor=0.99)
    pct = s.calculate(1000, 85, oxidation_factor=99)
    assert pct["results"]["co2"]["value"] == pytest.approx(frac["results"]["co2"]["value"])
    assert frac["results"]["co2"]["value"] == pytest.approx(1.0 * 0.85 * 0.99 * 44.01 / 12.011)


# ---------------------------------------------------------------- flare_defaults.py
def test_facility_segment_without_a_database():
    from calculations.flare_defaults import facility_segment

    assert facility_segment({"facility_segment": " Downstream "}) == "downstream"
    assert facility_segment({"facility_id": "not-a-number"}) == ""                              # lookup failed: none
    assert facility_segment({}) == ""


# ---------------------------------------------------------------- constants.get_active_gwp
def test_gwp_override_and_unknown_standard():
    from calculations.constants import get_active_gwp

    assert get_active_gwp(gwp_dict={"ch4": 30, "n2o": None}) == {"CO2": 1.0, "CH4": 30.0, "N2O": 265.0}
    assert get_active_gwp(gwp_dict={"n2o": 300})["CH4"] in (25.0, 28.0, 27.0, 29.8, 27.9)        # no CH4: setting used
    with pytest.raises(ValueError, match="Unknown GWP standard"):
        get_active_gwp(standard="AR7")


def test_gwp_setting_cache_and_bad_stored_setting(app, monkeypatch, caplog):
    import calculations.constants as c
    import routes.auth as auth

    c.invalidate_gwp_cache()
    monkeypatch.setitem(auth._app_settings, "gwp_standard", "AR9")
    monkeypatch.setattr(auth, "load_settings_from_db", lambda: None)
    with caplog.at_level("WARNING"):
        assert c.get_active_gwp()["CH4"] == c.GWP_STANDARDS["AR5"]["CH4"]
    assert "unknown; using AR5" in caplog.text
    monkeypatch.setitem(auth._app_settings, "gwp_standard", "AR6")
    assert c.get_active_gwp()["CH4"] == c.GWP_STANDARDS["AR5"]["CH4"]                          # 30 s cache (jobs)
    c.invalidate_gwp_cache()

    def broken():
        raise RuntimeError("database down")

    monkeypatch.setattr(auth, "load_settings_from_db", broken)
    assert c.get_active_gwp()["CH4"] == c.GWP_STANDARDS["AR6"]["CH4"]                          # stored value still read
    c.invalidate_gwp_cache()
    with app.test_request_context("/"):
        first = c.get_active_gwp()
        monkeypatch.setitem(auth._app_settings, "gwp_standard", "AR4")
        assert c.get_active_gwp() == first                                                       # one read per request
    c.invalidate_gwp_cache()


def test_mass_units_and_acid_n2o_table_6_53():
    from calculations.stoichiometry import NitricAcidCalculator, mass_to_kg

    assert mass_to_kg(2, "Short-Ton") == pytest.approx(2 * 907.18474)
    assert mass_to_kg(1, "lb") == pytest.approx(0.45359237)
    with pytest.raises(ValueError, match="Unknown mass unit"):
        mass_to_kg(1, "bushel")
    n = NitricAcidCalculator()
    nitric = n.calculate(1000, mass_unit="tonne")
    assert nitric["results"]["n2o"]["value"] == pytest.approx(1000 * 0.009)                     # 9 kg N2O/t, no NSCR
    adipic = n.calculate(1000, abatement_efficiency=92.5, process_type="adipic_acid_production")
    assert adipic["results"]["n2o"]["value"] == pytest.approx(1000 * 0.3 * 0.075)               # 0.3 t/t, abated
    assert n.calculate(1000, ef_n2o=0)["results"]["n2o"]["value"] == 0                          # entered 0 kept
    assert n.calculate(1000, ef_n2o=2, abatement_efficiency=0.5)["results"]["n2o"]["value"] == pytest.approx(1.0)


def test_dispatcher_acid_routes_keep_an_entered_zero():
    from calculations.dispatcher import CalculationDispatcher

    d = CalculationDispatcher()
    zero = d.dispatch("nitric_acid_production", {"amount": 100, "unit": "tonne", "ef_n2o": 0, "factor_source": "specific"}, {}, {})
    assert zero["results"]["n2o"]["value"] == 0
    stoich = d.dispatch("nitric_acid_production", {"amount": 1000, "unit": "kg", "carbon_content": 50,
                                                        "factor_source": "specific"}, {}, {})
    assert stoich["results"]["co2"]["value"] == pytest.approx(0.5 * 44.01 / 12.011)


def test_refinery_flare_destruction_for_downstream_facilities(monkeypatch):
    import calculations.flare_defaults as fd

    seen = []
    monkeypatch.setattr(fd, "_compute_emissions", lambda p, f, **k: seen.append((p, f)) or "ok")
    catalog = {"ch4": 2.0, "combustion_efficiency_ch4": 0.98}
    assert fd.compute_emissions({"process_type": "Flaring", "facility_segment": "Downstream"}, dict(catalog)) == "ok"
    payload, factor = seen[-1]
    assert payload["destruction_efficiency"] == 0.995
    assert factor["ch4"] == pytest.approx(0.5) and factor["combustion_efficiency_ch4"] == 0.995
    fd.compute_emissions({"process_type": "flaring", "facility_segment": "downstream"}, {"co2": 1})
    assert seen[-1][1] == {"co2": 1}                                                             # no catalog CH4
    nested = {"process_type": "flaring", "facility_segment": "downstream", "calc_inputs": {"flaring": {"flare_eff": 99}}}
    fd.compute_emissions(nested, dict(catalog))
    assert "destruction_efficiency" not in seen[-1][0] and seen[-1][1] == catalog               # entered: kept
    fd.compute_emissions({"process_type": "flaring", "facility_segment": "upstream"}, dict(catalog))
    assert seen[-1][1] == catalog


def test_facility_segment_reads_the_facility(app):
    from calculations.flare_defaults import facility_segment
    from models import Facility, db

    with app.app_context():
        fac = Facility(name="Seg refinery T", code="SEGREF-T", segment="Downstream")
        db.session.add(fac)
        db.session.commit()
        try:
            assert facility_segment({"facility_id": fac.id}) == "downstream"
            assert facility_segment({"facility_id": 99_999_999}) == ""
        finally:
            db.session.delete(fac)
            db.session.commit()


def test_gwp_20_year_and_no_request(monkeypatch):
    import calculations.constants as c

    assert c.get_active_gwp(standard="AR6", horizon="20") == {"CO2": 1.0, "CH4": c.GWP_STANDARDS["AR6"]["CH4_20"],
                                                             "N2O": c.GWP_STANDARDS["AR6"].get("N2O_20", 264.0)}


def test_gwp_cache_cleared_inside_a_request_and_settings_unavailable(app, monkeypatch):
    import sys

    import calculations.constants as c

    with app.test_request_context("/"):
        from flask import g

        g._gwp_standard = "AR6"
        c.invalidate_gwp_cache()
        assert "_gwp_standard" not in g
    monkeypatch.setitem(sys.modules, "routes.auth", None)                                        # import fails
    assert c.get_active_gwp() == {"CO2": 1.0, "CH4": c.GWP_STANDARDS["AR5"]["CH4"],
                                  "N2O": c.GWP_STANDARDS["AR5"]["N2O"]}
    c.invalidate_gwp_cache()


def test_component_dict_without_factor_and_fraction_ch4():
    from calculations.fugitive import ComponentFugitiveCalculator, EquipmentFugitiveCalculator

    res = ComponentFugitiveCalculator().calculate({"valve": {"count": 4}}, 0.5, {})
    assert res["results"]["ch4"]["value"] == pytest.approx(4 * 0.0045 * 0.5 * 8760 / 1000)       # catalog gas valve
    eq = EquipmentFugitiveCalculator().calculate(2, 0.1, ch4_content=0.5, ef_unit="kg TOC/hr/source")
    assert eq["results"]["ch4"]["value"] == pytest.approx(2 * 0.1 * 0.5 * 8760 / 1000)
