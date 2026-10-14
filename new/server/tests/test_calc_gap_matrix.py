"""Calculation checks for paths the other suites do not reach, against hand-computed values:
nitric / adipic acid, hydrogen plant and CCS capture, share parsing, unit conversion round trips,
GWP horizons and uncertainty aggregation."""
import itertools
import math

import pytest

from calculations.constants import GWP_STANDARDS
from calculations.dispatcher import dispatcher
from calculations.stoichiometry import NitricAcidCalculator
from calculations.uncertainty import (Tier, combine_uncertainties_product, combine_uncertainties_sum,
                                      propagate_uncertainty, resolve_tier, srss_inventory)
from calculations.units import ALL_DIMENSION_MAPS, calculate_co2e, convert, to_kelvin, to_psia


def _val(res, gas):
    g = res["results"][gas]
    return g["value"] if isinstance(g, dict) else g


# ---------------------------------------------------------------- nitric / adipic acid
@pytest.mark.parametrize("amount,unit,tonnes", [(1000, "tonne", 1000.0), (1_000_000, "kg", 1000.0),
                                               (1000, "short_ton", 907.18474)])
def test_nitric_acid_units(amount, unit, tonnes):
    res = NitricAcidCalculator().calculate(amount, mass_unit=unit)
    assert _val(res, "n2o") == pytest.approx(tonnes * 9.0 / 1000.0, rel=1e-6)  # 9 kg N2O per tonne, uncontrolled


@pytest.mark.parametrize("abate", [0.9, 90.0])
def test_nitric_acid_abatement(abate):
    res = NitricAcidCalculator().calculate(1000, abatement_efficiency=abate)
    assert _val(res, "n2o") == pytest.approx(1000 * 9.0 * 0.1 / 1000.0, rel=1e-9)


def test_adipic_default_and_custom_factor_and_gwp():
    c = NitricAcidCalculator()
    assert _val(c.calculate(10, process_type="adipic_acid_production"), "n2o") == pytest.approx(10 * 300 / 1000.0)
    assert _val(c.calculate(10, ef_n2o=5.0), "n2o") == pytest.approx(10 * 5.0 / 1000.0)
    res = c.calculate(1000, gwp_dict={"CO2": 1, "CH4": 28, "N2O": 265})
    assert res["total_co2e"] == pytest.approx(9.0 * 265, rel=1e-9)


# ---------------------------------------------------------------- hydrogen plant and CCS capture
H2_SCF_PER_T = 2204.62 / 2.016 * 379.3  # Compendium basis
H2_CO2_PER_SCF = 13.41 / 1e6            # Table 6-51, t CO2 per scf H2


def _h2(**kw):
    return dispatcher.dispatch("hydrogen_plant", {"process_type": "hydrogen_plant", **kw}, {}, {})


def test_hydrogen_table_6_51_and_tonnes_basis():
    assert _val(_h2(h2_produced_scf=2_000_000), "co2") == pytest.approx(2e6 * H2_CO2_PER_SCF, rel=1e-9)
    assert _val(_h2(h2_produced_tonnes=3), "co2") == pytest.approx(3 * H2_SCF_PER_T * H2_CO2_PER_SCF, rel=1e-9)


@pytest.mark.parametrize("cap", [0.9, 90, "90%", "0.9"])
def test_capture_removes_the_captured_share_of_co2(cap):
    base = _val(_h2(h2_produced_tonnes=1), "co2")
    res = _h2(h2_produced_tonnes=1, ccs_capture_rate=cap)
    assert _val(res, "co2") == pytest.approx(base * 0.1, rel=1e-9)
    assert res["total_co2e"] == pytest.approx(base * 0.1, rel=1e-9)
    assert _val(res, "ch4") == 0 and _val(res, "n2o") == 0


def test_capture_zero_and_full():
    base = _val(_h2(h2_produced_tonnes=1), "co2")
    assert _val(_h2(h2_produced_tonnes=1, ccs_capture_rate=0), "co2") == pytest.approx(base)
    assert _val(_h2(h2_produced_tonnes=1, ccs_capture_rate="100%"), "co2") == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("bad", [150, "150%", -10])
def test_capture_outside_0_100_is_refused(bad):
    with pytest.raises(ValueError):
        _h2(h2_produced_tonnes=1, ccs_capture_rate=bad)


def test_blowdown_residual_pressure():
    assert dispatcher._blowdown_residual({}) == {}
    assert dispatcher._blowdown_residual({"final_pressure": "5"}) == {"blowdown_mode": "differential", "final_pressure": 5.0}
    assert dispatcher._blowdown_residual({"blowdown_final_pressure": 7, "final_pressure": 1})["final_pressure"] == 7.0


