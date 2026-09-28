import math

from .units import UnitError
from .uncertainty import COVERAGE_FACTOR_95
import math
from .combustion import CombustionCalculator, FlaringCalculator, factor_hhv_unit
from .vented import (
    PneumaticDeviceCalculator,
    LiquidsUnloadingCalculator,
    MudDegassingCalculator,
    TankFlashingCalculator,
    CompletionFlowbackCalculator,
    BlowdownCalculator,
    AssociatedGasVentingCalculator,
)
from .fugitive import (
    ComponentFugitiveCalculator,
    EquipmentFugitiveCalculator,
    CompressorSealCalculator,
)
from .fugitive_onshore import (
    OnshoreFacilityFugitiveCalculator,
    OnshoreEquipmentFugitiveCalculator,
    OnshoreComponentFugitiveCalculator,
    OnshoreScreeningMeasurementCalculator,
    convert_fugitive_flow_to_kg_hr,
)
from .midstream import AGRCalculator, DehydratorCalculator
from .indirect import IndirectSteamCalculator, CogenAllocationCalculator
from .vented_downstream import RefiningHydrogenPlantCalculator
from .stoichiometry import StoichiometricCalculator, NitricAcidCalculator
from .activity_factors import ACTIVITY_FACTORS, ActivityFactorCalculator
from .vented_gas import VentedGasCalculator
from .combustion_methods import CombustionMethodCalculator
from .units import CONVERSIONS, calculate_co2e
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
    PROCESS_CATEGORY,
)


# process-type aliases -> the `processes` names used by ACTIVITY_FACTORS rows
ACTIVITY_PROCESS_ALIASES = {
    "pneumatic_devices": "pneumatic", "pneumatic_device": "pneumatic", "pneumatics": "pneumatic",
    "acid_gas_removal": "agr", "dehydrators": "dehydrator", "well_test": "well_testing",
    "workover": "workovers", "blowdown": "non_routine_venting", "venting": "non_routine_venting",
    "crude_loading": "loading",
}
# default gas-volume method for the processes that are VentedGasCalculator-only
VENT_DEFAULT_METHOD = {"desiccant_dehydrator": "desiccant", "co2_eor": "co2_mass", "vented_gas": "volume"}
COMBUSTION_METHOD_PROCESSES = {
    "stationary_combustion", "combustion", "mobile_combustion", "mobile", "flaring", "routine_flaring",
    "non_routine_flaring", "safety_flaring", "flare", "thermal_oxidizer",
}


