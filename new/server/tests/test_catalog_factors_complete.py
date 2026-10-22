"""Every catalog factor pinned (completes tests/test_catalog_factors.py, which checks ~90 rows).

Each row is checked by the strongest means available, in this order:
  1. recomputed from the basis the row itself states (whole-gas scf x mol % CH4, scf CH4, kg TOC/hr,
     carbon atoms, t/10^12 J) with the Compendium constants 379.3 scf/lbmol, 16.04 / 44.01 lb/lbmol;
  2. compared with an independently typed published value (40 CFR 98 Tables C-1 / C-2, which the
     Compendium reproduces as Tables 4-5 / 4-6; AP-42 Chapter 3; IPCC 2006 Vol 3 Table 3.3);
  3. table values compared on 2026-10-16 with the Compendium text (api.org API-GHG-Compendium-110921.pdf,
     pdftotext): every printed catalog value occurs in it; the rows not printed verbatim are the derived ones
     recomputed above (flaring, venting, engines, acetylene, pure-gas flares). The one row found in no table,
     "Component - Flange (Gathering)" (1.05E-06), was removed.
test_every_row_is_pinned fails when a catalog row has none of these, so a new row needs a reference.
"""
import pytest

import emission_factors as ef

CAT = {**ef.API_FACTORS, **ef.ALL_EMISSION_FACTORS}
SCF_PER_LBMOL, LB_PER_T, MV = 379.3, 2204.62, 23.685
MMBTU_PER_TJ_KG = 1.055056          # 1 t / 10^12 J = 1.055056 kg / MMBtu
LB_TO_KG = 0.45359237


def t_ch4(scf_ch4):
    return scf_ch4 / SCF_PER_LBMOL * 16.04 / LB_PER_T


PINNED = set()


def pin(*keys):
    PINNED.update(keys)
    return keys


# ---------------------------------------------------------------- combustion: Table C-1 (Table 4-5)
C1 = {  # key: (HHV in the row's base unit, kg CO2 / MMBtu)
    "Propylene": (91000, 67.77), "Butane": (103000, 64.77), "Isobutane": (99000, 64.94),
    "Naphtha": (125000, 68.02), "Lubricants": (144000, 74.27), "Waste Oil": (138000, 74.00),
    "Tires": (28000, 85.97), "Compressed Natural Gas (CNG)": (1020, 53.06),
    "Liquefied Natural Gas (LNG)": (1020, 53.06), "Natural Gas - Turbine": (1020, 53.06),
    "Natural Gas - Heater/Boiler": (1020, 53.06), "Natural Gas - 2-Stroke Lean Burn Engine": (1020, 53.06),
    "Natural Gas - 4-Stroke Lean Burn Engine": (1020, 53.06), "Natural Gas - 4-Stroke Rich Burn Engine": (1020, 53.06),
    # already in test_catalog_factors.py, repeated so this file covers every combustion row
    "Natural Gas": (1020, 53.06), "Propane (Gas)": (2516, 61.46), "Propane (Liquid)": (91000, 62.87),
    "Propane (Liquid/LPG)": (91000, 62.87), "Ethane": (68000, 59.60), "Diesel (No. 2 Fuel Oil)": (138000, 73.96),
    "Marine Diesel Oil": (138000, 73.96), "Residual Fuel Oil (No. 6)": (150000, 75.10), "Kerosene": (135000, 75.20),
    "Jet Fuel": (135000, 72.22), "Motor Gasoline": (125000, 70.22), "Crude Oil": (138000, 74.54),
    "Anthracite Coal": (25090, 103.69), "Bituminous Coal": (24930, 93.28), "Sub-Bituminous Coal": (17250, 97.17),
    "Lignite Coal": (14210, 97.72), "Petroleum Coke": (30000, 102.41), "Blast Furnace Gas": (92, 274.32),
    "Coke Oven Gas": (599, 46.85), "Refinery Fuel Gas": (1388, 59.00),
}
pin(*C1)


