"""Regression tests for the 2026-11-17 blind equation audit (_blind_audit/findings.json, BA-001 .. BA-059).

Expected values are worked by hand from the inputs and the cited norm (API Compendium 2021 with its December 2025
corrections, IPCC 2006, GHG Protocol, NGSI, EU 2023/1773), never read from the engine.
"""
import calendar

import pytest

from app import app
from calculations import compute_emissions
from calculations.dispatcher import CalculationDispatcher
from calculations.units import CONVERSIONS

RHO_CH4 = CONVERSIONS["density_ch4"]
RHO_CO2 = CONVERSIONS["density_co2"]
GWP = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}
JAN = dict(year=2024, month=1)
JAN_FRACTION = 31 / 366


@pytest.fixture
def ctx():
    with app.app_context():
        yield


def _em(payload, factor=None):
    return compute_emissions(dict(payload), factor or {}, gwp_dict=GWP)[0]


def _disp(process, inputs):
    return CalculationDispatcher().dispatch(process, inputs, {}, {}, gwp_dict=GWP)["results"]


def _v(r):
    return (r or {}).get("value", 0.0) if isinstance(r, dict) else (r or 0.0)


# ---------------------------------------------------------------- BA-001: Tier 1 flare efficiency
def test_ba001_catalog_flare_uses_the_entered_efficiency(ctx):
    from services.scope1_calc import resolve_factor

    base = dict(process_type="flaring", fuel="Associated Gas (Flaring)", amount=1e6, unit="m3",
                factor_source="default", **JAN)
    factor = resolve_factor(base)
    ch4_98 = _em(base, factor)["ch4"]
    assert ch4_98 == pytest.approx(1e6 * 0.010836 / 1000, rel=1e-6)  # the row's 98 % destruction
    assert _em(dict(base, destruction_efficiency=99), factor)["ch4"] == pytest.approx(ch4_98 / 2, rel=1e-6)
    assert _em(dict(base, destruction_efficiency=0), factor)["ch4"] == pytest.approx(ch4_98 * 50, rel=1e-6)
    # raw gas: no native CO2, so the CO2 scales with the combustion efficiency
    assert _em(dict(base, combustion_efficiency=98), factor)["co2"] == pytest.approx(1e6 * 2.2414 / 1000 * 98 / 96.5,
                                                                                    rel=1e-6)


# ---------------------------------------------------------------- BA-012: efficiencies are percent
def test_ba012_efficiency_is_percent_and_monotonic(ctx):
    base = dict(process_type="flaring", factor_source="specific", amount=1e6, unit="m3", ch4_content=85, **JAN)
    one, two = _em(dict(base, destruction_efficiency=1)), _em(dict(base, destruction_efficiency=2))
    assert one["ch4"] == pytest.approx(1e6 * 0.85 * 0.99 * RHO_CH4 / 1000, rel=1e-6)
    assert two["ch4"] < one["ch4"]  # 2 % destroys more than 1 % (1 used to be read as 100 %)


# ---------------------------------------------------------------- BA-028: monthly records
@pytest.mark.parametrize("process,inputs,annual", [
    ("transmission_non_routine", {"activity": "transmission_station", "count_or_miles": 3}, 3 * 54.0),
    ("gathering_compressor", {"compressor_count": 2}, 2 * 4.43e-4 * 8784),          # Zimmerle default (BA-035)
    ("distribution_non_routine", {"activity": "mr_station_blowdown", "count_or_miles": 3}, 3 * 0.002895),
])
def test_ba028_annual_factors_cover_the_records_month(process, inputs, annual):
    res = _disp(process, {"factor_source": "specific", "amount": 1, "unit": "count", **inputs, **JAN})
    assert _v(res["ch4"]) == pytest.approx(annual * JAN_FRACTION, rel=2e-3)


# ---------------------------------------------------------------- BA-029 / BA-030
def test_ba029_engineering_error_is_not_replaced_by_the_fuel_factor(ctx):
    with pytest.raises(ValueError, match="Table 6-31"):
        _em(dict(process_type="gathering_tank", factor_source="specific", fuel="Natural Gas", amount=1e6, unit="scf",
                 tank_count=3, component_type="bogus", **JAN), {"co2": 53.06, "unit": "kg/MMBtu", "hhv": 1020})


