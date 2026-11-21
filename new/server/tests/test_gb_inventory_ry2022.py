"""GB HBNS & El Merk GHG inventory RY 2022 (API SANGEA, AR4) run through the calculation engine.

Phase 1 of the real-inventory validation: every source of the report's Tables 7 / 8 and 14 / 15 whose inputs are
printed is recalculated with compute_emissions and compared with the printed tonnes (gb_ry2022_cases.py). Where the
platform's default method differs from SANGEA on purpose, a separate test pins the size of the difference and the
input that reproduces the report. Findings: docs/validation-gb-ry2022.md.
"""
from types import SimpleNamespace

import pytest

from calculations import compute_emissions
from calculations.constants import GWP_AR4
from gb_ry2022_cases import (ABS_TOL, EMK_ONROAD_PRINTED, H, E, EMK_GAS, HBNS_GAS, MODULE_TOTALS, PRODUCTION,
                             SITE_TOTALS, SOURCES, diesel_engine, flare, run_source)

REPRODUCE = [s for s in SOURCES if s["kind"] == "reproduce"]


def _close(got, want, rel):
    return abs(got - want) <= max(rel * abs(want), ABS_TOL)


@pytest.mark.parametrize("src", REPRODUCE, ids=[f"{s['site']} {s['name']}" for s in REPRODUCE])
def test_source_matches_report(src):
    got = run_source(src, GWP_AR4)
    bad = []
    for gas, want in src["printed"].items():
        if want is None or gas in src["skip"]:
            continue
        if not _close(got[gas], want, src["tol"][gas]):
            bad.append(f"{gas}: platform {got[gas]:,.4f} vs printed {want:,.4f} "
                       f"({(got[gas] - want) / want * 100 if want else float('inf'):+.2f} %)")
    assert not bad, "; ".join(bad)


def _site_platform(site):
    by_module = {}
    for s in SOURCES:
        if s["site"] != site:
            continue
        if s["kind"] == "reproduce":
            v = run_source(s, GWP_AR4)["co2e"]
        else:  # implied sources: the report's own figure (the platform cannot be given their inputs)
            v = s["printed"].get("co2e") or 0.0
        by_module[s["module"]] = by_module.get(s["module"], 0.0) + v
    return by_module


@pytest.mark.parametrize("site", [H, E])
def test_module_and_site_totals(site):
    """Module totals (Tables 9 / 16) and the site total within 0.8 % (flare N2O kept at the platform default)."""
    got = _site_platform(site)
    for mod, want in MODULE_TOTALS[site].items():
        assert got[mod] == pytest.approx(want, rel=8e-3, abs=0.05), mod
    assert sum(got.values()) == pytest.approx(SITE_TOTALS[site]["co2e"], rel=8e-3)


def test_el_merk_onroad_row_holds_only_heavy_duty_diesel():
    """Report error: Table 15's on-road row (425.84 t CO2) is the heavy-duty diesel alone; the light-duty diesel
    and gasoline of Table 14 are in the module total (2,356.07 t) but not in the row."""
    onroad = [s for s in SOURCES if s["site"] == E and s["name"].startswith("On-Road")]
    res = {s["name"]: run_source(s, GWP_AR4) for s in onroad}
    assert res["On-Road HD Diesel"]["co2"] == pytest.approx(EMK_ONROAD_PRINTED["co2"], rel=0.01)
    assert sum(r["co2"] for r in res.values()) > 2.3 * EMK_ONROAD_PRINTED["co2"]


@pytest.mark.parametrize("site,volume,gas,printed_n2o", [
    (H, 41_544_753.91, HBNS_GAS, 1.544), (E, 56_782_637.02, EMK_GAS["hp"], 2.11)])
def test_flare_n2o_default_is_eq_5_6_not_sangea(site, volume, gas, printed_n2o):
    """Method difference: the platform's flare N2O without an entered factor is Eq 5-6 (CO2 x 1e-4 / 60), about
    8 x below SANGEA, whose flare N2O is per gas volume (3.716e-5 kg N2O/Nm3 on every HBNS and El Merk flare,
    whatever the gas HHV). Entering that factor per Nm3 reproduces the report."""
    p, _ = flare(volume, gas)
    em, _ = compute_emissions(dict(p), {}, gwp_dict=GWP_AR4)
    assert float(em["n2o"]) / printed_n2o == pytest.approx(0.12, abs=0.02)
    em, _ = compute_emissions({**p, "n2o_factor": 3.716e-5, "n2o_factor_unit": "kg/Nm3"}, {}, gwp_dict=GWP_AR4)
    assert float(em["n2o"]) == pytest.approx(printed_n2o, rel=0.02)