@pytest.mark.parametrize("key", sorted(C1))
def test_table_c1_heating_value_and_co2(key):
    hhv, co2 = C1[key]
    assert CAT[key]["hhv"] == pytest.approx(hhv) and CAT[key]["co2"] == pytest.approx(co2)
    assert CAT[key]["unit"] == "kg/MMBtu"


# Table C-2 (Table 4-6), kg / MMBtu
_NG, _PET, _COAL, _SOLID = (1.0e-3, 1.0e-4), (3.0e-3, 6.0e-4), (1.1e-2, 1.6e-3), (3.2e-2, 4.2e-3)
C2 = {
    **{k: _NG for k in ("Natural Gas", "Compressed Natural Gas (CNG)", "Liquefied Natural Gas (LNG)",
                         "Natural Gas - Heater/Boiler")},
    **{k: _PET for k in ("Propylene", "Butane", "Isobutane", "Naphtha", "Lubricants", "Waste Oil", "Propane (Gas)",
                          "Propane (Liquid)", "Propane (Liquid/LPG)", "Ethane", "Ethane (Gas)", "Diesel (No. 2 Fuel Oil)",
                          "Residual Fuel Oil (No. 6)", "Kerosene", "Jet Fuel", "Motor Gasoline",
                          "Crude Oil", "Refinery Fuel Gas", "Acetylene")},
    **{k: _COAL for k in ("Anthracite Coal", "Bituminous Coal", "Sub-Bituminous Coal", "Lignite Coal")},
    **{k: _SOLID for k in ("Tires", "Petroleum Coke")},   # EPA EF Hub: 32 g CH4, 4.2 g N2O per MMBtu
    "Blast Furnace Gas": (2.2e-5, 1.0e-4), "Coke Oven Gas": (4.8e-4, 1.0e-4),
    # Table 4-16 "Diesel Ships" (Exhibit 4.13): 2.5E-04 t CH4 and 7.2E-05 t N2O per m3 of fuel,
    # divided by 0.138 MMBtu/gal x 264.172 gal/m3 = 36.456 MMBtu/m3
    "Marine Diesel Oil": (0.25 / (0.138 * 264.172052), 0.072 / (0.138 * 264.172052)),
}


@pytest.mark.parametrize("key", sorted(C2))
def test_table_c2_ch4_n2o(key):
    ch4, n2o = C2[key]
    assert CAT[key]["ch4"] == pytest.approx(ch4) and CAT[key]["n2o"] == pytest.approx(n2o)


# Table 4-7 (t / 10^12 J, HHV) and AP-42 Tables 3.1-2a / 3.2-1 / 3.2-2 / 3.2-3 (lb / MMBtu) for engines and turbines
ENGINES = {  # key: (gas, Table 4-7 t/TJ, AP-42 lb/MMBtu)
    "Natural Gas - 2-Stroke Lean Burn Engine": ("ch4", 0.623, 1.45),
    "Natural Gas - 4-Stroke Lean Burn Engine": ("ch4", 0.537, 1.25),
    "Natural Gas - 4-Stroke Rich Burn Engine": ("ch4", 0.10, 0.229),
    "Natural Gas - Turbine": ("ch4", 0.0037, 8.6e-3),
}


@pytest.mark.parametrize("key", sorted(ENGINES))
def test_table_4_7_engines_and_ap42(key):
    gas, t_tj, lb = ENGINES[key]
    assert CAT[key][gas] == pytest.approx(t_tj * MMBTU_PER_TJ_KG, rel=1e-4)
    assert CAT[key][gas] == pytest.approx(lb * LB_TO_KG, rel=0.02)     # the Compendium rounds 0.229 lb to 0.10 t/TJ


def test_turbine_n2o_and_engine_n2o():
    assert CAT["Natural Gas - Turbine"]["n2o"] == pytest.approx(0.0013 * MMBTU_PER_TJ_KG, rel=5e-4)
    assert CAT["Natural Gas - Turbine"]["n2o"] == pytest.approx(3.0e-3 * LB_TO_KG, rel=0.01)   # AP-42 3.1-2a
    for key in ("Natural Gas - 2-Stroke Lean Burn Engine", "Natural Gas - 4-Stroke Lean Burn Engine",
                "Natural Gas - 4-Stroke Rich Burn Engine"):
        assert CAT[key]["n2o"] == pytest.approx(_NG[1])


