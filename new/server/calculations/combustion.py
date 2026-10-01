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
    is_actual_volume_unit,
    gas_volume_m3,
    GAS_VOLUME_UNITS,
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


from .units import (UnitError, factor_to_kg_per_activity, norm_unit, parse_factor_unit,
                    unit_dimension)


def _normalize_efficiency(eff_val, default=0.0):
    """
    Defensively normalizes efficiency inputs provided as either fractional ratios (0.0 - 1.0)
    or percentages (1.0 - 100.0) into a bounded 0.0 - 1.0 float.
    Traps negative numbers and percentages > 1.0 to prevent negative emission inversions.
    """
    if eff_val in [None, "", "-"]:
        return default
    try:
        val = float(str(eff_val).replace("%", "").strip())
    except (ValueError, TypeError):
        return default
    if val < 0.0:
        return 0.0
    if val > 1.0:
        val /= 100.0
    return max(0.0, min(1.0, val))


BTU_TO_MJ = 0.00105505585262

# Catalog HHV basis by fuel type (API Compendium 2021 Table 4-3 conventions used by the catalog):
# gases in Btu/scf, liquids in Btu/gal, solids in kBtu/short ton. An explicit "hhv_unit" on the
# factor overrides this (e.g. Ethane, typed as a gas but tabulated per gallon of liquid).
_HHV_BASIS = {
    "gases": ("scf", 1.0), "gas": ("scf", 1.0),
    "liquids": ("gal", 1.0), "liquid": ("gal", 1.0),
    "solids": ("short_ton", 1000.0), "solid": ("short_ton", 1000.0),
}
_LIQUID_WORDS = ("diesel", "gasoil", "gasoline", "fuel oil", "crude", "kerosene", "jet", "petroleum", "naphtha", "condensate")
_SOLID_WORDS = ("coal", "coke", "lignite", "anthracite", "bituminous", "peat", "wood", "biomass")


_GAS_VOL = {"scf", "cf", "ft3", "mscf", "mcf", "mmscf", "sm3", "sm³", "nm3", "ksm3", "mmsm3"}
_LIQUID_VOL = {"gal", "gallon", "gallons", "bbl", "barrel", "barrels", "kbbl", "mbbl", "mmbbl", "l", "liter", "liters"}


_BASEUNIT_HHV = {"gal": "btu/gal", "scf": "btu/scf", "bbl": "btu/bbl", "ton": "kbtu/short_ton",
                 "short_ton": "kbtu/short_ton", "l": "btu/l", "m3": "btu/m3"}


def factor_hhv_unit(factor_data):
    """Explicit HHV basis of a factor: `hhv_unit`, else derived from its `baseUnit` (BUG-027)."""
    if not factor_data:
        return None
    if factor_data.get("hhv_unit"):
        return factor_data["hhv_unit"]
    return _BASEUNIT_HHV.get(str(factor_data.get("baseUnit") or "").strip().lower())


_HHV_ENERGY_TO_BTU = {"btu": 1.0, "kbtu": 1e3, "mmbtu": 1e6, "mj": 1.0 / BTU_TO_MJ, "kj": 1e-3 / BTU_TO_MJ,
                      "gj": 1e3 / BTU_TO_MJ, "kcal": 0.0041868 / BTU_TO_MJ, "kwh": 3.6 / BTU_TO_MJ, "therm": 1e5}


