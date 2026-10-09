"""Catalog factor check against the API Compendium 2021 (audit/CATALOG_FACTOR_CHECK.md).

Expected values are the Compendium table entries (or the Compendium equation applied to the
Compendium's own default composition), never the catalog under test.
"""
import json
import os
import shutil
import subprocess

import pytest

import emission_factors as ef

CAT = {**ef.API_FACTORS, **ef.ALL_EMISSION_FACTORS}
MV = 23.685  # Sm3 / kgmole, Compendium section 5.1.2


def flare(ch4, nmhc_c, co2_in, de, ce=0.965):
    """Eq 5-2 (combustion efficiency ce, 96.5 % per the Dec 2025 corrections) / Eq 5-4 (destruction de)."""
    co2 = ((ch4 + nmhc_c) * ce + co2_in) * 44.01 / MV
    return co2, ch4 * (1 - de) * 16.04 / MV


# ---- Table 4-5 (40 CFR 98 Table C-1): heating value and kg CO2/MMBtu ----
@pytest.mark.parametrize("key,hhv,co2", [
    ("Natural Gas", 1020, 53.06), ("Propane (Gas)", 2516, 61.46), ("Propane (Liquid)", 91000, 62.87),
    ("Propane (Liquid/LPG)", 91000, 62.87), ("Ethane", 68000, 59.60), ("Diesel (No. 2 Fuel Oil)", 138000, 73.96),
    ("Marine Diesel Oil", 138000, 73.96), ("Residual Fuel Oil (No. 6)", 150000, 75.10), ("Kerosene", 135000, 75.20),
    ("Jet Fuel", 135000, 72.22), ("Motor Gasoline", 125000, 70.22), ("Crude Oil", 138000, 74.54),
    ("Anthracite Coal", 25090, 103.69), ("Bituminous Coal", 24930, 93.28), ("Sub-Bituminous Coal", 17250, 97.17),
    ("Lignite Coal", 14210, 97.72), ("Petroleum Coke", 30000, 102.41), ("Blast Furnace Gas", 92, 274.32),
    ("Coke Oven Gas", 599, 46.85), ("Refinery Fuel Gas", 1388, 59.00),
])
def test_table_4_5_fuels(key, hhv, co2):
    assert CAT[key]["hhv"] == pytest.approx(hhv) and CAT[key]["co2"] == pytest.approx(co2)


def test_table_4_6_petroleum_coke_and_fuel_gas():
    assert (CAT["Petroleum Coke"]["ch4"], CAT["Petroleum Coke"]["n2o"]) == (0.032, 0.0042)
    assert (CAT["Refinery Fuel Gas"]["ch4"], CAT["Refinery Fuel Gas"]["n2o"]) == (0.003, 0.0006)


# ---- flaring rows: Equations 5-2 / 5-4 on the Table 5-1 compositions ----
@pytest.mark.parametrize("key,comp,de", [
    ("Natural Gas (Flaring)", (0.919, 0.0684 * 2, 0.0058), 0.98),
    ("Natural Gas (Flaring - Elevated)", (0.919, 0.0684 * 2, 0.0058), 0.98),
    ("Natural Gas (Flaring - Enclosed)", (0.919, 0.0684 * 2, 0.0058), 0.98),  # by segment, not design
    ("Associated Gas (Flaring)", (0.80, 0.15 * 2 + 0.05 * 3, 0.0), 0.98),
])
def test_flaring_rows_equations_5_2_5_4(key, comp, de):
    co2, ch4 = flare(*comp, de)
    assert CAT[key]["co2"] == pytest.approx(co2, rel=1e-4)
    assert CAT[key]["ch4"] == pytest.approx(ch4, rel=1e-4)


def test_unsourced_rows_removed():
    for key in ("Natural Gas (Flaring - Ground)", "Sour Gas (Flaring)", "Refinery Gas (Flaring)",
                "Tank - Working Losses (Oil)", "Tank - Breathing Losses (Oil)", "Tank - Gas-Well Condensate (Large, >10 bbl/d)",
                "Loading - Crude Oil (Tank Truck)", "Loading - Crude Oil (Marine Vessel)", "Wastewater - Oil/Water Separator",
                "Fugitive - Valve (Gas/Vapor)", "Gathering - Pipeline", "Component - Pump Seal (Heavy Oil Service)"):
        assert key not in CAT, key