def test_ethane_gas_and_acetylene_from_their_properties():
    # ethane: ideal gross heating value 1,769.7 Btu/scf (GPA 2145, 60 F); CO2 per MMBtu as the liquid row
    assert CAT["Ethane (Gas)"]["hhv"] == pytest.approx(1769.7, rel=1e-3)
    assert CAT["Ethane (Gas)"]["co2"] == pytest.approx(C1["Ethane"][1])
    # acetylene C2H2: 26.038 lb/lbmol, 92.26 wt % carbon, 1,470 Btu/scf, full oxidation
    lb_per_scf = 26.038 / SCF_PER_LBMOL
    kg_co2_per_scf = lb_per_scf * (24.022 / 26.038) * 44.01 / 12.011 * LB_TO_KG
    assert CAT["Acetylene"]["hhv"] == 1470
    assert CAT["Acetylene"]["co2"] == pytest.approx(kg_co2_per_scf / 1470e-6, rel=2e-3)


pin("Ethane (Gas)", "Acetylene")


@pytest.mark.parametrize("key", sorted(k for k, v in CAT.items() if "combustion" in (v.get("usage") or [])))
def test_combustion_rows_are_complete(key):
    row = CAT[key]
    # the activity unit comes from baseUnit, or from the physical state (gases per scf, liquids per gal, solids per ton)
    assert row.get("hhv", 0) > 0 and row.get("unit") == "kg/MMBtu", key
    assert row.get("baseUnit") or row.get("type") in ("gases", "liquids", "solids"), key
    assert key in C2 or key in ENGINES, f"{key}: no Table C-2 / 4-7 reference for CH4 / N2O"


# ---------------------------------------------------------------- flaring: carbon balance
PURE_FLARES = {"Propane (Flaring)": 3, "Butane (Flaring)": 4, "Ethylene (Flaring)": 2, "Propylene (Flaring)": 3}
pin(*PURE_FLARES, "Natural Gas (Flaring)", "Natural Gas (Flaring - Elevated)", "Natural Gas (Flaring - Enclosed)",
    "Associated Gas (Flaring)", "Natural Gas (Venting/Blowdown)")   # the last five: test_catalog_factors.py


@pytest.mark.parametrize("key", sorted(PURE_FLARES))
def test_pure_gas_flare_carbon_balance(key):
    co2 = PURE_FLARES[key] * 44.01 / MV * 0.965      # Eq 5-2, 96.5 % combustion
    assert CAT[key]["co2"] == pytest.approx(co2, rel=1e-4)
    assert CAT[key]["ch4"] == 0
    assert CAT[key]["n2o"] == pytest.approx(co2 * 1e-4 / 60.0, rel=1e-3)     # Eq 5-6
    assert CAT[key]["unit"] == "kg/m³"


# ---------------------------------------------------------------- vented rows from their own stated basis
WHOLE_GAS = sorted(k for k, v in CAT.items() if v.get("whole_gas_ef") is not None and v.get("type") != "venting")
pin(*WHOLE_GAS)


@pytest.mark.parametrize("key", WHOLE_GAS)
def test_whole_gas_rows_reproduce_their_ch4(key):
    """Tables 6-5 / 6-6 / 6-10 / 6-11: tonnes CH4 = scf whole gas x mol % CH4 / 379.3 x 16.04 / 2204.62."""
    row = CAT[key]
    derived = t_ch4(row["whole_gas_ef"] * row["ch4_mol_pct"] / 100.0)
    # the tables print tonnes to three decimals (Midcontinent > 100 events: 0.00576 -> 0.006)
    assert row["ch4"] == pytest.approx(derived, rel=0.01) or row["ch4"] == pytest.approx(round(derived, 3), abs=1e-12)
    assert row.get("factor", row["ch4"]) == row["ch4"]
    if row.get("ch4_scf") is not None:                      # Table 6-10 also prints scf CH4 per event
        assert row["ch4_scf"] == pytest.approx(row["whole_gas_ef"] * row["ch4_mol_pct"] / 100.0, rel=0.01)