def user_hhv(hhv, hhv_unit):
    """A heating value entered with its own unit ("MJ/m3", "kcal/m3", "BTU/gal", "MJ/kg") ->
    (value in Btu, "btu/<basis>"). No unit, or the form's already-converted "BTU/unit", keeps the
    catalog basis: (hhv, None). An unreadable unit raises UnitError (S1K-F11: a bulk "MJ/m3" was
    read as Btu/scf, 27x low)."""
    if hhv in (None, "") or hhv_unit in (None, "") or str(hhv_unit).strip().lower() in ("btu/unit", "-"):
        return hhv, None
    hu = norm_unit(hhv_unit).replace(" ", "")
    num, _, den = hu.partition("/")
    mult = _HHV_ENERGY_TO_BTU.get(num)
    if mult is None or not den:
        raise UnitError(f"Unsupported HHV unit '{hhv_unit}' (use e.g. Btu/scf, MJ/m3, kcal/m3, Btu/gal, MJ/kg)")
    den = {"ft3": "scf", "cf": "scf", "lb": "lb", "m³": "m3"}.get(den, den)
    try:
        unit_dimension(den)
    except UnitError:
        raise UnitError(f"Unsupported HHV unit '{hhv_unit}': '{den}' is not a volume or mass unit")
    return float(hhv) * mult, f"btu/{den}"


def fuel_basis(fuel_type, hhv_unit=None):
    """(basis unit, Btu multiplier) of a catalog HHV. BUG-027: from the factor, never from the activity unit."""
    if hhv_unit:
        hu = norm_unit(hhv_unit)
        num, _, den = hu.partition("/")
        mult = {"btu": 1.0, "kbtu": 1e3, "mmbtu": 1e6}.get(num.strip())
        if mult is None or not den:
            raise UnitError(f"Unsupported HHV unit '{hhv_unit}'")
        return den.strip(), mult
    t = str(fuel_type or "").strip().lower()
    if t in _HHV_BASIS:
        return _HHV_BASIS[t]
    if any(w in t for w in _SOLID_WORDS):
        return _HHV_BASIS["solids"]
    if any(w in t for w in _LIQUID_WORDS):
        return _HHV_BASIS["liquids"]
    return _HHV_BASIS["gases"]


def _density_kg_m3(density, basis_dim):
    if density in (None, "", 0):
        return None
    d = float(density)
    # liquid/solid densities entered as kg/L (0.81) rather than kg/m3 (810)
    return d * 1000.0 if (basis_dim == "volume_liquid" and d < 5.0) else d


def hhv_mj_per_unit(hhv, activity_unit, fuel_type=None, density=None, hhv_unit=None):
    """Heating value in MJ per ONE activity unit, converting the activity into the HHV basis.

    Crossing volume <-> mass needs a density (kg/m3); without it the combination is rejected
    instead of being guessed (BUG-027: diesel per tonne, natural gas per tonne, propane per m3).
    """
    if not hhv:
        raise UnitError("A heating value (HHV) is required to apply an energy-based factor to a physical unit")
    basis_unit, mult = fuel_basis(fuel_type, hhv_unit)
    mj_per_basis = float(hhv) * mult * BTU_TO_MJ
    b_dim, b_f = unit_dimension(basis_unit)
    a_dim, a_f = unit_dimension(activity_unit)
    a_tok = norm_unit(activity_unit).replace(" ", "_")
    b_tok = norm_unit(basis_unit)
    if b_dim == a_dim == "volume":
        # gas-phase and liquid-phase volumes are not interchangeable (m3 is accepted for either)
        if b_tok in _LIQUID_VOL and a_tok in _GAS_VOL:
            raise UnitError(f"'{activity_unit}' is a gas volume but this fuel's heating value is per {basis_unit} of liquid")
        if b_tok in _GAS_VOL and a_tok in _LIQUID_VOL:
            raise UnitError(f"'{activity_unit}' is a liquid volume but this fuel's heating value is per {basis_unit} of gas")
    if a_dim == b_dim:
        return mj_per_basis * a_f / b_f
    liquid = basis_unit in ("gal", "bbl", "l", "liter")
    rho = _density_kg_m3(density, "volume_liquid" if (liquid or a_dim == "volume") and fuel_type not in ("gases", "gas") else "gas")
    if rho is None:
        raise UnitError(f"Activity unit '{activity_unit}' needs the fuel density to use a heating value tabulated per {basis_unit}")
    if a_dim == "mass" and b_dim == "volume":      # kg -> m3 -> basis
        return mj_per_basis * (a_f / rho) / b_f
    if a_dim == "volume" and b_dim == "mass":      # m3 -> kg -> basis
        return mj_per_basis * (a_f * rho) / b_f
    raise UnitError(f"Activity unit '{activity_unit}' cannot be converted to the HHV basis '{basis_unit}'")