# ---------------------------------------------------------------- shares: percent or fraction
@pytest.mark.parametrize("raw,expected", [(0, 0.0), ("0.0", 0.0), (0.5, 0.5), (1.0, 1.0), ("50%", 0.5), (85.5, 0.855),
                                          ("100%", 1.0), (100, 1.0), (" 98 % ", 0.98), ("0.5%", 0.005)])
def test_fraction_parsing(raw, expected):
    assert dispatcher._parse_fraction_value(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", [150, "150%", -5, "-1%", 100.5])
def test_fraction_parsing_rejects_out_of_range(raw):
    with pytest.raises(ValueError):
        dispatcher._parse_fraction_value(raw, key_name="x")


def test_fraction_not_a_number_is_none_and_required_complains():
    assert dispatcher._parse_fraction_value("abc") is None
    with pytest.raises(ValueError):
        dispatcher._require_fraction({"x": "abc"}, "x", "test")
    with pytest.raises(ValueError):
        dispatcher._require_fraction({}, "x", "test")


# ---------------------------------------------------------------- units
@pytest.mark.parametrize("dim_index", range(len(ALL_DIMENSION_MAPS)))
def test_round_trip_and_ratio_for_every_pair(dim_index):
    dim = ALL_DIMENSION_MAPS[dim_index]
    n = 0
    for a, b in itertools.permutations(dim, 2):
        x = 1234.5678
        assert convert(convert(x, a, b), b, a) == pytest.approx(x, rel=1e-9), (a, b)
        assert convert(1.0, a, b) == pytest.approx(dim[a] / dim[b], rel=1e-9), (a, b)
        n += 1
    assert n > 0


@pytest.mark.parametrize("value,frm,to,expected", [
    (1, "bbl", "gal", 42.0), (1, "gal", "l", 3.785411784), (1, "short_ton", "kg", 907.18474), (1, "tonne", "kg", 1000.0),
    (1, "mmbtu", "mj", 1055.05585), (1, "kwh", "mj", 3.6), (1, "m3", "l", 1000.0), (1, "lb", "kg", 0.45359237),
    (1, "scf", "m3", 0.0283168466),
])
def test_anchor_conversions(value, frm, to, expected):
    assert convert(value, frm, to) == pytest.approx(expected, rel=1e-6)


@pytest.mark.parametrize("val,unit,expected", [(0, "c", 273.15), (32, "f", 273.15), (300, "k", 300.0), (491.67, "r", 273.15)])
def test_to_kelvin(val, unit, expected):
    assert to_kelvin(val, unit) == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("val,unit,expected", [(0, "psig", 14.696), (14.696, "psia", 14.696), (101.325, "kpa", 14.6959),
                                               (1, "atm", 14.6959), (1, "bara", 14.5038)])
def test_to_psia(val, unit, expected):
    assert to_psia(val, unit) == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------- GWP horizons
GWP = {"AR4": {"100": (25, 298), "20": (72, 289)}, "AR5": {"100": (28, 265), "20": (84, 264)},
       "AR6": {"100": (29.8, 273), "20": (82.5, 273)}}


@pytest.mark.parametrize("std", GWP)
@pytest.mark.parametrize("horizon", ["100", "20"])
def test_gwp_horizons(std, horizon):
    ch4, n2o = GWP[std][horizon]
    assert std in GWP_STANDARDS
    assert calculate_co2e(10, 0, 0, gwp_standard=std, horizon=horizon) == pytest.approx(10)
    assert calculate_co2e(0, 2, 0, gwp_standard=std, horizon=horizon) == pytest.approx(2 * ch4)
    assert calculate_co2e(0, 0, 3, gwp_standard=std, horizon=horizon) == pytest.approx(3 * n2o)
    assert calculate_co2e(10, 2, 3, gwp_standard=std, horizon=horizon) == pytest.approx(10 + 2 * ch4 + 3 * n2o)


# ---------------------------------------------------------------- uncertainty
def test_tiers():
    assert [resolve_tier(x) for x in ("default", "custom", "specific")] == [1, 2, 3]


def test_product_and_sum_rules():
    assert combine_uncertainties_product(0.05, 0.02) == pytest.approx(math.hypot(0.05, 0.02))
    assert combine_uncertainties_product(0.1, 0.1, exact=True) == pytest.approx(math.sqrt(0.01 + 0.01 + 0.0001))
    assert combine_uncertainties_sum(100, 0.1, 300, 0.05) == pytest.approx(math.hypot(10, 15) / 400)


def test_srss_inventory_is_quadrature_over_total():
    src = [{"value": 100, "relative_uncertainty": 0.10}, {"value": 300, "relative_uncertainty": 0.05},
           {"value": 50, "relative_uncertainty": 0.20}]
    out = srss_inventory(src)
    assert out["relative_uncertainty_1sigma"] == pytest.approx(math.sqrt(10 ** 2 + 15 ** 2 + 10 ** 2) / 450)
    assert out["relative_uncertainty_95pct"] == pytest.approx(2 * out["relative_uncertainty_1sigma"])
    assert srss_inventory([])["total_value"] == 0.0


def test_propagate_uncertainty_k2():
    r = propagate_uncertainty(100.0, ef_uncertainty=0.05, activity_uncertainty=0.02, tier=Tier.T2,
                              process_category="scope2", gas="co2")
    assert r["coverage_factor"] == 2.0
    assert r["relative_uncertainty_95pct"] == pytest.approx(2 * r["relative_uncertainty_1sigma"])
    assert r["ci_95_abs"] == pytest.approx(r["relative_uncertainty_95pct"] * 100.0)
    assert r["lower_bound_95"] == pytest.approx(100 - r["ci_95_abs"])
    assert r["upper_bound_95"] == pytest.approx(100 + r["ci_95_abs"])


# ---------------------------------------------------------------- CCS capture on every process
from calculations.constants import GWP_AR5  # noqa: E402
from calculations.legacy_engine import compute_emissions  # noqa: E402
from process_categories import PROCESS_TYPES  # noqa: E402


def _matrix_payload(pid, meta):
    unit = "days" if pid in ("drilling", "mud_degassing") else ("m3" if meta["category"] in ("combustion", "vented") else "devices")
    payload = {"process_type": pid, "factor_source": "default", "amount": 100.0, "quantity": 100.0, "unit": unit,
               "fuel_type": "Natural Gas" if meta["category"] == "combustion" else None}
    if pid == "completions":
        payload["ch4_content"] = 80
    factor = {"co2": 50.0 if meta["category"] == "combustion" else 1.0, "ch4": 0.5, "n2o": 0.01,
              "unit": "kg/m3" if meta["category"] in ("combustion", "vented") else "kg/unit", "hhv": 1020.0}
    return payload, factor


@pytest.mark.parametrize("pid", list(PROCESS_TYPES))
def test_capture_applies_to_every_process_type(pid):
    payload, factor = _matrix_payload(pid, PROCESS_TYPES[pid])
    base = dispatcher.dispatch(pid, dict(payload), factor, {})
    cap = dispatcher.dispatch(pid, {**payload, "ccs_capture_rate": 0.4}, factor, {})
    b_co2, c_co2 = _val(base, "co2"), _val(cap, "co2")
    assert c_co2 == pytest.approx(b_co2 * 0.6, rel=1e-9, abs=1e-15)
    assert _val(cap, "ch4") == pytest.approx(_val(base, "ch4"), rel=1e-12, abs=1e-15)
    assert _val(cap, "n2o") == pytest.approx(_val(base, "n2o"), rel=1e-12, abs=1e-15)
    assert cap["total_co2e"] == pytest.approx(base["total_co2e"] - b_co2 * 0.4, rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("rate", [0.9, "90%", 90])
def test_capture_in_compute_emissions_dispatcher_and_factor_paths(rate):
    f = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu", "hhv": 1020}
    p = {"process_type": "stationary_combustion", "amount": 100, "unit": "MMBtu", "fuel": "Natural Gas",
         "factor_source": "default"}
    base, _ = compute_emissions(dict(p), f, gwp_dict=GWP_AR5)
    cap, _ = compute_emissions({**p, "ccs_capture_rate": rate}, f, gwp_dict=GWP_AR5)
    assert cap["co2"] == pytest.approx(base["co2"] * 0.1, rel=1e-9)
    assert cap["ch4"] == base["ch4"] and cap["n2o"] == base["n2o"]
    assert cap["totalCo2e"] == pytest.approx(base["totalCo2e"] - base["co2"] * 0.9, rel=1e-9)
    # a saved custom factor takes the factor-math path
    cf = {**f, "type": "custom", "name": "X", "custom_factor_id": 1}
    cbase, m = compute_emissions({**p, "factor_source": "custom"}, cf, gwp_dict=GWP_AR5)
    ccap, _ = compute_emissions({**p, "factor_source": "custom", "ccs_capture_rate": rate}, cf, gwp_dict=GWP_AR5)
    assert ccap["co2"] == pytest.approx(cbase["co2"] * 0.1, rel=1e-9)
    assert ccap["totalCo2e"] == pytest.approx(cbase["totalCo2e"] - cbase["co2"] * 0.9, rel=1e-9)