AGV = sorted(k for k, v in CAT.items() if k.startswith("Associated Gas Venting"))
pin(*AGV)


@pytest.mark.parametrize("key", AGV)
def test_table_6_8_associated_gas_kg_per_bbl(key):
    row = CAT[key]
    kg = row["whole_gas_ef"] * row["ch4_mol_basis"] / SCF_PER_LBMOL * 16.04 * LB_TO_KG   # mol % stored as a fraction
    # the table prints kg/bbl to one decimal; Permian is printed 6.5 kg/bbl beside 419 scf/bbl (6.56): the
    # Compendium's own figures, kept as printed
    if key == "Associated Gas Venting - Permian Basin (Basin 430)":
        assert row["ch4"] == pytest.approx(kg, abs=0.06)
    else:
        assert row["ch4"] == round(kg, 1)
    assert row["unit"] == "kg CH4/bbl" and row["baseUnit"] == "bbl"


PNEUMATIC_SCFH = {"Pneumatic Controller - High Bleed": 37.3, "Pneumatic Controller - High Bleed (>6 scfh)": 37.3,
                  "Pneumatic Controller - Low Bleed": 1.39, "Pneumatic Controller - Low Bleed (<6 scfh)": 1.39,
                  "Pneumatic Controller - Intermittent": 13.5}
pin(*PNEUMATIC_SCFH, "Pneumatic Controller - Continuous Vent (T&S)")


@pytest.mark.parametrize("key", sorted(PNEUMATIC_SCFH))
def test_pneumatic_bleed_rates_tables_6_14_6_15(key):
    """EPA GHGRP bleed rates (whole gas scf/h) x 8,760 h x 81.6 mol % CH4 -> tonnes CH4 per device-year."""
    assert CAT[key]["ch4"] == pytest.approx(t_ch4(PNEUMATIC_SCFH[key] * 8760 * 0.816), rel=0.005)


# ---------------------------------------------------------------- Table 7-12: kg TOC/hr -> tonne CH4/hr
TOC = sorted(k for k, v in CAT.items() if v.get("toc_ef_kg_hr") is not None)
pin(*TOC)


@pytest.mark.parametrize("key", TOC)
def test_table_7_12_one_ch4_fraction_and_unit(key):
    row = CAT[key]
    assert row["ch4"] * 1000 / row["toc_ef_kg_hr"] == pytest.approx(0.6523, rel=0.005)  # one TOC -> CH4 weight fraction
    assert row["factor_value"] == row["toc_ef_kg_hr"] and row["factor_unit"] == "kg TOC/hr/component"


# ---------------------------------------------------------------- rows whose metadata states the same factor
STRUCTURED = sorted(k for k, v in CAT.items() if v.get("factor_value") is not None and k not in TOC)
pin(*STRUCTURED)


@pytest.mark.parametrize("key", STRUCTURED)
def test_factor_value_metadata_matches_the_calculated_factor(key):
    row = CAT[key]
    assert row["factor_unit"] == row["unit"] and row["factor_value"] == pytest.approx(row["ch4"]), key


# ---------------------------------------------------------------- aliases of one piece of equipment agree
ALIASES = [
    ("Pneumatic Controller - High Bleed", "Pneumatic Controller - High Bleed (>6 scfh)"),
    ("Pneumatic Controller - Low Bleed", "Pneumatic Controller - Low Bleed (<6 scfh)"),
    ("UnloadPlunger", "Liquids Unloading - Plunger Lift", "Liquids Unloading - Plunger Lift (Tier 1 Default)"),
    ("UnloadNonPlunger", "Liquids Unloading - Non-Plunger", "Liquids Unloading - Non-Plunger (Tier 1 Default)"),
    ("Propane (Liquid)", "Propane (Liquid/LPG)"),
    ("Completion - Gas Well (No Flaring)", "Well Completion - Gas Well without Hydraulic Fracturing (Vented)"),
    ("Tank - Flash Emissions (Oil)", "Tank - Crude Oil (Large, >10 bbl/d)"),
    ("Component - Block Valve", "Component - Block Valve (Gathering)"),
    ("Component - Control Valve", "Component - Control Valve (Gathering)"),
    ("Component - Connector (Non-Compressor)", "Component - Connector (Gathering)"),
    ("Component - Pressure Relief Valve", "Component - Pressure Relief Valve (Gathering)"),
    ("Component - Pressure Regulator", "Component - Pressure Regulator (Gathering)"),
    ("Component - Compressor Seal", "Component - Compressor Seal (Gathering)"),
    ("Natural Gas (Flaring)", "Natural Gas (Flaring - Elevated)", "Natural Gas (Flaring - Enclosed)"),
    ("Drilling - Mud Degassing (Oil Based)", "Drilling - Mud Degassing (Synthetic)"),
]
for group in ALIASES:
    pin(*group)


