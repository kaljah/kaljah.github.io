"""API Compendium 2021 Table 4-16: mobile source CH4 and N2O emission factors by vehicle type and technology.

Values are the table's "converted to tonnes/1,000 gal fuel" column, the one its worked Exhibit 4.12 uses (the
original g/L column is kept beside it for reference). Mobile combustion used the stationary Table C-2 CH4 / N2O factors,
e.g. gasoline N2O 0.6 g/MMBtu, about 24 x below a Tier 1 light-duty gasoline vehicle (audit 2026-11 F-FAC-02).
Only liquid-fuel modes are listed: their factors are per volume of the liquid fuel burned.
"""

L_PER_GAL = 3.785411784

# key: (label, fuel, CH4 g/L, N2O g/L) - the original column
_ROWS = {
    "ldgv_tier2": ("Light-duty gasoline vehicle, Tier 2", "gasoline", 0.14, 0.022),
    "ldgv_tier1": ("Light-duty gasoline vehicle, Tier 1", "gasoline", 0.23, 0.47),
    "ldgv_tier0": ("Light-duty gasoline vehicle, Tier 0", "gasoline", 0.32, 0.66),
    "ldgv_oxidation_catalyst": ("Light-duty gasoline vehicle, oxidation catalyst", "gasoline", 0.52, 0.20),
    "ldgv_non_catalytic": ("Light-duty gasoline vehicle, non-catalytic controlled", "gasoline", 0.46, 0.028),
    "ldgt_tier2": ("Light-duty gasoline truck, Tier 2", "gasoline", 0.14, 0.022),
    "ldgt_tier1": ("Light-duty gasoline truck, Tier 1", "gasoline", 0.24, 0.58),
    "ldgt_tier0": ("Light-duty gasoline truck, Tier 0", "gasoline", 0.21, 0.66),
    "ldgt_oxidation_catalyst": ("Light-duty gasoline truck, oxidation catalyst", "gasoline", 0.43, 0.20),
    "ldgt_non_catalytic": ("Light-duty gasoline truck, non-catalytic controlled", "gasoline", 0.56, 0.028),
    "hdgv_three_way": ("Heavy-duty gasoline vehicle, three-way catalyst", "gasoline", 0.068, 0.20),
    "hdgv_non_catalytic": ("Heavy-duty gasoline vehicle, non-catalytic controlled", "gasoline", 0.29, 0.047),
    "hdgv_uncontrolled": ("Heavy-duty gasoline vehicle, uncontrolled", "gasoline", 0.49, 0.084),
    "motorcycle_non_catalytic": ("Motorcycle, non-catalytic controlled", "gasoline", 0.77, 0.041),
    "motorcycle_uncontrolled": ("Motorcycle, uncontrolled", "gasoline", 2.3, 0.048),
    "lddv_advanced": ("Light-duty diesel vehicle, advanced control", "diesel", 0.051, 0.22),
    "lddv_moderate": ("Light-duty diesel vehicle, moderate control", "diesel", 0.068, 0.21),
    "lddv_uncontrolled": ("Light-duty diesel vehicle, uncontrolled", "diesel", 0.10, 0.16),
    "lddt_advanced": ("Light-duty diesel truck, advanced control", "diesel", 0.068, 0.22),
    "lddt_moderate": ("Light-duty diesel truck, moderate control", "diesel", 0.068, 0.21),
    "lddt_uncontrolled": ("Light-duty diesel truck, uncontrolled", "diesel", 0.085, 0.16),
    "hd_diesel_advanced": ("Heavy-duty diesel vehicle, advanced control", "diesel", 0.11, 0.151),
    "hd_diesel_moderate": ("Heavy-duty diesel vehicle, moderate control", "diesel", 0.14, 0.082),
    "hd_diesel_uncontrolled": ("Heavy-duty diesel vehicle, uncontrolled", "diesel", 0.15, 0.075),
    "propane_vehicle": ("Propane vehicle", "propane", 0.64, 0.028),
    "offroad_gasoline_2s": ("Off-road gasoline, 2-stroke", "gasoline", 10.61, 0.013),
    "offroad_gasoline_4s": ("Off-road gasoline, 4-stroke", "gasoline", 5.08, 0.064),
    "offroad_diesel_lt19kw": ("Off-road diesel, < 19 kW", "diesel", 0.073, 0.022),
    "offroad_diesel_tier1_3": ("Off-road diesel, >= 19 kW, Tier 1-3", "diesel", 0.073, 0.022),
    "offroad_diesel_tier4": ("Off-road diesel, >= 19 kW, Tier 4", "diesel", 0.073, 0.227),
    "offroad_propane": ("Off-road propane", "propane", 0.64, 0.087),
    "diesel_train": ("Diesel train", "diesel", 0.15, 1.0),
    "marine_gasoline": ("Marine, gasoline", "gasoline", 0.22, 0.063),
    "marine_diesel": ("Marine, diesel", "diesel", 0.25, 0.072),
    "marine_light_fuel_oil": ("Marine, light fuel oil", "light_fuel_oil", 0.26, 0.073),
    "marine_heavy_fuel_oil": ("Marine, heavy fuel oil", "heavy_fuel_oil", 0.29, 0.082),
    "marine_kerosene": ("Marine, kerosene", "kerosene", 0.25, 0.071),
    "aviation_gasoline": ("Aviation gasoline", "aviation_gasoline", 2.2, 0.23),
    "aviation_turbo_fuel": ("Aviation turbo fuel", "jet_fuel", 0.029, 0.071),
}