def test_diesel_engine_tier1_default_takes_stationary_ch4():
    """Method difference: the Tier 1 diesel row carries Table C-2 stationary CH4 (0.003 kg/MMBtu), 4.8 x below the
    Table 4-11 diesel engine CH4 SANGEA uses; the equipment method (ic_diesel) reproduces the report."""
    from emission_factors import API_FACTORS
    p, fuel = diesel_engine(399_900.0, method="default")
    em, _ = compute_emissions(dict(p), dict(API_FACTORS[fuel]), gwp_dict=GWP_AR4)
    assert float(em["ch4"]) / 0.211 == pytest.approx(0.21, abs=0.02)
    p, f = diesel_engine(399_900.0)
    em, _ = compute_emissions(dict(p), f, gwp_dict=GWP_AR4)
    assert float(em["ch4"]) == pytest.approx(0.211, rel=0.02)


def test_scope2_catalog_algerian_grid_is_above_the_report_factor():
    """Factor difference: the catalog Algerian grid (2024 energy balance, 0.4974 kg CO2/kWh) against the IEA 2019
    0.419 the report uses: +18.7 % Scope 2 for an unchanged consumption."""
    from electricity_factors import GRID_FACTORS, grid_factor_kg_co2e_per_kwh
    got = 136_270e3 * grid_factor_kg_co2e_per_kwh(GRID_FACTORS["Algerian National Grid"], gwp=GWP_AR4) / 1000
    assert got / 57_165.28 == pytest.approx(1.187, abs=0.005)


@pytest.mark.parametrize("site", [H, E])
def test_ngsi_gas_ratio_uses_fixed_hhv(site):
    """Method difference: NGSI's production-segment gas ratio uses 1.235 MMBtu/Mcf; the report uses the gas's own
    HHV (1,363 / 1,168 Btu/scf), which reproduces its 0.141 % / 0.176 % exactly."""
    from services.methane_intensity import M3_PER_MCF, gas_ratio, ngsi_intensity_pct
    prod = PRODUCTION[site]
    ch4 = 2_628.66 if site == H else 4_627.02  # Scope 1 CH4, Tables 10 / 17
    c1 = HBNS_GAS["c1"] if site == H else EMK_GAS["fuel"]["c1"]
    gas_m3, oil = prod["gas_no_inj_sm3"], prod["liquids_boe"]
    platform = ngsi_intensity_pct(ch4, gas_m3, c1, gas_ratio("production", gas_m3, oil))
    e_gas = gas_m3 / M3_PER_MCF * prod["hhv"] / 1000.0
    report = ngsi_intensity_pct(ch4, gas_m3, c1, e_gas / (e_gas + oil * 5.8))
    assert report == pytest.approx(prod["ngsi_pct"], abs=6e-4)
    assert abs(platform - prod["ngsi_pct"]) / prod["ngsi_pct"] > 0.04


@pytest.mark.parametrize("site", [H, E])
def test_boe_denominator_differs_from_report_headline(site):
    """Method difference: the platform's per-BOE intensity uses production without injected gas (Appendix B basis);
    the headline 0.0147 / 0.0190 t CO2e/BOE divides by total production including injected gas, which the platform
    refuses as 'discordant' (> 30 % from oil + net gas) and replaces by oil + net gas at 5,647.52 scf/BOE."""
    from services.dashboard_filters import production_boe
    prod = PRODUCTION[site]
    row = dict(oil_amount=prod["liquids_boe"], oil_unit="bbl", gas_amount=None, gas_unit="mscf",
               gross_gas_mmsm3=prod["gas_sm3"] / 1e6,
               injected_gas_mmsm3=(prod["gas_sm3"] - prod["gas_no_inj_sm3"]) / 1e6,
               gas_without_injected_mmsm3=prod["gas_no_inj_sm3"] / 1e6, total_production_mmboe=prod["total_boe"] / 1e6,
               total_production_no_injected_mmboe=prod["total_no_inj_boe"] / 1e6, crude_oil_mmboe=None,
               condensate_mmboe=None, lpg_mmboe=None, ngl_mmboe=None, saleable_production_mmboe=None)
    assert production_boe(SimpleNamespace(**row)) == pytest.approx(prod["total_no_inj_boe"], rel=1e-9)
    gross_only = production_boe(SimpleNamespace(**{**row, "total_production_no_injected_mmboe": None}))
    assert gross_only < 0.6 * prod["total_boe"]  # the 72.2 / 60.7 MMBOE total is not used
    headline = SITE_TOTALS[site]["co2e"] / prod["total_boe"]
    assert headline == pytest.approx(prod["co2e_per_boe"], abs=6e-5)