def convert_factor_to_kg_per_unit(
    value, factor_unit, activity_unit, hhv=None, fuel_type=None, density=None, hhv_unit=None, hours=None,
    year_hours=None,
):
    """kg of gas per ONE activity unit, through the canonical unit parser (RC-5).

    - "kg/MMBtu" etc.: energy activity converts directly (kWh, MJ, GJ, therm, Btu - BUG-051);
      physical activity uses the heating value in its declared basis (BUG-027).
    - A bare factor unit ("scf", "tonne") is the Manage Data convention "kg per <unit>" (BUG-063).
    - Anything that cannot be interpreted raises UnitError instead of being applied 1:1.
    """
    if value is None:
        return 0.0
    val = float(value)
    if val == 0:
        return 0.0
    f_unit = norm_unit(factor_unit or "")
    a_unit = norm_unit(activity_unit or "")
    if not f_unit:
        raise UnitError("The emission factor has no unit")
    if "/" not in f_unit:
        f_unit = f"kg/{f_unit}"  # Manage Data stores the activity unit only; values are kg per unit
    spec = parse_factor_unit(f_unit)
    energy_den = next((d for d in spec["denominators"] if d[0] == "energy"), None)
    if energy_den is not None:
        a_dim, _ = unit_dimension(a_unit)
        if a_dim == "energy":
            return factor_to_kg_per_activity(val, f_unit, a_unit, hours=hours, year_hours=year_hours)
        mj = hhv_mj_per_unit(hhv, a_unit, fuel_type=fuel_type, density=density, hhv_unit=hhv_unit)
        return factor_to_kg_per_activity(val, f_unit, a_unit, hours=hours, hhv_mj_per_unit=mj, year_hours=year_hours)
    den_dim = spec["denominators"][0][0]
    a_dim, _ = unit_dimension(a_unit)
    if den_dim != a_dim and {den_dim, a_dim} == {"volume", "mass"}:
        rho = _density_kg_m3(density, "volume_liquid")
        if rho is None:
            raise UnitError(f"Factor per {spec['denominators'][0][2]} applied to '{activity_unit}' needs the fuel density")
        # express the activity unit in the factor's dimension, then convert
        if a_dim == "mass":   # kg of fuel per activity unit -> m3
            per_unit = factor_to_kg_per_activity(val, f_unit, "m3", hours=hours, year_hours=year_hours) * (unit_dimension(a_unit)[1] / rho)
        else:                 # m3 of fuel per activity unit -> kg
            per_unit = factor_to_kg_per_activity(val, f_unit, "kg", hours=hours, year_hours=year_hours) * (unit_dimension(a_unit)[1] * rho)
        return per_unit
    return factor_to_kg_per_activity(val, f_unit, a_unit, hours=hours, year_hours=year_hours)


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
        density=None,
        hhv_unit=None,
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
        ] or norm_unit(fuel_unit).replace(" ", "") in GAS_VOLUME_UNITS  # any gas volume (Sm3, Nm3, Mscf, MMcf...)

        # Apply API §4.2.1 thermodynamic normalization to gas fuels if operating T/P supplied
        raw_quantity = fuel_quantity
        # only a volume read at operating conditions is corrected (scf / Sm3 are already standard)
        if is_gas_fuel and is_actual_volume_unit(fuel_unit) and (
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
            ef_co2, ef_unit, fuel_unit, hhv=hhv, fuel_type=fuel_type, density=density, hhv_unit=hhv_unit
        )
        kg_per_unit_ch4 = convert_factor_to_kg_per_unit(
            ef_ch4, ef_unit, fuel_unit, hhv=hhv, fuel_type=fuel_type, density=density, hhv_unit=hhv_unit
        )
        kg_per_unit_n2o = convert_factor_to_kg_per_unit(
            ef_n2o, ef_unit, fuel_unit, hhv=hhv, fuel_type=fuel_type, density=density, hhv_unit=hhv_unit
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
        # only a composition that carries hydrocarbons: the dispatcher always passes c1..c10 (0.0
        # when no analysis was given), and a zero-carbon balance replaced the factor CO2 with 0
        def _pos(v):
            try:
                return float(v) > 0
            except (TypeError, ValueError):
                return False

        if any(_pos(comps.get(f"c{i}")) for i in range(1, 11)):
            raw_c = {f"c{i}": float(comps.get(f"c{i}") or 0.0) for i in range(1, 11)}
            raw_co2 = float(comps.get("co2_comp") or comps.get("co2_mol") or 0.0)
            total_raw = sum(raw_c.values()) + raw_co2

            if total_raw > 1.5:  # Entered as percentages (> 1.0)
                c_fractions = {k: v / 100.0 for k, v in raw_c.items()}
                co2_native_fraction = raw_co2 / 100.0
                total_sum = total_raw / 100.0
            else:
                c_fractions = dict(raw_c)
                co2_native_fraction = raw_co2
                total_sum = total_raw

            # Normalize to 1.0 only if total exceeds 1.0 (remainder is inert gas like N2)
            if total_sum > 1.0001:
                for k in c_fractions:
                    c_fractions[k] /= total_sum
                co2_native_fraction /= total_sum

            c2_plus_total = sum(
                c_fractions[k]
                for k in ["c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"]
            )
            if c2_plus_total > 0.10:
                heavy_hc_warning = True

            # Use passed combustion_efficiency (safely normalized to fraction)
            eta_c = _normalize_efficiency(combustion_efficiency, default=0.995)

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
                # quantity in standard m3; an energy or mass quantity is not a volume
                vol_m3 = gas_volume_m3(raw_quantity, u)

                density_co2 = CONVERSIONS["density_co2"]

                # Combusted CO2
                co2_combusted_vol = vol_m3 * total_carbon_moles * eta_c
                co2_combusted_kg = co2_combusted_vol * density_co2

                # Native CO2
                co2_native_kg = (vol_m3 * co2_native_fraction) * density_co2

                co2_val = (co2_combusted_kg + co2_native_kg) / 1000.0

                # Uncombusted methane slip per stoichiometry & combustion efficiency
                if c_fractions["c1"] > 0:
                    density_ch4 = CONVERSIONS["density_ch4"]
                    ch4_slip_vol = vol_m3 * c_fractions["c1"] * max(0.0, 1.0 - eta_c)
                    ch4_val = (ch4_slip_vol * density_ch4) / 1000.0

        # Resolve tier from factor_source (passed via uncertainties dict sidecar or defaults)
        uncertainties = uncertainties or {}
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
        ef_n2o=None,
        operating_temperature=None,
        temp_unit="C",
        operating_pressure=None,
        press_unit="psig",
        z_factor=1.0,
        gwp_dict=None,
        combustion_efficiency=None,
        destruction_efficiency=None,
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

        # Determine efficiencies based on flare type or custom parameter overrides
        ft = str(flare_type or "elevated").lower().strip().replace("-", "_").replace(" ", "_")
        if ft in ["enclosed", "enclosed_ground", "ground"]:
            default_eta_c = 0.996
            default_eta_d = 0.995  # Higher for enclosed
        elif ft in ["elevated", "steam_assisted", "air_assisted", "unassisted", "flare", "open"]:
            default_eta_c = 0.984
            default_eta_d = 0.98
        elif ft in ["pit", "open_pit", "other", "candle"]:
            default_eta_c = 0.920
            default_eta_d = 0.95
        else:
            default_eta_c = 0.984
            default_eta_d = 0.98

        eta_c = _normalize_efficiency(combustion_efficiency, default=default_eta_c)
        eta_d = _normalize_efficiency(destruction_efficiency, default=default_eta_d)

        # Normalize gas volume if actual temperature/pressure supplied
        unit_norm = str(fuel_unit or "").strip().lower()
        actual_volume = is_actual_volume_unit(unit_norm)
        # standard m3; an energy or mass quantity is refused (it used to be read as m3)
        vol_std = gas_volume_m3(gas_volume, "mscf" if unit_norm == "kscf" else (unit_norm or "m3"))

        if actual_volume and (operating_temperature is not None or operating_pressure is not None):
            vol_std = normalize_gas_volume_to_standard(
                volume=vol_std,
                operating_temp=operating_temperature,
                temp_unit=temp_unit,
                operating_press=operating_pressure,
                press_unit=press_unit,
                z_factor=z_factor,
            )

        # Parse C1-C10 from kwargs, falling back to ch4_fraction for C1 if not provided
        raw_c = {f"c{i}": float(comps.get(f"c{i}") if comps.get(f"c{i}") is not None else (ch4_fraction if i == 1 else 0.0)) for i in range(1, 11)}
        raw_co2 = float(comps.get("co2_comp") or comps.get("co2_mol") or 0.0)
        total_raw = sum(raw_c.values()) + raw_co2

        if total_raw > 1.5:  # Percentage format (> 1.0)
            c_fractions = {k: v / 100.0 for k, v in raw_c.items()}
            co2_native_fraction = raw_co2 / 100.0
            total_sum = total_raw / 100.0
        else:
            c_fractions = dict(raw_c)
            co2_native_fraction = raw_co2
            total_sum = total_raw

        # Normalize sum to 1.0 only if total exceeds 1.0 (remainder is inert gas like N2)
        if total_sum > 1.0001:
            for k in c_fractions:
                c_fractions[k] /= total_sum
            co2_native_fraction /= total_sum

        actual_ch4_fraction = c_fractions["c1"]

        # CH4 Emissions (Undestroyed native methane)
        density_ch4 = CONVERSIONS["density_ch4"]
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
        density_co2 = CONVERSIONS["density_co2"]
        co2_combusted_vol = vol_std * total_carbon_moles_per_mole_gas * eta_c
        co2_combusted_kg = co2_combusted_vol * density_co2

        # Add Native Uncombusted CO2 passing through the flare
        co2_native_vol = vol_std * co2_native_fraction
        co2_native_kg = co2_native_vol * density_co2

        co2_tonnes = (co2_combusted_kg + co2_native_kg) / 1000.0

        # Resolve tier — flaring with full gas composition is Tier 3
        uncertainties = uncertainties or {}
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

        # N2O from flaring (energy or volume basis aware)
        _ef_n2o = float(ef_n2o) if ef_n2o is not None else 0.0001  # API Compendium 2021 Table 5-3
        if _ef_n2o > 0:
            ef_u = str(ef_unit or "kg/mmbtu").lower()
            if "mmbtu" in ef_u or ef_unit is None:
                hhv_val = float(hhv or 1020.0)
                vol_scf = vol_std * CONVERSIONS.get("m3_to_scf", 35.3147)
                flared_mmbtu = (vol_scf * hhv_val) / 1_000_000.0
                n2o_tonnes = (flared_mmbtu * _ef_n2o) / 1000.0
            else:
                n2o_kg = vol_std * convert_factor_to_kg_per_unit(_ef_n2o, ef_unit, "m3", hhv=hhv, fuel_type="gases")
                n2o_tonnes = n2o_kg / 1000.0
        else:
            n2o_tonnes = 0.0

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