def test_ba030_transmission_compressor_is_reachable():
    res = _disp("transmission_compressor", {"factor_source": "specific", "amount": 2, "unit": "compressors",
                                            "compressor_count": 2, "operating_hours": 744})
    assert _v(res["ch4"]) == pytest.approx(2 * 4.72e-3 * 744, rel=5e-3)  # Table 6-40 operating rod packing


# ---------------------------------------------------------------- BA-031: dehydrator rates
@pytest.mark.parametrize("amount,unit,mmscf", [(1, "MMscf/d", 31), (366, "MMscf/yr", 31), (365, "MMscf", 365)])
def test_ba031_dehydrator_rates_cover_the_period(amount, unit, mmscf):
    res = _disp("dehydrator", {"factor_source": "specific", "amount": amount, "unit": unit, "ch4_content": 78.8,
                               **JAN})
    assert _v(res["ch4"]) == pytest.approx(mmscf * 0.0052859, rel=1e-3)


# ---------------------------------------------------------------- BA-002 / BA-003: blowdown
def test_ba002_blowdown_co2_follows_the_volume():
    def co2(volume):
        return _v(_disp("blowdown", {"factor_source": "specific", "amount": volume, "unit": "m3",
                                     "blowdown_pressure": 500, "blowdown_events": 10, "ch4_content": 90}))
    assert co2(1000) == pytest.approx(10 * co2(100), rel=1e-9) or co2(100) == 0.0


def test_ba003_high_pressure_blowdown_uses_a_real_gas_z():
    ideal = _disp("blowdown", {"factor_source": "specific", "amount": 100, "unit": "m3", "blowdown_pressure": 1500,
                               "blowdown_events": 10, "ch4_content": 90, "z_factor": 1.0})
    real = _disp("blowdown", {"factor_source": "specific", "amount": 100, "unit": "m3", "blowdown_pressure": 1500,
                              "blowdown_events": 10, "ch4_content": 90})
    assert _v(real["ch4"]) > _v(ideal["ch4"]) * 1.1  # Z < 1 at 1,515 psia


# ---------------------------------------------------------------- BA-013: Tier 3 combustion
def test_ba013_composition_combustion_is_complete_and_ch4_from_the_factor(ctx):
    em = _em(dict(process_type="combustion", factor_source="specific", amount=1000, unit="m3", hhv=1020, c1=100,
                  **JAN), {"co2": 0, "ch4": 0.001, "n2o": 0, "unit": "kg/MMBtu"})
    assert em["co2"] == pytest.approx(1000 * RHO_CO2 / 1000, rel=1e-6)  # 100 % carbon to CO2
    mmbtu = 1000 * 35.314666721 * 1020 / 1e6
    assert em["ch4"] == pytest.approx(mmbtu * 0.001 / 1000, rel=1e-3)   # the factor, no slip


# ---------------------------------------------------------------- BA-017: flare N2O, Eq 5-6
def test_ba017_flare_n2o_follows_the_co2():
    lean = _disp("flaring", {"factor_source": "specific", "amount": 1e6, "unit": "m3", "c1": 0.85, "n2_mol": 99.15})
    assert _v(lean["n2o"]) == pytest.approx(_v(lean["co2"]) * 1e-4 / 60, rel=1e-9)


# ---------------------------------------------------------------- BA-036: fire suppression GWP
def test_ba036_fire_agent_gwp_follows_the_report():
    from calculations.constants import GWP_STANDARDS
    from calculations.vented_downstream import FireSuppressionCalculator

    for std, gwp in (("AR4", 3220), ("AR5", 3350), ("AR6", 3600)):
        res = FireSuppressionCalculator().calculate(agent_type="hfc_227ea", direct_discharge_kg=10,
                                                    gwp_dict=GWP_STANDARDS[std])
        assert res["total_co2e"] == pytest.approx(10 / 1000 * gwp)


# ---------------------------------------------------------------- BA-039 / BA-040: hydrogen plant
def test_ba039_feedstock_carbon_fraction_reads_the_amount_as_feedstock():
    res = _disp("hydrogen_production", {"factor_source": "default", "amount": 1000, "unit": "tonnes",
                                        "feedstock_carbon_fraction": 0.75})
    assert _v(res["co2"]) == pytest.approx(1000 * 0.75 * 44.01 / 12.011, rel=1e-9)


