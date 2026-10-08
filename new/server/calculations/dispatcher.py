import math

from .units import UnitError
from .uncertainty import COVERAGE_FACTOR_95
import math
from .combustion import CombustionCalculator, FlaringCalculator, factor_hhv_unit, user_hhv
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


def unloading_row_selection(code):
    """Type / frequency class / basin of a liquids-unloading catalog row (Tables 6-10 and 6-11), from its code."""
    import re

    c = str(code or "")
    m = re.fullmatch(r"Unload(Plunger|NonPlunger)(?:_(T1))?(?:_(LE100|GT100|LE10|10_50|GT50))?"
                     r"(?:_(Appalachia|GulfCoast|Midcontinent|RockyMountain)(?:_(LT100|GT100))?)?", c)
    if not m:
        return {}
    kind = "plunger" if m.group(1) == "Plunger" else "non_plunger"
    out = {"type": kind}
    freq, region, rfreq = m.group(3), m.group(4), m.group(5)
    if not (freq or region):
        out["tier"] = 1  # per well-year (Table 6-11)
        return out
    out["tier"] = 2  # per event (Table 6-10)
    if region:
        out["region"] = re.sub(r"(?<!^)(?=[A-Z])", "_", region).lower()
    f = freq or rfreq
    if f:
        out["frequency"] = {"LE100": "plunger_le100", "LT100": "plunger_le100", "GT100": "plunger_gt100",
                            "LE10": "non_plunger_le10", "10_50": "non_plunger_10_to_50", "GT50": "non_plunger_gt50"}[f]
    return out


def record_period(inputs):
    """(hours, days, fraction of the year) of the period a record covers.

    Records are monthly (year + month): the default operating time is that calendar month, never a
    full year, so twelve monthly records add up to one year. Without a period (annual inventories,
    exhibit examples) the year is used.
    """
    import calendar

    try:
        y, m = int(inputs.get("year")), int(inputs.get("month"))
        if 1 <= m <= 12:
            days = calendar.monthrange(y, m)[1]
            return days * 24.0, float(days), days / (366.0 if calendar.isleap(y) else 365.0)
    except (TypeError, ValueError):
        pass
    return 8760.0, 365.0, 1.0