# key: (CH4, N2O) in tonnes per 1,000 gal, as printed
_T_PER_KGAL = {
    "ldgv_tier2": (0.00053, 8.3e-05),
    "ldgv_tier1": (0.00087, 0.0018),
    "ldgv_tier0": (0.0012, 0.0025),
    "ldgv_oxidation_catalyst": (0.002, 0.00076),
    "ldgv_non_catalytic": (0.0017, 0.00011),
    "ldgt_tier2": (0.00053, 8.3e-05),
    "ldgt_tier1": (0.00091, 0.0022),
    "ldgt_tier0": (0.00079, 0.0025),
    "ldgt_oxidation_catalyst": (0.0016, 0.00076),
    "ldgt_non_catalytic": (0.0021, 0.00011),
    "hdgv_three_way": (0.00026, 0.00076),
    "hdgv_non_catalytic": (0.0011, 0.00018),
    "hdgv_uncontrolled": (0.0019, 0.00032),
    "motorcycle_non_catalytic": (0.0029, 0.00016),
    "motorcycle_uncontrolled": (0.0087, 0.00018),
    "lddv_advanced": (0.00019, 0.00083),
    "lddv_moderate": (0.00026, 0.00079),
    "lddv_uncontrolled": (0.00038, 0.00061),
    "lddt_advanced": (0.00026, 0.00083),
    "lddt_moderate": (0.00026, 0.00079),
    "lddt_uncontrolled": (0.00032, 0.00061),
    "hd_diesel_advanced": (0.00042, 0.00057),
    "hd_diesel_moderate": (0.00053, 0.00031),
    "hd_diesel_uncontrolled": (0.00057, 0.00028),
    "propane_vehicle": (0.0024, 0.00011),
    "offroad_gasoline_2s": (0.04, 4.9e-05),
    "offroad_gasoline_4s": (0.019, 0.00024),
    "offroad_diesel_lt19kw": (0.00028, 8.3e-05),
    "offroad_diesel_tier1_3": (0.00028, 8.3e-05),
    "offroad_diesel_tier4": (0.00028, 0.00086),
    "offroad_propane": (0.0024, 0.00033),
    "diesel_train": (0.00057, 0.0038),
    "marine_gasoline": (0.00083, 0.00024),
    "marine_diesel": (0.00095, 0.00027),
    "marine_light_fuel_oil": (0.00098, 0.00028),
    "marine_heavy_fuel_oil": (0.0011, 0.00031),
    "marine_kerosene": (0.00095, 0.00027),
    "aviation_gasoline": (0.0083, 0.00087),
    "aviation_turbo_fuel": (0.00011, 0.00027),
}

# tonnes per US gallon of fuel
MOBILE_VEHICLES = {
    k: {"label": lab, "fuel": fuel, "ch4_t_per_gal": _T_PER_KGAL[k][0] / 1000.0, "n2o_t_per_gal": _T_PER_KGAL[k][1] / 1000.0,
        "ch4_g_per_l": ch4, "n2o_g_per_l": n2o, "source": "API Compendium 2021 Table 4-16"}
    for k, (lab, fuel, ch4, n2o) in _ROWS.items()
}

LIQ_TO_GAL = {"gal": 1.0, "gallon": 1.0, "gallons": 1.0, "bbl": 42.0, "l": 1 / L_PER_GAL, "litre": 1 / L_PER_GAL,
              "liter": 1 / L_PER_GAL, "liters": 1 / L_PER_GAL, "litres": 1 / L_PER_GAL,  # GB RY2022 GB-008
              "m3": 1000 / L_PER_GAL, "kgal": 1000.0}