def test_venting_row_table_6_50():
    assert CAT["Natural Gas (Venting/Blowdown)"]["ch4"] == pytest.approx(0.9307 * 16.04 / MV, rel=1e-4)
    assert CAT["Natural Gas (Venting/Blowdown)"]["co2"] == pytest.approx(0.00565 * 44.01 / MV, rel=1e-4)


# ---- Section 6 tables ----
@pytest.mark.parametrize("key,ch4", [
    ("Tank - Crude Oil (Large, >10 bbl/d)", 0.193), ("Tank - Crude Oil (Small, ≤10 bbl/d)", 0.0184),   # Table 6-22
    ("Tank - Production Condensate (Large, >10 bbl/d)", 0.146),                                        # Table 6-24
    ("Tank - Production Condensate (Small, ≤10 bbl/d)", 0.119),
    ("Tank - Flash Emissions (Oil)", 0.193),
    ("Dehydrator - Glycol (Uncontrolled)", 0.0052859),                                                 # Table 6-17
    ("Completion - Gas Well (No Flaring)", 1.7376), ("Workover - Gas Well (No Flaring)", 0.0470),      # 6-6 / 6-9
    ("Drilling - Mud Degassing (Water Based)", 0.0458), ("Drilling - Mud Degassing (Oil Based)", 0.0103),  # 6-2
    ("Liquids Unloading - Plunger Lift", 1.774), ("Liquids Unloading - Non-Plunger", 2.792),           # 6-11
    ("Well Completion - Gas Well with Hydraulic Fracturing (Uncontrolled Venting)", 28.8),             # 6-5
    ("Pneumatic Controller - High Bleed", 5.11), ("Pneumatic Controller - Low Bleed", 0.191),          # 6-14
    ("Pneumatic Controller - Intermittent", 1.85),                                                     # 6-15
    ("Pneumatic Controller - Continuous Vent (T&S)", 3.5),                                             # 6-42
])
def test_section_6_rows(key, ch4):
    assert CAT[key]["ch4"] == pytest.approx(ch4)


def test_tank_flash_has_no_invented_co2():
    assert not CAT["Tank - Flash Emissions (Oil)"]["co2"]


@pytest.mark.parametrize("key,co2,ch4", [
    ("Acrylonitrile", 1.00, 0.00018), ("Carbon Black", 2.63, 0.0287), ("Carbon Black (Thermal Abatement)", 2.63, 0.00006),
    ("Ethylene (Ethane Feedstock)", 0.77, 0.006), ("Ethylene (Other Feedstocks)", 0.77, 0.003),
    ("Ethylene Dichloride", 0.041, 0), ("Ethylene Oxide", 0.46, 0.00179),
    ("Ethylene Oxide (Thermal Abatement)", 0.46, 0.00079), ("Methanol", 0.67, 0.0023),
])
def test_table_6_53_chemicals(key, co2, ch4):
    assert CAT[key]["co2"] == pytest.approx(co2) and (CAT[key]["ch4"] or 0) == pytest.approx(ch4)


# ---- Chapter 7 ----
def test_chapter_7_rows():
    assert CAT["Offshore - Oil Production (Facility)"]["ch4"] == pytest.approx(9.386e-05)      # Table 7-3
    assert CAT["Component - Open-Ended Line (Gathering)"]["ch4"] == pytest.approx(7.09e-05)  # Table 7-30
    assert CAT["Component - Compressor Seal (Gathering)"]["ch4"] == pytest.approx(1.54e-04)
    # Table 7-12: kg THC/hr and converted tonne CH4/hr
    for key, kg, t in (("Component - Valve (Gas Service)", 4.5e-03, 2.94e-06),
                       ("Component - Other / PRV (Water/Oil Service)", 1.4e-02, 9.13e-06),
                       ("Component - Flange (Heavy Oil Service)", 3.9e-07, 2.54e-10)):
        assert CAT[key]["toc_ef_kg_hr"] == pytest.approx(kg) and CAT[key]["ch4"] == pytest.approx(t)


