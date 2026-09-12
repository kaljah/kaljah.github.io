"""
API Compendium 2021 - Section 5: Combustion and Flaring
Implementation of stationary combustion and flaring dual-efficiency calculations.
Supports API §4.2.1 thermodynamic temperature and pressure normalization.
"""

from .base import BaseCalculator
from .units import (
    CONVERSIONS,
    calculate_co2e,
    normalize_gas_volume_to_standard,
)
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
)


def _normalize_unit_str(u):
    if not u:
        return ""
    return (
        str(u)
        .replace("\u00c2", "")
        .replace("\u00b3", "3")
        .replace("^", "")
        .replace(" ", "")
        .lower()
    )


def convert_factor_to_kg_per_unit(
    value, factor_unit, activity_unit, hhv=None, fuel_type=None
):
    if value is None:
        return 0.0
    try:
        val = float(value)
    except (ValueError, TypeError):
        return 0.0
    if val == 0:
        return 0.0

    f_unit = _normalize_unit_str(factor_unit or "")
    a_unit = _normalize_unit_str(activity_unit or "")

    if not f_unit or f_unit in [a_unit, "kg/unit", "unit"]:
        return val

    # Normalize numerator to kg
    if f_unit.startswith("lb"):
        val *= 0.453592
    elif f_unit.startswith("tonne") or f_unit.startswith("metric_ton") or f_unit.startswith("t/"):
        val *= 1000.0
    elif f_unit.startswith("g/"):
        val /= 1000.0

    # Extract denominator
    factor_denom = f_unit.split("/")[1] if "/" in f_unit else f_unit

    # Handle Energy-based factor denominator (e.g. kg/MMBtu)
    if "mmbtu" in factor_denom or "mm_btu" in factor_denom:
        if a_unit in ["mmbtu", "mm_btu"]:
            return val
        if a_unit in ["gj", "gigajoule", "gigajoules"]:
            return val * 0.947817
        if a_unit in ["therm", "therms"]:
            return val * 0.1
        if a_unit in ["scf", "cf", "ft3"]:
            return val * ((hhv or 1020.0) / 1_000_000.0)
        if a_unit in ["m3", "cubic_meters", "m3"]:
            if fuel_type == "liquids":
                return val * (264.172 * (hhv or 138000.0) / 1_000_000.0)
            else:
                return val * (35.3147 * (hhv or 1020.0) / 1_000_000.0)
        if a_unit in ["mscf", "mcf"]:
            return val * (1000.0 * (hhv or 1020.0) / 1_000_000.0)
        if a_unit in ["mmscf"]:
            return val * (1_000_000.0 * (hhv or 1020.0) / 1_000_000.0)
        if a_unit in ["gal", "gallon", "gallons"]:
            return val * ((hhv or 138000.0) / 1_000_000.0)
        if a_unit in ["bbl", "barrel", "barrels"]:
            return val * (42.0 * (hhv or 138000.0) / 1_000_000.0)
        if a_unit in ["l", "liter", "liters"]:
            return val * (0.264172 * (hhv or 138000.0) / 1_000_000.0)
        return val * ((hhv or 1020.0) / 1_000_000.0)

    # Physical denominator conversions relative to standard reference volume (m3) or mass (kg)
    conv = {
        "m3": 1.0,
        "cubic_meters": 1.0,
        "scf": 35.3147,
        "cf": 35.3147,
        "ft3": 35.3147,
        "mscf": 0.0353147,
        "mcf": 0.0353147,
        "mmscf": 3.53147e-5,
        "gal": 264.172,
        "gallon": 264.172,
        "gallons": 264.172,
        "l": 1000.0,
        "liter": 1000.0,
        "liters": 1000.0,
        "bbl": 264.172 / 42.0,
        "barrel": 264.172 / 42.0,
        "barrels": 264.172 / 42.0,
        "kg": 1.0,
        "lb": 2.20462,
        "tonne": 0.001,
        "tonnes": 0.001,
        "ton": 0.00110231,
        "tons": 0.00110231,
    }

    f = conv.get(factor_denom)
    a = conv.get(a_unit)
    if f is not None and a is not None:
        return val * (f / a)

    return val


class CombustionCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Stationary Combustion", "Section 5.1")

    def calculate(
        self,
        fuel_quantity,
        ef_co2,
        ef_ch4,
        ef_n2o,
        uncertainties,
        hhv,
        ef_unit,
        fuel_unit,
        fuel_type,
        combustion_efficiency=0.995,
        operating_temperature=None,
        temp_unit="C",
        operating_pressure=None,
        press_unit="psig",
        z_factor=1.0,
        gwp_dict=None,
        **comps,
    ):
        """
        Standard fuel-based combustion calculation with API §4.2.1 thermodynamic normalization.
        Emissions = Quantity * EF * (HHV if energy-based)
        """
        # Validate inputs
        self.validate_inputs({"quantity": fuel_quantity}, ["quantity"])

        is_gas_fuel = fuel_type in [
            "gases",
            "gas",
            "Natural Gas",
            "natural_gas",
        ] or str(fuel_unit).lower() in ["m3", "scf", "mmscf", "cubic_meters", "m³"]

        # Apply API §4.2.1 thermodynamic normalization to gas fuels if operating T/P supplied
        raw_quantity = fuel_quantity
        if is_gas_fuel and (
            operating_temperature is not None or operating_pressure is not None
        ):
            normalized_gas_vol = normalize_gas_volume_to_standard(
                volume=fuel_quantity,
                operating_temp=operating_temperature,
                temp_unit=temp_unit,
                operating_press=operating_pressure,
                press_unit=press_unit,
                z_factor=z_factor,
            )
            raw_quantity = normalized_gas_vol

        u = str(fuel_unit).lower()

        # Convert EFs to kg per activity unit (unit-aware normalisation)
        kg_per_unit_co2 = convert_factor_to_kg_per_unit(
            ef_co2, ef_unit, fuel_unit, hhv=hhv, fuel_type=fuel_type
        )
        kg_per_unit_ch4 = convert_factor_to_kg_per_unit(
            ef_ch4, ef_unit, fuel_unit, hhv=hhv, fuel_type=fuel_type
        )
        kg_per_unit_n2o = convert_factor_to_kg_per_unit(
            ef_n2o, ef_unit, fuel_unit, hhv=hhv, fuel_type=fuel_type
        )

        co2_kg = raw_quantity * kg_per_unit_co2
        ch4_kg = raw_quantity * kg_per_unit_ch4
        n2o_kg = raw_quantity * kg_per_unit_n2o

        # Convert kg to tonnes
        co2_val = co2_kg / 1000.0
        ch4_val = ch4_kg / 1000.0
        n2o_val = n2o_kg / 1000.0

        # Tier 3 Gas Composition Override (Carbon Mass Balance)
        heavy_hc_warning = False
        if "c1" in comps and comps["c1"] not in [None, "", "-"]:
            c_fractions = {
                "c1": float(comps.get("c1") or 0),
                "c2": float(comps.get("c2") or 0),
                "c3": float(comps.get("c3") or 0),
                "c4": float(comps.get("c4") or 0),
                "c5": float(comps.get("c5") or 0),
                "c6": float(comps.get("c6") or 0),
                "c7": float(comps.get("c7") or 0),
                "c8": float(comps.get("c8") or 0),
                "c9": float(comps.get("c9") or 0),
                "c10": float(comps.get("c10") or 0),
            }

            c2_plus_total = sum(
                c_fractions[k]
                for k in ["c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"]
            )
            if c2_plus_total > 0.10:
                heavy_hc_warning = True

            # Use passed combustion_efficiency
            eta_c = combustion_efficiency or 0.995

            total_carbon_moles = (
                c_fractions["c1"] * 1
                + c_fractions["c2"] * 2
                + c_fractions["c3"] * 3
                + c_fractions["c4"] * 4
                + c_fractions["c5"] * 5
                + c_fractions["c6"] * 6
                + c_fractions["c7"] * 7
                + c_fractions["c8"] * 8
                + c_fractions["c9"] * 9
                + c_fractions["c10"] * 10
            )

            # Apply to gas streams (by fuel_type or volumetric units)
            if is_gas_fuel:
                # Convert quantity to standard m3
                vol_m3 = raw_quantity
                if u in ["scf"]:
                    vol_m3 = raw_quantity * CONVERSIONS.get("scf_to_m3", 0.0283168)
                elif u in ["mscf"]:
                    vol_m3 = (
                        raw_quantity * 1_000.0 * CONVERSIONS.get("scf_to_m3", 0.0283168)
                    )
                elif u in ["mmscf"]:
                    vol_m3 = (
                        raw_quantity
                        * 1_000_000.0
                        * CONVERSIONS.get("scf_to_m3", 0.0283168)
                    )

                density_co2 = CONVERSIONS.get("density_co2", 1.861)

                # Combusted CO2
                co2_combusted_vol = vol_m3 * total_carbon_moles * eta_c
                co2_combusted_kg = co2_combusted_vol * density_co2

                # Native CO2
                co2_native_fraction = float(
                    comps.get("co2_comp") or comps.get("co2_mol") or 0
                )
                co2_native_kg = (vol_m3 * co2_native_fraction) * density_co2

                co2_val = (co2_combusted_kg + co2_native_kg) / 1000.0

        # Resolve tier from factor_source (passed via uncertainties dict sidecar or defaults)
        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        _cat = "combustion"
        # Propagate uncertainty — tier-aware, 95% CI, non-negative bounds
        co2_res = propagate_uncertainty(
            co2_val,
            ef_uncertainty=resolve_ef_uncertainty(
                _cat, "co2", _tier, uncertainties.get("co2")
            ),
            tier=_tier,
            process_category=_cat,
            gas="co2",
        )
        ch4_res = propagate_uncertainty(
            ch4_val,
            ef_uncertainty=resolve_ef_uncertainty(
                _cat, "ch4", _tier, uncertainties.get("ch4")
            ),
            tier=_tier,
            process_category=_cat,
            gas="ch4",
        )
        n2o_res = propagate_uncertainty(
            n2o_val,
            ef_uncertainty=resolve_ef_uncertainty(
                _cat, "n2o", _tier, uncertainties.get("n2o")
            ),
            tier=_tier,
            process_category=_cat,
            gas="n2o",
        )

        total_co2e = calculate_co2e(co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "quantity": fuel_quantity,
                "hhv": hhv,
                "ef_unit": ef_unit,
                "fuel_unit": fuel_unit,
            },
            metadata={
                "operating_temperature": operating_temperature,
                "operating_pressure": operating_pressure,
                "heavy_hydrocarbon_warning": heavy_hc_warning,
                "thermodynamic_normalized": operating_temperature is not None
                or operating_pressure is not None,
            },
        )


class FlaringCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Flaring Dual-Efficiency", "Section 5.2")

    def calculate(
        self,
        gas_volume,
        ch4_fraction,
        flare_type,
        uncertainties,
        hhv=None,
        ef_unit=None,
        fuel_unit=None,
        fuel_type=None,
        ef_n2o=0.0,
        operating_temperature=None,
        temp_unit="C",
        operating_pressure=None,
        press_unit="psig",
        z_factor=1.0,
        gwp_dict=None,
        **comps,
    ):
        """
        Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic normalization.
        Supports full C1-C10 gas composition tracking for accurate CO2 math.
        """
        self.validate_inputs(
            {"volume": gas_volume, "ch4_fraction": ch4_fraction},
            ["volume", "ch4_fraction"],
        )

        # Determine efficiencies based on flare type
        ft = str(flare_type or "elevated").lower().strip().replace("-", "_").replace(" ", "_")
        if ft in ["enclosed", "enclosed_ground", "ground"]:
            eta_c = 0.996
            eta_d = 0.995  # Higher for enclosed
        elif ft in ["elevated", "steam_assisted", "air_assisted", "unassisted", "flare", "open"]:
            eta_c = 0.984
            eta_d = 0.98
        elif ft in ["pit", "open_pit", "other", "candle"]:
            eta_c = 0.920
            eta_d = 0.95
        else:
            eta_c = 0.984
            eta_d = 0.98

        # Normalize gas volume if actual temperature/pressure supplied
        vol_std = gas_volume
        if operating_temperature is not None or operating_pressure is not None:
            vol_std = normalize_gas_volume_to_standard(
                volume=gas_volume,
                operating_temp=operating_temperature,
                temp_unit=temp_unit,
                operating_press=operating_pressure,
                press_unit=press_unit,
                z_factor=z_factor,
            )

        # Parse C1-C10 from kwargs, falling back to ch4_fraction for C1 if not provided
        c_fractions = {
            "c1": float(comps.get("c1") or ch4_fraction or 0),
            "c2": float(comps.get("c2") or 0),
            "c3": float(comps.get("c3") or 0),
            "c4": float(comps.get("c4") or 0),
            "c5": float(comps.get("c5") or 0),
            "c6": float(comps.get("c6") or 0),
            "c7": float(comps.get("c7") or 0),
            "c8": float(comps.get("c8") or 0),
            "c9": float(comps.get("c9") or 0),
            "c10": float(comps.get("c10") or 0),
        }

        actual_ch4_fraction = c_fractions["c1"]
        co2_native_fraction = float(comps.get("co2_comp") or comps.get("co2_mol") or 0)

        # CH4 Emissions (Undestroyed native methane)
        density_ch4 = CONVERSIONS.get("density_ch4", 0.6785)
        ch4_undestroyed_vol = vol_std * actual_ch4_fraction * (1 - eta_d)
        ch4_mass_kg = ch4_undestroyed_vol * density_ch4
        ch4_tonnes = ch4_mass_kg / 1000.0

        # CO2 from Combustion of Hydrocarbons (C1-C10)
        total_carbon_moles_per_mole_gas = (
            c_fractions["c1"] * 1
            + c_fractions["c2"] * 2
            + c_fractions["c3"] * 3
            + c_fractions["c4"] * 4
            + c_fractions["c5"] * 5
            + c_fractions["c6"] * 6
            + c_fractions["c7"] * 7
            + c_fractions["c8"] * 8
            + c_fractions["c9"] * 9
            + c_fractions["c10"] * 10
        )

        # Calculate Combusted CO2 per API Compendium (2021) Eq. 5-4
        density_co2 = CONVERSIONS.get("density_co2", 1.861)
        co2_combusted_vol = vol_std * total_carbon_moles_per_mole_gas * eta_c
        co2_combusted_kg = co2_combusted_vol * density_co2

        # Add Native Uncombusted CO2 passing through the flare
        co2_native_vol = vol_std * co2_native_fraction
        co2_native_kg = co2_native_vol * density_co2

        co2_tonnes = (co2_combusted_kg + co2_native_kg) / 1000.0

        # Resolve tier — flaring with full gas composition is Tier 3
        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        _cat = "flaring"
        co2_res = propagate_uncertainty(
            co2_tonnes,
            ef_uncertainty=resolve_ef_uncertainty(
                _cat, "co2", _tier, uncertainties.get("co2")
            ),
            tier=_tier,
            process_category=_cat,
            gas="co2",
        )
        ch4_res = propagate_uncertainty(
            ch4_tonnes,
            ef_uncertainty=resolve_ef_uncertainty(
                _cat, "ch4", _tier, uncertainties.get("ch4")
            ),
            tier=_tier,
            process_category=_cat,
            gas="ch4",
        )

        # N2O from flaring
        n2o_tonnes = vol_std * (ef_n2o or 0.0) / 1000.0
        n2o_res = propagate_uncertainty(
            n2o_tonnes,
            ef_uncertainty=resolve_ef_uncertainty(
                _cat, "n2o", _tier, uncertainties.get("n2o")
            ),
            tier=_tier,
            process_category=_cat,
            gas="n2o",
        )

        total_co2e = calculate_co2e(
            co2_tonnes, ch4_tonnes, n2o_tonnes, gwp_dict=gwp_dict
        )

        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "gas_volume": gas_volume,
                "ch4_fraction": ch4_fraction,
                "flare_type": flare_type,
                "hhv": hhv,
                "ef_unit": ef_unit,
                "fuel_unit": fuel_unit,
                "fuel_type": fuel_type,
            },
            metadata={
                "combustion_efficiency": eta_c,
                "destruction_efficiency": eta_d,
                "thermodynamic_normalized": operating_temperature is not None
                or operating_pressure is not None,
            },
        )