def vehicle_row(key):
    row = MOBILE_VEHICLES.get(str(key or "").strip())
    if row is None:
        raise ValueError("Select the vehicle type and technology (API Compendium Table 4-16); "
                         f"one of: {', '.join(MOBILE_VEHICLES)}")
    return row


def fuel_gallons(quantity, unit):
    u = str(unit or "").strip().lower().replace("³", "3")
    if u not in LIQ_TO_GAL:
        raise ValueError("Mobile CH4 / N2O (Table 4-16) are per volume of liquid fuel: enter the fuel in gal, bbl, L or m3")
    return float(quantity) * LIQ_TO_GAL[u]


def vehicle_list():
    return [{"key": k, "label": v["label"], "fuel": v["fuel"]} for k, v in MOBILE_VEHICLES.items()]


def first_given(inputs, *keys):
    """The first of `keys` with a value (an entered 0 counts; `or` turned it into the default)."""
    return next((inputs.get(k) for k in keys if inputs.get(k) not in (None, "")), None)


def mobile_tier1_factors(res, process_type, factor_source, emission_factors, catalog, flat_inputs, quantity, unit,
                         gwp_dict):
    """Tier 1 mobile combustion of a liquid catalog fuel: CH4 / N2O from Table 4-16 by vehicle type. The catalog row's
    CH4 / N2O are stationary factors; an entered or custom factor, a gaseous fuel and a row that already carries its
    Table 4-16 mode (marine diesel) keep theirs."""
    ftype = str(emission_factors.get("type") or catalog.get("type") or "").lower()
    src = str(factor_source).lower()
    if process_type not in ("mobile_combustion", "mobile"):
        return res
    if (src in ("default", "tier1", "tier_1") and ftype in ("liquids", "liquid")
            and "table 4-16" not in str(emission_factors.get("source") or catalog.get("source") or "").lower()):
        return apply_mobile_factors(res, flat_inputs, quantity, unit, gwp_dict)
    # Compendium 4.6.1 (D11): CO2 from the fuel, CH4 / N2O from Table 4-16 by vehicle type at any tier. A site
    # (Tier 2 / custom / library) factor kept its own CH4 / N2O even when the vehicle type was given (GB RY2022
    # GB-020). Applied when the vehicle type is named and the fuel is a liquid volume.
    if (src in ("custom", "tier2", "tier_2", "library") and first_given(flat_inputs, "vehicle_type") is not None
            and str(unit or "").strip().lower().replace("³", "3") in LIQ_TO_GAL):
        return apply_mobile_factors(res, flat_inputs, quantity, unit, gwp_dict)
    return res


def apply_mobile_factors(res, flat_inputs, quantity, unit, gwp_dict):
    """Mobile CH4 / N2O from API Compendium Table 4-16 by vehicle type, on the gallons of liquid fuel burned.

    The stationary Table C-2 factors of the fuel row were used (audit 2026-11 F-FAC-02: gasoline N2O ~24 x low
    for a Tier 1 light-duty vehicle). A gaseous fuel keeps its row: Table 4-16 is per volume of liquid fuel.
    """
    from .units import calculate_co2e

    if not float(quantity or 0):
        return res  # zero activity is zero emissions on every process
    if str(unit or "").strip().lower().replace("³", "3") not in LIQ_TO_GAL:
        raise ValueError("Mobile CH4 / N2O (Table 4-16) are per volume of liquid fuel: enter the fuel in gal, bbl, L or m3")
    row = vehicle_row(flat_inputs.get("vehicle_type"))
    gal = fuel_gallons(quantity, unit)
    for gas, t_per_gal in (("ch4", row["ch4_t_per_gal"]), ("n2o", row["n2o_t_per_gal"])):
        r = res["results"].get(gas)
        new = gal * t_per_gal
        if isinstance(r, dict):
            old = float(r.get("value") or 0.0)
            scale = (new / old) if old else None
            for k in ("value", "abs_uncertainty", "abs_uncertainty_95", "lower_bound", "upper_bound",
                      "absolute_uncertainty", "ci_95_abs", "lower_bound_95", "upper_bound_95"):
                if k in r and isinstance(r[k], (int, float)):
                    r[k] = new if k == "value" else (r[k] * scale if scale is not None else (new if "bound" in k else 0.0))
        else:
            res["results"][gas] = new
    v = {g: float((res["results"].get(g) or {}).get("value", 0.0)) for g in ("co2", "ch4", "n2o")}
    res["total_co2e"] = calculate_co2e(co2=v["co2"], ch4=v["ch4"], n2o=v["n2o"], gwp_dict=gwp_dict)
    res["method"] = "Mobile Combustion (Table 4-16)"
    res.setdefault("inputs", {})["vehicle_type"] = row["label"]
    return res