def operating_hours(inputs):
    """Operating hours for per-hour factors (BUG-047).

    Uses operating_hours / hours / pneu_hours, or operating_days x 24. Without an input the
    source count operates for the whole period of the record (record_period).
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
    return record_period(inputs)[0]


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

    def _normalize_volume(self, value, unit, target_unit="m3", year=None, month=None):
        """Normalise a gas/liquid volume or volume RATE to `target_unit` (m3 or mmscf).

        RC-5 (BUG-066 / BUG-033): exact-token parsing; a rate unit ("MMscfd", "Mcf/day", "m3/yr")
        covers the record's month (its year when no month is given); an unknown unit raises
        instead of being returned unchanged.
        """
        from .units import period_volume_m3

        try:
            m3 = period_volume_m3(value, unit or "m3", year=year, month=month)
        except UnitError as err:
            raise ValueError(str(err))
        if target_unit == "m3":
            return m3
        if target_unit == "mmscf":
            return m3 / CONVERSIONS["mmscf_to_m3"]
        raise ValueError(f"Unsupported target volume unit '{target_unit}'")

    def _method_unit(self, flat_inputs, keys, unit, default=None):
        """The unit of a method input: its own column (tank_unit, agr_unit ...) or the record unit.
        S1K-F9: when both are given and are different physical amounts (bbl vs m3), the row is
        contradictory and refused instead of one silently winning."""
        from .units import UnitError, unit_dimension

        own = next((str(flat_inputs.get(k)).strip() for k in keys if flat_inputs.get(k) not in (None, "", "-")), None)
        rec = str(unit).strip() if unit not in (None, "", "-") else None
        if own and rec and own.lower() != rec.lower():
            try:
                d1, f1 = unit_dimension(own)
                d2, f2 = unit_dimension(rec)
            except UnitError:
                d1 = d2 = None
            if d1 and d1 == d2 and abs(f1 - f2) > 1e-12 * max(f1, f2):
                # two representations of the same activity (the form's converted top-level amount and
                # the method amount in its own unit) are consistent; one number in two units is not
                try:
                    top_amt = float(flat_inputs.get("_top_amount"))
                    own_amt = float(flat_inputs.get("amount") if flat_inputs.get("amount") not in (None, "") else
                                    flat_inputs.get("quantity"))
                    top_u = str(flat_inputs.get("_top_unit") or "").strip()
                    same = top_u.lower() == rec.lower() and top_amt > 0 and \
                        abs(top_amt * f2 - own_amt * f1) <= 1e-6 * top_amt * f2
                except (TypeError, ValueError):
                    same = False
                if not same:
                    raise ValueError(f"Contradicting units on the row: unit '{rec}' and {keys[0]} '{own}'")
        return own or rec or default

    def _liquid_bbl(self, value, unit_text, desc):
        """A liquid volume in bbl (S1K-F3: kbbl / Mbbl were read as bbl, and tonne / kg / MMBtu / scf
        were accepted as bbl)."""
        from .units import UnitError, unit_dimension

        u = str(unit_text or "bbl").strip().lower().replace(" ", "_")
        if u in ("scf", "cf", "ft3", "mscf", "mcf", "mmscf", "sm3", "nm3", "ksm3", "mmsm3"):
            raise ValueError(f"{desc}: '{unit_text}' is a gas volume; give the liquid volume (bbl, m3, gal, L)")
        try:
            dim, f = unit_dimension(u)
        except UnitError:
            raise ValueError(f"{desc}: unknown unit '{unit_text}' (use bbl, kbbl, m3, gal or L)")
        if dim != "volume":
            raise ValueError(f"{desc}: '{unit_text}' is not a liquid volume (use bbl, kbbl, m3, gal or L)")
        return float(value) * f / CONVERSIONS["bbl_to_m3"]

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

    _DENSITY_TO_KG_M3 = {"kg/m3": 1.0, "kg/l": 1000.0, "g/ml": 1000.0, "g/cm3": 1000.0, "t/m3": 1000.0,
                         "lb/gal": 119.826427, "lb/usgal": 119.826427, "lb/ft3": 16.0184634, "lb/bbl": 119.826427 / 42.0}

    def _fuel_density(self, flat_inputs):
        """Fuel density in kg/m3 (density / fuel_density, unit density_unit). The form enters kg/m3; a
        bulk density_unit was ignored (8.3 lb/gal read as 8.3 kg/m3)."""
        raw = flat_inputs.get("density") if flat_inputs.get("density") not in (None, "", "-") else flat_inputs.get("fuel_density")
        if raw in (None, "", "-"):
            return None
        d = float(raw)
        if not math.isfinite(d) or d <= 0:
            raise ValueError("Fuel density must be a positive number")
        u = str(flat_inputs.get("density_unit") or "").strip().lower().replace(" ", "").replace("³", "3")
        if not u:
            return d
        if u not in self._DENSITY_TO_KG_M3:
            raise ValueError(f"Unknown density unit '{flat_inputs.get('density_unit')}' "
                             "(use kg/m3, kg/L, g/cm3, lb/gal or lb/ft3)")
        return d * self._DENSITY_TO_KG_M3[u]

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
                days=flat_inputs.get("activity_days") if flat_inputs.get("activity_days") not in (None, "")
                else record_period(flat_inputs)[1],
                hours=flat_inputs.get("activity_hours") if flat_inputs.get("activity_hours") not in (None, "")
                else flat_inputs.get("operating_hours") if flat_inputs.get("operating_hours") not in (None, "")
                else record_period(flat_inputs)[0],
                year_fraction=flat_inputs.get("activity_year_fraction") if flat_inputs.get("activity_year_fraction") not in (None, "")
                else record_period(flat_inputs)[2],
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

        raw_qty = flat_inputs.get("amount") if flat_inputs.get("amount") not in [None, ""] else flat_inputs.get("quantity")
        if isinstance(raw_qty, str):
            s = raw_qty.strip()
            if "," in s and "." not in s:
                raw_qty = s.replace(",", ".")
            else:
                raw_qty = s.replace(",", "")
        try:
            quantity = float(raw_qty or 0)
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
                # S1K-F10: the activity unit must match the factor basis; "wells" with a per-event factor
                # (or "events" with a per-well-year factor, or "devices" / "components") used to switch
                # silently to another factor
                u_cnt = str(unit or "").strip().lower()
                fac_u = str(emission_factors.get("unit") or "").lower()
                fac_name = emission_factors.get("name") or flat_inputs.get("fuel") or "This factor"
                if u_cnt and u_cnt not in ("events", "event", "wells", "well"):
                    from .units import UnitError, unit_dimension
                    try:
                        is_count = unit_dimension(u_cnt)[0] == "count"
                    except UnitError:
                        is_count = False
                    if is_count:
                        raise ValueError(f"Liquids unloading is counted in events (per-event factors) or wells "
                                         f"(per well-year factors), not '{unit}'")
                if "/event" in fac_u and u_cnt in ("wells", "well"):
                    raise ValueError(f"'{fac_name}' is a per-event factor: give the number of unloading events "
                                     f"(unit 'events'), not wells")
                if "well-year" in fac_u and u_cnt in ("events", "event"):
                    raise ValueError(f"'{fac_name}' is a per well-year factor: give the number of wells "
                                     f"(unit 'wells'), not events")
                # the selected catalog row (Tables 6-10 / 6-11) names the type, frequency class and basin
                sel = unloading_row_selection(emission_factors.get("code"))
                u_type = flat_inputs.get("unloading_type") or flat_inputs.get("unload_type") or sel.get("type") or "plunger"

                is_explicit_tier1 = raw_tier in ["tier1", "tier_1", "t1", "1"] or calc_m in ["api_table_6_11", "table_6_11", "per_well"]                     or (sel.get("tier") == 1 and not raw_tier and not calc_m)
                is_explicit_tier2 = raw_tier in ["tier2", "tier_2", "t2", "2"] or calc_m in ["api_table_6_10", "table_6_10", "event_based"]                     or (sel.get("tier") == 2 and not raw_tier and not calc_m)
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
                        frequency_category=flat_inputs.get("frequency_category") or flat_inputs.get("freq_category")
                        or sel.get("frequency"),
                        region=flat_inputs.get("unload_region") or sel.get("region") or flat_inputs.get("region"),
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
                    # Table 6-11 is per well-YEAR: a record covers its own period (a month is its share of a year)
                    return calculator.calculate_tier1(
                        well_count=float(wc) * record_period(flat_inputs)[2] if wc not in (None, "") else wc,
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
                density_val = self._fuel_density(flat_inputs)
                # S1K-F11: a site HHV carries its own unit (MJ/m3, kcal/m3, Btu/gal ...)
                user_hu = None
                if flat_inputs.get("hhv") not in (None, ""):
                    hhv_val, user_hu = user_hhv(flat_inputs.get("hhv"), flat_inputs.get("hhv_unit"))
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
                        hhv_unit=user_hu or factor_hhv_unit(emission_factors),
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
                return calc_stationary_combustion(self, calculator, emission_factors, flat_inputs, gwp_dict, quantity, uncertainties, unit)

            elif process_type in ["flaring", "routine_flaring", "non_routine_flaring", "safety_flaring"]:
                return calc_flaring(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties, unit)

            elif process_type in ["drilling", "mud_degassing"]:
                return calc_drilling(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties, unit)

            elif process_type == "completions":
                return calc_completions(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties)

            elif process_type in ["liquids_unloading", "unloading"]:
                return calc_liquids_unloading(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties)

            elif process_type in ["venting", "blowdown"]:
                return calc_venting(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties, unit)

            elif process_type in ["associated_gas_venting", "associated_venting", "associated_gas"]:
                return calc_associated_gas_venting(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties)

            elif process_type in [
                "tank",
                "tank_flashing",
                "storage_tanks",
                "tank_working",
                "tank_breathing",
            ]:
                return calc_tank(self, calculator, emission_factors, flat_inputs, gwp_dict, process_type, uncertainties, unit)

            elif process_type in ["pneumatic_devices", "pneumatic_device", "pneumatic"]:
                return calc_pneumatic_devices(self, calculator, flat_inputs, gwp_dict, uncertainties)

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
                return calc_fugitive(self, emission_factors, flat_inputs, gwp_dict, process_type, uncertainties)

            elif process_type in ["compressor_seal", "compressor_fugitive"]:
                return calc_compressor_seal(self, calculator, flat_inputs, gwp_dict, uncertainties)

            elif process_type in ["agr", "acid_gas_removal"]:
                return calc_agr(self, calculator, flat_inputs, gwp_dict, uncertainties, unit)

            elif process_type in ["cogen_allocation", "cogen"]:
                return calc_cogen_allocation(self, calculator, flat_inputs, uncertainties)

            elif process_type in [
                "nitric_acid_production",
                "adipic_acid_production",
            ]:
                return calc_nitric_acid_production(self, calculator, emission_factors, flat_inputs, gwp_dict, process_type, uncertainties, unit)

            elif process_type in [
                "stoichiometry",
                "chemical_production",
                "asphalt_blowing",
                "asphalt",
            ]:
                return calc_stoichiometry(self, calculator, flat_inputs, gwp_dict, uncertainties, unit)

            elif process_type == "dehydrator":
                return calc_dehydrator(self, calculator, flat_inputs, gwp_dict, uncertainties)

            elif process_type == "indirect_steam":
                return calc_indirect_steam(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties)

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
            density=self._fuel_density(inputs) or emission_factors.get("density"),
            hhv_unit=factor_hhv_unit(emission_factors) or factor_hhv_unit(catalog),
            hours=hours,
            # hours in the record's year: a per-year factor over a leap-year month is days / 366
            year_hours=record_period(inputs)[0] / record_period(inputs)[2],
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
        _cat = PROCESS_CATEGORY.get(str(process_type).lower(), str(process_type).lower())

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


# Branch implementations of _dispatch_impl, split into their own modules; imported last because
# they use the helpers and imports defined above.
from .dispatcher_branches_combustion import calc_stationary_combustion, calc_flaring, calc_drilling, calc_completions, calc_liquids_unloading  # noqa: E402,F401
from .dispatcher_branches_venting import calc_venting, calc_associated_gas_venting, calc_tank, calc_pneumatic_devices, calc_dehydrator  # noqa: E402,F401
from .dispatcher_branches_fugitive import calc_fugitive, calc_compressor_seal, calc_agr, calc_cogen_allocation, calc_nitric_acid_production, calc_stoichiometry, calc_indirect_steam  # noqa: E402,F401