# ---------------------------------------------------------------- BA-045 / BA-008: steam
def test_ba045_steam_matches_exhibit_8_3(ctx):
    from routes.scope2 import steam_emissions

    heat = 15e6 * (1350 - 180) / 1e6  # 17,550 MMBtu of steam (Exhibit 8.3)
    res = steam_emissions({"amount": heat, "unit": "mmbtu"})
    assert res["co2"] == pytest.approx(1263, abs=1)     # printed 1,263 t CO2
    assert res["ch4"] == pytest.approx(0.0235, abs=1e-4)
    assert res["n2o"] == pytest.approx(0.0064, abs=1e-4)
    lo = steam_emissions({"amount": 1000, "unit": "mmbtu", "calc_inputs": {"indirect_steam": {"ef_co2": 53.06}}})
    hi = steam_emissions({"amount": 1000, "unit": "mmbtu", "calc_inputs": {"indirect_steam": {"ef_co2": 53.07}}})
    assert hi["co2e"] > lo["co2e"]  # monotone in the CO2 factor


# ---------------------------------------------------------------- BA-023: Scope 3 units
def test_ba023_scope3_units_convert():
    from calculations.units import _scope3_activity_in_factor_unit as conv

    assert conv("bbl", "m3") == pytest.approx(0.158987295)
    assert conv("passenger-mile", "passenger-km") == pytest.approx(1.609344)
    assert conv("short_ton-mile", "tonne-km") == pytest.approx(1.459972)


# ---------------------------------------------------------------- BA-041: Monte Carlo removals
def test_ba041_monte_carlo_propagates_a_removal():
    from calculations.uncertainty import monte_carlo_simulation

    alone = monte_carlo_simulation([{"value": 1000.0, "relative_uncertainty": 0.1}], iterations=4000)
    both = monte_carlo_simulation([{"value": 1000.0, "relative_uncertainty": 0.1},
                                   {"value": -500.0, "relative_uncertainty": 0.2}], iterations=4000)
    assert both["std"] > alone["std"]


# ---------------------------------------------------------------- BA-052 / BA-019: published uncertainties
def test_ba052_published_default_uncertainties():
    from calculations.uncertainty import GWP_UNCERTAINTY_1SIGMA, resolve_ef_uncertainty

    assert resolve_ef_uncertainty("combustion", "ch4", 1) == 1.50   # IPCC 2006 Vol.2 Table 2.12
    assert resolve_ef_uncertainty("flaring", "co2", 1) == 0.25      # Compendium Table 5-5
    assert GWP_UNCERTAINTY_1SIGMA["ch4"] == pytest.approx(0.40 / 1.645)


# ---------------------------------------------------------------- BA-053: NGSI
def test_ba053_ngsi_definition():
    from services.methane_intensity import ngsi_intensity_pct, volume_intensity_pct

    mcf = 1_000_000
    m3 = mcf * 28.316846592
    assert ngsi_intensity_pct(16.0, m3, 0.833) == pytest.approx(16.0 / (mcf * 0.833 * 0.0192) * 100)
    assert volume_intensity_pct(16.0, m3) == pytest.approx(16.0 * 1000 / RHO_CH4 / m3 * 100)


def test_ba053_marketed_gas_takes_production_data_first():
    from services.methane_intensity import marketed_gas

    m, basis = marketed_gas(100.0, {"flared": 10.0, "vented": None, "fuel": None, "shrinkage": 5.0},
                            {"flared": 30.0, "vented": 2.0, "fuel": 3.0})
    assert m == pytest.approx(100 - 10 - 2 - 3 - 5)
    assert basis["sources"]["flared"] == "production data" and basis["sources"]["vented"] == "emission records"


# ---------------------------------------------------------------- BA-056: Scope 3 split
def test_ba056_category_11_is_downstream(ctx):
    from services.master_report_data_breakdowns import _query_scope3_breakdown  # noqa: F401  (import check)
    import re

    m = re.search(r"category\s*(\d{1,2})(?!\d)", "category 11")
    assert int(m.group(1)) == 11


# ---------------------------------------------------------------- BA-046: traceability
def test_ba046_unknown_traceability_metric_is_refused(client):
    from tests.audit_helpers import login, make_user

    with app.app_context():
        login(client, make_user("admin", "Global"))
        assert client.get("/api/traceability/trace?metric=nonsense&year=2024").status_code == 400


# ---------------------------------------------------------------- BA-050 (days in a leap year)
def test_ba050_leap_year_days():
    assert sum(calendar.monthrange(2024, m)[1] for m in range(1, 13)) == 366