def operating_hours(inputs):
    """Operating hours for per-hour factors (BUG-047).

    Uses operating_hours / hours / pneu_hours, or operating_days x 24. Without an input the
    source count is taken as an annual inventory (8,760 h), the same convention as the Tier 3
    equipment-fugitive calculator and the audit's hand values.
    """
    for key in ("operating_hours", "hours", "pneu_hours", "hours_per_year"):
        v = inputs.get(key)
        if v not in (None, "", "-"):
            h = float(v)
            if not math.isfinite(h) or h < 0 or h > 8784:
                raise ValueError(f"'{key}' must be between 0 and 8784 hours")
            return h
    d = inputs.get("operating_days") or inputs.get("duration_days")
    if d not in (None, "", "-"):
        days = float(d)
        if not math.isfinite(days) or days < 0 or days > 366:
            raise ValueError("'operating_days' must be between 0 and 366")
        return days * 24.0
    return 8760.0


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
            "routine_flaring": FlaringCalculator(),
            "non_routine_flaring": FlaringCalculator(),
            "safety_flaring": FlaringCalculator(),
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
            "pneumatics": PneumaticDeviceCalculator(),
            "pneumatic": PneumaticDeviceCalculator(),
            "fugitive_facility": OnshoreFacilityFugitiveCalculator(),
            "facility_fugitive": OnshoreFacilityFugitiveCalculator(),
            "fugitive_component": OnshoreComponentFugitiveCalculator(),
            "component_fugitive": OnshoreComponentFugitiveCalculator(),
            "equipment_fugitive": OnshoreEquipmentFugitiveCalculator(),
            "wellhead_fugitive": OnshoreEquipmentFugitiveCalculator(),
            "separator_fugitive": OnshoreEquipmentFugitiveCalculator(),
            "gathering_boosting": OnshoreEquipmentFugitiveCalculator(),
            "gas_processing": EquipmentFugitiveCalculator(),
            "transmission_storage": EquipmentFugitiveCalculator(),
            "refinery_fugitive": EquipmentFugitiveCalculator(),
            "distribution_fugitive": EquipmentFugitiveCalculator(),
            "lng_operations": EquipmentFugitiveCalculator(),
            "compressor_fugitive": CompressorSealCalculator(),
            "compressor_seal": CompressorSealCalculator(),
            "fugitive": OnshoreEquipmentFugitiveCalculator(),
            "fugitive_screening": OnshoreScreeningMeasurementCalculator(),
            "fugitive_ogi": OnshoreScreeningMeasurementCalculator(),
            "fugitive_measurement": OnshoreScreeningMeasurementCalculator(),
            "agr": AGRCalculator(),
            "acid_gas_removal": AGRCalculator(),
            "dehydrator": DehydratorCalculator(),
            "indirect_steam": IndirectSteamCalculator(),
            # section 6.11.3 hydrogen plants (routed to _hydrogen_plant before the catalog path)
            "hydrogen_production": RefiningHydrogenPlantCalculator(),
            "hydrogen_plant": RefiningHydrogenPlantCalculator(),
            "smr_hydrogen": RefiningHydrogenPlantCalculator(),
            "cogen_allocation": CogenAllocationCalculator(),
            "cogen": CogenAllocationCalculator(),
            "stoichiometry": StoichiometricCalculator(),
            "chemical_production": StoichiometricCalculator(),
            "nitric_acid_production": NitricAcidCalculator(),
            "adipic_acid_production": NitricAcidCalculator(),
            "asphalt_blowing": StoichiometricCalculator(),
            "asphalt": StoichiometricCalculator(),
            "venting": BlowdownCalculator(),
            "blowdown": BlowdownCalculator(),
            "associated_gas_venting": AssociatedGasVentingCalculator(),
            "associated_venting": AssociatedGasVentingCalculator(),
            "associated_gas": AssociatedGasVentingCalculator(),
            # Section 6 activity-factor sources (Tables 6-4 to 6-47) and measured / engineered gas volumes
            "well_testing": ActivityFactorCalculator(),
            "workovers": ActivityFactorCalculator(),
            "casing_gas": ActivityFactorCalculator(),
            "compressor_venting": ActivityFactorCalculator(),
            "non_routine_venting": ActivityFactorCalculator(),
            "loading": ActivityFactorCalculator(),
            "vented_gas": VentedGasCalculator(),
            "desiccant_dehydrator": VentedGasCalculator(),
            "co2_eor": VentedGasCalculator(),
            "thermal_oxidizer": CombustionMethodCalculator(),
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
        """Normalise a gas/liquid volume or volume RATE to `target_unit` (m3 or mmscf).

        RC-5 (BUG-066 / BUG-033): exact-token parsing; rate units ("MMscfd", "Mcf/day", "m3/yr")
        are annualised; an unknown unit raises instead of being returned unchanged.
        """
        from .units import annual_volume_m3

        try:
            m3 = annual_volume_m3(value, unit or "m3")
        except UnitError as err:
            raise ValueError(str(err))
        if target_unit == "m3":
            return m3
        if target_unit == "mmscf":
            return m3 / CONVERSIONS["mmscf_to_m3"]
        raise ValueError(f"Unsupported target volume unit '{target_unit}'")

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

    def _optional_float(self, flat_inputs, keys, default=None):
        """Extracts an optional float parameter from flat_inputs, returning default if missing."""
        if isinstance(keys, str):
            keys = [keys]
        for k in keys:
            val = flat_inputs.get(k)
            if val not in [None, "", "-"]:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
        return default

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

    def _composition(self, flat_inputs, c1_keys=("c1",)):
        """BUG-023: one percent/fraction decision for the whole analysis (calculations.units)."""
        from .units import composition_fractions

        raw = {}
        for k in c1_keys:
            if flat_inputs.get(k) not in (None, "", "-"):
                raw["c1"] = flat_inputs.get(k)
                break
        for i in range(2, 11):
            if flat_inputs.get(f"c{i}") not in (None, "", "-"):
                raw[f"c{i}"] = flat_inputs.get(f"c{i}")
        # N2 / H2S under any of their keys: a dropped inert made a 98.4 % analysis renormalise to 100 %
        # and inflated the hydrocarbons by 1.6 % (Exhibit 4.4a)
        for key, names in (("co2", ("co2_mol", "co2_content", "co2_comp")),
                           ("n2", ("n2", "n2_mol", "n2_comp", "n2_content", "n2_mole_pct")),
                           ("h2s", ("h2s", "h2s_mol", "h2s_content"))):
            for n in names:
                if flat_inputs.get(n) not in (None, "", "-"):
                    raw[key] = flat_inputs.get(n)
                    break
        basis = str(flat_inputs.get("composition_basis") or "").lower() or None
        fr, _info = composition_fractions(raw, basis={"mol%": "percent", "percent": "percent",
                                                      "fraction": "fraction"}.get(basis) if basis else None)
        comps = {f"c{i}": fr.get(f"c{i}", 0.0) for i in range(1, 11)}
        comps["co2_comp"] = fr.get("co2", 0.0)
        comps["n2_comp"] = fr.get("n2", 0.0)
        return comps

    def _hydrogen_plant(self, flat_inputs, uncertainties, gwp_dict):
        """API Compendium 2021 section 6.11.3 via RefiningHydrogenPlantCalculator.

        - feedstock carbon balance (Eq 6-49) when feedstock rate + carbon fraction / composition are given;
        - otherwise Table 6-51 on hydrogen produced (13.41 t CO2 / 10^6 scf H2). Tonnes of H2 are
          converted on the Compendium basis: t x 2204.62 lb/t / 2.016 lb/lbmol x 379.3 scf/lbmol.
        A CCS capture rate (fraction or %) removes the captured share of the process CO2.
        """
        from .vented_downstream import RefiningHydrogenPlantCalculator

        def num(*keys):
            for k in keys:
                v = flat_inputs.get(k)
                if v not in (None, "", "-"):
                    x = float(v)
                    if not math.isfinite(x) or x < 0:
                        raise ValueError(f"'{k}' must be a finite, non-negative number")
                    return x
            return None

        calc = RefiningHydrogenPlantCalculator()
        # feed gas composition (mol %): enables the rigorous Eq 6-49 / Eq 6-50 methods (Exhibits 6-42 / 6-43)
        comp = {}
        for key, sp in (("feed_ch4", "CH4"), ("feed_c2h6", "C2H6"), ("feed_c3h8", "C3H8"),
                        ("feed_c4h10", "C4H10"), ("feed_c5h12", "C5H12"), ("feed_co2", "CO2"), ("feed_n2", "N2")):
            v = num(key)
            if v is not None:
                comp[sp] = v / 100.0 if v > 1.0 else v
        feed_scf = num("feedstock_scf", "feedstock_volume_scf")
        if comp and feed_scf is not None:
            res = calc.calculate(method="feedstock_balance", feedstock_volume_scf_yr=feed_scf, feedstock_comp=comp,
                                 uncertainties=uncertainties, gwp_dict=gwp_dict)
            return self._apply_capture(res, flat_inputs)
        if comp and num("h2_produced_scf") is not None:
            res = calc.calculate(method="h2_stoichiometry", h2_production_scf_yr=num("h2_produced_scf"),
                                 feedstock_comp=comp, uncertainties=uncertainties, gwp_dict=gwp_dict)
            return self._apply_capture(res, flat_inputs)
        feed_t = num("feedstock_rate_tonnes", "feedstock_tonnes")
        cf = num("feedstock_carbon_fraction")
        if feed_t is not None and cf is not None:
            res = calc.calculate(method="feedstock_balance", feedstock_rate_tonnes_yr=feed_t,
                                 feedstock_carbon_fraction=cf if cf <= 1 else cf / 100.0,
                                 uncertainties=uncertainties, gwp_dict=gwp_dict)
        else:
            h2_scf = num("h2_produced_scf")
            if h2_scf is None:
                h2_t = num("h2_produced_tonnes")
                if h2_t is None and str(flat_inputs.get("unit") or "").lower() in ("t", "tonne", "tonnes", "metric ton"):
                    h2_t = num("amount", "quantity")
                if h2_t is None:
                    raise ValueError("Missing required field: hydrogen produced (h2_produced_tonnes or h2_produced_scf), "
                                     "or feedstock rate with carbon fraction")
                h2_scf = h2_t * 2204.62 / 2.016 * 379.3
            res = calc.calculate(method="simple_factor", simple_basis="h2_scf", simple_volume=h2_scf,
                                 uncertainties=uncertainties, gwp_dict=gwp_dict)
        return self._apply_capture(res, flat_inputs)

    def _facility_fugitive(self, flat_inputs, uncertainties, gwp_dict):
        """BUG-110 / RC-17: facility-level onshore fugitives, API 2021 Table 7-8 (per unit of production)."""
        fac_type = flat_inputs.get("facility_type")
        if fac_type in (None, ""):
            fuel = str(flat_inputs.get("fuel") or "").lower()
            fac_type = "oil_production" if "oil production" in fuel else ("gas_production" if "gas production" in fuel else None)
        if fac_type in (None, ""):
            raise ValueError("Missing required field: facility_type (oil_production or gas_production) for "
                             "facility-level fugitives")
        production = self._require_float(flat_inputs, ["production_volume", "amount", "quantity"], "production volume")
        unit = flat_inputs.get("production_unit") or flat_inputs.get("unit")
        ch4 = next((flat_inputs.get(k) for k in ("ch4_content", "c1") if flat_inputs.get(k) not in (None, "", "-")), None)
        return OnshoreFacilityFugitiveCalculator().calculate(
            production=production, production_unit=unit, facility_type=str(fac_type), ch4_content=ch4,
            uncertainties=uncertainties, gwp_dict=gwp_dict,
        )

    def _apply_capture(self, res, flat_inputs):
        capture = self._optional_fraction(flat_inputs, ["ccs_capture_rate", "capture_rate"], 0.0)
        if capture:
            keep = 1.0 - capture
            co2 = res["results"]["co2"]
            if isinstance(co2, dict):
                for k in ("value", "absolute_uncertainty", "lower_bound", "upper_bound", "lower_bound_95",
                          "upper_bound_95", "ci_95_abs"):
                    if isinstance(co2.get(k), (int, float)):
                        co2[k] = co2[k] * keep
            res["total_co2e"] = float(res.get("total_co2e") or 0.0) * keep
            res.setdefault("inputs", {})["ccs_capture_rate"] = capture
        return res

    @staticmethod
    def _blowdown_residual(flat_inputs):
        fp = flat_inputs.get("blowdown_final_pressure")
        if fp in (None, ""):
            fp = flat_inputs.get("final_pressure")
        if fp in (None, ""):
            return {}
        return {"blowdown_mode": "differential", "final_pressure": float(fp)}

    @staticmethod
    def _well_location(flat_inputs):
        """'offshore' only when the entry says so explicitly (well_location / location_type)."""
        for k in ("well_location", "location_type", "offshore"):
            v = flat_inputs.get(k)
            if v is True or str(v).strip().lower() in ("offshore", "true", "1", "yes"):
                return "offshore"
        return "onshore"

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

    def dispatch(self, process_type, inputs, emission_factors, uncertainties=None, gwp_dict=None, gwp_standard=None):
        """Run the calculator, then apply the audit RC-10 uncertainty rules to every result.

        - BUG-025: meter (activity-data) and GC (composition) uncertainty overrides are applied to
          every gas result whichever calculator ran (they were collected but never used).
        - BUG-008: the EF and AD components (1-sigma) are exposed as `uncertainty_components` so
          the record can store them and the inventory can correlate the EF part.
        """
        if uncertainties is None:
            uncertainties = {}
        res = self._dispatch_impl(process_type, inputs, emission_factors, uncertainties,
                                  gwp_dict=gwp_dict, gwp_standard=gwp_standard)
        if not isinstance(res, dict) or "results" not in res:
            return res
        calc_inputs = (inputs.get("calc_inputs") or {}).get(process_type, {}) if isinstance(inputs, dict) else {}
        flat = {**(inputs or {}), **(calc_inputs or {})}

        def pct(key):
            v = flat.get(key)
            if v in (None, "", "-"):
                return None
            x = float(v)
            if not math.isfinite(x) or x < 0 or x > 200:
                raise ValueError(f"'{key}' must be a percentage between 0 and 200")
            return x / 100.0  # entered as a 95 % half-width, like catalog uncertainties

        meter, gc = pct("meter_uncertainty_pct"), pct("gc_uncertainty_pct")
        comps = {}
        for gas in ("co2", "ch4", "n2o"):
            r = res["results"].get(gas)
            if not isinstance(r, dict) or "value" not in r:
                continue
            if meter is not None or gc is not None:
                u_ef95 = float(r.get("ef_uncertainty_1sigma") or 0.0) * COVERAGE_FACTOR_95
                u_ad95 = meter if meter is not None else float(r.get("ad_uncertainty_1sigma") or 0.0) * COVERAGE_FACTOR_95
                new = propagate_uncertainty(r["value"], ef_uncertainty=u_ef95, activity_uncertainty=u_ad95,
                                            composition_uncertainty=gc if gc is not None else (
                                                float(r.get("comp_uncertainty_1sigma") or 0.0) * COVERAGE_FACTOR_95 or None),
                                            gas=gas)
                r.update(new)
            if r.get("value"):
                comps[f"ef_{gas}"] = r.get("ef_uncertainty_1sigma")
                comps.setdefault("activity", r.get("ad_uncertainty_1sigma"))
        if comps:
            res["uncertainty_components"] = comps
        return res

    def _route_section_methods(self, process_type, flat_inputs, uncertainties, gwp_dict):
        """Activity-factor rows, gas-volume methods and combustion / waste-gas methods.

        Chosen by an explicit key in the inputs (activity_key, vent_method, combustion_method) or by a
        process type that only has these methods. Returns None when none applies.
        """
        key = flat_inputs.get("activity_key")
        if key not in (None, ""):
            row = ACTIVITY_FACTORS.get(str(key))
            if row is None:
                raise ValueError(f"Unknown activity factor '{key}'")
            canon = ACTIVITY_PROCESS_ALIASES.get(process_type, process_type)
            if canon not in row["processes"]:
                raise ValueError(f"Activity factor '{key}' does not apply to process '{process_type}'")
            return ActivityFactorCalculator().calculate(
                key,
                flat_inputs.get("activity_amount") if flat_inputs.get("activity_amount") not in (None, "")
                else flat_inputs.get("amount") if flat_inputs.get("amount") not in (None, "") else flat_inputs.get("quantity"),
                unit=flat_inputs.get("activity_unit") or flat_inputs.get("unit"),
                days=flat_inputs.get("activity_days"),
                hours=flat_inputs.get("activity_hours") if flat_inputs.get("activity_hours") not in (None, "")
                else flat_inputs.get("operating_hours"),
                ch4_content=flat_inputs.get("ch4_content"),
                co2_content=flat_inputs.get("co2_content"),
                toc_ch4_wt=flat_inputs.get("toc_ch4_wt"),
                uncertainties=uncertainties,
                gwp_dict=gwp_dict,
            )

        vent_method = flat_inputs.get("vent_method") or VENT_DEFAULT_METHOD.get(process_type)
        if vent_method not in (None, ""):
            return VentedGasCalculator().calculate(vent_method, flat_inputs, uncertainties=uncertainties, gwp_dict=gwp_dict)

        comb_method = flat_inputs.get("combustion_method") or ("thermal_oxidizer" if process_type == "thermal_oxidizer" else None)
        if comb_method not in (None, "") and process_type in COMBUSTION_METHOD_PROCESSES:
            return CombustionMethodCalculator().calculate(comb_method, flat_inputs, uncertainties=uncertainties, gwp_dict=gwp_dict)

        if isinstance(self.calculators.get(process_type), ActivityFactorCalculator):
            raise ValueError("Select an activity factor (activity_key) or a gas volume method (vent_method)")
        return None

    def _dispatch_impl(
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

        # Library factor (site factor database) is activity x the selected factor for every
        # process — separate from the API Compendium tier methods
        if str(flat_inputs.get("factor_mode") or "").lower() == "library":
            return self._generic_calculation(
                flat_inputs, emission_factors, uncertainties, process_type, gwp_dict=gwp_dict
            )

        if not calculator:
            # processes without a calculator (e.g. separation) still take Compendium activity rows
            if flat_inputs.get("activity_key") not in (None, ""):
                return self._route_section_methods(process_type, flat_inputs, uncertainties, gwp_dict)
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

        routed = self._route_section_methods(process_type, flat_inputs, uncertainties, gwp_dict)
        if routed is not None:
            return routed

        # One percent / fraction decision per gas analysis (Tier 3 browser test #14: CH4 85 with CO2 1
        # read CO2 as the fraction 1.0 = 100 %). When any member of a group is above 1 the whole group
        # is in percent and is converted to fractions here.
        for group in (("ch4_content", "co2_content", "c2plus_content"),
                      ("comp_ch4_content", "comp_co2_content", "comp_c2plus_content"),
                      ("pneu_ch4_content", "pneu_co2_content")):
            vals = {}
            for k in group:
                v = flat_inputs.get(k)
                if v in (None, "", "-"):
                    continue
                try:
                    vals[k] = float(v)
                except (TypeError, ValueError):
                    vals = {}
                    break
            # a single member cannot be decided jointly, and a c1..c10 analysis makes its own
            # whole-analysis decision (BUG-023, Exhibit 5.1)
            if any(flat_inputs.get(f"c{i}") not in (None, "", "-") for i in range(1, 11)):
                continue
            if len(vals) >= 2 and any(v > 1.0 for v in vals.values()):
                flat_inputs = {**flat_inputs, **{k: v / 100.0 for k, v in vals.items()}}

        # Validate required gas composition for specific factor sources
        if process_type in [
            "stationary_combustion",
            "combustion",
            "mobile_combustion",
            "mobile",
            "flaring",
            "routine_flaring",
            "non_routine_flaring",
            "safety_flaring",
            "flare",
            "separation",
        ]:
            spec = flat_inputs.get("specific_factors") or flat_inputs.get("specificFactors")
            has_spec = isinstance(spec, dict) and any(
                str(v).strip() not in [None, "", "-"]
                for k, v in spec.items()
                if not k.endswith("Unit")
            )
            if factor_source == "specific" and has_spec:
                has_ef = bool(spec.get("co2") or spec.get("ch4"))
                c1_val = flat_inputs.get("c1") or flat_inputs.get("ch4_content") or flat_inputs.get("gas_ch4_content")
                if not has_ef and c1_val in [None, "", "-"]:
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
        # BUG-104 (section 6.11.3): hydrogen plants are a stoichiometric calculation, never a catalog product
        if process_type in ("hydrogen_production", "hydrogen_plant", "smr_hydrogen"):
            return self._hydrogen_plant(flat_inputs, uncertainties, gwp_dict)

        # RC-17: Tier 1 table methods that are calculators, not catalog multiplications — pneumatic
        # controllers by type (Tables 6-14 / 6-15) and tank flashing without a catalog factor
        # (Tables 6-22 / 6-24)
        _has_catalog_ef = any(emission_factors.get(k) not in (None, "", "-", 0, 0.0) for k in ("co2", "ch4", "n2o"))
        table_calculator = (
            (process_type in ("pneumatic_devices", "pneumatic_device", "pneumatic")
             and flat_inputs.get("pneu_controller_type") not in (None, ""))
            or (process_type in ("tank", "tank_flashing", "storage_tanks") and not _has_catalog_ef)
            # Tier 2B component count without a selected factor: Table 7-12 by component / service
            or (process_type in ("fugitive", "fugitive_component", "component_fugitive")
                and str(flat_inputs.get("fugitive_method") or "").lower() == "component"
                and not _has_catalog_ef)
        )
        if factor_source in ["default", "custom"] and not table_calculator and process_type not in [
            "drilling", "mud_degassing", "completions", "completion_flowback",
            "associated_gas_venting", "associated_venting", "associated_gas"
        ]:
            if process_type in ["liquids_unloading", "unloading"]:
                raw_tier = str(
                    flat_inputs.get("tier")
                    or flat_inputs.get("tier_mode")
                    or flat_inputs.get("source_type")
                    or flat_inputs.get("calculation_level")
                    or ""
                ).lower().strip()
                calc_m = str(
                    flat_inputs.get("calc_method")
                    or flat_inputs.get("calculation_method")
                    or flat_inputs.get("method")
                    or flat_inputs.get("unloading_method")
                    or ""
                ).lower().strip()
                u_type = flat_inputs.get("unloading_type") or flat_inputs.get("unload_type") or "plunger"

                is_explicit_tier1 = raw_tier in ["tier1", "tier_1", "t1", "1"] or calc_m in ["api_table_6_11", "table_6_11", "per_well"]
                is_explicit_tier2 = raw_tier in ["tier2", "tier_2", "t2", "2"] or calc_m in ["api_table_6_10", "table_6_10", "event_based"]
                if is_explicit_tier1:
                    is_tier1 = True
                    is_tier2 = False
                elif is_explicit_tier2:
                    is_tier2 = True
                    is_tier1 = False
                else:
                    is_tier2 = (
                        str(unit).lower() in ["events", "event", "count"]
                        or flat_inputs.get("events") is not None
                        or flat_inputs.get("unload_events") is not None
                        or flat_inputs.get("unload_freq") is not None
                        or flat_inputs.get("frequency_category") is not None
                        or flat_inputs.get("region") is not None
                    )
                    is_tier1 = not is_tier2

                if is_tier2:
                    ev = (
                        flat_inputs.get("events")
                        or flat_inputs.get("unload_events")
                        or flat_inputs.get("unload_freq")
                        or quantity
                    )
                    wc = float(flat_inputs.get("well_count") or flat_inputs.get("wells") or 1)
                    ch4_c = self._optional_fraction(flat_inputs, ["ch4_content", "c1", "unload_ch4_content"], None)
                    co2_c = self._optional_fraction(flat_inputs, ["co2_content", "co2_mol"], 0.0)
                    flare_e = self._optional_fraction(flat_inputs, ["unload_flare_eff", "control_efficiency"], 0.0)
                    return calculator.calculate_tier2(
                        events=ev,
                        unloading_type=u_type,
                        well_count=wc,
                        frequency_category=flat_inputs.get("frequency_category") or flat_inputs.get("freq_category"),
                        region=flat_inputs.get("region"),
                        ch4_content=ch4_c,
                        co2_content=co2_c,
                        control_efficiency=flare_e,
                        uncertainties=uncertainties,
                        hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                        gwp_dict=gwp_dict,
                    )
                elif is_tier1:
                    wc = (
                        flat_inputs.get("well_count")
                        or flat_inputs.get("wells")
                        or quantity
                    )
                    ch4_c = self._optional_fraction(flat_inputs, ["ch4_content", "c1", "unload_ch4_content"], None)
                    co2_c = self._optional_fraction(flat_inputs, ["co2_content", "co2_mol"], 0.0)
                    flare_e = self._optional_fraction(flat_inputs, ["unload_flare_eff", "control_efficiency"], 0.0)
                    return calculator.calculate_tier1(
                        well_count=wc,
                        unloading_type=u_type,
                        ch4_content=ch4_c,
                        co2_content=co2_c,
                        control_efficiency=flare_e,
                        uncertainties=uncertainties,
                        hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                        gwp_dict=gwp_dict,
                    )

            if process_type in [
                "stationary_combustion",
                "combustion",
                "mobile_combustion",
                "mobile",
            ]:
                hhv_val = flat_inputs.get("hhv") or emission_factors.get("hhv")
                density_val = flat_inputs.get("density") or flat_inputs.get("fuel_density")
                if hhv_val or density_val:
                    return calculator.calculate(
                        fuel_quantity=quantity,
                        ef_co2=emission_factors.get("co2", 0),
                        ef_ch4=emission_factors.get("ch4", 0),
                        ef_n2o=emission_factors.get("n2o", 0),
                        uncertainties=uncertainties,
                        hhv=float(hhv_val) if hhv_val else 1020.0,
                        ef_unit=flat_inputs.get(
                            "ef_unit", emission_factors.get("unit", "kg/unit")
                        ),
                        fuel_unit=unit,
                        # BUG-027: the HHV basis comes from the factor's catalog type / hhv_unit
                        fuel_type=emission_factors.get("type") or flat_inputs.get("fuel_type")
                        or emission_factors.get("fuel_type", "unknown"),
                        hhv_unit=factor_hhv_unit(emission_factors),
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
                        density=float(density_val) if density_val else None,
                    )
            # BUG-110: the facility-level Tier 1 fugitive method (Table 7-1/7-2) is a calculator,
            # not a catalog multiplication; it used to fall through to "valves x count"
            if process_type in ("fugitive", "fugitive_facility", "facility_fugitive") and (
                process_type != "fugitive"
                or str(flat_inputs.get("fugitive_tier") or "").lower() in ("tier1", "tier_1", "facility")
                or flat_inputs.get("facility_type") not in (None, "")
            ):
                return self._facility_fugitive(flat_inputs, uncertainties, gwp_dict)
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

                comps = self._composition(flat_inputs)
                # Tier 3 fuel analysis needs the fuel composition or measured factors; an HHV alone
                # used to give a Verified 0 tCO2e record (Tier 3 browser test #10)
                _spec = flat_inputs.get("specific_factors") or flat_inputs.get("specificFactors") or {}
                _measured = any(
                    (emission_factors.get(k) not in (None, "", "-", 0, 0.0))
                    or (isinstance(_spec, dict) and str(_spec.get(k) or "").strip() not in ("", "0", "0.0", "-"))
                    for k in ("co2", "ch4", "n2o")
                )
                if not any(comps.get(f"c{i}") for i in range(1, 11)) and not comps.get("co2_comp") and not _measured:
                    raise ValueError(
                        "Tier 3 fuel analysis needs the fuel gas composition (Gas analysis) or measured emission factors"
                    )

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

            elif process_type in ["flaring", "routine_flaring", "non_routine_flaring", "safety_flaring"]:
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

                comps = self._composition(flat_inputs, c1_keys=("c1", "ch4_content", "flare_ch4_content"))
                if not comps.get("c1"):
                    comps["c1"] = ch4_content

                def _get_eff(keys):
                    for k in keys:
                        v = flat_inputs.get(k)
                        if v not in [None, "", "-"]:
                            return v
                    return None

                comb_eff = _get_eff(["combustion_efficiency", "combustion_eff", "eta_c"])
                dest_eff = _get_eff(["destruction_efficiency", "destruction_eff", "eta_d"])
                ef_n2o_val = emission_factors.get("n2o") if emission_factors.get("n2o") not in [None, "", "-"] else (
                    emission_factors.get("ef_n2o") if emission_factors.get("ef_n2o") not in [None, "", "-"] else flat_inputs.get("ef_n2o", 0.0)
                )

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
                    ef_n2o=float(ef_n2o_val or 0.0),
                    combustion_efficiency=comb_eff,
                    destruction_efficiency=dest_eff,
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
                raw_tier = str(
                    flat_inputs.get("tier")
                    or flat_inputs.get("tier_mode")
                    or flat_inputs.get("source_type")
                    or uncertainties.get("_factor_source")
                    or "tier1"
                ).lower().strip()

                # Mud type parsing: an explicit mud type, else the one named by the selected Table 6-2 row
                raw_mud_type = str(flat_inputs.get("mud_type") or emission_factors.get("mud_type") or "water_based").lower()
                mud_type = "oil_based" if ("oil" in raw_mud_type or "synth" in raw_mud_type) else "water_based"
                # Catalog rows carry no override: Table 6-2 is applied by mud type and location (browser test
                # F3: the rows' kg-based values were read as tonnes per day). A saved library / custom factor is
                # in kg per unit (Manage Data convention) and the calculator works in tonnes.
                if str(emission_factors.get("type") or "").lower() == "custom":
                    _cf = emission_factors.get("ch4")
                    drill_ef = float(_cf) / 1000.0 if _cf not in (None, "", "-") else 0
                else:
                    drill_ef = 0

                # Check gas concentrations for Tier 2+
                ch4_conc = (
                    flat_inputs.get("ch4_fraction")
                    if flat_inputs.get("ch4_fraction") is not None
                    else flat_inputs.get("ch4_concentration")
                )
                if ch4_conc is None and flat_inputs.get("ch4_pct") is not None:
                    ch4_conc = float(flat_inputs.get("ch4_pct")) / 100.0

                co2_conc = (
                    flat_inputs.get("co2_fraction")
                    if flat_inputs.get("co2_fraction") is not None
                    else flat_inputs.get("co2_concentration")
                )
                if co2_conc is None and flat_inputs.get("co2_pct") is not None:
                    co2_conc = float(flat_inputs.get("co2_pct")) / 100.0

                unit_str = str(flat_inputs.get("unit") or unit or "").lower().strip()

                # Determine whether Tier 1, Tier 2, or Tier 2+
                is_tier2_plus = (
                    raw_tier in ["tier2_plus", "tier_2_plus", "tier2+", "tier_2+"]
                    or (ch4_conc is not None and float(ch4_conc) != 0.8385)
                    or (co2_conc is not None and float(co2_conc) > 0)
                )
                is_tier2 = (
                    is_tier2_plus
                    or raw_tier in ["tier2", "tier_2", "custom", "t2"]
                    or unit_str in ["days", "day", "d"]
                    or flat_inputs.get("drilling_days") is not None
                    or (flat_inputs.get("mud_type") is not None and raw_tier not in ["tier1", "tier_1", "t1"])
                )

                if is_tier2_plus:
                    drilling_days = self._require_float(
                        flat_inputs,
                        ["drilling_days", "days", "amount", "quantity", "mud_vol", "mud_volume", "volume", "activity_data"],
                        "drilling days",
                    )
                    return calculator.calculate(
                        location=self._well_location(flat_inputs),  # BUG-103: offshore Tables 6-2 / 6-7
                        tier="tier2_plus",
                        drilling_days=drilling_days,
                        mud_type=mud_type,
                        ch4_concentration=ch4_conc,
                        co2_concentration=co2_conc,
                        uncertainties=uncertainties,
                        ef_ch4=drill_ef,
                        gwp_dict=gwp_dict,
                    )
                elif is_tier2:
                    drilling_days = self._require_float(
                        flat_inputs,
                        ["drilling_days", "days", "amount", "quantity", "mud_vol", "mud_volume", "volume", "activity_data"],
                        "drilling days",
                    )
                    return calculator.calculate(
                        location=self._well_location(flat_inputs),  # BUG-103: offshore Tables 6-2 / 6-7
                        tier="tier2",
                        drilling_days=drilling_days,
                        mud_type=mud_type,
                        uncertainties=uncertainties,
                        ef_ch4=drill_ef,
                        gwp_dict=gwp_dict,
                    )
                else:
                    # Tier 1 (wells default)
                    wells = self._require_float(
                        flat_inputs,
                        ["wells", "well_count", "amount", "quantity", "mud_vol", "mud_volume", "volume", "drilling_wells", "activity_data"],
                        "well count",
                    )
                    return calculator.calculate(
                        location=self._well_location(flat_inputs),  # BUG-103: offshore Tables 6-2 / 6-7
                        tier="tier1",
                        wells=wells,
                        uncertainties=uncertainties,
                        ef_ch4=drill_ef,
                        gwp_dict=gwp_dict,
                    )

            elif process_type == "completions":
                comp_tier = (
                    flat_inputs.get("tier")
                    or flat_inputs.get("comp_tier")
                    or ("tier1" if emission_factors.get("code") in [
                        "CompGasHF_Uncontrolled", "CompGasHF_REC",
                        "CompOilHF_Uncontrolled", "CompOilHF_REC",
                        "CompGasNoHF_Vented", "CompOilNoHF_Vented",
                        "CompGasNoFlare", "WorkoverGasNoFlare"
                    ] else None)
                )
                comp_method = (
                    flat_inputs.get("comp_method")
                    or flat_inputs.get("calc_method")
                    or flat_inputs.get("calculation_method")
                )
                if not comp_method and flat_inputs.get("comp_rate") not in (None, "") and flat_inputs.get("comp_duration") not in (None, ""):
                    comp_method = "rate_duration"  # BUG-012: the method the form shows by default
                unit = flat_inputs.get("unit") or "m3"

                # Events determination
                events_val = float(
                    flat_inputs.get("events")
                    or flat_inputs.get("num_events")
                    or (flat_inputs.get("amount") if str(unit).lower() in ["count", "event", "events", "completions", "wells"] else (
                        flat_inputs.get("amount") if comp_tier == "tier1" else 1.0
                    ))
                    or 1.0
                )

                gas_sales_mcf = float(flat_inputs.get("comp_gas_produced_mcf") or flat_inputs.get("gas_produced_sales_mcf") or 0.0)
                gas_sales_scf = gas_sales_mcf * 1000.0 if gas_sales_mcf else float(flat_inputs.get("gas_produced_sales_scf") or 0.0)

                # Flowback volume for Tier 3
                vol_val = None
                vol_unit_val = str(unit or "m3").lower().strip()
                if comp_tier in ["tier3", "3"] or (not comp_tier and not flat_inputs.get("comp_rate") and not flat_inputs.get("comp_liquid_bbl") and not flat_inputs.get("daily_production_rate")):
                    raw_vol = flat_inputs.get("flowback_volume") or flat_inputs.get("comp_volume") or (
                        flat_inputs.get("amount") if vol_unit_val not in ["count", "event", "events", "completions"] else None
                    ) or flat_inputs.get("quantity")
                    if raw_vol is not None:
                        vol_val = float(raw_vol)
                        # the flowback volume carries its own unit (the record's unit may be "events");
                        # an unknown unit is an error, never a silent m3 (Exhibit 6-3 check)
                        explicit = flat_inputs.get("volume_unit") or flat_inputs.get("comp_volume_unit")
                        if explicit:
                            vol_unit_val = str(explicit).lower().strip()
                        if vol_unit_val not in ["scf", "m3", "sm3", "mcf", "mscf", "mmscf"]:
                            raise ValueError("Tier 3 completions need the flowback volume unit (scf, Mcf, MMscf or m3)")

                ch4_content = self._optional_fraction(
                    flat_inputs, ["ch4_content", "c1", "comp_ch4_content"], None
                )
                co2_content = self._optional_fraction(
                    flat_inputs, ["co2_content", "co2_mol", "comp_co2_content"], 0.0
                )
                default_eff = 0.98 if str(flat_inputs.get("disposition") or flat_inputs.get("comp_disposition") or "").lower() == "flared" else 0.0
                flare_eff = self._optional_fraction(
                    flat_inputs, ["comp_flare_eff", "control_efficiency", "flare_efficiency"], default_eff
                )

                # Rate unit: UI default is Mcf/hr
                # BUG-011: the form collects "Avg Gas Rate (Mcf/hr)"; default to that unit
                rate_u = flat_inputs.get("comp_rate_unit") or flat_inputs.get("rate_unit") or "mcf/hr"

                return calculator.calculate(
                    location=self._well_location(flat_inputs),  # BUG-103: offshore Tables 6-2 / 6-7
                    flowback_volume=vol_val,
                    volume_unit=vol_unit_val,
                    ch4_content=ch4_content,
                    co2_content=co2_content,
                    control_efficiency=flare_eff,
                    uncertainties=uncertainties,
                    ef_co2=emission_factors.get("co2"),
                    ef_ch4=emission_factors.get("ch4"),
                    ef_n2o=emission_factors.get("n2o"),
                    calculation_method=comp_method,
                    tier=comp_tier,
                    well_type=flat_inputs.get("well_type") or emission_factors.get("well_type", "gas"),
                    fracturing=flat_inputs.get("fracturing") if flat_inputs.get("fracturing") is not None else emission_factors.get("fracturing"),
                    control_type=flat_inputs.get("control_type") or emission_factors.get("control_type"),
                    flowback_rate=flat_inputs.get("comp_rate") or flat_inputs.get("flowback_rate"),
                    rate_unit=rate_u,
                    flowback_duration_hours=flat_inputs.get("comp_duration") or flat_inputs.get("flowback_duration_hours"),
                    daily_production_rate=flat_inputs.get("daily_production_rate") or flat_inputs.get("comp_daily_prod_rate"),
                    prod_rate_unit=flat_inputs.get("prod_rate_unit") or flat_inputs.get("comp_prod_rate_unit", "mcf/day"),
                    vent_duration_hours=flat_inputs.get("vent_duration_hours"),
                    vent_duration_days=flat_inputs.get("vent_duration_days"),
                    liquid_flowback_bbl=flat_inputs.get("comp_liquid_bbl") or flat_inputs.get("liquid_flowback_bbl"),
                    gas_oil_ratio=flat_inputs.get("comp_gor") or flat_inputs.get("gas_oil_ratio"),
                    gas_produced_sales_scf=gas_sales_scf,
                    c2plus_content=self._optional_fraction(flat_inputs, ["comp_c2plus_content", "c2plus_content"], 0.0),
                    injected_n2_volume=flat_inputs.get("comp_injected_n2") or flat_inputs.get("injected_n2_volume") or 0.0,
                    injected_n2_unit=flat_inputs.get("comp_injected_n2_unit") or flat_inputs.get("injected_n2_unit", "scf"),
                    injected_gas_type=flat_inputs.get("comp_injected_gas_type") or flat_inputs.get("injected_gas_type", "n2"),
                    initial_flowback_hours=flat_inputs.get("comp_initial_flowback_hours") or flat_inputs.get("initial_flowback_hours"),
                    disposition=flat_inputs.get("comp_disposition") or flat_inputs.get("disposition"),
                    frac_vented=flat_inputs.get("frac_vented") or flat_inputs.get("comp_frac_vented"),
                    frac_flared=flat_inputs.get("frac_flared") or flat_inputs.get("comp_frac_flared"),
                    frac_recovered=flat_inputs.get("frac_recovered") or flat_inputs.get("comp_frac_recovered"),
                    hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                    gwp_dict=gwp_dict,
                    events=events_val,
                    factor_code=emission_factors.get("code"),
                )

            elif process_type in ["liquids_unloading", "unloading"]:
                calc_method = str(
                    flat_inputs.get("calc_method")
                    or flat_inputs.get("calculation_method")
                    or flat_inputs.get("method")
                    or flat_inputs.get("unloading_method")
                    or ""
                ).lower().strip()

                # API Equation 6-11: Automated plunger lift
                if (
                    calc_method in ["api_equation_6_11", "equation_6_11", "eq_6_11", "automated_plunger"]
                    or (flat_inputs.get("p_shut") is not None and flat_inputs.get("p_sep") is not None)
                ):
                    p_shut = self._require_float(flat_inputs, ["p_shut", "shut_pressure"], "shut-in pressure (Pshut)")
                    p_line = self._require_float(flat_inputs, ["p_line", "line_pressure"], "flow-line pressure (Pline)")
                    p_sep = self._require_float(flat_inputs, ["p_sep", "separator_pressure"], "separator pressure (Psep)")
                    sfr_p = self._require_float(flat_inputs, ["sfr_p", "sfr", "production_rate"], "daily gas production rate (SFRp)")
                    t_p = self._require_float(flat_inputs, ["t_p", "hours_open", "venting_time"], "hours vented per event (Tp)")
                    events = int(self._require_float(flat_inputs, ["unload_freq", "unload_events", "events", "amount"], "annual unloading events"))
                    ch4_content = self._optional_fraction(flat_inputs, ["ch4_content", "c1", "unload_ch4_content"], 0.85)
                    co2_content = self._optional_fraction(flat_inputs, ["co2_content", "co2_mol"], 0.0)
                    flare_eff = self._optional_fraction(flat_inputs, ["unload_flare_eff", "control_efficiency"], 0.0)
                    press_unit = flat_inputs.get("unload_press_unit") or flat_inputs.get("press_unit", "psia")

                    return calculator.calculate_tier3_equation_6_11(
                        p_shut=p_shut,
                        p_line=p_line,
                        p_sep=p_sep,
                        sfr_p=sfr_p,
                        t_p=t_p,
                        events=events,
                        well_count=float(flat_inputs.get("well_count") or flat_inputs.get("wells") or 1),
                        ch4_content=ch4_content,
                        co2_content=co2_content,
                        control_efficiency=flare_eff,
                        press_unit=press_unit,
                        sfr_unit=flat_inputs.get("sfr_unit", "scf/hr"),
                        uncertainties=uncertainties,
                        hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                        gwp_dict=gwp_dict,
                    )

                # API Equation 6-10: EPA Subpart W (W-8 / W-9)
                elif (
                    calc_method in ["api_equation_6_10", "equation_6_10", "eq_6_10", "subpart_w"]
                    or (flat_inputs.get("sfr") is not None and flat_inputs.get("hours_open") is not None)
                ):
                    depth = self._require_float(flat_inputs, ["unload_depth", "well_depth"], "well depth (ft)")
                    diam = self._require_float(flat_inputs, ["unload_diam", "diameter"], "casing diameter (in)")
                    press = self._require_float(flat_inputs, ["unload_press", "pressure"], "shut-in surface pressure (psig)")
                    events = int(self._require_float(flat_inputs, ["unload_freq", "unload_events", "events", "amount"], "annual unloading events"))
                    sfr = self._require_float(flat_inputs, ["sfr", "subpart_w_sfr"], "sales flow rate (SFR)")
                    hours_open = self._require_float(flat_inputs, ["hours_open", "hrs_open", "venting_hours"], "hours venting during unloading (HR)")
                    ch4_content = self._require_fraction(flat_inputs, ["ch4_content", "c1", "unload_ch4_content"], "gas CH4 content %")
                    co2_content = self._optional_fraction(flat_inputs, ["co2_content", "co2_mol"], 0.0)
                    flare_eff = self._optional_fraction(flat_inputs, ["unload_flare_eff", "control_efficiency"], 0.0)
                    depth_unit = flat_inputs.get("unload_depth_unit") or flat_inputs.get("depth_unit", "ft")
                    diam_unit = flat_inputs.get("unload_diam_unit") or flat_inputs.get("diameter_unit", "in")
                    press_unit = flat_inputs.get("unload_press_unit") or flat_inputs.get("press_unit", "psig")

                    return calculator.calculate_tier3_equation_6_10(
                        events=events,
                        well_depth=depth,
                        diameter=diam,
                        pressure=press,
                        sfr=sfr,
                        hours_open=hours_open,
                        unloading_type=flat_inputs.get("unloading_type") or flat_inputs.get("unload_type", "non_plunger"),
                        well_count=float(flat_inputs.get("well_count") or flat_inputs.get("wells") or 1),
                        ch4_content=ch4_content,
                        co2_content=co2_content,
                        control_efficiency=flare_eff,
                        depth_unit=depth_unit,
                        diameter_unit=diam_unit,
                        press_unit=press_unit,
                        sfr_unit=flat_inputs.get("sfr_unit", "scf/hr"),
                        uncertainties=uncertainties,
                        hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                        gwp_dict=gwp_dict,
                    )

                # Default Tier 3: API Equation 6-3 (Volume-based wellbore decompression geometry)
                else:
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

                    return calculator.calculate_volume_based(
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
                        well_count=float(flat_inputs.get("well_count") or flat_inputs.get("wells") or 1),
                        unloading_type=flat_inputs.get("unloading_type") or flat_inputs.get("unload_type", "plunger"),
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
                    # Eq 6-32 / Exhibit 6-25 by default; a residual pressure switches to the released dP (BUG-101)
                    **self._blowdown_residual(flat_inputs),
                )

            elif process_type in ["associated_gas_venting", "associated_venting", "associated_gas"]:
                tier_val = flat_inputs.get("tier") or flat_inputs.get("tier_level")
                factor_src = flat_inputs.get("factor_source")

                # Activity Data (oil production, vent rate, or vent volume)
                raw_oil = self._optional_float(
                    flat_inputs,
                    ["oil_production", "oil_amount", "amount", "quantity", "oil_rate"],
                    None,
                )
                oil_unit = flat_inputs.get("oil_unit") or flat_inputs.get("unit") or "bbl"

                # Basin / regional factor
                basin = (
                    flat_inputs.get("basin")
                    or flat_inputs.get("region")
                    or flat_inputs.get("fuel")
                    or flat_inputs.get("fuel_type")
                    or emission_factors.get("name")
                    or "US Average"
                )

                # Tier 2 parameters: GOR, venting duration, mass balance
                gor = self._optional_float(
                    flat_inputs,
                    ["gor", "gas_oil_ratio", "gas_to_oil_ratio"],
                    None,
                )
                gor_unit = flat_inputs.get("gor_unit") or "scf/bbl"

                venting_duration = self._optional_float(
                    flat_inputs,
                    ["venting_duration", "duration", "hours", "days", "vent_duration"],
                    None,
                )
                duration_unit = flat_inputs.get("duration_unit") or "days"
                period_duration = self._optional_float(
                    flat_inputs,
                    ["period_duration", "total_period", "period_days", "operating_days"],
                    None,
                )

                rec_gas = self._optional_float(
                    flat_inputs,
                    ["recovered_gas_volume", "recovered_gas", "gas_recovered"],
                    0.0,
                )
                flared_gas = self._optional_float(
                    flat_inputs,
                    ["flared_gas_volume", "flared_gas", "gas_flared"],
                    0.0,
                )
                gas_vol_unit = flat_inputs.get("gas_volume_unit") or flat_inputs.get("gas_unit") or "scf"

                # Tier 3 parameters: direct measurement
                vent_rate = self._optional_float(
                    flat_inputs,
                    ["vent_rate", "measured_vent_rate", "flow_rate"],
                    None,
                )
                vent_rate_unit = flat_inputs.get("vent_rate_unit") or "scfh"
                vent_volume = self._optional_float(
                    flat_inputs,
                    ["vent_volume", "measured_vent_volume"],
                    None,
                )
                vent_volume_unit = flat_inputs.get("vent_volume_unit") or "scf"

                # Gas composition
                ch4_content = self._optional_fraction(
                    flat_inputs, ["ch4_content", "c1", "ch4_mol_pct", "ch4"], None
                )
                co2_content = self._optional_fraction(
                    flat_inputs, ["co2_content", "co2_mol", "co2_mol_pct", "co2"], None
                )

                ef_co2 = emission_factors.get("co2")
                ef_ch4 = emission_factors.get("ch4")

                return calculator.calculate(
                    tier=tier_val,
                    factor_source=factor_src,
                    oil_production=raw_oil,
                    oil_unit=oil_unit,
                    basin=basin,
                    gor=gor,
                    gor_unit=gor_unit,
                    venting_duration=venting_duration,
                    duration_unit=duration_unit,
                    period_duration=period_duration,
                    recovered_gas_volume=rec_gas,
                    flared_gas_volume=flared_gas,
                    gas_volume_unit=gas_vol_unit,
                    vent_rate=vent_rate,
                    vent_rate_unit=vent_rate_unit,
                    vent_volume=vent_volume,
                    vent_volume_unit=vent_volume_unit,
                    ch4_content=ch4_content,
                    co2_content=co2_content,
                    ef_ch4=ef_ch4,
                    ef_co2=ef_co2,
                    uncertainties=uncertainties,
                    gwp_dict=gwp_dict,
                )

            elif process_type in [
                "tank",
                "tank_flashing",
                "storage_tanks",
                "tank_working",
                "tank_breathing",
            ]:
                if process_type in ("tank_working", "tank_breathing"):
                    # Section 6.3.9.3: working / standing losses are the total hydrocarbon loss (AP-42
                    # Chapter 7 or simulation) x the vent CH4 / CO2 weight fraction, not flashing
                    raise ValueError(
                        "Working and breathing losses: enter the total hydrocarbon loss and the vent CH4 / CO2 weight % (vent_method 'thc_mass')"
                    )
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

                # BUG-102: GOR is one of several methods; without it the Table 6-22 / 6-24 defaults (or
                # VBE / Standing / EUB when separator data are given) apply instead of zero emissions
                def _opt(keys):
                    for k in keys:
                        v = flat_inputs.get(k)
                        if v not in (None, "", "-"):
                            return v
                    return None

                gor = _opt(["tank_gor", "gor"])
                ch4_raw = _opt(["tank_ch4_content", "ch4_content", "c1"])
                tank_eff = self._optional_fraction(
                    flat_inputs, ["tank_control_eff", "control_efficiency"], 0.0
                )
                co2_content = self._optional_fraction(
                    flat_inputs, ["tank_co2_content", "co2_content", "co2_mol"], 0.0
                )
                liquid = str(_opt(["tank_liquid_type", "liquid_type"]) or "crude").lower()
                if liquid not in ("crude", "condensate", "produced_water"):
                    raise ValueError("tank liquid type must be crude, condensate or produced_water")
                api_g = _opt(["api_gravity", "tank_api_gravity"])
                sep_p = _opt(["separator_pressure_psig", "sep_pressure"])
                sep_t = _opt(["separator_temp_f", "sep_temp"])

                return calculator.calculate(
                    throughput=throughput_bbl,
                    gas_oil_ratio=float(gor) if gor is not None else None,
                    ch4_content=self._parse_fraction_value(ch4_raw, key_name="ch4_content") if ch4_raw is not None else None,
                    control_efficiency=tank_eff,
                    uncertainties=uncertainties,
                    process_type=process_type,
                    ef_ch4=emission_factors.get("ch4", 0),
                    co2_content=co2_content,
                    hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
                    gwp_dict=gwp_dict,
                    method=_opt(["tank_method", "flashing_method"]),
                    liquid_type=liquid,
                    tank_size=str(_opt(["tank_size"]) or "large").lower(),
                    api_gravity=float(api_g) if api_g is not None else None,
                    separator_pressure_psig=float(sep_p) if sep_p is not None else None,
                    separator_temp_f=float(sep_t) if sep_t is not None else None,
                )

            elif process_type in ["pneumatic_devices", "pneumatic_device", "pneumatic"]:
                # BUG-100: API 2021 section 6.3.6 - controller type (Tables 6-14 / 6-15), Eq 6-14 monitoring
                # survey, Eq 6-13 actuation volume, or a measured bleed rate
                count = self._require_float(
                    flat_inputs,
                    ["pneu_count", "device_count", "count", "amount", "quantity"],
                    "device count",
                )
                hours_raw = next((flat_inputs.get(k) for k in ("pneu_hours", "hours_operating", "hours", "operating_hours")
                                  if flat_inputs.get(k) not in (None, "", "-")), None)
                hours = float(hours_raw) if hours_raw is not None else 8760.0
                if not (0 <= hours <= 8784):
                    raise ValueError("annual operating hours must be between 0 and 8,784")
                ctype = flat_inputs.get("pneu_controller_type") or flat_inputs.get("controller_type")
                monitoring = str(flat_inputs.get("pneu_monitoring") or "").lower() in ("true", "1", "yes")
                bleed_raw = flat_inputs.get("pneu_bleed_rate") or flat_inputs.get("bleed_rate")
                if not ctype and not monitoring and bleed_raw in (None, "", "-"):
                    raise ValueError("Missing required parameter for Tier 3 specific calculation: pneumatic "
                                     "controllers need a controller type (Tables 6-14 / 6-15), monitoring "
                                     "survey counts, or a measured bleed rate")
                bleed_rate = float(bleed_raw) if bleed_raw not in (None, "", "-") else None
                if bleed_rate is not None and flat_inputs.get("pneu_bleed_unit", "scf") == "m3":
                    bleed_rate *= 35.3147  # m3 -> scf
                ch4_raw = next((flat_inputs.get(k) for k in ("pneu_ch4_content", "ch4_content", "c1", "gas_content")
                                if flat_inputs.get(k) not in (None, "", "-")), None)
                if ch4_raw is None and bleed_rate is not None and not ctype:
                    raise ValueError("Missing required field: gas CH4 content % (measured bleed rate method)")
                # Table factors are on an 81.6 mol % CH4 basis; without a site analysis that basis is used
                ch4_content = (self._parse_fraction_value(ch4_raw, key_name="ch4_content")
                               if ch4_raw is not None else 0.816)
                actuations = flat_inputs.get("pneu_actuations") or flat_inputs.get("actuations")
                actuations_val = float(actuations) if actuations not in [None, "", "-"] else None

                def _f(k):
                    v = flat_inputs.get(k)
                    return float(v) if v not in (None, "", "-") else None

                return calculator.calculate(
                    count=count,
                    hours=hours,
                    bleed_rate=bleed_rate,
                    ch4_content=ch4_content,
                    uncertainties=uncertainties,
                    actuations=actuations_val,
                    co2_content=self._optional_fraction(flat_inputs, ["pneu_co2_content", "co2_content"], 0.0),
                    gwp_dict=gwp_dict,
                    controller_type=str(ctype).lower() if ctype else None,
                    source_standard=str(flat_inputs.get("pneu_factor_standard") or "api").lower(),
                    monitoring_program=monitoring,
                    normal_count=_f("pneu_normal_count"),
                    normal_fraction_year=_f("pneu_normal_fraction") if _f("pneu_normal_fraction") is not None else 1.0,
                    malfunctioning_count=_f("pneu_malfunction_count"),
                    malfunctioning_fraction_year=_f("pneu_malfunction_fraction") or 0.0,
                )

            elif process_type in [
                "fugitive",
                "fugitive_facility",
                "facility_fugitive",
                "fugitive_component",
                "component_fugitive",
                "equipment_fugitive",
                "wellhead_fugitive",
                "separator_fugitive",
                "gathering_boosting",
                "fugitive_screening",
                "fugitive_ogi",
                "fugitive_measurement",
                "gas_processing",
                "transmission_storage",
                "refinery_fugitive",
                "distribution_fugitive",
                "lng_operations",
            ]:
                # 1. Duration / Time Basis Handling with proper unit conversion
                _t = next((flat_inputs.get(k) for k in ("hours", "operating_hours", "hours_operating")
                           if flat_inputs.get(k) not in (None, "")), None)
                raw_time = float(_t) if _t is not None else 0.0
                _time_given = _t is not None  # an entered 0 h is 0, not a full year
                time_unit = str(
                    flat_inputs.get("time_unit")
                    or flat_inputs.get("duration_unit")
                    or "hours"
                ).lower()

                if not _time_given:
                    raw_days = float(
                        flat_inputs.get("operating_days")
                        or flat_inputs.get("days")
                        or 0.0
                    )
                    if raw_days > 0:
                        op_days = raw_days
                        op_hours = raw_days * 24.0
                    else:
                        op_hours = 8760.0
                        op_days = 365.25
                else:
                    if "day" in time_unit:
                        op_days = raw_time
                        op_hours = raw_time * 24.0
                    elif "month" in time_unit:
                        op_days = raw_time * (365.25 / 12.0)
                        op_hours = op_days * 24.0
                    elif "yr" in time_unit or "year" in time_unit:
                        op_days = raw_time * 365.25
                        op_hours = raw_time * 8760.0
                    else:
                        op_hours = raw_time
                        op_days = raw_time / 24.0

                # 2. Methodology & Sub-Type Detection
                fug_tier = str(flat_inputs.get("fugitive_tier") or "").lower()
                fug_method = str(flat_inputs.get("fugitive_method") or "").lower()
                source_type = str(flat_inputs.get("factor_source") or "default").lower()
                fuel_str = str(flat_inputs.get("fuel") or "").lower()
                ef_unit_str = str(emission_factors.get("unit") or flat_inputs.get("unit") or "").lower()

                is_facility = (
                    process_type in ["fugitive_facility", "facility_fugitive"]
                    or fug_tier in ["tier1", "tier_1", "facility"]
                    or fug_method == "facility"
                    or "facility" in fuel_str
                    or "facility/day" in ef_unit_str
                    or "pad" in fuel_str
                )

                is_screening_measurement = (
                    process_type in ["fugitive_screening", "fugitive_ogi", "fugitive_measurement"]
                    or fug_tier in ["tier3", "tier_3", "measurement", "screening"]
                    or fug_method in ["screening", "method21", "ogi", "measurement", "correlation"]
                    # BUG-048: "specific" with a catalog leak factor and no measurement inputs is the
                    # engineering count x factor x hours method, not a direct measurement of `amount`
                    or (source_type == "specific" and not (emission_factors.get("ch4") or emission_factors.get("factor")
                                                           or flat_inputs.get("ef") not in (None, "")))
                    or flat_inputs.get("fugitive_ppm") is not None
                    or flat_inputs.get("screening_ppm") is not None
                    or flat_inputs.get("measured_rate") is not None
                    or flat_inputs.get("leakers_count") is not None
                )

                is_component = (
                    process_type in ["fugitive_component", "component_fugitive"]
                    or fug_tier in ["tier2_component", "component"]
                    or fug_method == "component"
                    or flat_inputs.get("component_type") is not None
                    or flat_inputs.get("component_counts") is not None
                    or "component" in fuel_str
                    or "kg/hr/source" in ef_unit_str
                    or "kg toc/hr" in ef_unit_str
                )

                if is_facility:
                    return self._facility_fugitive(flat_inputs, uncertainties, gwp_dict)

                elif is_screening_measurement:
                    calc = OnshoreScreeningMeasurementCalculator()
                    # the explicit method decides (Tier 3 browser test #3: "method21" fell through to
                    # direct measurement; stale keys of another method must not re-route a record)
                    sub_mode = str(flat_inputs.get("fugitive_sub_method") or fug_method or "").lower()
                    if not sub_mode:
                        sub_mode = ("ogi" if flat_inputs.get("leakers_count") is not None
                                    else "correlation" if flat_inputs.get("corr_screened_count") is not None
                                    else "measurement")
                    comp_type = str(flat_inputs.get("component_type") or "valve")
                    service = str(flat_inputs.get("service_type") or flat_inputs.get("service") or "gas")
                    y_ch4 = self._optional_fraction(flat_inputs, ["ch4_content", "ch4_mole_pct", "ch4_fraction", "c1"], None)
                    y_co2 = self._optional_fraction(flat_inputs, ["co2_content", "co2_mole_pct", "co2_fraction"], None)

                    if "ogi" in sub_mode or sub_mode in ("leaker", "leakers"):
                        leakers = self._require_float(flat_inputs, ["leakers_count", "detected_leakers"], "number of leakers")
                        surveyed = flat_inputs.get("surveyed_count") or flat_inputs.get("total_surveyed")
                        return calc.calculate_ogi_survey(
                            component_type=flat_inputs.get("ogi_component") or comp_type,
                            service_type=flat_inputs.get("ogi_service") or service,
                            total_surveyed=surveyed,
                            leakers_detected=leakers,
                            operating_hours=op_hours,
                            uncertainties=uncertainties,
                            gwp_dict=gwp_dict,
                            ch4_mol=y_ch4,
                            co2_mol=y_co2,
                        )
                    elif "corr" in sub_mode:
                        ppm_vals = flat_inputs.get("screening_values_ppm")
                        if isinstance(ppm_vals, str):
                            ppm_vals = [v for v in ppm_vals.replace(";", ",").split(",") if v.strip()]
                        if not ppm_vals and flat_inputs.get("corr_screened_count") not in (None, ""):
                            n_scr = int(float(flat_inputs.get("corr_screened_count") or 0))
                            if n_scr:
                                ppm = self._require_float(flat_inputs, ["fugitive_ppm", "screening_ppm", "ppm"], "screening ppm")
                                ppm_vals = [ppm] * n_scr
                        elif not ppm_vals and not any(
                            flat_inputs.get(k) not in (None, "")
                            for k in ("corr_zero_count", "corr_pegged_10k_count", "corr_pegged_100k_count")
                        ):
                            ppm = self._require_float(flat_inputs, ["fugitive_ppm", "ppm", "screening_ppm"], "screening ppm")
                            count = int(float(flat_inputs.get("amount") or flat_inputs.get("quantity") or 1))
                            ppm_vals = [ppm] * count
                        # CH4 weight fraction of TOC (not the gas mole %); default 0.564 (Table C-1)
                        return calc.calculate_correlation_equation(
                            component_type=flat_inputs.get("correlation_type") or comp_type,
                            service_type=service,
                            screening_values_ppm=ppm_vals or [],
                            operating_hours=op_hours,
                            ch4_content=flat_inputs.get("ch4_wt_fraction"),
                            uncertainties=uncertainties,
                            gwp_dict=gwp_dict,
                            zero_count=flat_inputs.get("corr_zero_count"),
                            pegged_10k_count=flat_inputs.get("corr_pegged_10k_count"),
                            pegged_100k_count=flat_inputs.get("corr_pegged_100k_count"),
                        )
                    elif "method21" in sub_mode or "range" in sub_mode or sub_mode == "screening":
                        below = flat_inputs.get("m21_below_count")
                        above = flat_inputs.get("m21_above_count")
                        if below in (None, "") and above in (None, ""):
                            # older payloads: one screening value for `amount` components
                            count = self._require_float(flat_inputs, ["amount", "quantity", "component_count"], "component count")
                            ppm = self._require_float(flat_inputs, ["screening_ppm", "fugitive_ppm", "ppm"], "screening value (ppmv)")
                            below, above = (0, count) if ppm >= 10000 else (count, 0)
                        return calc.calculate_method21_ranges(
                            component_type=flat_inputs.get("m21_component") or comp_type,
                            service_type=flat_inputs.get("m21_service") or service,
                            non_pegged_count=below,
                            pegged_count=above,
                            operating_hours=op_hours,
                            ch4_content=flat_inputs.get("ch4_wt_fraction"),
                            uncertainties=uncertainties,
                            gwp_dict=gwp_dict,
                        )
                    elif "measure" in sub_mode:
                        meas_rate = self._require_float(
                            flat_inputs, ["measured_rate", "flow_rate", "rate"], "measured leak rate"
                        )
                        rate_u = str(flat_inputs.get("rate_unit") or flat_inputs.get("measurement_unit") or "")
                        if not rate_u:
                            raise ValueError("Select the unit of the measured leak rate")
                        return calc.calculate_direct_measurement(
                            measured_rate=meas_rate,
                            measurement_unit=rate_u,
                            operating_hours=op_hours,
                            ch4_mol=y_ch4,
                            co2_mol=y_co2,
                            uncertainties=uncertainties,
                            gwp_dict=gwp_dict,
                        )
                    else:
                        raise ValueError(f"Unknown fugitive Tier 3 method '{sub_mode}'")

                elif is_component:
                    calc = OnshoreComponentFugitiveCalculator()
                    comps_dict = flat_inputs.get("component_counts")
                    if not comps_dict:
                        c_type = flat_inputs.get("component_type") or flat_inputs.get("fuel")
                        if not c_type:
                            raise ValueError("Select the component type")
                        c_type = str(c_type)
                        c_count = self._require_float(
                            flat_inputs,
                            ["amount", "quantity", "count", "component_count"],
                            "component count",
                        )
                        c_ef = float(
                            emission_factors.get("ch4")
                            or emission_factors.get("factor")
                            or flat_inputs.get("ef")
                            or 0.0
                        )
                        if c_ef > 0:
                            c_unit = str(emission_factors.get("unit") or flat_inputs.get("ef_unit") or "kg TOC/hr/component")
                            comps_dict = {c_type: {"count": c_count, "ef": c_ef, "unit": c_unit}}
                        else:
                            # no catalog / custom factor: Table 7-12 by component and service (the former
                            # invented 0.0045 kg/hr fallback is removed)
                            comps_dict = {c_type: c_count}

                    service = str(flat_inputs.get("service_type") or flat_inputs.get("service") or "Gas")
                    # gas mole fractions (Table 7-12 scaling, CO2) and the CH4 weight fraction of TOC
                    c_ch4 = self._optional_fraction(flat_inputs, ["ch4_mole_pct", "ch4_content", "c1"], None)
                    c_co2 = self._optional_fraction(flat_inputs, ["co2_mole_pct", "co2_content", "co2_fraction"], None)
                    return calc.calculate(
                        component_counts=comps_dict,
                        service_type=service,
                        operating_hours=op_hours,
                        ch4_content=c_ch4,
                        co2_content=c_co2,
                        uncertainties=uncertainties,
                        gwp_dict=gwp_dict,
                        ch4_wt_fraction=flat_inputs.get("ch4_wt_fraction") or flat_inputs.get("ch4_fraction"),
                    )

                else:
                    # Equipment-Level (Tier 2A) or backward-compatible equipment factor
                    calc = OnshoreEquipmentFugitiveCalculator()
                    count = self._require_float(
                        flat_inputs,
                        ["equipment_count", "well_count", "separator_count", "amount", "quantity", "count"],
                        "equipment count",
                    )
                    ef = float(
                        emission_factors.get("ch4")
                        or emission_factors.get("factor")
                        or flat_inputs.get("ef")
                        or 0.0
                    )
                    ef_u = str(emission_factors.get("unit") or flat_inputs.get("unit") or "tonne CH4/well/hr")
                    eq_type = str(flat_inputs.get("equipment_type") or flat_inputs.get("fuel") or "Equipment")
                    service = str(flat_inputs.get("service_type") or "Gas")
                    return calc.calculate(
                        equipment_count=count,
                        equipment_type=eq_type,
                        service_type=service,
                        operating_hours=op_hours,
                        factor_value=ef,
                        factor_unit=ef_u,
                        uncertainties=uncertainties,
                        gwp_dict=gwp_dict,
                        ch4_wt_fraction=next((flat_inputs.get(k) for k in ("ch4_wt_fraction", "ch4_content")
                                              if flat_inputs.get(k) not in (None, "")), None),
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

                raw_hours = float(flat_inputs.get("hours") or flat_inputs.get("operating_hours") or 8760.0)
                return calculator.calculate(
                    compressor_count=count,
                    seal_type=seal_type,
                    hours=raw_hours,
                    uncertainties=uncertainties,
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

                if flat_inputs.get("agr_co2_in") not in (None, ""):
                    # the form's fields are labelled "%": always percentages (0.9 % is not 90 %)
                    co2_in, co2_out = raw_co2_in / 100.0, (raw_co2_out / 100.0 if raw_co2_out_val not in [None, "", "-"] else 0.0)
                elif raw_co2_in > 1.0 or raw_co2_out > 1.0:
                    co2_in = raw_co2_in / 100.0 if raw_co2_in > 1.0 else raw_co2_in
                    co2_out = (raw_co2_out / 100.0) if raw_co2_in > 1.0 else (raw_co2_out / 100.0 if raw_co2_out > 1.0 else raw_co2_out)
                else:
                    co2_in = raw_co2_in
                    co2_out = raw_co2_out

                if co2_out > co2_in:
                    raise ValueError("Outlet CO2 cannot exceed inlet CO2")

                ch4_in = self._optional_fraction(
                    flat_inputs, ["agr_ch4_in", "ch4_in", "c1", "ch4_mole_pct"], 0.85
                )
                ch4_slip = self._optional_fraction(
                    flat_inputs,
                    ["agr_ch4_slip_pct", "ch4_slip_pct", "agr_ch4_slip", "ch4_slip_fraction", "methane_slip_factor", "ch4_slip"],
                    None,
                )
                ctrl_eff = self._optional_fraction(
                    flat_inputs, ["agr_control_eff", "control_efficiency", "removal_efficiency"], 0.0
                )
                ctrl_type = (
                    flat_inputs.get("agr_control_type")
                    or flat_inputs.get("acid_gas_control_type")
                    or flat_inputs.get("control_type")
                    # BUG-090: older clients sent a bare "routed to flare" flag
                    or ("flare" if str(flat_inputs.get("offgas_to_flare", "")).lower() in ("true", "1", "yes") else "vent")
                )
                if str(ctrl_type).strip().lower() != "vent" and ctrl_eff <= 0:
                    raise ValueError(
                        f"Acid gas control '{ctrl_type}' needs a control / destruction efficiency (agr_control_eff, %)"
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
                "nitric_acid_production",
                "adipic_acid_production",
            ]:
                if flat_inputs.get("carbon_content") is not None or flat_inputs.get("c_content") is not None:
                    stoich_calc = StoichiometricCalculator()
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
                    oxidation_factor = self._optional_fraction(
                        flat_inputs,
                        ["oxidation_factor", "ox_factor"],
                        1.0,
                    )
                    return stoich_calc.calculate(
                        fuel_mass=raw_amt,
                        carbon_content=carbon_content,
                        oxidation_factor=oxidation_factor,
                        uncertainties=uncertainties,
                        mass_unit=unit,
                        gwp_dict=gwp_dict,
                    )
                else:
                    raw_amt = self._require_float(
                        flat_inputs,
                        ["production_amount", "amount", "quantity", "fuel_mass"],
                        "production amount",
                    )
                    ef_n2o = (
                        emission_factors.get("n2o")
                        or emission_factors.get("ef_n2o")
                        or flat_inputs.get("ef_n2o")
                        or flat_inputs.get("n2o")
                    )
                    abatement_eff = self._optional_fraction(
                        flat_inputs,
                        ["abatement_efficiency", "abatement_eff", "control_efficiency", "eta_abatement"],
                        0.0,
                    )
                    return calculator.calculate(
                        production_amount=raw_amt,
                        ef_n2o=ef_n2o,
                        abatement_efficiency=abatement_eff,
                        mass_unit=unit,
                        uncertainties=uncertainties,
                        gwp_dict=gwp_dict,
                        process_type=process_type,
                    )

            elif process_type in [
                "stoichiometry",
                "chemical_production",
                "asphalt_blowing",
                "asphalt",
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
                oxidation_factor = self._optional_fraction(
                    flat_inputs,
                    ["oxidation_factor", "ox_factor"],
                    1.0,
                )

                return calculator.calculate(
                    fuel_mass=raw_amt,
                    carbon_content=carbon_content,
                    oxidation_factor=oxidation_factor,
                    uncertainties=uncertainties,
                    mass_unit=unit,
                    gwp_dict=gwp_dict,
                )

            elif process_type == "dehydrator":
                # Tier 3 browser test #12: the former "parametric solubility" model had no source in the
                # API Compendium. Section 6.3.8.1 methods: Tables 6-17/6-18/6-35/6-36 (Tier 1 activity
                # factors), a process simulation (GRI-GLYCalc) or measurement (vent_method routes)
                if flat_inputs.get("dehy_pump_rate") not in (None, "") or flat_inputs.get("pump_rate") not in (None, ""):
                    raise ValueError(
                        "Glycol dehydrator Tier 3: enter the measured vent volume or the simulation (GLYCalc) result; "
                        "use Tier 1 for the Compendium factors"
                    )
                throughput = (
                    flat_inputs.get("dehy_throughput")
                    or flat_inputs.get("amount")
                    or flat_inputs.get("quantity")
                )
                pump_rate = (
                    flat_inputs.get("dehy_pump_rate")
                    or flat_inputs.get("teg_pump_rate")
                    or flat_inputs.get("pump_rate")
                )
                pump_unit = (
                    flat_inputs.get("dehy_pump_unit")
                    or flat_inputs.get("teg_pump_unit")
                    or "gph"
                )
                hours = float(
                    flat_inputs.get("dehy_hours")
                    or flat_inputs.get("hours_operating")
                    or flat_inputs.get("annual_hours")
                    or 8760
                )
                ch4_content = self._optional_fraction(
                    flat_inputs, ["dehy_ch4_content", "ch4_content", "c1", "gas_ch4_mole_pct"], 0.85
                )
                control_eff = self._optional_fraction(
                    flat_inputs, ["dehy_eff", "control_efficiency"], 0.0
                )
                contactor_press = float(
                    flat_inputs.get("dehy_press")
                    or flat_inputs.get("dehy_pressure")  # BUG-090: key the form used to send
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
                still_type = flat_inputs.get("dehy_still_type") or flat_inputs.get("still_vent_control") or "none"
                flash_type = flat_inputs.get("dehy_flash_type", "none")
                stripping_rate = (
                    flat_inputs.get("dehy_stripping_rate")
                    or flat_inputs.get("stripping_rate")
                    or flat_inputs.get("stripping_gas_rate")
                )
                stripping_unit = (
                    flat_inputs.get("dehy_stripping_unit")
                    or flat_inputs.get("stripping_unit")
                    or flat_inputs.get("stripping_gas_unit")
                    or "scf/hr"
                )
                stripping_scf = (
                    flat_inputs.get("dehy_stripping_scf")
                    or flat_inputs.get("stripping_scf")
                    or flat_inputs.get("stripping_gas_scf")
                )

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
                    stripping_gas_rate=float(stripping_rate) if stripping_rate not in [None, "", "-"] else 0.0,
                    stripping_gas_unit=stripping_unit,
                    stripping_gas_scf=float(stripping_scf) if stripping_scf not in [None, "", "-"] else None,
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
        raw_q = inputs.get("amount") if inputs.get("amount") not in [None, ""] else inputs.get("quantity")
        if isinstance(raw_q, str):
            s = raw_q.strip()
            if "," in s and "." not in s:
                raw_q = s.replace(",", ".")
            else:
                raw_q = s.replace(",", "")
        quantity = float(raw_q or 0)
        if not math.isfinite(quantity) or quantity < 0:
            raise ValueError("Activity amount must be a finite, non-negative number")  # BUG-050
        has_factor = any(emission_factors.get(k) not in (None, "", "-", 0, 0.0)
                         for k in ("co2", "ch4", "n2o", "ef_co2", "ef_ch4", "ef_n2o"))
        if quantity == 0 or not has_factor:
            # zero activity is zero emissions; a missing factor is reported by compute_emissions'
            # MissingFactorError guard (never booked as zero)
            zero = {g: propagate_uncertainty(0.0, 0.0, gas=g) for g in ("co2", "ch4", "n2o")}
            return {"results": zero, "total_co2e": 0.0, "method": "api2021_generic"}
        unit = inputs.get("unit")
        f_unit = emission_factors.get("unit")
        if not unit:
            raise ValueError("Missing required field: unit (the activity unit is needed to apply the factor)")
        if not f_unit:
            raise ValueError(f"Emission factor '{emission_factors.get('name') or inputs.get('fuel')}' has no unit")

        # RC-5 (BUG-047/049/051/063): one parser for every factor unit; per-hour factors need
        # operating hours; energy factors need the heating value in the factor's declared basis.
        from .combustion import convert_factor_to_kg_per_unit

        hours = operating_hours(inputs)
        # a named catalog fuel supplies its own tabulated HHV / basis when the factor row lacks them
        catalog = {}
        if not (inputs.get("hhv") or emission_factors.get("hhv")):
            try:
                from routes.emissions import _lookup_api_factor

                catalog = _lookup_api_factor(inputs.get("fuel") or inputs.get("fuel_type")) or {}
            except Exception:
                catalog = {}
        conv = dict(
            hhv=inputs.get("hhv") or emission_factors.get("hhv") or catalog.get("hhv"),
            fuel_type=emission_factors.get("type") or catalog.get("type") or inputs.get("fuel_type") or inputs.get("fuel"),
            density=inputs.get("density") or inputs.get("fuel_density") or emission_factors.get("density"),
            hhv_unit=factor_hhv_unit(emission_factors) or factor_hhv_unit(catalog),
            hours=hours,
        )

        def ef(*keys):
            for k in keys:
                v = emission_factors.get(k)
                if v not in (None, "", "-"):
                    return float(v)
            return 0.0

        try:
            co2_tonnes = quantity * convert_factor_to_kg_per_unit(ef("co2", "ef_co2"), f_unit, unit, **conv) / 1000.0
            ch4_tonnes = quantity * convert_factor_to_kg_per_unit(ef("ch4", "ef_ch4"), f_unit, unit, **conv) / 1000.0
            n2o_tonnes = quantity * convert_factor_to_kg_per_unit(ef("n2o", "ef_n2o"), f_unit, unit, **conv) / 1000.0
        except UnitError as err:
            raise ValueError(str(err))

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