CLIENT_TS = os.path.join(os.path.dirname(__file__), "..", "..", "client", "src", "utils", "EmissionFactors.ts")
CLIENT_JS = os.path.join(os.path.dirname(__file__), "..", "..", "client", "src", "utils", "EmissionFactors.js")
CLIENT = CLIENT_TS if os.path.exists(CLIENT_TS) else CLIENT_JS


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_client_catalog_matches_server():
    script = ("import(process.argv[1]).then(m => { const o = {}; for (const [k, v] of Object.entries(m.API_FACTORS)) "
              "o[k] = { co2: v.co2, ch4: v.ch4, n2o: v.n2o, hhv: v.hhv, usage: v.usage }; "
              "console.log(JSON.stringify(o)); })")
    url = "file:///" + os.path.abspath(CLIENT).replace("\\", "/")
    node_cmd = ["node"]
    if CLIENT.endswith(".ts"):
        node_cmd.append("--experimental-strip-types")
    node_cmd.extend(["-e", script, url])
    out = subprocess.run(node_cmd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert out.returncode == 0, out.stderr
    client = json.loads(out.stdout)
    # client-side names of server-computed Tier 1 choices (the server applies Table 6-3 / 6-5 / 6-6 / 6-10)
    by_calculator = {k for k in client if k.startswith(("Gas Well Completion - ", "Oil Well Completion - ",
                                                         "Liquids Unloading - Plunger (", "Drilling - Gas Well Drilling"))}
    problems = []
    for k, v in client.items():
        if k in by_calculator:
            continue
        s = CAT.get(k)
        if s is None:
            problems.append(f"client-only: {k}")
            continue
        for f in ("co2", "ch4", "n2o", "hhv"):
            cv, sv = v.get(f), s.get(f)
            if (cv or 0) != pytest.approx(sv or 0, rel=1e-4):
                problems.append(f"{k}.{f}: client {cv} server {sv}")
    assert not problems, problems


# ---- Scope 2 grids: Tables 8-2 (eGRID2019, CO2 / CH4 / N2O) and 8-6 (AIB 2020, CO2) ----
def test_grid_factors_tables_8_2_8_6():
    from electricity_factors import GRID_FACTORS, grid_entry, grid_factor_kg_co2e_per_kwh

    us = GRID_FACTORS["US Average"]
    assert (us["co2"], us["ch4"], us["n2o"]) == (0.401, 3.40e-05, 4.99e-06)
    # CO2e follows the GWP set: AR5 and AR6 differ only through CH4 / N2O
    assert grid_factor_kg_co2e_per_kwh(us, {"CH4": 28, "N2O": 265}) == pytest.approx(0.401 + 3.40e-05 * 28 + 4.99e-06 * 265)
    assert grid_factor_kg_co2e_per_kwh(us, {"CH4": 27.9, "N2O": 273}) == pytest.approx(0.401 + 3.40e-05 * 27.9 + 4.99e-06 * 273)
    assert GRID_FACTORS["US-ERCT (ERCOT All)"]["co2"] == 0.394        # tonne, not the 0.434 short ton
    assert GRID_FACTORS["France (grid average)"]["co2"] == 0.0513
    assert grid_entry("UK National Grid") == ("United Kingdom (grid average)", GRID_FACTORS["United Kingdom (grid average)"])
    for gone in ("US-WECC", "EU Grid Average", "Algerian Grid - North", "Algerian Grid - South / Isolated"):
        assert grid_entry(gone)[1] is None
    # Algeria 2024: MEM Bilan Energetique National (23,855 ktep gas to power, PCS; 101,386 GWh) x IPCC 2006
    # natural gas (56,100 kg CO2, 1 kg CH4, 0.1 kg N2O per TJ NCV; NCV = 0.9 x PCS)
    tj_ncv = 23855 * 41.868 * 0.9
    dz = GRID_FACTORS["Algerian National Grid"]
    assert dz["co2"] == pytest.approx(tj_ncv * 56.1 / 101386 / 1000.0, rel=1e-3)
    assert dz["ch4"] == pytest.approx(tj_ncv * 1e-3 / 101386 / 1000.0, rel=1e-3)
    assert all(v["verified"] for v in GRID_FACTORS.values())


# ---- Scope 3 spend: EPA Supply Chain GHG Emission Factors v1.3.0 (NAICS-6, 2022 USD, AR5, with margins) ----
def test_eeio_factors_are_the_epa_dataset():
    from emission_factors.eeio_factors import EEIO_FACTORS, get_eeio_factor, search_eeio_factors

    assert len(EEIO_FACTORS) == 1016
    for code, per_usd in (("331110", 0.787), ("327310", 3.924), ("213112", 0.372), ("211130", 0.405)):
        assert get_eeio_factor(code)["kg_co2e_per_usd"] == per_usd
    for bad in ("211", "000", "221112", "abc"):        # partial, invented fallback, electricity, junk
        with pytest.raises(LookupError):
            get_eeio_factor(bad)
    assert {"331110", "331210"} <= {h["naics"] for h in search_eeio_factors("steel")}