@pytest.mark.parametrize("group", ALIASES, ids=lambda g: g[0])
def test_aliases_agree(group):
    first = CAT[group[0]]
    for key in group[1:]:
        for gas in ("co2", "ch4", "n2o", "hhv"):
            assert (CAT[key].get(gas) or 0) == pytest.approx(first.get(gas) or 0), (key, gas)


# ---------------------------------------------------------------- table values as printed in the Compendium
TRANSCRIBED = {  # key: (gas, value, unit)
    "Well Completion - Gas Well with Hydraulic Fracturing (REC with Venting)": ("ch4", 13.542, "tonnes/completion"),
    "Workover - Gas Well (No Flaring)": ("ch4", 0.047, "tonnes/event"),                       # Table 6-9
    "Tank - Crude Oil (Small, ≤10 bbl/d)": ("ch4", 0.0184, "kg CH₄/bbl"),                     # Table 6-22
    "Tank - Production Condensate (Small, ≤10 bbl/d)": ("ch4", 0.119, "kg CH₄/bbl"),          # Table 6-24
    "Tank - Production Condensate (Large, >10 bbl/d)": ("ch4", 0.146, "kg CH₄/bbl"),
    "Drilling - Mud Degassing (Water Based)": ("ch4", 0.0458, "tonnes CH4/drilling day"),     # Table 6-2
    "Dehydrator - Glycol (Uncontrolled)": ("ch4", 0.0052859, "tonnes CH4/MMscf"),             # Table 6-17
    "Pneumatic Controller - Continuous Vent (T&S)": ("ch4", 3.5, "tonnes CH₄/yr"),            # Table 6-42
    "Asphalt": ("ch4", 3.07, "kg/short_ton"),                                                 # Table 6-52
    "Gathering - AGRU": ("ch4", 6.83e-05, "tonne CH₄/unit/hr"),                               # Table 7-29
    "Gathering - Dehydrator": ("ch4", 5.69e-05, "tonne CH₄/unit/hr"),
    "Gathering - Separator": ("ch4", 1.05e-05, "tonne CH₄/unit/hr"),
    "Gathering - Tank": ("ch4", 6.4e-04, "tonne CH₄/unit/hr"),
    "Component - Connector (Non-Compressor)": ("ch4", 9.79e-07, "tonne CH₄/hr/source"),       # Table 7-30
    "Component - Block Valve": ("ch4", 4.36e-06, "tonne CH₄/hr/source"),
    "Component - Control Valve": ("ch4", 1.11e-05, "tonne CH₄/hr/source"),
    "Component - Pressure Relief Valve": ("ch4", 1.39e-07, "tonne CH₄/hr/source"),
    "Component - Pressure Regulator": ("ch4", 1.87e-06, "tonne CH₄/hr/source"),
    "Component - Compressor Seal": ("ch4", 1.54e-04, "tonne CH₄/hr/source"),
    "Processing - Reciprocating Compressor": ("ch4", 8.95e-03, "tonne CH₄/compressor/hr"),   # Table 7-35
    "Processing - Centrifugal Compressor": ("ch4", 0.017, "tonne CH₄/compressor/hr"),
    "LNG - Storage Station": ("ch4", 4.39e-04, "tonne CH₄/facility"),    # Table 7-76, refused (unverified_basis)
    "LNG - Import Terminal": ("ch4", 3.29e-04, "tonne CH₄/facility"),
    "LNG - Export Terminal": ("ch4", 1.26e-03, "tonne CH₄/facility"),
    "Refinery - Fuel Gas System (50-99k bbl/day)": ("ch4", 3.75e-04, "tonnes CH₄/10³ bbl feedstock"),   # Table 7-80
    "Refinery - Fuel Gas System (100-199k bbl/day)": ("ch4", 1.41e-03, "tonnes CH₄/10³ bbl feedstock"),
    "Offshore - Oil Production (Facility)": ("ch4", 9.386e-05, "tonne CH₄/bbl produced"),    # Table 7-3
    "Offshore - Gas Production (Facility)": ("ch4", 0.0104, "tonne CH₄/10⁶ scf produced"),
    # Table 6-53
    "Acrylonitrile": ("co2", 1.0, None), "Carbon Black": ("co2", 2.63, None),
    "Carbon Black (Thermal Abatement)": ("co2", 2.63, None), "Ethylene (Other Feedstocks)": ("co2", 0.77, None),
    "Ethylene (Ethane Feedstock)": ("co2", 0.77, None), "Ethylene Dichloride": ("co2", 0.041, None),
    "Ethylene Oxide": ("co2", 0.46, None), "Ethylene Oxide (Thermal Abatement)": ("co2", 0.46, None),
    "Methanol": ("co2", 0.67, None),
    "Adipic Acid - Thermal Abatement": ("n2o", 13.0, "kg N₂O/tonne product"),
    "Adipic Acid - Catalytic Abatement": ("n2o", 53.0, "kg N₂O/tonne product"),
}
pin(*TRANSCRIBED)


