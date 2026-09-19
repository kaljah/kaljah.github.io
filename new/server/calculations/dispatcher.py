import math
from .combustion import CombustionCalculator, FlaringCalculator
from .vented import (
    PneumaticDeviceCalculator,
    LiquidsUnloadingCalculator,
    MudDegassingCalculator,
    TankFlashingCalculator,
    CompletionFlowbackCalculator,
    BlowdownCalculator,
)
from .fugitive import (
    ComponentFugitiveCalculator,
    EquipmentFugitiveCalculator,
    CompressorSealCalculator,
)
from .midstream import AGRCalculator, DehydratorCalculator
from .indirect import IndirectSteamCalculator, CogenAllocationCalculator
from .stoichiometry import StoichiometricCalculator
from .units import CONVERSIONS, calculate_co2e
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
    PROCESS_CATEGORY,
)


class CalculationDispatcher:
    """
    Routes a calculation request to the appropriate API 2021 calculator.
    """

    def __init__(self):
        self.calculators = {
            "stationary_combustion": CombustionCalculator(),
            "combustion": CombustionCalculator(),
            "mobile_combustion": CombustionCalculator(),
            "mobile": CombustionCalculator(),
            "flaring": FlaringCalculator(),
            "flare": FlaringCalculator(),
            "drilling": MudDegassingCalculator(),
            "mud_degassing": MudDegassingCalculator(),
            "completions": CompletionFlowbackCalculator(),
            "completion_flowback": CompletionFlowbackCalculator(),
            "liquids_unloading": LiquidsUnloadingCalculator(),
            "unloading": LiquidsUnloadingCalculator(),
            "tank": TankFlashingCalculator(),
            "tank_flashing": TankFlashingCalculator(),
            "tank_working": TankFlashingCalculator(),
            "tank_breathing": TankFlashingCalculator(),
            "storage_tanks": TankFlashingCalculator(),
            "pneumatic_devices": PneumaticDeviceCalculator(),
            "pneumatic_device": PneumaticDeviceCalculator(),
            "pneumatic": PneumaticDeviceCalculator(),
            "fugitive_component": ComponentFugitiveCalculator(),
            "component_fugitive": ComponentFugitiveCalculator(),
            "equipment_fugitive": EquipmentFugitiveCalculator(),
            "wellhead_fugitive": EquipmentFugitiveCalculator(),
            "separator_fugitive": EquipmentFugitiveCalculator(),
            "gathering_boosting": EquipmentFugitiveCalculator(),
            "gas_processing": EquipmentFugitiveCalculator(),
            "transmission_storage": EquipmentFugitiveCalculator(),
            "refinery_fugitive": EquipmentFugitiveCalculator(),
            "distribution_fugitive": EquipmentFugitiveCalculator(),
            "lng_operations": EquipmentFugitiveCalculator(),
            "compressor_fugitive": CompressorSealCalculator(),
            "compressor_seal": CompressorSealCalculator(),
            "fugitive": EquipmentFugitiveCalculator(),
            "agr": AGRCalculator(),
            "acid_gas_removal": AGRCalculator(),
            "dehydrator": DehydratorCalculator(),
            "indirect_steam": IndirectSteamCalculator(),
            "cogen_allocation": CogenAllocationCalculator(),
            "cogen": CogenAllocationCalculator(),
            "stoichiometry": StoichiometricCalculator(),
            "chemical_production": StoichiometricCalculator(),
            "nitric_acid_production": StoichiometricCalculator(),
            "adipic_acid_production": StoichiometricCalculator(),
            "venting": BlowdownCalculator(),
            "blowdown": BlowdownCalculator(),
        }

    def _require(self, key, inputs, description):
        val = inputs.get(key)
        if val in [None, "", "-"]:
            from flask import current_app, has_app_context

            if has_app_context():
                current_app.logger.warning(
                    f"Missing required field: {key} ({description})"
                )
            else:
                import logging

                logging.warning(f"Missing required field: {key} ({description})")
            raise ValueError(f"Missing required field: {key} ({description})")
        return float(val)

    def _normalize_volume(self, value, unit, target_unit="m3"):
        """Normalizes a volume value to the specified target unit."""
        u = str(unit or "m3").lower()
        if target_unit == "m3":
            if u in ["scf", "cf", "ft3"]:
                return value * CONVERSIONS["scf_to_m3"]
            if u in ["mcf", "mscf"]:
                return value * 1000.0 * CONVERSIONS["scf_to_m3"]
            if u == "mmscf":
                return value * 1000000.0 * CONVERSIONS["scf_to_m3"]
            if u in ["bbl", "barrel", "barrels"]:
                return value * CONVERSIONS["bbl_to_m3"]
            if u in ["gal", "gallon", "gallons"]:
                return value * CONVERSIONS["gal_to_m3"]
            if u in ["l", "liter", "liters"]:
                return value * CONVERSIONS["liter_to_m3"]
            return value  # Default m3
        elif target_unit == "mmscf":
            if u in ["scf", "cf", "ft3"]:
                return value / 1_000_000.0
            if u in ["mcf", "mscf"]:
                return value / 1000.0
            if u == "m3":
                return (value / CONVERSIONS["scf_to_m3"]) / 1_000_000.0
            if u in ["bbl", "barrel", "barrels"]:
                return (
                    value * CONVERSIONS["bbl_to_m3"] / CONVERSIONS["scf_to_m3"]
                ) / 1_000_000.0
            return value  # Default mmscf
        return value

    def _require_float(self, flat_inputs, keys, desc):
        """Strictly extracts a required float parameter without falling back to defaults."""
        if isinstance(keys, str):
            keys = [keys]
        for k in keys:
            val = flat_inputs.get(k)
            if val not in [None, "", "-"]:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid numeric value for '{k}' ({desc}): {val}")
        raise ValueError(
            f"Missing required parameter for Tier 3 specific calculation: '{keys[0]}' ({desc})"
        )

    def _parse_fraction_value(self, val, key_name="", is_percent=False):
        """Cleanly parses a percentage (0-100) or fraction (0-1) into a 0.0 - 1.0 ratio."""
        if val in [None, "", "-"]:
            return None
        s = str(val).strip()
        has_percent_sign = "%" in s
        clean_str = s.replace("%", "").strip()
        try:
            num = float(clean_str)
        except (ValueError, TypeError):
            return None

        key_lower = str(key_name).lower()
        is_pct_key = "pct" in key_lower or "percent" in key_lower
        if is_percent or has_percent_sign or is_pct_key:
            return max(0.0, num / 100.0)
        if num > 1.0:
            return max(0.0, num / 100.0)
        return max(0.0, num)

    def _require_fraction(self, flat_inputs, keys, desc, is_percent=False):
        """Extracts a percentage or fraction strictly and normalizes to 0.0 - 1.0."""
        if isinstance(keys, str):
            keys = [keys]
        for k in keys:
            val = flat_inputs.get(k)
            if val not in [None, "", "-"]:
                res = self._parse_fraction_value(val, key_name=k, is_percent=is_percent)
                if res is not None:
                    return res
                raise ValueError(f"Invalid numeric fraction/percentage for '{k}' ({desc}): {val}")
        raise ValueError(
            f"Missing required parameter for Tier 3 specific calculation: '{keys[0]}' ({desc})"
        )

    def _optional_fraction(self, flat_inputs, keys, default=0.0, is_percent=False):
        """Extracts an optional percentage or fraction normalized to 0.0 - 1.0."""
        if isinstance(keys, str):
            keys = [keys]
        for k in keys:
            val = flat_inputs.get(k)
            if val not in [None, "", "-"]:
                res = self._parse_fraction_value(val, key_name=k, is_percent=is_percent)
                if res is not None:
                    return res
        return default

    def dispatch(
        self,
        process_type,
        inputs,
        emission_factors,
        uncertainties,
        gwp_dict=None,
        gwp_standard=None,
    ):
        """
        Executes the calculation for the given process type.
        - Tier 1 (default / custom): Requires only activity data (quantity & unit) and uses catalog emission factors.
        - Tier 3 (specific): Requires all physical engineering parameters with zero silent defaults.
        """
        from .constants import get_active_gwp

        # Support callers passing gwp_dict as 4th positional argument
        if gwp_dict is None and isinstance(uncertainties, dict) and "CH4" in uncertainties:
            gwp_dict = uncertainties
            uncertainties = {}

        if gwp_dict is None:
            gwp_dict = get_active_gwp(standard=gwp_standard)
        calculator = self.calculators.get(process_type)

        # Extract process-specific inputs if nested
        calc_inputs = inputs.get("calc_inputs", {}).get(process_type, {})
        flat_inputs = {**inputs, **calc_inputs}

        factor_source = flat_inputs.get("factor_source", "default")

        if not calculator:
            return self._generic_calculation(
                flat_inputs,
                emission_factors,
                uncertainties,
                process_type,
                gwp_dict=gwp_dict,
            )

        # Inject tier info into uncertainties dict so calculators can call resolve_tier()
        uncertainties = dict(uncertainties)
        uncertainties.setdefault("_factor_source", factor_source)

        # Inject dynamic uncertainty overrides for Tier 3 calculations
        if flat_inputs.get("meter_uncertainty_pct") not in [None, "", "-"]:
            try:
                uncertainties["_activity_uncertainty"] = (
                    float(flat_inputs["meter_uncertainty_pct"]) / 100.0
                )
            except ValueError:
                pass

        if flat_inputs.get("gc_uncertainty_pct") not in [None, "", "-"]:
            try:
                uncertainties["_composition_uncertainty"] = (
                    float(flat_inputs["gc_uncertainty_pct"]) / 100.0
                )
            except ValueError:
                pass

        user_unc = flat_inputs.get("user_uncertainty")
        if isinstance(user_unc, dict):
            for g in ["co2", "ch4", "n2o"]:
                if user_unc.get(g) not in [None, "", "-"]:
                    try:
                        uncertainties[g] = float(user_unc[g]) / 100.0
                    except ValueError:
                        pass

        # Validate required gas composition for specific factor sources
        if process_type in [
            "stationary_combustion",
            "combustion",
            "mobile_combustion",
            "mobile",
            "flaring",
            "flare",
            "separation",
        ]:
            if factor_source == "specific" and (
                flat_inputs.get("specific_factors")
                or flat_inputs.get("specificFactors")
            ):
                if flat_inputs.get("c1") in [None, "", "-"]:
                    raise ValueError(
                        "Missing required gas composition (C1 mole fraction) for Tier 3 specific calculation"
                    )

        # Extract common quantity
        raw_qty = flat_inputs.get("amount") or flat_inputs.get("quantity") or 0
        try:
            quantity = float(raw_qty)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid numeric quantity/amount: {raw_qty}")
        if math.isnan(quantity) or math.isinf(quantity):
            raise ValueError(f"Quantity/Amount cannot be NaN or Infinite: {quantity}")
        if quantity < 0:
            raise ValueError(f"Quantity/Amount cannot be negative: {quantity}")
        unit = str(flat_inputs.get("unit", "m3")).lower()

        # =========================================================================
        # TIER 1 / TIER 2 ROUTING: default or custom factor sources
        # Only requires standard activity data; never fails on missing engineering inputs.
        # =========================================================================
        if factor_source in ["default", "custom"]:
            if process_type in [
                "stationary_combustion",
                "combustion",
                "mobile_combustion",
                "mobile",
            ]:
                hhv_val = flat_inputs.get("hhv") or emission_factors.get("hhv")
                if hhv_val:
                    return calculator.calculate(
                        fuel_quantity=quantity,
                        ef_co2=emission_factors.get("co2", 0),
                        ef_ch4=emission_factors.get("ch4", 0),
                        ef_n2o=emission_factors.get("n2o", 0),
                        uncertainties=uncertainties,
                        hhv=float(hhv_val),
                        ef_unit=flat_inputs.get(
                            "ef_unit", emission_factors.get("unit", "kg/unit")
                        ),
                        fuel_unit=unit,
                        fuel_type=flat_inputs.get("fuel_type")
                        or emission_factors.get("fuel_type", "unknown"),
                        combustion_efficiency=float(
                            flat_inputs.get("combustion_efficiency") or 0.995
                        ),
                        operating_temperature=flat_inputs.get("operating_temperature")
                        or flat_inputs.get("temperature"),
                        temp_unit=flat_inputs.get("temp_unit", "C"),
                        operating_pressure=flat_inputs.get("operating_pressure")
                        or flat_inputs.get("pressure"),
                        press_unit=flat_inputs.get("press_unit", "psig"),
                        z_factor=flat_inputs.get("z_factor", 1.0),
                        gwp_dict=gwp_dict,
                    )
            # Default / Custom for all processes uses standard catalog multiplication
            return self._generic_calculation(
                flat_inputs,
                emission_factors,
                uncertainties,
                process_type,
                gwp_dict=gwp_dict,
            )

        # =========================================================================
        # TIER 3 ROUTING: factor_source == 'specific' (Engineering Mode)
        # Strict validation with zero silent defaults.
        # =========================================================================
        try:
            if process_type in [
                "stationary_combustion",
                "combustion",
                "mobile_combustion",
                "mobile",
            ]:
                hhv_val = self._require_float(
                    flat_inputs, ["hhv"], "Higher Heating Value (HHV)"
                )
                comb_eff = self._require_float(
                    flat_inputs,
                    [
                        "combustion_efficiency",
                        "combustion_eff",
                        "combustioneff",
                        "comb_eff",
                        "efficiency",
                    ],
                    "Combustion Efficiency (%)",
                )
                if comb_eff > 1.0:
                    comb_eff_frac = comb_eff / 100.0
                else:
                    comb_eff_frac = comb_eff

                def safe_frac(key):
                    val = flat_inputs.get(key)
                    if val in [None, "", "-"]:
                        return 0.0
                    try:
                        num = float(val)
                        return num / 100.0 if num > 1.0 else num
                    except (ValueError, TypeError):
                        return 0.0

                comps = {
                    "c1": safe_frac("c1"),
                    "c2": safe_frac("c2"),
                    "c3": safe_frac("c3"),
                    "c4": safe_frac("c4"),
                    "c5": safe_frac("c5"),
                    "c6": safe_frac("c6"),
                    "c7": safe_frac("c7"),
                    "c8": safe_frac("c8"),
                    "c9": safe_frac("c9"),
                    "c10": safe_frac("c10"),
                    "co2_comp": safe_frac("co2_mol") or safe_frac("co2_content"),
                    "n2_comp": safe_frac("n2") or safe_frac("n2_mol"),
                }

                return calculator.calculate(
                    fuel_quantity=quantity,
                    ef_co2=emission_factors.get("co2", 0),
                    ef_ch4=emission_factors.get("ch4", 0),
                    ef_n2o=emission_factors.get("n2o", 0),
                    uncertainties=uncertainties,
                    hhv=hhv_val,
                    ef_unit=flat_inputs.get(
                        "ef_unit", emission_factors.get("unit", "kg/unit")
                    ),
                    fuel_unit=unit,
                    fuel_type=flat_inputs.get("fuel_type")
                    or emission_factors.get("fuel_type", "unknown"),
                    combustion_efficiency=comb_eff_frac,
                    operating_temperature=flat_inputs.get("operating_temperature")
                    or flat_inputs.get("temperature"),
                    temp_unit=flat_inputs.get("temp_unit", "C"),
                    operating_pressure=flat_inputs.get("operating_pressure")
                    or flat_inputs.get("pressure"),
                    press_unit=flat_inputs.get("press_unit", "psig"),
                    z_factor=flat_inputs.get("z_factor", 1.0),
                    gwp_dict=gwp_dict,
                    **comps,
                )

            elif process_type == "flaring":
                vol_raw = self._require_float(
                    flat_inputs,
                    ["amount", "quantity", "gas_volume"],
                    "flared gas volume",
                )
                vol_m3 = self._normalize_volume(vol_raw, unit, "m3")
                ch4_content = self._require_fraction(
                    flat_inputs,
                    ["c1", "ch4_content", "flare_ch4_content"],
                    "flared gas CH4 content %",
                )
                flare_type = flat_inputs.get("flare_type", "elevated")
                hhv_val = flat_inputs.get("hhv") or emission_factors.get("hhv")

                def safe_frac(key):
                    val = flat_inputs.get(key)
                    if val in [None, "", "-"]:
                        return 0.0
                    try:
                        num = float(val)
                        return num / 100.0 if num > 1.0 else num
                    except (ValueError, TypeError):
                        return 0.0

                comps = {
                    "c1": ch4_content,
                    "c2": safe_frac("c2"),
                    "c3": safe_frac("c3"),
                    "c4": safe_frac("c4"),
                    "c5": safe_frac("c5"),
                    "c6": safe_frac("c6"),
                    "c7": safe_frac("c7"),
                    "c8": safe_frac("c8"),
                    "c9": safe_frac("c9"),
                    "c10": safe_frac("c10"),
                    "co2_comp": safe_frac("co2_mol") or safe_frac("co2_content"),
                    "n2_comp": safe_frac("n2") or safe_frac("n2_mol"),
                }

                return calculator.calculate(
                    gas_volume=vol_m3,
                    ch4_fraction=ch4_content,
                    flare_type=flare_type,
                    uncertainties=uncertainties,
                    hhv=float(hhv_val) if hhv_val else None,
                    ef_unit=flat_inputs.get(
                        "ef_unit", emission_factors.get("unit", "kg/unit")
                    ),
                    fuel_unit="m3",
                    fuel_type=flat_inputs.get("fuel_type"),
                    ef_n2o=emission_factors.get("n2o", 0.0),
                    operating_temperature=flat_inputs.get("operating_temperature")
                    or flat_inputs.get("temperature"),
                    temp_unit=flat_inputs.get("temp_unit", "C"),
                    operating_pressure=flat_inputs.get("operating_pressure")
                    or flat_inputs.get("pressure"),
                    press_unit=flat_inputs.get("press_unit", "psig"),
                    z_factor=flat_inputs.get("z_factor", 1.0),
                    gwp_dict=gwp_dict,
                    **comps,
                )

            elif process_type in ["drilling", "mud_degassing"]:
                mud_vol = self._require_float(
                    flat_inputs,
                    ["mud_vol", "mud_volume", "amount", "quantity"],
                    "drilling mud volume",
                )
                vol_m3 = self._normalize_volume(
                    mud_vol, flat_inputs.get("mud_unit") or unit, "m3"
                )
                mud_type = flat_inputs.get("mud_type") or "water_based"
                return calculator.calculate(
                    mud_volume=vol_m3,
                    mud_type=mud_type,
                    uncertainties=uncertainties,
                    ef_ch4=emission_factors.get("ch4", 0),
                    gwp_dict=gwp_dict,
                )

            elif process_type == "completions":
                comp_method = flat_inputs.get("comp_method") or flat_inputs.get(
                    "calculation_method", "metered_volume"
                )

                vol_m3 = 0.0
                if comp_method == "metered_volume" or (
                    not flat_inputs.get("comp_rate")
                    and not flat_inputs.get("comp_liquid_bbl")
                ):
                    vol_raw = self._require_float(
                        flat_inputs,
                        ["amount", "quantity", "flowback_volume", "comp_volume"],
                        "flowback volume",
                    )
                    vol_m3 = self._normalize_volume(vol_raw, unit, "m3")

                ch4_content = self._require_fraction(
                    flat_inputs,
                    ["ch4_content", "c1", "comp_ch4_content"],
                    "gas CH4 content %",
                )
                co2_content = self._optional_fraction(
                    flat_inputs, ["co2_content", "co2_mol"], 0.0
                )
                flare_eff = self._optional_fraction(
                    flat_inputs, ["comp_flare_eff", "control_efficiency"], 0.0
                )

                ef_co2 = emission_factors.get("co2")
                ef_ch4 = emission_factors.get("ch4")
                ef_n2o = emission_factors.get("n2o")

                return calculator.calculate(
                    flowback_volume=vol_m3,
                    ch4_content=ch4_content,
                    control_efficiency=flare_eff,
                    uncertainties=uncertainties,
                    co2_content=co2_content,
                    ef_co2=ef_co2,
                    ef_ch4=ef_ch4,
                    ef_n2o=ef_n2o,
                    calculation_method=comp_method,
                    flowback_rate=flat_inputs.get("comp_rate"),
                    flowback_duration_hours=flat_inputs.get("comp_duration"),
                    liquid_flowback_bbl=flat_inputs.get("comp_liquid_bbl")
                    or flat_inputs.get("liquid_flowback_bbl"),
                    gas_oil_ratio=flat_inputs.get("comp_gor")
                    or flat_inputs.get("gas_oil_ratio"),
                    choke_size_in=flat_inputs.get("comp_choke_size"),
                    well_head_pressure=flat_inputs.get("comp_whp"),
                    hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                    gwp_dict=gwp_dict,
                )

            elif process_type in ["liquids_unloading", "unloading"]:
                depth = self._require_float(
                    flat_inputs, ["unload_depth", "well_depth"], "well depth (ft)"
                )
                diam = self._require_float(
                    flat_inputs, ["unload_diam", "diameter"], "casing diameter (in)"
                )
                press = self._require_float(
                    flat_inputs,
                    ["unload_press", "pressure"],
                    "shut-in surface pressure (psig)",
                )
                events = int(
                    self._require_float(
                        flat_inputs,
                        ["unload_freq", "unload_events", "events", "amount"],
                        "annual unloading event count",
                    )
                )
                ch4_content = self._require_fraction(
                    flat_inputs,
                    ["ch4_content", "c1", "unload_ch4_content"],
                    "gas CH4 content %",
                )
                co2_content = self._optional_fraction(
                    flat_inputs, ["co2_content", "co2_mol"], 0.0
                )
                flare_eff = self._optional_fraction(
                    flat_inputs, ["unload_flare_eff", "control_efficiency"], 0.0
                )

                ef_co2 = emission_factors.get("co2")
                ef_ch4 = emission_factors.get("ch4")
                ef_n2o = emission_factors.get("n2o")

                depth_unit = (
                    flat_inputs.get("unload_depth_unit")
                    or flat_inputs.get("depth_unit", "ft")
                )
                diam_unit = (
                    flat_inputs.get("unload_diam_unit")
                    or flat_inputs.get("diameter_unit", "in")
                )
                press_unit = (
                    flat_inputs.get("unload_press_unit")
                    or flat_inputs.get("press_unit", "psig")
                )

                return calculator.calculate(
                    well_depth=depth,
                    diameter=diam,
                    pressure=press,
                    ch4_content=ch4_content,
                    events=events,
                    uncertainties=uncertainties,
                    co2_content=co2_content,
                    control_efficiency=flare_eff,
                    ef_co2=ef_co2,
                    ef_ch4=ef_ch4,
                    ef_n2o=ef_n2o,
                    operating_temperature=flat_inputs.get("unload_temp")
                    or flat_inputs.get("operating_temperature", 60.0),
                    temp_unit=flat_inputs.get("temp_unit", "F"),
                    depth_unit=depth_unit,
                    diameter_unit=diam_unit,
                    press_unit=press_unit,
                    hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                    gwp_dict=gwp_dict,
                )

            elif process_type in ["venting", "blowdown"]:
                raw_vol = self._require_float(
                    flat_inputs,
                    ["blowdown_volume", "amount", "quantity"],
                    "vessel physical volume",
                )
                raw_unit = flat_inputs.get("blowdown_unit") or unit or "m3"
                vol_m3 = self._normalize_volume(raw_vol, raw_unit, "m3")
                press = self._require_float(
                    flat_inputs,
                    ["blowdown_pressure", "pressure"],
                    "vessel pressure before blowdown (psig)",
                )
                events = int(
                    self._require_float(
                        flat_inputs,
                        ["blowdown_events", "events"],
                        "number of blowdown events",
                    )
                )
                ch4_content = self._require_fraction(
                    flat_inputs, ["ch4_content", "c1"], "gas CH4 content %"
                )
                co2_content = self._optional_fraction(
                    flat_inputs, ["co2_content", "co2_mol"], 0.0
                )
                flare_eff = self._optional_fraction(
                    flat_inputs, ["control_efficiency"], 0.0
                )

                ef_co2 = emission_factors.get("co2")
                ef_ch4 = emission_factors.get("ch4")
                ef_n2o = emission_factors.get("n2o")

                return calculator.calculate(
                    blowdown_volume=vol_m3,
                    pressure=press,
                    events=events,
                    ch4_content=ch4_content,
                    uncertainties=uncertainties,
                    co2_content=co2_content,
                    control_efficiency=flare_eff,
                    ef_co2=ef_co2,
                    ef_ch4=ef_ch4,
                    ef_n2o=ef_n2o,
                    operating_temperature=flat_inputs.get("blowdown_temp")
                    or flat_inputs.get("operating_temperature", 60.0),
                    temp_unit=flat_inputs.get("temp_unit")
                    or flat_inputs.get("blowdown_temp_unit", "F"),
                    press_unit=flat_inputs.get("press_unit")
                    or flat_inputs.get("blowdown_press_unit", "psig"),
                    z_factor=flat_inputs.get("z_factor", 1.0),
                    hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                    gwp_dict=gwp_dict,
                )

            elif process_type in [
                "tank",
                "tank_flashing",
                "storage_tanks",
                "tank_working",
                "tank_breathing",
            ]:
                raw_throughput = self._require_float(
                    flat_inputs,
                    ["amount", "quantity", "throughput"],
                    "tank liquid throughput",
                )
                t_unit = str(
                    flat_inputs.get("tank_unit")
                    or flat_inputs.get("throughput_unit")
                    or unit
                    or "bbl"
                ).lower()
                if t_unit in ["m3", "m³", "cubic_meters"]:
                    throughput_bbl = raw_throughput * CONVERSIONS.get(
                        "m3_to_bbl", 6.28981
                    )
                elif t_unit in ["gal", "gallon", "gallons"]:
                    throughput_bbl = raw_throughput / 42.0
                elif t_unit in ["l", "liter", "liters"]:
                    throughput_bbl = (raw_throughput / 1000.0) * CONVERSIONS.get(
                        "m3_to_bbl", 6.28981
                    )
                else:
                    throughput_bbl = raw_throughput  # bbl

                gor = self._require_float(
                    flat_inputs, ["tank_gor", "gor"], "Gas-Oil Ratio (GOR scf/bbl)"
                )
                ch4_content = self._require_fraction(
                    flat_inputs,
                    ["tank_ch4_content", "ch4_content", "c1"],
                    "tank flash gas CH4 content %",
                )
                tank_eff = self._optional_fraction(
                    flat_inputs, ["tank_control_eff", "control_efficiency"], 0.0
                )
                co2_content = self._optional_fraction(
                    flat_inputs, ["tank_co2_content", "co2_content", "co2_mol"], 0.0
                )

                ef_ch4_val = emission_factors.get("ch4", 0)
                if not ef_ch4_val and gor == 0:
                    from flask import current_app, has_app_context

                    if has_app_context():
                        current_app.logger.warning(
                            "[Dispatcher] Storage tank calculation: both EF CH4 and GOR are zero."
                        )

                return calculator.calculate(
                    throughput=throughput_bbl,
                    gas_oil_ratio=gor,
                    ch4_content=ch4_content,
                    control_efficiency=tank_eff,
                    uncertainties=uncertainties,
                    process_type="tank_flashing",
                    ef_ch4=ef_ch4_val,
                    co2_content=co2_content,
                    hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                    gwp_dict=gwp_dict,
                )

            elif process_type in ["pneumatic_devices", "pneumatic_device", "pneumatic"]:
                count = self._require_float(
                    flat_inputs,
                    ["pneu_count", "device_count", "count", "amount", "quantity"],
                    "device count",
                )
                hours = self._require_float(
                    flat_inputs,
                    ["pneu_hours", "hours_operating", "hours", "operating_hours"],
                    "annual operating hours",
                )
                bleed_rate = self._require_float(
                    flat_inputs,
                    ["pneu_bleed_rate", "bleed_rate"],
                    "measured bleed rate",
                )
                bleed_unit = flat_inputs.get("pneu_bleed_unit", "scf")
                if bleed_unit == "m3":
                    bleed_rate *= 35.3147  # convert m3/hr to scf/hr
                ch4_content = self._require_fraction(
                    flat_inputs,
                    ["pneu_ch4_content", "ch4_content", "c1", "gas_content"],
                    "gas CH4 content %",
                )

                actuations = flat_inputs.get("pneu_actuations") or flat_inputs.get("actuations")
                actuations_val = float(actuations) if actuations not in [None, "", "-"] else None

                return calculator.calculate(
                    count=count,
                    hours=hours,
                    bleed_rate=bleed_rate,
                    ch4_content=ch4_content,
                    uncertainties=uncertainties,
                    actuations=actuations_val,
                    gwp_dict=gwp_dict,
                )

            elif process_type == "fugitive":
                fugitive_method = flat_inputs.get("fugitive_method", "average")
                if fugitive_method == "screening":
                    ppm = self._require_float(
                        flat_inputs,
                        ["fugitive_ppm", "ppm", "screening_ppm"],
                        "screening concentration (PPM)",
                    )
                    comp_count = self._require_float(
                        flat_inputs,
                        ["amount", "quantity", "component_count", "count", "equipment_count"],
                        "component count",
                    )
                    ef_base = float(
                        emission_factors.get("ch4")
                        or emission_factors.get("factor")
                        or 0.0
                    )
                    ef_unit = str(emission_factors.get("unit") or flat_inputs.get("unit") or "").lower()
                    is_annual = "yr" in ef_unit or "year" in ef_unit
                    is_tonne = "tonne" in ef_unit or "mt" in ef_unit
                    is_methane = any(x in ef_unit for x in ["ch4", "methane"])

                    hours = float(
                        flat_inputs.get("hours")
                        or flat_inputs.get("hours_operating")
                        or 8760.0
                    )
                    ch4_fraction = self._optional_fraction(
                        flat_inputs, ["ch4_fraction", "ch4_content", "c1"], 1.0
                    )
                    screening_mult = 2.5 if ppm >= 10000 else 1.0

                    if is_annual:
                        annual_hours_ratio = hours / 8760.0 if hours != 8760.0 else 1.0
                        ch4_raw = comp_count * ef_base * screening_mult * annual_hours_ratio
                    else:
                        ch4_raw = comp_count * ef_base * screening_mult * hours

                    if not is_methane:
                        ch4_raw *= ch4_fraction

                    ch4_tonnes = ch4_raw if is_tonne else (ch4_raw / 1000.0)

                    def _wrap_unc(val, gas):
                        u = propagate_uncertainty(
                            val,
                            ef_uncertainty=resolve_ef_uncertainty(
                                "fugitive",
                                gas,
                                resolve_tier(
                                    flat_inputs.get("factor_source", "default")
                                ),
                                uncertainties.get(gas),
                            ),
                            tier=resolve_tier(
                                flat_inputs.get("factor_source", "default")
                            ),
                            process_category="fugitive",
                            gas=gas,
                        )
                        return u

                    return {
                        "results": {
                            "co2": _wrap_unc(0, "co2"),
                            "ch4": _wrap_unc(ch4_tonnes, "ch4"),
                            "n2o": _wrap_unc(0, "n2o"),
                        },
                        "total_co2e": calculate_co2e(
                            0, ch4_tonnes, 0, gwp_dict=gwp_dict
                        ),
                        "method": "api2021_fugitive_screening",
                    }
                else:
                    return self._generic_calculation(
                        flat_inputs,
                        emission_factors,
                        uncertainties,
                        process_type,
                        gwp_dict=gwp_dict,
                    )

            elif process_type in ["compressor_seal", "compressor_fugitive"]:
                count = self._require_float(
                    flat_inputs,
                    ["compressor_count", "count", "amount", "quantity"],
                    "compressor count",
                )
                raw_seal = str(
                    flat_inputs.get("seal_type")
                    or flat_inputs.get("comp_mode")
                    or flat_inputs.get("compressor_type")
                    or "reciprocating"
                ).lower().strip()
                if "dry" in raw_seal:
                    seal_type = "centrifugal_dry"
                elif "wet" in raw_seal:
                    seal_type = "centrifugal_wet"
                else:
                    seal_type = "reciprocating"

                return calculator.calculate(
                    compressor_count=count,
                    seal_type=seal_type,
                    uncertainties=uncertainties,
                    gwp_dict=gwp_dict,
                )

            elif process_type in ["fugitive_component", "component_fugitive"]:
                comps_dict = flat_inputs.get("component_counts")
                if not comps_dict and (
                    flat_inputs.get("component_type")
                    or flat_inputs.get("count")
                    or flat_inputs.get("amount")
                    or flat_inputs.get("quantity")
                ):
                    c_type = str(flat_inputs.get("component_type") or "valves")
                    c_count = float(
                        flat_inputs.get("count")
                        or flat_inputs.get("amount")
                        or flat_inputs.get("quantity")
                        or 0
                    )
                    c_ef = float(
                        emission_factors.get("ch4")
                        or emission_factors.get("factor")
                        or flat_inputs.get("ef")
                        or 0.0
                    )
                    c_unit = str(
                        emission_factors.get("unit")
                        or flat_inputs.get("unit")
                        or "kg/hr"
                    )
                    comps_dict = {
                        c_type: {"count": c_count, "ef": c_ef, "unit": c_unit}
                    }

                ch4_content = self._optional_fraction(
                    flat_inputs, ["ch4_content", "ch4_fraction", "c1"], 0.85
                )
                return calculator.calculate(
                    component_counts=comps_dict or {},
                    ch4_content=ch4_content,
                    uncertainties=uncertainties,
                    gwp_dict=gwp_dict,
                )

            elif process_type in [
                "equipment_fugitive",
                "wellhead_fugitive",
                "separator_fugitive",
                "gathering_boosting",
                "gas_processing",
                "transmission_storage",
                "refinery_fugitive",
                "distribution_fugitive",
                "lng_operations",
            ]:
                count = self._require_float(
                    flat_inputs,
                    ["equipment_count", "well_count", "separator_count", "count", "amount", "quantity"],
                    "equipment count",
                )
                ef = float(
                    emission_factors.get("ch4")
                    or emission_factors.get("factor")
                    or flat_inputs.get("ef")
                    or 0.0
                )
                ch4_content = self._optional_fraction(
                    flat_inputs, ["ch4_content", "ch4_fraction", "c1"], 0.85
                )
                ef_unit = str(emission_factors.get("unit") or flat_inputs.get("unit") or "kg/hr")
                return calculator.calculate(
                    equipment_count=count,
                    ef=ef,
                    ch4_content=ch4_content,
                    uncertainties=uncertainties,
                    ef_unit=ef_unit,
                    gwp_dict=gwp_dict,
                )

            elif process_type in ["agr", "acid_gas_removal"]:
                agr_vol = self._require_float(
                    flat_inputs,
                    ["agr_throughput", "gas_throughput", "amount", "quantity", "throughput"],
                    "gas throughput",
                )
                vol_mmscf = self._normalize_volume(
                    agr_vol, flat_inputs.get("agr_unit") or unit, "mmscf"
                )
                raw_co2_in = self._require_float(
                    flat_inputs, ["agr_co2_in", "co2_in", "co2_content"], "inlet CO2 mole %"
                )
                raw_co2_out_val = flat_inputs.get("agr_co2_out") or flat_inputs.get("co2_out")
                raw_co2_out = float(raw_co2_out_val) if raw_co2_out_val not in [None, "", "-"] else 0.001

                if raw_co2_in > 1.0 or raw_co2_out > 1.0:
                    co2_in = raw_co2_in / 100.0 if raw_co2_in > 1.0 else raw_co2_in
                    co2_out = (raw_co2_out / 100.0) if raw_co2_in > 1.0 else (raw_co2_out / 100.0 if raw_co2_out > 1.0 else raw_co2_out)
                else:
                    co2_in = raw_co2_in
                    co2_out = raw_co2_out

                if co2_out > co2_in:
                    co2_out = co2_in

                ch4_in = self._optional_fraction(
                    flat_inputs, ["agr_ch4_in", "ch4_in", "c1", "ch4_mole_pct"], 0.85
                )
                ch4_slip = self._optional_fraction(
                    flat_inputs,
                    ["agr_ch4_slip", "ch4_slip_fraction", "methane_slip_factor"],
                    0.001,
                )
                ctrl_eff = self._optional_fraction(
                    flat_inputs, ["agr_control_eff", "control_efficiency", "removal_efficiency"], 0.0
                )
                ctrl_type = (
                    flat_inputs.get("agr_control_type")
                    or flat_inputs.get("acid_gas_control_type")
                    or flat_inputs.get("control_type", "vent")
                )

                return calculator.calculate(
                    throughput=vol_mmscf,
                    co2_in=co2_in,
                    co2_out=co2_out,
                    uncertainties=uncertainties,
                    ch4_in=ch4_in,
                    ch4_slip_fraction=ch4_slip,
                    acid_gas_control_eff=ctrl_eff,
                    acid_gas_control_type=ctrl_type,
                    gwp_dict=gwp_dict,
                )

            elif process_type in ["cogen_allocation", "cogen"]:
                tot_em = self._require_float(
                    flat_inputs,
                    ["total_emissions", "amount", "quantity"],
                    "total emissions",
                )
                heat_out = self._require_float(
                    flat_inputs, ["heat_output"], "heat output"
                )
                power_out = self._require_float(
                    flat_inputs, ["power_output"], "power output"
                )
                c_method = flat_inputs.get("cogen_method") or flat_inputs.get(
                    "method", "wri_efficiency"
                )
                return calculator.calculate(
                    total_emissions=tot_em,
                    heat_output=heat_out,
                    power_output=power_out,
                    method=c_method,
                    uncertainties=uncertainties,
                )

            elif process_type in [
                "stoichiometry",
                "chemical_production",
                "nitric_acid_production",
                "adipic_acid_production",
            ]:
                raw_amt = self._require_float(
                    flat_inputs,
                    ["quantity", "amount", "fuel_mass", "production_amount"],
                    "mass / production amount",
                )
                carbon_content = self._optional_fraction(
                    flat_inputs,
                    ["carbon_content", "c_content"],
                    0.85,
                )

                return calculator.calculate(
                    fuel_mass=raw_amt,
                    carbon_content=carbon_content,
                    uncertainties=uncertainties,
                    mass_unit=unit,
                    gwp_dict=gwp_dict,
                )

            elif process_type == "dehydrator":
                throughput = (
                    flat_inputs.get("dehy_throughput")
                    or flat_inputs.get("amount")
                    or flat_inputs.get("quantity")
                )
                pump_rate = flat_inputs.get("dehy_pump_rate") or flat_inputs.get(
                    "pump_rate"
                )
                pump_unit = flat_inputs.get("dehy_pump_unit", "gph")
                hours = float(
                    flat_inputs.get("dehy_hours")
                    or flat_inputs.get("hours_operating")
                    or 8760
                )
                ch4_content = self._optional_fraction(
                    flat_inputs, ["dehy_ch4_content", "ch4_content", "c1"], 0.85
                )
                control_eff = self._optional_fraction(
                    flat_inputs, ["dehy_eff", "control_efficiency"], 0.0
                )
                contactor_press = float(
                    flat_inputs.get("dehy_press")
                    or flat_inputs.get("contactor_pressure")
                    or 800.0
                )
                press_u = flat_inputs.get("dehy_press_unit", "psig")
                contactor_t = float(
                    flat_inputs.get("dehy_temp")
                    or flat_inputs.get("contactor_temperature")
                    or 100.0
                )
                temp_u = flat_inputs.get("dehy_temp_unit", "F")
                has_flash = flat_inputs.get("dehy_has_flash", True)
                if isinstance(has_flash, str):
                    has_flash = has_flash.lower() in ["true", "1", "yes"]
                flash_eff = self._optional_fraction(
                    flat_inputs, ["dehy_flash_eff", "flash_control_eff"], 0.0
                )
                still_type = flat_inputs.get("dehy_still_type", "none")
                flash_type = flat_inputs.get("dehy_flash_type", "none")

                return calculator.calculate(
                    throughput=throughput,
                    pump_rate=pump_rate,
                    pump_unit=pump_unit,
                    hours=hours,
                    ch4_content=ch4_content,
                    control_eff=control_eff,
                    uncertainties=uncertainties,
                    contactor_pressure=contactor_press,
                    press_unit=press_u,
                    contactor_temperature=contactor_t,
                    temp_unit=temp_u,
                    has_flash_tank=has_flash,
                    flash_control_eff=flash_eff,
                    still_control_type=still_type,
                    flash_control_type=flash_type,
                    gwp_dict=gwp_dict,
                )

            elif process_type == "indirect_steam":
                heat = self._require_float(
                    flat_inputs, ["quantity", "amount", "heat_energy"], "heat energy"
                )
                boiler_eff = self._require_float(
                    flat_inputs,
                    ["boiler_eff", "boiler_efficiency"],
                    "boiler efficiency fraction (e.g. 0.80)",
                )
                trans_loss = self._optional_fraction(
                    flat_inputs, ["trans_loss", "transmission_loss"], 0.0
                )

                return calculator.calculate(
                    heat_energy=heat,
                    ef_co2=emission_factors.get("co2", 0),
                    boiler_efficiency=boiler_eff,
                    transmission_loss=trans_loss,
                    uncertainties=uncertainties,
                    heat_unit=flat_inputs.get("heat_unit", "btu"),
                )

            else:
                return self._generic_calculation(
                    flat_inputs,
                    emission_factors,
                    uncertainties,
                    process_type,
                    gwp_dict=gwp_dict,
                )

        except Exception as e:
            from flask import current_app, has_app_context

            if has_app_context():
                current_app.logger.error(
                    f"[Dispatcher] Calculation failed for process_type='{process_type}': {e}",
                    exc_info=True,
                )
            else:
                import logging

                logging.error(
                    f"[Dispatcher] Calculation failed for process_type='{process_type}': {e}",
                    exc_info=True,
                )
            raise ValueError(f"Calculation error for '{process_type}': {str(e)}") from e

    def _generic_calculation(
        self,
        inputs,
        emission_factors,
        uncertainties,
        process_type="combustion",
        gwp_dict=None,
    ):
        """Standard Quantity * EF fallback with unit handling and tier-aware uncertainty."""
        quantity = float(inputs.get("quantity") or inputs.get("amount") or 0)
        unit = str(inputs.get("unit") or "m3").lower()
        f_unit = str(emission_factors.get("unit") or "kg/m3").lower()

        f_parts = f_unit.split("/")
        f_num = f_parts[0].strip() if len(f_parts) > 0 else f_unit
        f_denom = f_parts[1].strip() if len(f_parts) > 1 else ""

        vol_factors = {
            "m3": 1.0, "m³": 1.0, "cubic_meter": 1.0, "cubic_meters": 1.0,
            "scf": CONVERSIONS["scf_to_m3"], "cf": CONVERSIONS["scf_to_m3"], "ft3": CONVERSIONS["scf_to_m3"],
            "mcf": 1000.0 * CONVERSIONS["scf_to_m3"], "mscf": 1000.0 * CONVERSIONS["scf_to_m3"],
            "mmscf": 1_000_000.0 * CONVERSIONS["scf_to_m3"],
            "bbl": CONVERSIONS["bbl_to_m3"], "barrel": CONVERSIONS["bbl_to_m3"], "barrels": CONVERSIONS["bbl_to_m3"],
            "gal": CONVERSIONS["gal_to_m3"], "gallon": CONVERSIONS["gal_to_m3"], "gallons": CONVERSIONS["gal_to_m3"],
            "l": CONVERSIONS["liter_to_m3"], "liter": CONVERSIONS["liter_to_m3"], "liters": CONVERSIONS["liter_to_m3"],
        }
        mass_factors = {
            "kg": 1.0, "kilogram": 1.0, "kilograms": 1.0,
            "g": 0.001, "gram": 0.001, "grams": 0.001,
            "tonne": 1000.0, "tonnes": 1000.0, "metric_ton": 1000.0, "metric ton": 1000.0, "mt": 1000.0, "t": 1000.0,
            "lb": 0.453592, "lbs": 0.453592, "pound": 0.453592, "pounds": 0.453592,
            "ton": 907.185, "tons": 907.185, "short_ton": 907.185, "us_ton": 907.185,
        }

        # Energy-based normalization (Standard EFs are usually kg/MMBtu)
        if "mmbtu" in f_unit:
            if unit in ["mmbtu", "mm_btu"]:
                energy_mmbtu = quantity
            elif unit in ["gj", "gigajoule", "gigajoules"]:
                energy_mmbtu = quantity * 0.947817
            elif unit in ["therm", "therms"]:
                energy_mmbtu = quantity * 0.1
            else:
                fuel_name = str(inputs.get("fuel_type") or inputs.get("fuel") or "").lower()
                is_liquid = (
                    any(liq in fuel_name for liq in ["diesel", "gasoline", "petrol", "fuel oil", "crude", "oil", "kerosene", "lpg", "propane", "condensate", "naphtha", "liquid"])
                    or unit in ["bbl", "barrel", "barrels", "gal", "gallon", "gallons", "l", "liter", "liters"]
                )
                if is_liquid:
                    # Liquid fuel HHV: standard ~138,000 Btu/gal (0.138 MMBtu/gal)
                    hhv_liquid = float(inputs.get("hhv") or emission_factors.get("hhv") or 138000.0)
                    if unit in ["bbl", "barrel", "barrels"]:
                        gallons = quantity * 42.0
                    elif unit in ["l", "liter", "liters"]:
                        gallons = quantity * CONVERSIONS.get("l_to_gal", 0.264172)
                    elif unit in ["m3", "m³", "cubic_meter", "cubic_meters"]:
                        gallons = quantity * CONVERSIONS["m3_to_gal"]
                    else:  # gal
                        gallons = quantity
                    energy_mmbtu = (gallons * hhv_liquid) / 1_000_000.0
                else:
                    # Gaseous fuel HHV: standard ~1,020 Btu/scf
                    hhv_gas = float(inputs.get("hhv") or emission_factors.get("hhv") or 1020.0)
                    if unit in ["m3", "m³", "cubic_meter", "cubic_meters"]:
                        scf = quantity * CONVERSIONS["m3_to_scf"]
                    elif unit == "mmscf":
                        scf = quantity * 1_000_000.0
                    elif unit in ["mcf", "mscf"]:
                        scf = quantity * 1000.0
                    else:
                        scf = quantity
                    energy_mmbtu = (scf * hhv_gas) / 1_000_000.0
            quantity = energy_mmbtu
        else:
            # Check for volume factor denominator conversion
            matched_v_denom = next((k for k in sorted(vol_factors.keys(), key=len, reverse=True) if k == f_denom or k in f_denom), None)
            matched_v_unit = next((k for k in sorted(vol_factors.keys(), key=len, reverse=True) if k == unit or k in unit), None)
            if matched_v_denom and matched_v_unit:
                quantity = quantity * (vol_factors[matched_v_unit] / vol_factors[matched_v_denom])
            else:
                # Check for mass factor denominator conversion
                matched_m_denom = next((k for k in sorted(mass_factors.keys(), key=len, reverse=True) if k == f_denom or k in f_denom), None)
                matched_m_unit = next((k for k in sorted(mass_factors.keys(), key=len, reverse=True) if k == unit or k in unit), None)
                if matched_m_denom and matched_m_unit:
                    quantity = quantity * (mass_factors[matched_m_unit] / mass_factors[matched_m_denom])

        # Calculate raw values (Usually EF is kg/unit)
        co2_ef = float(
            emission_factors.get("co2") or emission_factors.get("ef_co2") or 0
        )
        ch4_ef = float(
            emission_factors.get("ch4") or emission_factors.get("ef_ch4") or 0
        )
        n2o_ef = float(
            emission_factors.get("n2o") or emission_factors.get("ef_n2o") or 0
        )
        co2_val = quantity * co2_ef
        ch4_val = quantity * ch4_ef
        n2o_val = quantity * n2o_ef

        # Determine result unit based on factor numerator only (prevent kg/tonne from being misidentified as tonne)
        is_tonne = any(
            t in f_num for t in ["tonne", "metric_ton", "metric ton", "t co2", "tco2", "t ch4", "tch4", "t n2o", "tco2e", "mtco2"]
        ) or f_num in ["t", "tonne", "tonnes", "mt"]
        is_gram = (
            f_num in ["g", "gram", "grams"]
            or any(f_num.startswith(p) for p in ["g/", "g ", "gco2", "gch4", "gn2o", "gco2e"])
            or any(p in f_num for p in ["g co2", "g ch4", "g n2o", "g co2e"])
        )

        if is_tonne:
            co2_tonnes, ch4_tonnes, n2o_tonnes = co2_val, ch4_val, n2o_val
        elif is_gram:
            co2_tonnes = co2_val / 1_000_000.0
            ch4_tonnes = ch4_val / 1_000_000.0
            n2o_tonnes = n2o_val / 1_000_000.0
        else:
            co2_tonnes = co2_val / 1000.0
            ch4_val_t = ch4_val / 1000.0
            n2o_val_t = n2o_val / 1000.0
            ch4_tonnes, n2o_tonnes = ch4_val_t, n2o_val_t

        # Tier-aware uncertainty propagation — 95% CI, non-negative bounds
        _tier = resolve_tier(
            inputs.get("factor_source")
            or uncertainties.get("_factor_source", "default")
        )
        _cat = PROCESS_CATEGORY.get(str(process_type).lower(), "combustion")

        def wrap(val, gas):
            return propagate_uncertainty(
                val,
                ef_uncertainty=resolve_ef_uncertainty(
                    _cat, gas, _tier, uncertainties.get(gas)
                ),
                tier=_tier,
                process_category=_cat,
                gas=gas,
            )

        total_co2e = calculate_co2e(
            co2_tonnes, ch4_tonnes, n2o_tonnes, gwp_dict=gwp_dict
        )

        return {
            "results": {
                "co2": wrap(co2_tonnes, "co2"),
                "ch4": wrap(ch4_tonnes, "ch4"),
                "n2o": wrap(n2o_tonnes, "n2o"),
            },
            "total_co2e": total_co2e,
            "method": "api2021_generic",
        }


# Global dispatcher instance
dispatcher = CalculationDispatcher()