@pytest.mark.parametrize("key", sorted(TRANSCRIBED))
def test_transcribed_rows(key):
    gas, value, unit = TRANSCRIBED[key]
    assert CAT[key][gas] == pytest.approx(value)
    if unit:
        assert CAT[key]["unit"] == unit


def test_asphalt_co2():
    assert CAT["Asphalt"]["co2"] == pytest.approx(5.61)


# IPCC 2006 Vol 3 Table 3.3 (nitric acid) and Table 3.4 (adipic acid, uncontrolled)
IPCC_N2O = {"Nitric Acid - With NSCR": 2.0, "Nitric Acid - Without NSCR": 9.0, "Adipic Acid - Uncontrolled": 300.0}
pin(*IPCC_N2O)


@pytest.mark.parametrize("key", sorted(IPCC_N2O))
def test_ipcc_n2o_production(key):
    assert CAT[key]["n2o"] == pytest.approx(IPCC_N2O[key]) and CAT[key]["co2"] == 0 and CAT[key]["ch4"] == 0


def test_adipic_abatement_lies_below_uncontrolled():
    unc = CAT["Adipic Acid - Uncontrolled"]["n2o"]
    assert 0 < CAT["Adipic Acid - Thermal Abatement"]["n2o"] < CAT["Adipic Acid - Catalytic Abatement"]["n2o"] < unc


# ---------------------------------------------------------------- completeness and row hygiene
def test_every_row_is_pinned():
    missing = sorted(set(CAT) - PINNED)
    assert not missing, f"catalog rows without a reference value: {missing}"
    stale = sorted(PINNED - set(CAT))
    assert not stale, f"pinned rows no longer in the catalog: {stale}"


@pytest.mark.parametrize("key", sorted(CAT))
def test_row_hygiene(key):
    row = CAT[key]
    assert row.get("unit"), key
    for gas in ("co2", "ch4", "n2o"):
        v = row.get(gas)
        assert v is None or (isinstance(v, (int, float)) and v >= 0), (key, gas, v)
    assert any((row.get(g) or 0) > 0 for g in ("co2", "ch4", "n2o")), f"{key}: no gas has a factor"
    for gas, u in (row.get("uncertainty") or {}).items():
        assert 0 <= u <= 5, (key, gas, u)


def test_unsourced_gathering_flange_row_removed():
    """Table 7-30 (gathering) has no flange row and 1.05E-06 occurs nowhere in the Compendium."""
    assert "Component - Flange (Gathering)" not in CAT
