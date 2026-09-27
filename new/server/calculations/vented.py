"""
API Compendium 2021 - Section 6: Vented and Process Emissions
Implementation of equations for mud degassing, completions, liquids unloading, 
blowdowns (with thermodynamic T & P corrections), tanks, and pneumatics.
"""

from .base import BaseCalculator
from .units import (
    CONVERSIONS,
    calculate_co2e,
    convert,
    to_psia,
    to_kelvin,
    STD_TEMP_K,
    STD_PRESSURE_PSIA,
    normalize_efficiency,
)
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
    Tier,
)
import math


def _split_vented_and_flared(
    total_gas_m3: float,
    ch4_tonnes: float,
    co2_tonnes: float,
    ctrl_eff: float,
    hhv: float = 1020.0,
    ef_n2o: float = None,
):
    """
    D-01 / API Compendium 2021 stoichiometric flaring partition helper.
    Partitions total gas into vented (1 - ctrl_eff) and flared (ctrl_eff).
    Flared combustion:
      - 98% CH4 converted to CO2 stoichiometrically: CH4 * 0.98 * (44.01 / 16.04)
      - Native CO2 in flared stream passes through unreacted
      - 2% unburnt CH4 emitted
      - N2O emitted = flared_mmbtu * (ef_n2o or 0.0001) where flared_scf = flared_m3 * (1 / scf_to_m3)
        and flared_mmbtu = flared_scf * (hhv or 1020.0) / 1e6.
        Catalog ef_n2o is in kg/MMBtu (default 0.0001 kg/MMBtu); convert to tonnes: / 1000.0.
    """
    ctrl = normalize_efficiency(ctrl_eff, default=0.0)
    vented_frac = 1.0 - ctrl

    vented_ch4 = ch4_tonnes * vented_frac
    vented_co2 = co2_tonnes * vented_frac

    flared_co2 = 0.0
    flared_unburnt_ch4 = 0.0
    flared_n2o = 0.0

    if ctrl > 0:
        flared_ch4_mass = ch4_tonnes * ctrl
        flared_native_co2 = co2_tonnes * ctrl

        # 98% combustion of CH4 to CO2
        flared_ch4_combusted = flared_ch4_mass * 0.98
        flared_co2 = (flared_ch4_combusted * (44.01 / 16.04)) + flared_native_co2
        flared_unburnt_ch4 = flared_ch4_mass * 0.02

        # N2O from energy of flared gas
        flared_m3 = total_gas_m3 * ctrl
        flared_scf = convert(flared_m3, "m3", "scf")
        hhv_val = float(hhv or 1020.0)
        flared_mmbtu = (flared_scf * hhv_val) / 1_000_000.0
        n2o_ef_kg = float(ef_n2o if ef_n2o is not None else 0.0001)
        flared_n2o = (flared_mmbtu * n2o_ef_kg) / 1000.0

    total_ch4 = vented_ch4 + flared_unburnt_ch4
    total_co2 = vented_co2 + flared_co2

    return {
        "vented_ch4": vented_ch4,
        "vented_co2": vented_co2,
        "flared_co2": flared_co2,
        "flared_unburnt_ch4": flared_unburnt_ch4,
        "flared_n2o": flared_n2o,
        "total_ch4": total_ch4,
        "total_co2": total_co2,
    }


def _propagate_vented_results(
    total_ch4: float,
    total_co2: float,
    flared_n2o: float,
    uncertainties: dict,
    factor_source: str = "specific",
    process_category: str = "vented",
):
    _tier = resolve_tier(factor_source)
    ch4_res = propagate_uncertainty(
        total_ch4,
        resolve_ef_uncertainty(process_category, "ch4", _tier, (uncertainties or {}).get("ch4")),
        tier=_tier,
        process_category=process_category,
        gas="ch4",
    )
    co2_res = (
        propagate_uncertainty(
            total_co2,
            resolve_ef_uncertainty(process_category, "co2", _tier, (uncertainties or {}).get("co2")),
            tier=_tier,
            process_category=process_category,
            gas="co2",
        )
        if total_co2 > 0
        else None
    )
    n2o_res = (
        propagate_uncertainty(
            flared_n2o,
            resolve_ef_uncertainty(process_category, "n2o", _tier, (uncertainties or {}).get("n2o")),
            tier=_tier,
            process_category=process_category,
            gas="n2o",
        )
        if flared_n2o > 0
        else None
    )
    return ch4_res, co2_res, n2o_res


class MudDegassingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Drilling Mud Degassing", "Section 6.2 & 6.3")

    # API Compendium Table 6-3: Default for natural gas well drilling (tonnes CH4 / well)
    TIER1_WELL_EF = 0.0524

    # API Compendium 2021 Table 6-2: Onshore mud degassing (tonnes CH4 / drilling day)
    TABLE_6_2_ONSHORE = {
        "water_based": 0.0458,
        "oil_based": 0.0103,
        "synthetic": 0.0103,
    }
    # API Compendium 2021 Table 6-2: Offshore mud degassing (tonnes CH4 / drilling day)
    TABLE_6_2_OFFSHORE = {
        "water_based": 0.2605,
        "oil_based": 0.0586,
        "synthetic": 0.0586,
    }
    DEFAULT_CH4_CONCENTRATION = 0.8385  # 83.85% molar default underlying Table 6-2

    def calculate(
        self,
        wells_or_tier=None,
        mud_type_or_wells=None,
        uncertainties=None,
        ef_ch4=None,
        gwp_dict=None,
        tier=None,
        wells=None,
        drilling_days=None,
        mud_type="water_based",
        ch4_concentration=None,
        co2_concentration=None,
        mud_volume=None,
        location="onshore",
    ):
        """
        API Compendium 2021 Drilling Mud Degassing:
        - Tier 1 (Table 6-3): Simplified API default: wells × 0.0524 t CH4/well
        - Tier 2 (Onshore defaults or Custom Factor from DB): drilling days × mud EF (water: 0.0458, oil: 0.0103 t CH4/day, or custom factor EF)
        - Tier 2+ (Onshore + Gas Composition): DD × EF × (X_CH4,site / 83.85%) [+ CO2 if X_CO2,site provided]
        """
        # Flexible argument unpacking to support legacy positional calls:
        if isinstance(wells_or_tier, (int, float)) and not isinstance(wells_or_tier, bool):
            if wells is None and drilling_days is None and mud_volume is None:
                wells = float(wells_or_tier)
        elif isinstance(wells_or_tier, str):
            if tier is None:
                tier = wells_or_tier

        if isinstance(mud_type_or_wells, str):
            mud_type = mud_type_or_wells
        elif isinstance(mud_type_or_wells, dict) and uncertainties is None:
            uncertainties = mud_type_or_wells

        uncertainties = uncertainties or {}

        # Determine calculation tier mode
        raw_source = str(uncertainties.get("_factor_source") or "").lower().strip()
        raw_tier = str(tier or "tier1").lower().strip()

        if (
            raw_tier in ["tier2_plus", "tier_2_plus", "tier2+", "tier_2+"]
            or raw_source in ["tier2_plus", "tier_2_plus", "tier2+", "tier_2+"]
            or (
                ch4_concentration is not None
                and (
                    float(ch4_concentration) != self.DEFAULT_CH4_CONCENTRATION
                    or (co2_concentration is not None and float(co2_concentration) > 0)
                )
            )
        ):
            tier_mode = "tier2_plus"
        elif (
            raw_tier in ["tier2", "tier_2", "custom", "t2"]
            or raw_source in ["tier2", "tier_2", "custom", "t2"]
            or (drilling_days is not None and wells is None)
        ):
            tier_mode = "tier2"
        else:
            tier_mode = "tier1"

        if tier_mode == "tier1":
            # Tier 1: Wells count
            w = float(
                wells
                if wells is not None
                else (drilling_days if drilling_days is not None else (mud_volume if mud_volume is not None else 1.0))
            )
            self.validate_inputs({"wells": w}, ["wells"])
            ef = (
                float(ef_ch4)
                if (ef_ch4 is not None and float(ef_ch4) > 0)
                else self.TIER1_WELL_EF
            )
            ch4_tonnes = w * ef
            co2_tonnes = 0.0
            resolved_tier_val = Tier.T1
            inputs_used = {
                "tier": "Tier 1",
                "wells": w,
                "ef_ch4_used": ef,
                "api_reference": "Table 6-3",
            }

        elif tier_mode == "tier2":
            # Tier 2: Drilling days * Table 6-2 mud EF
            dd = float(
                drilling_days
                if drilling_days is not None
                else (mud_volume if mud_volume is not None else (wells if wells is not None else 0.0))
            )
            self.validate_inputs({"drilling_days": dd}, ["drilling_days"])

            raw_type = str(mud_type or "water_based").lower().strip()
            norm_type = (
                "oil_based"
                if ("oil" in raw_type or "synth" in raw_type)
                else "water_based"
            )

            is_offshore = str(location or "onshore").lower().strip() == "offshore"
            mud_table = self.TABLE_6_2_OFFSHORE if is_offshore else self.TABLE_6_2_ONSHORE
            default_mud_ef = 0.2605 if is_offshore else 0.0458

            ef = (
                float(ef_ch4)
                if (ef_ch4 is not None and float(ef_ch4) > 0)
                else mud_table.get(norm_type, default_mud_ef)
            )
            ch4_tonnes = dd * ef
            co2_tonnes = 0.0
            resolved_tier_val = Tier.T2
            inputs_used = {
                "tier": "Tier 2",
                "drilling_days": dd,
                "mud_type": norm_type,
                "ef_ch4_used": ef,
                "location": "offshore" if is_offshore else "onshore",
                "api_reference": "API Compendium Table 6-2 (Offshore)" if is_offshore else "API Compendium Table 6-2 (Onshore)",
            }

        else:
            # Tier 2+: Drilling days * Table 6-2 mud EF * (X_CH4,site / 83.85%) [+ CO2 if X_CO2,site provided]
            dd = float(
                drilling_days
                if drilling_days is not None
                else (mud_volume if mud_volume is not None else (wells if wells is not None else 0.0))
            )
            self.validate_inputs({"drilling_days": dd}, ["drilling_days"])

            raw_type = str(mud_type or "water_based").lower().strip()
            norm_type = (
                "oil_based"
                if ("oil" in raw_type or "synth" in raw_type)
                else "water_based"
            )

            is_offshore = str(location or "onshore").lower().strip() == "offshore"
            mud_table = self.TABLE_6_2_OFFSHORE if is_offshore else self.TABLE_6_2_ONSHORE
            default_mud_ef = 0.2605 if is_offshore else 0.0458

            ef = (
                float(ef_ch4)
                if (ef_ch4 is not None and float(ef_ch4) > 0)
                else mud_table.get(norm_type, default_mud_ef)
            )

            x_ch4 = float(
                ch4_concentration
                if ch4_concentration is not None
                else self.DEFAULT_CH4_CONCENTRATION
            )
            if x_ch4 > 1.0:
                x_ch4 = x_ch4 / 100.0

            x_co2 = float(
                co2_concentration if co2_concentration is not None else 0.0
            )
            if x_co2 > 1.0:
                x_co2 = x_co2 / 100.0

            ch4_tonnes = dd * ef * (x_ch4 / self.DEFAULT_CH4_CONCENTRATION)
            if x_co2 > 0:
                # Stoichiometric molar mass conversion: (44.01 / 16.04)
                co2_tonnes = (
                    dd
                    * ef
                    * (x_co2 / self.DEFAULT_CH4_CONCENTRATION)
                    * (44.01 / 16.04)
                )
            else:
                co2_tonnes = 0.0

            resolved_tier_val = Tier.T2
            inputs_used = {
                "tier": "Tier 2+",
                "drilling_days": dd,
                "mud_type": norm_type,
                "ef_ch4_used": ef,
                "ch4_fraction": x_ch4,
                "co2_fraction": x_co2,
                "api_reference": "Table 6-2 (Onshore) + Site-Specific Gas Composition",
            }

        _tier = resolved_tier_val
        ch4_res = propagate_uncertainty(
            ch4_tonnes,
            resolve_ef_uncertainty("vented", "ch4", _tier, uncertainties.get("ch4")),
            tier=_tier,
            process_category="vented",
            gas="ch4",
        )
        co2_res = (
            propagate_uncertainty(
                co2_tonnes,
                resolve_ef_uncertainty("vented", "co2", _tier, uncertainties.get("co2")),
                tier=_tier,
                process_category="vented",
                gas="co2",
            )
            if co2_tonnes > 0
            else None
        )
        total_co2e = calculate_co2e(ch4=ch4_tonnes, co2=co2_tonnes, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            total_co2e=total_co2e,
            inputs=inputs_used,
        )


class CompletionFlowbackCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.2.3: Well Completions (Onshore).
    Implements the full 3-tier hierarchy:
      - Tier 1: API Tables 6-5 & 6-6 default emission factors (Oil vs Gas, Hydraulic Fracturing vs Non-HF,
        Uncontrolled Venting vs REC with Venting vs Flared, with Footnote c composition adjustments).
      - Tier 2: API Engineering calculations from operational data:
          * API Eq. 6-7: Average daily production rate * vent duration (for completions without HF)
          * Liquid flowback volume * GOR minus sales gas
          * Flowback rate * duration (with explicit unit conversion: Mcf/hr, Mcf/day, scf/hr, m3/day, m3/hr)
      - Tier 3: Direct / Metered Flowback:
          * API Eq. 6-4: Net flowback volume = V_t - EnF (injected N2 deduction; injected CO2 does not deduct)
          * API Eq. 6-5: Initial unmetered flowback V_i = (T_i * (V_gas / T_m)) / 2 (100% vented)
          * Fate partitioning: Vented, Flared (combusted with flare efficiency, N2O), and Recovered (REC / sales = 0 emissions)
    """

    TABLE_6_5 = {
        ("gas", "uncontrolled"): {"ch4": 28.8, "scf": 1842577.0, "code": "CompGasHF_Uncontrolled", "standard": "API Compendium 2021 §6.2.3.1, Table 6-5"},
        ("gas", "rec"): {"ch4": 13.542, "scf": 866413.0, "code": "CompGasHF_REC", "standard": "API Compendium 2021 §6.2.3.1, Table 6-5"},
        ("oil", "uncontrolled"): {"ch4": 14.419, "scf": 922498.0, "code": "CompOilHF_Uncontrolled", "standard": "API Compendium 2021 §6.2.3.1, Table 6-5"},
        ("oil", "rec"): {"ch4": 0.615, "scf": 39357.0, "code": "CompOilHF_REC", "standard": "API Compendium 2021 §6.2.3.1, Table 6-5"},
    }

    TABLE_6_6 = {
        ("gas", "uncontrolled"): {"ch4": 1.7376, "scf": 111173.0, "code": "CompGasNoHF_Vented", "standard": "API Compendium 2021 §6.2.3.2, Table 6-6"},
        ("gas", "vented"): {"ch4": 1.7376, "scf": 111173.0, "code": "CompGasNoHF_Vented", "standard": "API Compendium 2021 §6.2.3.2, Table 6-6"},
        ("oil", "uncontrolled"): {"ch4": 0.0141, "scf": 902.0, "code": "CompOilNoHF_Vented", "standard": "API Compendium 2021 §6.2.3.2, Table 6-6"},
        ("oil", "vented"): {"ch4": 0.0141, "scf": 902.0, "code": "CompOilNoHF_Vented", "standard": "API Compendium 2021 §6.2.3.2, Table 6-6"},
    }

    # API Compendium 2021 Table 6-7: Offshore well completions (tonnes CH4 / completion-day)
    TABLE_6_7 = {
        ("gas", "uncontrolled"): {"ch4": 136.2, "scf": 8700000.0, "code": "CompOffshoreGas", "standard": "API Compendium 2021 §6.2.3.3, Table 6-7"},
        ("gas", "vented"): {"ch4": 136.2, "scf": 8700000.0, "code": "CompOffshoreGas", "standard": "API Compendium 2021 §6.2.3.3, Table 6-7"},
        # Table 6-7 has no offshore oil-well row; oil wells are rejected rather than given the gas factor
    }

    DEFAULT_CH4_MOL_PCT = 0.816  # 81.6 mole % per API Footnote c

    def __init__(self):
        super().__init__("Well Completion Flowback", "Section 6.2.3")

    def _validate_non_negative(self, val, name):
        if val is not None:
            try:
                num = float(val)
                if num < 0:
                    raise ValueError(f"{name} cannot be negative (received {val})")
                return num
            except (ValueError, TypeError) as e:
                if "cannot be negative" in str(e):
                    raise
                raise ValueError(f"Invalid numeric value for {name}: {val}")
        return None

    def _normalize_fraction(self, val, name, default=0.0):
        if val is None or val == "":
            return default
        num = float(val)
        if num < 0:
            raise ValueError(f"{name} cannot be negative (received {val})")
        if num > 1.0:
            if num <= 100.0:
                num = num / 100.0
            else:
                raise ValueError(f"{name} must be between 0 and 1 (or 0% to 100%, received {val})")
        return num

    def calculate(
        self,
        flowback_volume=None,
        ch4_content=None,
        control_efficiency=None,
        uncertainties=None,
        co2_content=None,
        ef_co2=None,
        ef_ch4=None,
        ef_n2o=None,
        calculation_method=None,
        tier=None,
        well_type="gas",
        fracturing=None,
        control_type=None,
        flowback_rate=None,
        rate_unit="mscf/day",
        flowback_duration_hours=None,
        daily_production_rate=None,
        prod_rate_unit="mcf/day",
        vent_duration_hours=None,
        vent_duration_days=None,
        liquid_flowback_bbl=None,
        gas_oil_ratio=None,
        gas_produced_sales_scf=0.0,
        injected_n2_volume=0.0,
        injected_n2_unit="scf",
        injected_gas_type="n2",
        initial_flowback_hours=None,
        disposition=None,
        frac_vented=None,
        frac_flared=None,
        frac_recovered=None,
        volume_unit="m3",
        hhv=1020.0,
        gwp_dict=None,
        events=1.0,
        factor_code=None,
        choke_size_in=None,
        well_head_pressure=None,
        location="onshore",
    ):
        uncertainties = uncertainties or {}

        # 1. Non-negative validation for core physical inputs
        num_events = self._validate_non_negative(events, "Number of events")
        if num_events is None or num_events == 0:
            num_events = 1.0 if (events is None) else 0.0

        self._validate_non_negative(flowback_volume, "Flowback volume")
        self._validate_non_negative(flowback_rate, "Flowback rate")
        self._validate_non_negative(flowback_duration_hours, "Flowback duration")
        self._validate_non_negative(daily_production_rate, "Daily production rate")
        self._validate_non_negative(vent_duration_hours, "Vent duration hours")
        self._validate_non_negative(vent_duration_days, "Vent duration days")
        self._validate_non_negative(liquid_flowback_bbl, "Liquid flowback volume")
        self._validate_non_negative(gas_oil_ratio, "Gas-oil ratio (GOR)")
        self._validate_non_negative(gas_produced_sales_scf, "Gas produced to sales")
        self._validate_non_negative(injected_n2_volume, "Injected N2 volume")
        self._validate_non_negative(initial_flowback_hours, "Initial flowback duration")

        # 2. Fractions validation
        y_ch4 = self._normalize_fraction(
            ch4_content, "Methane (CH4) mole fraction", default=None
        )
        y_co2 = self._normalize_fraction(
            co2_content, "Carbon dioxide (CO2) mole fraction", default=0.0
        )
        if y_ch4 is not None and (y_ch4 + y_co2 > 1.001):
            raise ValueError(
                f"Sum of CH4 ({y_ch4*100:.1f}%) and CO2 ({y_co2*100:.1f}%) mole fractions cannot exceed 100%"
            )

        flare_eff = self._normalize_fraction(
            control_efficiency, "Flare control efficiency", default=0.98
        )

        # 3. Determine tier mode
        raw_tier = str(tier or "").lower().strip()
        raw_method = str(calculation_method or "").lower().strip()
        well_type_norm = str(well_type or "gas").lower().strip()
        if well_type_norm not in ["gas", "oil"]:
            well_type_norm = "oil" if "oil" in well_type_norm else "gas"

        is_hf = True
        if fracturing is not None:
            if isinstance(fracturing, bool):
                is_hf = fracturing
            else:
                is_hf = str(fracturing).lower().strip() in ["true", "1", "yes", "hf", "with_hf"]
        elif factor_code and "NoHF" in str(factor_code):
            is_hf = False

        if raw_tier in ["tier1", "t1", "1", "default", "factor"]:
            resolved_tier = "tier1"
        elif raw_tier in ["tier2", "t2", "2", "engineering"]:
            resolved_tier = "tier2"
        elif raw_tier in ["tier3", "t3", "3", "measured", "direct", "specific"]:
            resolved_tier = "tier3"
        else:
            # Auto-detect tier based on provided inputs
            if (
                daily_production_rate is not None
                or raw_method in ["production_rate_duration", "eq_6_7", "gor", "gor_liquid", "rate_duration"]
                or (flowback_rate is not None and flowback_duration_hours is not None)
                or (liquid_flowback_bbl is not None and gas_oil_ratio is not None)
            ):
                resolved_tier = "tier2"
            elif (
                (injected_n2_volume is not None and float(injected_n2_volume) > 0)
                or (initial_flowback_hours is not None and float(initial_flowback_hours) > 0)
                or (flowback_volume is not None and not factor_code)
                or raw_method == "metered_volume"
            ):
                resolved_tier = "tier3"
            else:
                resolved_tier = "tier1"

        hhv_val = float(hhv or 1020.0)
        n2o_ef_val = float(ef_n2o if ef_n2o is not None else 0.0001)

        # Handle zero-event or zero-volume cases cleanly
        if num_events == 0.0:
            ch4_res, co2_res, n2o_res = _propagate_vented_results(
                0.0, 0.0, 0.0, uncertainties=uncertainties, factor_source="default", process_category="completions"
            )
            return self.format_result(
                ch4=ch4_res, co2=co2_res, n2o=n2o_res, total_co2e=0.0,
                inputs={"tier": resolved_tier, "events": 0.0},
                metadata={"standard": "API Compendium §6.2.3", "calculation_method": resolved_tier}
            )

        # =====================================================================
        # TIER 1: API Compendium 2021 Tables 6-5 & 6-6 Default Factors
        # =====================================================================
        if resolved_tier == "tier1":
            ctrl = str(control_type or disposition or "uncontrolled").lower().strip()
            is_rec = "rec" in ctrl
            is_flared = "flare" in ctrl

            is_offshore = str(location or "onshore").lower().strip() == "offshore"
            if is_offshore:
                table_key = (well_type_norm, "uncontrolled")
                if table_key not in self.TABLE_6_7:
                    raise ValueError("API Compendium 2021 Table 6-7 gives an offshore completion factor for gas "
                                     "wells only; use a measured / engineering (Tier 3) method for this well")
                entry = self.TABLE_6_7[table_key]
                standard_ref = entry["standard"]
            elif is_hf:
                table_key = (well_type_norm, "rec" if is_rec else "uncontrolled")
                entry = self.TABLE_6_5.get(table_key, self.TABLE_6_5[("gas", "uncontrolled")])
                standard_ref = entry["standard"]
            else:
                table_key = (well_type_norm, "uncontrolled")
                entry = self.TABLE_6_6.get(table_key, self.TABLE_6_6[("gas", "uncontrolled")])
                standard_ref = entry["standard"]

            base_ch4_per_event = float(ef_ch4) if (ef_ch4 is not None and float(ef_ch4) > 0) else entry["ch4"]
            base_ch4_tonnes = base_ch4_per_event * num_events

            # Footnote c adjustments
            actual_ch4_mol = y_ch4 if y_ch4 is not None else self.DEFAULT_CH4_MOL_PCT
            ch4_adjusted = base_ch4_tonnes * (actual_ch4_mol / self.DEFAULT_CH4_MOL_PCT)

            co2_native = 0.0
            if y_co2 > 0 and actual_ch4_mol > 0:
                co2_adjusted = ch4_adjusted * (y_co2 / actual_ch4_mol) * (44.01 / 16.04)
            else:
                co2_adjusted = 0.0

            flared_n2o = 0.0
            if is_flared:
                unburnt_ch4 = ch4_adjusted * (1.0 - flare_eff)
                combusted_co2 = ch4_adjusted * flare_eff * (44.01 / 16.04)
                total_co2 = co2_adjusted + combusted_co2
                total_ch4 = unburnt_ch4

                scf_flared = entry["scf"] * num_events
                flared_mmbtu = (scf_flared * hhv_val) / 1_000_000.0
                flared_n2o = (flared_mmbtu * n2o_ef_val) / 1000.0
            else:
                total_ch4 = ch4_adjusted
                total_co2 = co2_adjusted

            ch4_res, co2_res, n2o_res = _propagate_vented_results(
                total_ch4=total_ch4,
                total_co2=total_co2,
                flared_n2o=flared_n2o,
                uncertainties=uncertainties,
                factor_source="default",
                process_category="completions",
            )
            total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

            return self.format_result(
                ch4=ch4_res,
                co2=co2_res,
                n2o=n2o_res,
                total_co2e=total_co2e,
                inputs={
                    "tier": "Tier 1",
                    "table": "Table 6-7" if is_offshore else ("Table 6-5" if is_hf else "Table 6-6"),
                    "location": "offshore" if is_offshore else "onshore",
                    "factor_code": entry["code"],
                    "well_type": well_type_norm,
                    "fracturing": is_hf,
                    "control_type": ctrl,
                    "events": num_events,
                    "base_ef_ch4_tonnes": base_ch4_per_event,
                    "ch4_content": actual_ch4_mol,
                    "co2_content": y_co2,
                    "whole_gas_scf": entry["scf"] * num_events,
                },
                metadata={
                    "standard": standard_ref,
                    "calculation_method": f"Tier 1: {entry['code']}",
                },
            )

        # =====================================================================
        # TIER 2 & TIER 3 VOLUMETRIC DETERMINATION
        # =====================================================================
        actual_ch4_mol = y_ch4 if y_ch4 is not None else 0.85
        actual_co2_mol = y_co2
        method = raw_method

        total_net_scf = 0.0
        initial_scf = 0.0
        standard_ref = "API Compendium 2021 §6.2.3"
        calc_method_label = "Tier 2: Engineering"

        if resolved_tier == "tier2":
            if method in ["production_rate_duration", "eq_6_7"] or (daily_production_rate is not None):
                # API Equation 6-7: V_CC = V_Pi * T (completions without HF)
                self.validate_inputs({"daily_production_rate": daily_production_rate}, ["daily_production_rate"])
                rate_val = float(daily_production_rate)
                unit_norm = str(prod_rate_unit or "mcf/day").lower().strip()
                if "mmscf" in unit_norm:
                    rate_scf_day = rate_val * 1_000_000.0
                elif "mcf" in unit_norm or "mscf" in unit_norm:
                    rate_scf_day = rate_val * 1000.0
                elif "m3" in unit_norm or "sm3" in unit_norm:
                    rate_scf_day = convert(rate_val, "m3", "scf")
                else:
                    rate_scf_day = rate_val

                if vent_duration_days is not None:
                    duration_days = float(vent_duration_days)
                elif vent_duration_hours is not None:
                    duration_days = float(vent_duration_hours) / 24.0
                else:
                    duration_days = float(flowback_duration_hours or 24.0) / 24.0

                total_net_scf = rate_scf_day * duration_days * num_events
                standard_ref = "API Compendium 2021 §6.2.3.2, Equation 6-7"
                calc_method_label = "Tier 2: Eq. 6-7 (Prod Rate × Duration)"

            elif method in ["gor", "gor_liquid"] or (liquid_flowback_bbl is not None and gas_oil_ratio is not None):
                # Liquid Flowback * GOR - sales gas
                self.validate_inputs(
                    {"liquid_flowback_bbl": liquid_flowback_bbl, "gas_oil_ratio": gas_oil_ratio},
                    ["liquid_flowback_bbl", "gas_oil_ratio"]
                )
                gross_scf = float(liquid_flowback_bbl) * float(gas_oil_ratio) * num_events
                sales_scf = float(gas_produced_sales_scf or 0.0)
                total_net_scf = max(0.0, gross_scf - sales_scf)
                standard_ref = "API Compendium 2021 §6.2.3.1, Flowback GOR"
                calc_method_label = "Tier 2: Liquid Flowback × GOR"

            else:
                # Rate * Duration
                self.validate_inputs(
                    {"flowback_rate": flowback_rate, "flowback_duration_hours": flowback_duration_hours},
                    ["flowback_rate", "flowback_duration_hours"]
                )
                rate_val = float(flowback_rate)
                # BUG-011: exact-token rate parsing ("mmscf/d" is not "mscf/d"); a plain volume is
                # not a rate and is rejected instead of being read as per-day.
                from .units import parse_volume_rate

                m3_per_unit, per_year = parse_volume_rate(rate_unit or "mcf/hr")
                if per_year is None:
                    raise ValueError(f"Flowback rate unit '{rate_unit}' must be a rate (e.g. Mcf/hr, MMscf/d)")
                rate_scf_hr = rate_val * m3_per_unit * CONVERSIONS["m3_to_scf"] * per_year / 8760.0

                total_net_scf = rate_scf_hr * float(flowback_duration_hours) * num_events
                standard_ref = "API Compendium 2021 §6.2.3.1, Flowback Rate × Duration"
                calc_method_label = "Tier 2: Flowback Rate × Duration"

        else:
            # TIER 3: Direct / Metered Flowback
            self.validate_inputs({"flowback_volume": flowback_volume}, ["flowback_volume"])
            raw_vol = float(flowback_volume or 0.0)
            u_norm = str(volume_unit or "m3").lower().strip()

            if u_norm in ["m3", "sm3", "cubic_meters"]:
                vol_scf_raw = convert(raw_vol, "m3", "scf")
            elif u_norm in ["mcf", "mscf"]:
                vol_scf_raw = raw_vol * 1000.0
            elif u_norm in ["mmscf"]:
                vol_scf_raw = raw_vol * 1_000_000.0
            else:
                vol_scf_raw = raw_vol

            # API Eq. 6-4: Net gas V_gas = V_t - EnF (injected N2 deduction)
            injected_n2_scf = 0.0
            gas_type_norm = str(injected_gas_type or "n2").lower().strip()
            if gas_type_norm != "co2" and injected_n2_volume:
                n2_val = float(injected_n2_volume)
                n2_u = str(injected_n2_unit or "scf").lower().strip()
                if n2_u in ["m3", "sm3"]:
                    injected_n2_scf = convert(n2_val, "m3", "scf")
                elif n2_u in ["mcf", "mscf"]:
                    injected_n2_scf = n2_val * 1000.0
                elif n2_u in ["mmscf"]:
                    injected_n2_scf = n2_val * 1_000_000.0
                else:
                    injected_n2_scf = n2_val

            net_scf_single = max(0.0, vol_scf_raw - injected_n2_scf)
            total_net_scf = net_scf_single * num_events

            # API Eq. 6-5: Initial unmetered flowback period
            if initial_flowback_hours and float(initial_flowback_hours) > 0:
                t_i = float(initial_flowback_hours)
                t_m = float(flowback_duration_hours or 0.0)
                if t_m <= 0:
                    raise ValueError("Metered flowback duration (Tm) cannot be zero when initial flowback duration is specified.")
                initial_scf = (t_i * (total_net_scf / t_m)) / 2.0

            standard_ref = "API Compendium 2021 §6.2.3.1, Equations 6-4 & 6-5"
            calc_method_label = "Tier 3: Metered Flowback"

        # =====================================================================
        # GAS FATE PARTITIONING & STOICHIOMETRIC CALCULATIONS
        # =====================================================================
        # Disposition options: 'vented', 'flared', 'rec' / 'recovered', 'split'
        disp = str(disposition or "").lower().strip()
        combustion_eff = 0.98
        if not disp:
            # Fallback to control_efficiency if disposition unstated (treated as flared routing fraction per D-01)
            if control_efficiency is not None and float(control_efficiency) > 0:
                f_flared = flare_eff
                f_vented = 1.0 - f_flared
                f_rec = 0.0
                combustion_eff = 0.98
            else:
                f_vented = 1.0
                f_flared = 0.0
                f_rec = 0.0
        elif disp in ["rec", "recovered", "green", "green_completion"]:
            f_vented = 0.0
            f_flared = 0.0
            f_rec = 1.0
        elif disp in ["flared", "flare"]:
            f_vented = 0.0
            f_flared = 1.0
            f_rec = 0.0
            combustion_eff = flare_eff if control_efficiency is not None else 0.98
        elif disp in ["vented", "vent"]:
            f_vented = 1.0
            f_flared = 0.0
            f_rec = 0.0
        elif disp in ["split", "custom"]:
            f_v = self._normalize_fraction(frac_vented, "Vented fraction", default=0.0)
            f_f = self._normalize_fraction(frac_flared, "Flared fraction", default=0.0)
            f_r = self._normalize_fraction(frac_recovered, "Recovered fraction", default=0.0)
            split_sum = f_v + f_f + f_r
            if abs(split_sum - 1.0) > 0.01:
                raise ValueError(
                    f"Disposition fractions (vented={f_v*100:.1f}%, flared={f_f*100:.1f}%, recovered={f_r*100:.1f}%) must sum to 100% (sum is {split_sum*100:.1f}%)"
                )
            f_vented = f_v
            f_flared = f_f
            f_rec = f_r
            combustion_eff = flare_eff if control_efficiency is not None else 0.98
        else:
            f_vented = 1.0
            f_flared = 0.0
            f_rec = 0.0

        # Initial flowback is 100% vented to atmosphere (API Compendium §6.2.3.1)
        vented_scf = initial_scf + (total_net_scf * f_vented)
        flared_scf = total_net_scf * f_flared
        recovered_scf = total_net_scf * f_rec

        # Conversions to m3 at standard conditions
        vented_m3 = convert(vented_scf, "scf", "m3")
        flared_m3 = convert(flared_scf, "scf", "m3")
        net_m3 = convert(total_net_scf, "scf", "m3")
        initial_m3 = convert(initial_scf, "scf", "m3")

        # 1. Vented Stream Emissions
        vented_ch4_tonnes = (vented_m3 * actual_ch4_mol * CONVERSIONS["density_ch4"]) / 1000.0
        vented_co2_tonnes = (vented_m3 * actual_co2_mol * CONVERSIONS["density_co2"]) / 1000.0

        # Initial breakdown
        init_vented_ch4_tonnes = (initial_m3 * actual_ch4_mol * CONVERSIONS["density_ch4"]) / 1000.0

        # 2. Flared Stream Emissions (Stoichiometric Combustion per API Section 5 & Exhibit 6-3)
        flared_gross_ch4_tonnes = (flared_m3 * actual_ch4_mol * CONVERSIONS["density_ch4"]) / 1000.0
        flared_native_co2_tonnes = (flared_m3 * actual_co2_mol * CONVERSIONS["density_co2"]) / 1000.0

        flared_unburnt_ch4 = flared_gross_ch4_tonnes * (1.0 - combustion_eff)
        flared_combustion_co2 = flared_gross_ch4_tonnes * combustion_eff * (44.01 / 16.04)
        flared_total_co2 = flared_native_co2_tonnes + flared_combustion_co2

        flared_mmbtu = (flared_scf * hhv_val) / 1_000_000.0
        flared_n2o = (flared_mmbtu * n2o_ef_val) / 1000.0 if flared_scf > 0 else 0.0

        # 3. Aggregated Totals
        total_ch4 = vented_ch4_tonnes + flared_unburnt_ch4
        total_co2 = vented_co2_tonnes + flared_total_co2
        total_n2o = flared_n2o

        resolved_tier_enum = Tier.T3 if resolved_tier == "tier3" else (Tier.T2 if resolved_tier == "tier2" else Tier.T1)
        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=total_n2o,
            uncertainties=uncertainties,
            factor_source="site_specific" if resolved_tier in ["tier2", "tier3"] else "default",
            process_category="completions",
        )
        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=total_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "tier": resolved_tier.capitalize(),
                "method": calc_method_label,
                "events": num_events,
                "net_flowback_m3": net_m3,
                "net_flowback_scf": total_net_scf,
                "initial_flowback_m3": initial_m3,
                "initial_flowback_scf": initial_scf,
                "initial_vented_ch4_tonnes": init_vented_ch4_tonnes,
                "flared_unburnt_ch4_tonnes": flared_unburnt_ch4,
                "flared_combustion_co2_tonnes": flared_combustion_co2,
                "injected_n2_deducted_scf": injected_n2_scf if resolved_tier == "tier3" else 0.0,
                "disposition": disp or ("flared" if f_flared > 0 else "vented"),
                "ch4_content": actual_ch4_mol,
                "co2_content": actual_co2_mol,
                "control_efficiency": flare_eff,
                "frac_vented": f_vented,
                "frac_flared": f_flared,
                "frac_recovered": f_rec,
            },
            metadata={
                "standard": standard_ref,
                "calculation_method": calc_method_label,
            },
        )



class LiquidsUnloadingCalculator(BaseCalculator):
    """
    API Compendium 2021 - Section 6.3.4: Well Venting from Liquids Unloading.
    Supports complete tier hierarchy:
      - Tier 1: API Table 6-11 per-well default factors (plunger and non-plunger)
      - Tier 2: API Table 6-10 event-based factors (average and regional)
      - Tier 3: Engineering and measured data:
          * API Eq. 6-10 (EPA Subpart W integrated W-8/W-9)
          * API Eq. 6-11 (Automated plunger lift vent rate)
          * API Eq. 6-3 (Volume-based wellbore decompression geometry)
    """

    # --- API TABLE 6-11: TIER 1 PER-WELL VENTED EMISSION FACTORS ---
    TABLE_6_11 = {
        "plunger": {
            "ch4_kg_per_well_yr": 1774.0,
            "ch4_tonnes_per_well_yr": 1.774,
            "whole_gas_scf_per_well_yr": 113466.0,
            "default_ch4_mol_pct": 81.6,
            "uncertainty": {"ch4": 0.50, "co2": 0.50},
        },
        "non_plunger": {
            "ch4_kg_per_well_yr": 2792.0,
            "ch4_tonnes_per_well_yr": 2.792,
            "whole_gas_scf_per_well_yr": 178531.0,
            "default_ch4_mol_pct": 81.6,
            "uncertainty": {"ch4": 0.50, "co2": 0.50},
        },
    }

    # --- API TABLE 6-10: TIER 2 EVENT-BASED EMISSION FACTORS (AVERAGE) ---
    TABLE_6_10_AVERAGE = {
        "plunger_le100": {
            "scf_ch4_event": 9650.0,
            "tonnes_ch4_event": 0.185,
            "scf_gas_event": 11308.0,
            "ch4_mol_pct": 85.3,
            "uncertainty": {"ch4": 0.285},
        },
        "plunger_gt100": {
            "scf_ch4_event": 1260.0,
            "tonnes_ch4_event": 0.024,
            "scf_gas_event": 1503.0,
            "ch4_mol_pct": 83.9,
            "uncertainty": {"ch4": 0.667},
        },
        "non_plunger_le10": {
            "scf_ch4_event": 21500.0,
            "tonnes_ch4_event": 0.412,
            "scf_gas_event": 24109.0,
            "ch4_mol_pct": 89.2,
            "uncertainty": {"ch4": 0.758},
        },
        "non_plunger_10_to_50": {
            "scf_ch4_event": 24100.0,
            "tonnes_ch4_event": 0.462,
            "scf_gas_event": 25690.0,
            "ch4_mol_pct": 93.8,
            "uncertainty": {"ch4": 1.09},
        },
        "non_plunger_gt50": {
            "scf_ch4_event": 35000.0,
            "tonnes_ch4_event": 0.670,
            "scf_gas_event": 36512.0,
            "ch4_mol_pct": 95.9,
            "uncertainty": {"ch4": 0.514},
        },
    }

    # --- API TABLE 6-10: TIER 2 REGIONAL EMISSION FACTORS ---
    TABLE_6_10_REGIONAL = {
        "appalachia": {
            "plunger_le100": {"scf_ch4": 5100.0, "tonnes_ch4": 0.098, "scf_gas": 5172.0, "ch4_mol_pct": 98.6, "uncertainty": {"ch4": 0.470}},
            "plunger_gt100": {"scf_ch4": 1260.0, "tonnes_ch4": 0.024, "scf_gas": 1278.0, "ch4_mol_pct": 98.6, "uncertainty": {"ch4": 0.667}},
            "non_plunger": {"scf_ch4": 4550.0, "tonnes_ch4": 0.087, "scf_gas": 4615.0, "ch4_mol_pct": 98.6, "uncertainty": {"ch4": 0.912}},
        },
        "gulf_coast": {
            "plunger_le100": {"scf_ch4": 9650.0, "tonnes_ch4": 0.185, "scf_gas": 9807.0, "ch4_mol_pct": 98.4, "uncertainty": {"ch4": 0.285}},
            "plunger_gt100": {"scf_ch4": 1260.0, "tonnes_ch4": 0.024, "scf_gas": 1280.0, "ch4_mol_pct": 98.4, "uncertainty": {"ch4": 0.667}},
            "non_plunger": {"scf_ch4": 13300.0, "tonnes_ch4": 0.255, "scf_gas": 13516.0, "ch4_mol_pct": 98.4, "uncertainty": {"ch4": 0.271}},
        },
        "midcontinent": {
            "plunger_le100": {"scf_ch4": 6400.0, "tonnes_ch4": 0.123, "scf_gas": 6544.0, "ch4_mol_pct": 97.8, "uncertainty": {"ch4": 0.563}},
            "plunger_gt100": {"scf_ch4": 300.0, "tonnes_ch4": 0.006, "scf_gas": 307.0, "ch4_mol_pct": 97.8, "uncertainty": {"ch4": 0.550}},
            "non_plunger": {"scf_ch4": 47800.0, "tonnes_ch4": 0.916, "scf_gas": 48875.0, "ch4_mol_pct": 97.8, "uncertainty": {"ch4": 0.504}},
        },
        "rocky_mountain": {
            "plunger_le100": {"scf_ch4": 12600.0, "tonnes_ch4": 0.241, "scf_gas": 14433.0, "ch4_mol_pct": 87.3, "uncertainty": {"ch4": 0.381}},
            "plunger_gt100": {"scf_ch4": 1400.0, "tonnes_ch4": 0.027, "scf_gas": 1604.0, "ch4_mol_pct": 87.3, "uncertainty": {"ch4": 0.857}},
            "non_plunger": {"scf_ch4": 15200.0, "tonnes_ch4": 0.291, "scf_gas": 17411.0, "ch4_mol_pct": 87.3, "uncertainty": {"ch4": 0.382}},
        },
    }

    # API Standard Molar Conversion Factors (at 60°F, 14.696 psia: 379.3 scf/lbmol, 2204.6226 lb/tonne)
    # Mass (tonnes) = scf * MW / (379.3 * 2204.6226218)
    SCF_TO_TONNES_CH4 = 16.04 / (379.3 * 2204.6226218)  # ≈ 1.9184852e-5
    SCF_TO_TONNES_CO2 = 44.01 / (379.3 * 2204.6226218)  # ≈ 5.263158e-5

    def __init__(self):
        super().__init__("Liquids Unloading", "Section 6.3.4")

    def _normalize_unloading_type(self, raw_type: str) -> str:
        s = str(raw_type or "").lower().strip().replace(" ", "_").replace("-", "_")
        if "non" in s or "without" in s:
            return "non_plunger"
        if "plunger" in s:
            return "plunger"
        return "plunger"

    def _validate_fraction(self, val, default=0.0, name="fraction"):
        if val is None or val == "" or val == "-":
            return default
        try:
            f = float(val)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid numeric value for {name}: {val}")
        if f < 0.0:
            raise ValueError(f"{name} cannot be negative: {f}")
        if f > 1.0:
            if f <= 100.0:
                f /= 100.0
            else:
                raise ValueError(f"{name} cannot exceed 100%: {val}")
        return max(0.0, min(1.0, f))

    def calculate_tier1(
        self,
        well_count,
        unloading_type="plunger",
        ch4_content=None,
        co2_content=0.0,
        control_efficiency=0.0,
        factor_key=None,
        uncertainties=None,
        hhv=1020.0,
        ef_n2o=None,
        gwp_dict=None,
    ):
        """
        API Compendium 2021 Section 6.3.4 / Table 6-11:
        Tier 1: Per-well default vented emission factors.
        Used when the number of unloading events is not available.
        """
        if well_count is None or str(well_count).strip() == "":
            raise ValueError("Number of wells is required for Tier 1 calculation.")
        try:
            wells = float(well_count)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid well count: {well_count}")
        if wells < 0:
            raise ValueError("Number of wells cannot be negative.")
        if wells > 100000:
            raise ValueError(f"Unrealistic number of wells: {wells}")

        u_type = self._normalize_unloading_type(unloading_type)
        t1_data = self.TABLE_6_11[u_type]

        c_ch4 = self._validate_fraction(ch4_content, default=t1_data["default_ch4_mol_pct"] / 100.0, name="Gas CH4 content")
        c_co2 = self._validate_fraction(co2_content, default=0.0, name="Gas CO2 content")
        if c_ch4 + c_co2 > 1.0001:
            raise ValueError(f"Combined CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) content cannot exceed 100%.")

        if wells == 0:
            return self.format_result(
                ch4=None,
                co2=None,
                n2o=None,
                total_co2e=0.0,
                inputs={
                    "tier": "Tier 1",
                    "method": "api_table_6_11",
                    "calculation_level": "Tier 1 (API Table 6-11)",
                    "unloading_type": u_type,
                    "well_count": 0,
                    "amount": 0,
                    "unit": "wells",
                    "whole_gas_scf": 0.0,
                    "whole_gas_m3": 0.0,
                    "ch4_content": c_ch4,
                    "co2_content": c_co2,
                    "control_efficiency": 0.0,
                    "api_reference": "API Compendium 2021 Section 6.3.4, Table 6-11",
                },
            )

        total_gas_scf = wells * t1_data["whole_gas_scf_per_well_yr"]
        total_gas_m3 = total_gas_scf * CONVERSIONS["scf_to_m3"]

        # Footnote b: adjust based on site-specific CH4/CO2 content
        default_basis = t1_data["default_ch4_mol_pct"] / 100.0
        if ch4_content is not None and abs(c_ch4 - default_basis) > 1e-4:
            ch4_tonnes = total_gas_scf * c_ch4 * self.SCF_TO_TONNES_CH4
        else:
            ch4_tonnes = wells * t1_data["ch4_tonnes_per_well_yr"]

        co2_tonnes = total_gas_scf * c_co2 * self.SCF_TO_TONNES_CO2

        ctrl_eff = normalize_efficiency(control_efficiency, default=0.0)
        split = _split_vented_and_flared(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=ch4_tonnes,
            co2_tonnes=co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )

        unc = dict(uncertainties or {})
        unc.setdefault("ch4", t1_data["uncertainty"]["ch4"])
        unc.setdefault("co2", t1_data["uncertainty"]["co2"])
        unc["_factor_source"] = "default"

        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=split["total_ch4"],
            total_co2=split["total_co2"],
            flared_n2o=split["flared_n2o"],
            uncertainties=unc,
            factor_source="default",
            process_category="vented",
        )

        total_co2e = calculate_co2e(
            ch4=split["total_ch4"],
            co2=split["total_co2"],
            n2o=split["flared_n2o"],
            gwp_dict=gwp_dict,
        )

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "tier": "Tier 1",
                "method": "api_table_6_11",
                "calculation_level": "Tier 1 (API Table 6-11)",
                "unloading_type": u_type,
                "well_count": wells,
                "amount": wells,
                "unit": "wells",
                "whole_gas_scf": total_gas_scf,
                "whole_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "control_efficiency": ctrl_eff,
                "api_reference": "API Compendium 2021 Section 6.3.4, Table 6-11",
            },
        )

    def calculate_tier2(
        self,
        events,
        unloading_type="plunger",
        well_count=1,
        frequency_category=None,
        region=None,
        ch4_content=None,
        co2_content=0.0,
        control_efficiency=0.0,
        factor_key=None,
        uncertainties=None,
        hhv=1020.0,
        ef_n2o=None,
        gwp_dict=None,
    ):
        """
        API Compendium 2021 Section 6.3.4 / Table 6-10:
        Tier 2: Event-based vented emission factors for wells.
        """
        if events is None or str(events).strip() == "":
            raise ValueError("Number of unloading events is required for Tier 2 calculation.")
        try:
            ev = float(events)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid unloading events: {events}")
        if ev < 0:
            raise ValueError("Number of unloading events cannot be negative.")

        wc = float(well_count or 1)
        if wc <= 0:
            raise ValueError("Number of wells must be greater than zero.")

        u_type = self._normalize_unloading_type(unloading_type)

        # Invariant: zero events results in zero emissions
        if ev == 0:
            return self.format_result(
                ch4={"value": 0.0, "uncertainty": 0.0},
                co2={"value": 0.0, "uncertainty": 0.0},
                n2o={"value": 0.0, "uncertainty": 0.0},
                total_co2e=0.0,
                inputs={
                    "tier": "Tier 2",
                    "method": "api_table_6_10",
                    "unloading_type": u_type,
                    "events": 0,
                    "well_count": wc,
                },
            )

        total_events = ev * wc
        ev_per_well = ev  # per well-year basis for threshold

        # Resolve Table 6-10 factor
        reg_key = str(region or "").lower().strip().replace(" ", "_").replace("-", "_")
        selected_factor = None
        unc_val = 0.50

        if reg_key in self.TABLE_6_10_REGIONAL:
            reg_dict = self.TABLE_6_10_REGIONAL[reg_key]
            if u_type == "plunger":
                sub_key = "plunger_le100" if ev_per_well <= 100 else "plunger_gt100"
                selected_factor = reg_dict[sub_key]
            else:
                selected_factor = reg_dict["non_plunger"]
        else:
            # Average factors
            if u_type == "plunger":
                cat = frequency_category or ("plunger_le100" if ev_per_well <= 100 else "plunger_gt100")
                selected_factor = self.TABLE_6_10_AVERAGE.get(cat, self.TABLE_6_10_AVERAGE["plunger_le100"])
            else:
                if frequency_category:
                    cat = frequency_category
                elif ev_per_well <= 10:
                    cat = "non_plunger_le10"
                elif ev_per_well <= 50:
                    cat = "non_plunger_10_to_50"
                else:
                    cat = "non_plunger_gt50"
                selected_factor = self.TABLE_6_10_AVERAGE.get(cat, self.TABLE_6_10_AVERAGE["non_plunger_le10"])

        unc_val = selected_factor.get("uncertainty", {}).get("ch4", 0.50)
        wgf = selected_factor.get("scf_gas_event") or selected_factor.get("scf_gas")
        ef_tonnes = selected_factor.get("tonnes_ch4_event") or selected_factor.get("tonnes_ch4")
        base_mol_pct = selected_factor.get("ch4_mol_pct", 85.0)

        c_ch4 = self._validate_fraction(ch4_content, default=base_mol_pct / 100.0, name="Gas CH4 content")
        c_co2 = self._validate_fraction(co2_content, default=0.0, name="Gas CO2 content")
        if c_ch4 + c_co2 > 1.0001:
            raise ValueError(f"Combined CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) content cannot exceed 100%.")

        total_gas_scf = total_events * wgf
        total_gas_m3 = total_gas_scf * CONVERSIONS["scf_to_m3"]

        # If site-specific CH4 fraction is provided, convert whole gas; otherwise use catalog tonnes EF
        if ch4_content is not None and abs(c_ch4 - (base_mol_pct / 100.0)) > 1e-4:
            ch4_tonnes = total_gas_scf * c_ch4 * self.SCF_TO_TONNES_CH4
        else:
            ch4_tonnes = total_events * ef_tonnes

        co2_tonnes = total_gas_scf * c_co2 * self.SCF_TO_TONNES_CO2

        ctrl_eff = normalize_efficiency(control_efficiency, default=0.0)
        split = _split_vented_and_flared(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=ch4_tonnes,
            co2_tonnes=co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )

        unc = dict(uncertainties or {})
        unc.setdefault("ch4", unc_val)
        unc.setdefault("co2", unc_val)
        unc["_factor_source"] = "custom"

        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=split["total_ch4"],
            total_co2=split["total_co2"],
            flared_n2o=split["flared_n2o"],
            uncertainties=unc,
            factor_source="custom",
            process_category="vented",
        )

        total_co2e = calculate_co2e(
            ch4=split["total_ch4"],
            co2=split["total_co2"],
            n2o=split["flared_n2o"],
            gwp_dict=gwp_dict,
        )

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "tier": "Tier 2",
                "method": "api_table_6_10",
                "calculation_level": "Tier 2 (API Table 6-10)",
                "unloading_type": u_type,
                "events": ev,
                "well_count": wc,
                "total_events": total_events,
                "region": region or "Average",
                "whole_gas_scf": total_gas_scf,
                "whole_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "control_efficiency": ctrl_eff,
                "api_reference": "API Compendium 2021 Section 6.3.4, Table 6-10",
            },
        )

    def calculate_tier3_equation_6_10(
        self,
        events,
        well_depth,
        diameter,
        pressure,
        sfr=0.0,
        hours_open=0.0,
        unloading_type="non_plunger",
        well_count=1,
        ch4_content=0.85,
        co2_content=0.0,
        control_efficiency=0.0,
        depth_unit="ft",
        diameter_unit="in",
        press_unit="psig",
        sfr_unit="scf/hr",
        uncertainties=None,
        hhv=1020.0,
        ef_n2o=None,
        gwp_dict=None,
    ):
        """
        API Compendium 2021 Section 6.3.4 / Equation 6-10 (EPA GHGRP Subpart W W-8 / W-9):
        VR = (# events / well-year * 0.37e-3 * D^2 * Depth * P) + (SFR * (HR - X) * Z)
        """
        # Validate inputs
        if well_depth is None or float(well_depth) <= 0:
            raise ValueError("Well depth must be greater than zero for Equation 6-10.")
        if diameter is None or float(diameter) <= 0:
            raise ValueError("Tubing/casing diameter must be greater than zero for Equation 6-10.")
        if pressure is None:
            raise ValueError("Flow-line pressure is required for Equation 6-10.")
        if events is None or float(events) < 0:
            raise ValueError("Number of unloading events cannot be negative.")

        ev = float(events)
        wc = float(well_count or 1)
        if wc <= 0:
            raise ValueError("Number of wells must be greater than zero.")

        u_type = self._normalize_unloading_type(unloading_type)

        # Invariant: zero events and zero flow-line time results in zero emissions
        sfr_val = max(0.0, float(sfr or 0.0))
        hr_val = max(0.0, float(hours_open or 0.0))
        if ev == 0 and (sfr_val == 0 or hr_val == 0):
            return self.format_result(
                ch4={"value": 0.0, "uncertainty": 0.0},
                co2={"value": 0.0, "uncertainty": 0.0},
                n2o={"value": 0.0, "uncertainty": 0.0},
                total_co2e=0.0,
                inputs={"tier": "Tier 3", "method": "api_equation_6_10", "events": 0},
            )

        # Diameter conversion to inches (D)
        d_val = float(diameter)
        du = str(diameter_unit or "in").lower().strip()
        if du in ["mm", "millimeter", "millimeters"]:
            d_in = d_val / 25.4
        elif du in ["cm", "centimeter", "centimeters"]:
            d_in = d_val / 2.54
        elif du in ["m", "meter", "meters"]:
            d_in = d_val / 0.0254
        elif du in ["ft", "feet"]:
            d_in = d_val * 12.0
        else:  # 'in', 'inch', 'inches'
            d_in = d_val
        if d_in <= 0 or d_in > 60:
            raise ValueError(f"Unrealistic well diameter: {d_in:.2f} inches.")

        # Depth conversion to feet (Depth)
        dep_val = float(well_depth)
        dep_u = str(depth_unit or "ft").lower().strip()
        if dep_u in ["m", "meter", "meters"]:
            depth_ft = dep_val / 0.3048
        elif dep_u in ["km", "kilometer"]:
            depth_ft = (dep_val * 1000.0) / 0.3048
        else:  # 'ft', 'feet'
            depth_ft = dep_val
        if depth_ft <= 0 or depth_ft > 50000:
            raise ValueError(f"Unrealistic well depth: {depth_ft:.1f} feet.")

        # Pressure conversion to psig (P)
        p_val = float(pressure)
        pu = str(press_unit or "psig").lower().strip()
        p_abs = to_psia(p_val, pu)
        p_psig = max(0.0, p_abs - STD_PRESSURE_PSIA)

        # SFR conversion to scf/hr
        sfru = str(sfr_unit or "scf/hr").lower().strip()
        if "day" in sfru:
            if "m3" in sfru:
                sfr_scf_hr = (sfr_val * CONVERSIONS["m3_to_scf"]) / 24.0
            else:
                sfr_scf_hr = sfr_val / 24.0
        elif "m3" in sfru:
            sfr_scf_hr = sfr_val * CONVERSIONS["m3_to_scf"]
        elif "mcf" in sfru or "mscf" in sfru:
            sfr_scf_hr = sfr_val * 1000.0
        else:
            sfr_scf_hr = sfr_val

        # Equation 6-10 parameters:
        # X: 0.5 for plunger lift, 1.0 for non-plunger
        x_param = 0.5 if u_type == "plunger" else 1.0
        # Z: If HR < 1.0, Z is 0; if HR >= 1.0, Z is 1
        z_param = 1.0 if hr_val >= 1.0 else 0.0

        wellbore_vol_scf = ev * (0.37e-3) * (d_in ** 2) * depth_ft * p_psig
        flowline_vol_scf = sfr_scf_hr * max(0.0, hr_val - x_param) * z_param
        vr_per_well_scf = wellbore_vol_scf + flowline_vol_scf

        total_gas_scf = wc * vr_per_well_scf
        total_gas_m3 = total_gas_scf * CONVERSIONS["scf_to_m3"]

        c_ch4 = self._validate_fraction(ch4_content, default=0.85, name="Gas CH4 content")
        c_co2 = self._validate_fraction(co2_content, default=0.0, name="Gas CO2 content")
        if c_ch4 + c_co2 > 1.0001:
            raise ValueError(f"Combined CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) content cannot exceed 100%.")

        ch4_tonnes = total_gas_scf * c_ch4 * self.SCF_TO_TONNES_CH4
        co2_tonnes = total_gas_scf * c_co2 * self.SCF_TO_TONNES_CO2

        ctrl_eff = normalize_efficiency(control_efficiency, default=0.0)
        split = _split_vented_and_flared(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=ch4_tonnes,
            co2_tonnes=co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )

        unc = dict(uncertainties or {})
        unc.setdefault("ch4", 0.15)
        unc.setdefault("co2", 0.15)
        unc["_factor_source"] = "specific"

        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=split["total_ch4"],
            total_co2=split["total_co2"],
            flared_n2o=split["flared_n2o"],
            uncertainties=unc,
            factor_source="specific",
            process_category="vented",
        )

        total_co2e = calculate_co2e(
            ch4=split["total_ch4"],
            co2=split["total_co2"],
            n2o=split["flared_n2o"],
            gwp_dict=gwp_dict,
        )

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "tier": "Tier 3",
                "method": "api_equation_6_10",
                "calculation_level": "Tier 3 Engineering (API Eq. 6-10)",
                "unloading_type": u_type,
                "events": ev,
                "well_count": wc,
                "diameter_in": d_in,
                "depth_ft": depth_ft,
                "pressure_psig": p_psig,
                "sfr_scf_hr": sfr_scf_hr,
                "hours_open": hr_val,
                "x_param": x_param,
                "z_param": z_param,
                "vr_per_well_scf": vr_per_well_scf,
                "whole_gas_scf": total_gas_scf,
                "whole_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "control_efficiency": ctrl_eff,
                "api_reference": "API Compendium 2021 Section 6.3.4, Equation 6-10",
            },
        )

    def calculate_tier3_equation_6_11(
        self,
        p_shut,
        p_line,
        p_sep,
        sfr_p,
        t_p,
        events=1,
        well_count=1,
        p_atm=14.696,
        ch4_content=0.85,
        co2_content=0.0,
        control_efficiency=0.0,
        press_unit="psia",
        sfr_unit="scf/hr",
        uncertainties=None,
        hhv=1020.0,
        ef_n2o=None,
        gwp_dict=None,
    ):
        """
        API Compendium 2021 Section 6.3.4 / Equation 6-11:
        VR = sqrt(Pshut - Patm) / sqrt(Pline - Psep) * SFRp * Tp
        Vented emissions from automated plunger lift well unloading.
        """
        if p_shut is None or p_line is None or p_sep is None:
            raise ValueError("Pressures (Pshut, Pline, Psep) are required for Equation 6-11.")
        if sfr_p is None:
            raise ValueError("Production rate SFRp is required for Equation 6-11.")
        if t_p is None:
            raise ValueError("Venting time Tp is required for Equation 6-11.")

        ev = float(events if events is not None else 1)
        wc = float(well_count or 1)
        if ev < 0:
            raise ValueError("Number of unloading events cannot be negative.")
        if wc <= 0:
            raise ValueError("Number of wells must be greater than zero.")

        # Normalize pressures to psia
        p_shut_abs = to_psia(p_shut, press_unit)
        p_line_abs = to_psia(p_line, press_unit)
        p_sep_abs = to_psia(p_sep, press_unit)
        p_atm_abs = to_psia(p_atm, "psia")

        if p_shut_abs < p_atm_abs:
            raise ValueError(f"Shut-in pressure ({p_shut_abs:.2f} psia) must be greater than or equal to atmospheric pressure ({p_atm_abs:.2f} psia).")
        if p_line_abs <= p_sep_abs:
            raise ValueError(f"Line pressure ({p_line_abs:.2f} psia) must be strictly greater than separator pressure ({p_sep_abs:.2f} psia) for Equation 6-11.")

        sfr_val = max(0.0, float(sfr_p))
        tp_val = max(0.0, float(t_p))

        # Invariant: 0 events or 0 time/rate yields 0 emissions
        if ev == 0 or sfr_val == 0 or tp_val == 0:
            return self.format_result(
                ch4={"value": 0.0, "uncertainty": 0.0},
                co2={"value": 0.0, "uncertainty": 0.0},
                n2o={"value": 0.0, "uncertainty": 0.0},
                total_co2e=0.0,
                inputs={"tier": "Tier 3", "method": "api_equation_6_11", "events": 0},
            )

        # Normalize SFRp to scf/hr
        sfru = str(sfr_unit or "scf/hr").lower().strip()
        if "day" in sfru:
            if "m3" in sfru:
                sfr_rate = (sfr_val * CONVERSIONS["m3_to_scf"]) / 24.0
            else:
                sfr_rate = sfr_val / 24.0
        elif "m3" in sfru:
            sfr_rate = sfr_val * CONVERSIONS["m3_to_scf"]
        elif "mcf" in sfru or "mscf" in sfru:
            sfr_rate = sfr_val * 1000.0
        else:
            sfr_rate = sfr_val

        # Equation 6-11: VR = sqrt(Pshut - Patm) / sqrt(Pline - Psep) * SFRp * Tp
        press_ratio = math.sqrt(p_shut_abs - p_atm_abs) / math.sqrt(p_line_abs - p_sep_abs)
        vr_scf = press_ratio * sfr_rate * tp_val

        total_gas_scf = vr_scf * ev * wc
        total_gas_m3 = total_gas_scf * CONVERSIONS["scf_to_m3"]

        c_ch4 = self._validate_fraction(ch4_content, default=0.85, name="Gas CH4 content")
        c_co2 = self._validate_fraction(co2_content, default=0.0, name="Gas CO2 content")
        if c_ch4 + c_co2 > 1.0001:
            raise ValueError(f"Combined CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) content cannot exceed 100%.")

        ch4_tonnes = total_gas_scf * c_ch4 * self.SCF_TO_TONNES_CH4
        co2_tonnes = total_gas_scf * c_co2 * self.SCF_TO_TONNES_CO2

        ctrl_eff = normalize_efficiency(control_efficiency, default=0.0)
        split = _split_vented_and_flared(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=ch4_tonnes,
            co2_tonnes=co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )

        unc = dict(uncertainties or {})
        unc.setdefault("ch4", 0.15)
        unc.setdefault("co2", 0.15)
        unc["_factor_source"] = "specific"

        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=split["total_ch4"],
            total_co2=split["total_co2"],
            flared_n2o=split["flared_n2o"],
            uncertainties=unc,
            factor_source="specific",
            process_category="vented",
        )

        total_co2e = calculate_co2e(
            ch4=split["total_ch4"],
            co2=split["total_co2"],
            n2o=split["flared_n2o"],
            gwp_dict=gwp_dict,
        )

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "tier": "Tier 3",
                "method": "api_equation_6_11",
                "calculation_level": "Tier 3 Engineering (API Eq. 6-11)",
                "unloading_type": "plunger",
                "events": ev,
                "well_count": wc,
                "p_shut_psia": p_shut_abs,
                "p_line_psia": p_line_abs,
                "p_sep_psia": p_sep_abs,
                "p_atm_psia": p_atm_abs,
                "press_ratio": press_ratio,
                "sfr_scf_hr": sfr_rate,
                "t_p_hr": tp_val,
                "vr_per_event_scf": vr_scf,
                "whole_gas_scf": total_gas_scf,
                "whole_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "control_efficiency": ctrl_eff,
                "api_reference": "API Compendium 2021 Section 6.3.4, Equation 6-11",
            },
        )

    def calculate_volume_based(
        self,
        well_depth,
        diameter,
        pressure,
        ch4_content,
        events,
        uncertainties=None,
        co2_content=0.0,
        control_efficiency=0.0,
        ef_co2=None,
        ef_ch4=None,
        ef_n2o=None,
        operating_temperature=60.0,
        temp_unit="F",
        depth_unit="ft",
        diameter_unit="in",
        press_unit="psig",
        z_factor=1.0,
        well_count=1,
        unloading_type="plunger",
        hhv=1020.0,
        gwp_dict=None,
    ):
        """
        API Equation 6-3 - Volume per unloading event with temperature and compressibility correction:
        V_std = (pi/4) * D^2 * Depth * (P_tubing_abs / P_std) * (T_std / T_well_abs) * (1 / Z)
        Preserved with backwards compatibility for existing differential and unit tests.
        """
        self.validate_inputs(
            {
                "depth": well_depth,
                "diameter": diameter,
                "pressure": pressure,
                "events": events,
            },
            ["depth", "diameter", "pressure", "events"],
        )

        d_val = float(diameter)
        if d_val <= 0:
            raise ValueError(f"Casing/tubing diameter must be greater than zero: {d_val}")
        du = str(diameter_unit or "in").lower().strip()
        if du in ["in", "inch", "inches"]:
            d_m = d_val * 0.0254
        elif du in ["mm", "millimeter", "millimeters"]:
            d_m = d_val * 0.001
        elif du in ["cm", "centimeter", "centimeters"]:
            d_m = d_val * 0.01
        elif du in ["m", "meter", "meters"]:
            d_m = d_val
        elif du in ["ft", "feet"]:
            d_m = d_val * 0.3048
        else:
            d_m = d_val * 0.0254

        depth_val = float(well_depth)
        if depth_val <= 0:
            raise ValueError(f"Well depth must be greater than zero: {depth_val}")
        dep_u = str(depth_unit or "ft").lower().strip()
        if dep_u in ["m", "meter", "meters"]:
            depth_m = depth_val
        elif dep_u in ["km", "kilometer"]:
            depth_m = depth_val * 1000.0
        else:  # 'ft', 'feet'
            depth_m = depth_val * 0.3048

        # Volume at tubing conditions (m3)
        v_tubing = (math.pi / 4.0) * (d_m ** 2) * depth_m

        # Pressure, temperature, and compressibility correction (API Eq. 6-3 & §4.2.1)
        p_abs = to_psia(pressure, press_unit)
        p_factor = p_abs / STD_PRESSURE_PSIA

        t_abs_k = to_kelvin(operating_temperature, temp_unit)
        t_factor = STD_TEMP_K / max(1.0, t_abs_k)

        z = float(z_factor) if z_factor and float(z_factor) > 0 else 1.0

        ev = float(events)
        if ev < 0:
            raise ValueError("Number of unloading events cannot be negative.")
        wc = float(well_count or 1)
        if wc <= 0:
            raise ValueError("Number of wells must be greater than zero.")

        v_std = v_tubing * p_factor * t_factor * (1.0 / z)
        total_v_std = v_std * ev * wc

        c_ch4 = self._validate_fraction(ch4_content, default=0.85, name="Gas CH4 content")
        c_co2 = self._validate_fraction(co2_content, default=0.0, name="Gas CO2 content")
        if c_ch4 + c_co2 > 1.0001:
            raise ValueError(f"Combined CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) content cannot exceed 100%.")

        ch4_vol = total_v_std * c_ch4
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        co2_vol = total_v_std * c_co2
        co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
        co2_tonnes = co2_mass_kg / 1000.0

        ctrl_eff = float(control_efficiency or 0.0)
        split = _split_vented_and_flared(
            total_gas_m3=total_v_std,
            ch4_tonnes=ch4_tonnes,
            co2_tonnes=co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]
        flared_n2o_tonnes = split["flared_n2o"]

        unc = dict(uncertainties or {})
        unc.setdefault("ch4", 0.15)
        unc.setdefault("co2", 0.15)
        unc["_factor_source"] = unc.get("_factor_source", "specific")

        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o_tonnes,
            uncertainties=unc,
            factor_source=unc.get("_factor_source", "specific"),
            process_category="vented",
        )

        total_co2e = calculate_co2e(
            ch4=total_ch4, co2=total_co2, n2o=flared_n2o_tonnes, gwp_dict=gwp_dict
        )

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "tier": "Tier 3",
                "method": "api_equation_6_3",
                "calculation_level": "Tier 3 Engineering (API Eq. 6-3)",
                "well_depth": well_depth,
                "diameter": diameter,
                "pressure": pressure,
                "events": ev,
                "well_count": wc,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "control_efficiency": control_efficiency,
                "operating_temperature": operating_temperature,
                "api_reference": "API Compendium 2021 Section 6.3.4, Equation 6-3",
            },
        )

    def calculate(
        self,
        well_depth=None,
        diameter=None,
        pressure=None,
        ch4_content=None,
        events=None,
        uncertainties=None,
        co2_content=0.0,
        control_efficiency=0.0,
        ef_co2=None,
        ef_ch4=None,
        ef_n2o=None,
        operating_temperature=60.0,
        temp_unit="F",
        depth_unit="ft",
        diameter_unit="in",
        press_unit="psig",
        z_factor=1.0,
        well_count=None,
        unloading_type=None,
        tier=None,
        method=None,
        calc_method=None,
        sfr=None,
        hours_open=None,
        p_shut=None,
        p_line=None,
        p_sep=None,
        sfr_p=None,
        t_p=None,
        region=None,
        frequency_category=None,
        hhv=1020.0,
        gwp_dict=None,
        **kwargs,
    ):
        """
        Unified calculate entry point that routes to Tier 1, Tier 2, or Tier 3 calculations.
        """
        m = str(method or calc_method or kwargs.get("unloading_method") or "").lower().strip()
        t = str(tier or kwargs.get("calculation_level") or "").lower().strip()
        factor_src = str((uncertainties or {}).get("_factor_source") or kwargs.get("factor_source") or "").lower().strip()

        # Check for Equation 6-11
        if m in ["api_equation_6_11", "equation_6_11", "eq_6_11"] or (p_shut is not None and p_sep is not None):
            return self.calculate_tier3_equation_6_11(
                p_shut=p_shut,
                p_line=p_line,
                p_sep=p_sep,
                sfr_p=sfr_p or sfr,
                t_p=t_p or hours_open,
                events=events or 1,
                well_count=well_count or 1,
                p_atm=kwargs.get("p_atm", 14.696),
                ch4_content=ch4_content,
                co2_content=co2_content,
                control_efficiency=control_efficiency,
                press_unit=press_unit,
                uncertainties=uncertainties,
                hhv=hhv,
                ef_n2o=ef_n2o,
                gwp_dict=gwp_dict,
            )

        # Check for Equation 6-10
        if m in ["api_equation_6_10", "equation_6_10", "eq_6_10"] or (sfr is not None and hours_open is not None):
            return self.calculate_tier3_equation_6_10(
                events=events or kwargs.get("unload_events") or kwargs.get("unload_freq") or 1,
                well_depth=well_depth or kwargs.get("unload_depth"),
                diameter=diameter or kwargs.get("unload_diam"),
                pressure=pressure or kwargs.get("unload_press"),
                sfr=sfr,
                hours_open=hours_open,
                unloading_type=unloading_type or kwargs.get("unload_type", "non_plunger"),
                well_count=well_count or kwargs.get("wells", 1),
                ch4_content=ch4_content,
                co2_content=co2_content,
                control_efficiency=control_efficiency,
                depth_unit=depth_unit,
                diameter_unit=diameter_unit,
                press_unit=press_unit,
                sfr_unit=kwargs.get("sfr_unit", "scf/hr"),
                uncertainties=uncertainties,
                hhv=hhv,
                ef_n2o=ef_n2o,
                gwp_dict=gwp_dict,
            )

        # Check for Tier 1: Per-well Table 6-11
        is_tier1 = (
            t in ["1", "tier1", "tier_1"]
            or m in ["api_table_6_11", "table_6_11", "tier1", "per_well"]
            or (factor_src == "default" and well_count is not None and well_depth is None)
        )
        if is_tier1:
            wc = well_count or kwargs.get("wells") or kwargs.get("amount") or kwargs.get("quantity") or 1
            return self.calculate_tier1(
                well_count=wc,
                unloading_type=unloading_type or kwargs.get("unload_type", "plunger"),
                ch4_content=ch4_content,
                co2_content=co2_content,
                control_efficiency=control_efficiency,
                factor_key=kwargs.get("fuel") or kwargs.get("factor_key"),
                uncertainties=uncertainties,
                hhv=hhv,
                ef_n2o=ef_n2o,
                gwp_dict=gwp_dict,
            )

        # Check for Tier 2: Event-based Table 6-10
        is_tier2 = (
            t in ["2", "tier2", "tier_2"]
            or m in ["api_table_6_10", "table_6_10", "tier2", "event_based"]
            or (factor_src == "custom" and well_depth is None and (events is not None or kwargs.get("amount") is not None))
        )
        if is_tier2:
            ev = events if events is not None else (kwargs.get("unload_events") if kwargs.get("unload_events") is not None else (kwargs.get("unload_freq") if kwargs.get("unload_freq") is not None else kwargs.get("amount") or kwargs.get("quantity")))
            return self.calculate_tier2(
                events=ev,
                unloading_type=unloading_type or kwargs.get("unload_type", "plunger"),
                well_count=well_count or kwargs.get("wells", 1),
                frequency_category=frequency_category or kwargs.get("freq_category"),
                region=region,
                ch4_content=ch4_content,
                co2_content=co2_content,
                control_efficiency=control_efficiency,
                factor_key=kwargs.get("fuel") or kwargs.get("factor_key"),
                uncertainties=uncertainties,
                hhv=hhv,
                ef_n2o=ef_n2o,
                gwp_dict=gwp_dict,
            )

        # Default to Volume-based wellbore decompression (API Eq. 6-3)
        ev = events if events is not None else (kwargs.get("unload_events") if kwargs.get("unload_events") is not None else kwargs.get("unload_freq"))
        return self.calculate_volume_based(
            well_depth=well_depth or kwargs.get("unload_depth"),
            diameter=diameter or kwargs.get("unload_diam"),
            pressure=pressure or kwargs.get("unload_press"),
            ch4_content=ch4_content,
            events=ev,
            uncertainties=uncertainties,
            co2_content=co2_content,
            control_efficiency=control_efficiency,
            ef_co2=ef_co2,
            ef_ch4=ef_ch4,
            ef_n2o=ef_n2o,
            operating_temperature=operating_temperature or kwargs.get("unload_temp", 60.0),
            temp_unit=temp_unit,
            depth_unit=depth_unit,
            diameter_unit=diameter_unit,
            press_unit=press_unit,
            z_factor=z_factor,
            well_count=well_count or 1,
            unloading_type=unloading_type or "plunger",
            hhv=hhv,
            gwp_dict=gwp_dict,
        )



# BlowdownCalculator, TankFlashingCalculator, PneumaticDeviceCalculator: canonical implementations in
# vented_production.py, re-exported at the end of this module (audit RC-17 dedupe)


class AssociatedGasVentingCalculator(BaseCalculator):
    """
    API GHG Compendium 2021 - Section 6.3.1: Associated Gas Venting
    Implementation of:
      - Equation 6-8: Direct vent rate / mass emissions:
          E_x = VR * F_x * (MW_x / molar_volume_conversion) * T_v
      - Equation 6-9: Gas-to-Oil Ratio (GOR) approach:
          VR = GOR * Oil_p
      - Table 6-8: Regional Associated Gas Venting default emission factors with
        footnote b gas composition adjustment (CH4 and CO2 relative concentration).
      - Net-vented mass balance partitioning:
          V_vented = Total_Produced - V_recovered - V_flared
        Ensuring zero double-counting with Section 5 Flaring.
      - Full uncertainty propagation across Tiers 1, 2, and 3.
    """

    # API 2021 Table 6-8: Associated Gas Venting Emission Factors by Region
    TABLE_6_8_FACTORS = {
        "us_average": {
            "name": "Associated Gas Venting – US Average",
            "ef_ch4_kg_bbl": 1.4,
            "ef_tonnes_1000bbl": 1.4,
            "whole_gas_scf_bbl": 89.0,
            "ch4_mol_basis": 0.816,
            "uncertainty_ch4": 0.40,
            "uncertainty_co2": 0.20,
            "source": "API Compendium 2021 Section 6.3.1, Table 6-8",
        },
        "gulf_coast": {
            "name": "Gulf Coast Basin (Basin 220)",
            "ef_ch4_kg_bbl": 0.7,
            "ef_tonnes_1000bbl": 0.7,
            "whole_gas_scf_bbl": 47.0,
            "ch4_mol_basis": 0.816,
            "uncertainty_ch4": 0.40,
            "uncertainty_co2": 0.20,
            "source": "API Compendium 2021 Section 6.3.1, Table 6-8",
        },
        "anadarko": {
            "name": "Anadarko Basin (Basin 360)",
            "ef_ch4_kg_bbl": 9.7,
            "ef_tonnes_1000bbl": 9.7,
            "whole_gas_scf_bbl": 622.0,
            "ch4_mol_basis": 0.816,
            "uncertainty_ch4": 0.40,
            "uncertainty_co2": 0.20,
            "source": "API Compendium 2021 Section 6.3.1, Table 6-8",
        },
        "williston": {
            "name": "Williston Basin (Basin 395)",
            "ef_ch4_kg_bbl": 8.9,
            "ef_tonnes_1000bbl": 8.9,
            "whole_gas_scf_bbl": 570.0,
            "ch4_mol_basis": 0.816,
            "uncertainty_ch4": 0.40,
            "uncertainty_co2": 0.20,
            "source": "API Compendium 2021 Section 6.3.1, Table 6-8",
        },
        "permian": {
            "name": "Permian Basin (Basin 430)",
            "ef_ch4_kg_bbl": 6.5,
            "ef_tonnes_1000bbl": 6.5,
            "whole_gas_scf_bbl": 419.0,
            "ch4_mol_basis": 0.816,
            "uncertainty_ch4": 0.40,
            "uncertainty_co2": 0.20,
            "source": "API Compendium 2021 Section 6.3.1, Table 6-8",
        },
        "other": {
            "name": "\"Other\" US Basins",
            "ef_ch4_kg_bbl": 0.4,
            "ef_tonnes_1000bbl": 0.4,
            "whole_gas_scf_bbl": 26.0,
            "ch4_mol_basis": 0.816,
            "uncertainty_ch4": 0.40,
            "uncertainty_co2": 0.20,
            "source": "API Compendium 2021 Section 6.3.1, Table 6-8",
        },
    }

    # Physical molecular weights (API Compendium 2021 Table 3-1 & 3-2)
    MW_CH4 = 16.0425
    MW_CO2 = 44.01
    MOLAR_VOLUME_SCF_LBMOLE = 379.3  # scf/lb-mole at 60°F, 14.696 psia
    LB_TO_TONNE = 1.0 / 2204.6226218487757

    def __init__(self):
        super().__init__("Associated Gas Venting", "Section 6.3.1")

    @classmethod
    def resolve_basin_factor(cls, basin_name):
        """Matches a basin input string to Table 6-8 factor."""
        if not basin_name:
            return cls.TABLE_6_8_FACTORS["us_average"]
        b = str(basin_name).lower().strip()
        if "gulf" in b or "220" in b:
            return cls.TABLE_6_8_FACTORS["gulf_coast"]
        if "anadarko" in b or "360" in b:
            return cls.TABLE_6_8_FACTORS["anadarko"]
        if "williston" in b or "395" in b:
            return cls.TABLE_6_8_FACTORS["williston"]
        if "permian" in b or "430" in b:
            return cls.TABLE_6_8_FACTORS["permian"]
        if "other" in b:
            return cls.TABLE_6_8_FACTORS["other"]
        return cls.TABLE_6_8_FACTORS["us_average"]

    @staticmethod
    def _normalize_fraction(val, default=0.0):
        if val in [None, "", "-"]:
            return default
        try:
            f = float(str(val).replace("%", "").strip())
        except (ValueError, TypeError):
            return default
        if f > 1.0:
            f /= 100.0
        return f

    def calculate(
        self,
        tier=None,
        factor_source=None,
        # Tier 1 inputs
        oil_production=None,
        oil_unit="bbl",
        basin="US Average",
        # Tier 2 inputs
        gor=None,
        gor_unit="scf/bbl",
        venting_duration=None,
        duration_unit="days",
        period_duration=None,
        recovered_gas_volume=0.0,
        flared_gas_volume=0.0,
        gas_volume_unit="scf",
        # Tier 3 inputs
        vent_rate=None,
        vent_rate_unit="scfh",
        vent_volume=None,
        vent_volume_unit="scf",
        # Gas composition
        ch4_content=None,
        co2_content=None,
        # Factors & Uncertainty
        ef_ch4=None,
        ef_co2=None,
        uncertainties=None,
        gwp_dict=None,
        control_efficiency=0.0,
        **kwargs,
    ):
        uncertainties = uncertainties or {}

        # 1. Resolve Tier
        resolved_tier = None
        if tier is not None:
            t_str = str(tier).strip().lower()
            if "3" in t_str:
                resolved_tier = Tier.T3
            elif "2" in t_str:
                resolved_tier = Tier.T2
            elif "1" in t_str:
                resolved_tier = Tier.T1

        if resolved_tier is None and factor_source is not None:
            fs_str = str(factor_source).strip().lower()
            if fs_str in ["specific", "site_specific", "direct", "measurement", "cems", "tier3", "tier_3", "t3"]:
                resolved_tier = Tier.T3
            elif fs_str in ["engineering", "custom", "gor", "tier2", "tier_2", "t2"]:
                resolved_tier = Tier.T2
            elif fs_str in ["default", "tier1", "tier_1", "t1"]:
                resolved_tier = Tier.T1

        if resolved_tier is None:
            # Auto-detect from provided arguments
            if vent_rate is not None or vent_volume is not None:
                resolved_tier = Tier.T3
            elif gor is not None:
                resolved_tier = Tier.T2
            else:
                resolved_tier = Tier.T1

        # 2. Validate Gas Composition (applies across all tiers when provided)
        c_ch4 = None
        c_co2 = None
        if ch4_content is not None:
            c_ch4 = self._normalize_fraction(ch4_content)
            if c_ch4 < 0.0 or c_ch4 > 1.0:
                raise ValueError(f"CH4 molar fraction must be between 0.0 and 1.0 (got {c_ch4}).")

        if co2_content is not None:
            c_co2 = self._normalize_fraction(co2_content)
            if c_co2 < 0.0 or c_co2 > 1.0:
                raise ValueError(f"CO2 molar fraction must be between 0.0 and 1.0 (got {c_co2}).")

        if c_ch4 is not None and c_co2 is not None:
            if (c_ch4 + c_co2) > 1.0001:
                raise ValueError(
                    f"Gas composition error: Sum of CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) "
                    f"exceeds 100% ({((c_ch4 + c_co2)*100):.1f}%)."
                )

        qa_flags = []

        # =====================================================================
        # TIER 1: API TABLE 6-8 DEFAULT FACTOR METHODOLOGY
        # =====================================================================
        if resolved_tier == Tier.T1:
            if oil_production is None:
                raise ValueError("Oil production is required for Tier 1 Associated Gas Venting calculation.")
            oil_val = float(oil_production)
            if math.isnan(oil_val) or math.isinf(oil_val):
                raise ValueError(f"Oil production cannot be NaN or Infinite: {oil_val}")
            if oil_val < 0.0:
                raise ValueError(f"Oil production cannot be negative: {oil_val}")

            # Unit conversion to barrels (bbl)
            u_oil = str(oil_unit or "bbl").strip().lower()
            try:
                oil_bbl = convert(oil_val, u_oil, "bbl")
            except Exception:
                oil_bbl = oil_val  # fallback if already bbl

            # Basin Factor Lookup
            basin_info = self.resolve_basin_factor(basin or kwargs.get("region") or kwargs.get("fuel"))
            tbl_ef_ch4 = float(ef_ch4) if (ef_ch4 is not None and float(ef_ch4) > 0) else basin_info["ef_ch4_kg_bbl"]
            whole_gas_ef = float(basin_info.get("whole_gas_scf_bbl", 89.0))
            ch4_mol_basis = float(basin_info.get("ch4_mol_basis", 0.816))

            # Gas composition adjustment per Table 6-8 footnote b:
            # If site-specific CH4 is provided, adjust CH4 factor by (c_ch4 / 0.816)
            adj_ratio = 1.0
            if c_ch4 is not None and c_ch4 > 0:
                adj_ratio = c_ch4 / ch4_mol_basis
            else:
                c_ch4 = ch4_mol_basis

            ch4_kg = oil_bbl * tbl_ef_ch4 * adj_ratio
            ch4_tonnes = ch4_kg / 1000.0

            # CO2 adjustment per Table 6-8 footnote b:
            # Adjusted based on the relative concentrations of CH4 and CO2
            if c_co2 is not None and c_co2 > 0:
                co2_tonnes = ch4_tonnes * (c_co2 / c_ch4) * (self.MW_CO2 / self.MW_CH4)
            else:
                co2_tonnes = 0.0

            total_co2e = calculate_co2e(ch4=ch4_tonnes, co2=co2_tonnes, gwp_dict=gwp_dict)

            # Uncertainty propagation (Tier 1)
            ch4_res = propagate_uncertainty(
                ch4_tonnes,
                resolve_ef_uncertainty("vented", "ch4", Tier.T1, uncertainties.get("ch4")),
                tier=Tier.T1,
                process_category="vented",
                gas="ch4",
            )
            co2_res = propagate_uncertainty(
                co2_tonnes,
                resolve_ef_uncertainty("vented", "co2", Tier.T1, uncertainties.get("co2")),
                tier=Tier.T1,
                process_category="vented",
                gas="co2",
            ) if co2_tonnes > 0 else {"value": 0.0, "uncertainty": 0.0, "lower_bound": 0.0, "upper_bound": 0.0}

            return self.format_result(
                ch4=ch4_res,
                co2=co2_res,
                total_co2e=total_co2e,
                inputs={
                    "tier": "Tier 1",
                    "method": "api_table_6_8_default",
                    "basin": basin_info["name"],
                    "oil_production": oil_val,
                    "oil_unit": u_oil,
                    "oil_bbl": oil_bbl,
                    "ch4_factor_kg_bbl": tbl_ef_ch4,
                    "ch4_content_mol_pct": c_ch4 * 100.0,
                    "co2_content_mol_pct": (c_co2 or 0.0) * 100.0,
                    "composition_adjusted": adj_ratio != 1.0 or (c_co2 and c_co2 > 0),
                },
                metadata={
                    "standard": "API GHG Compendium 2021 Table 6-8 (Tier 1)",
                    "source": basin_info["source"],
                    "default_ch4_basis_mol_pct": ch4_mol_basis * 100.0,
                    "whole_gas_scf_bbl": whole_gas_ef,
                    "qa_flags": qa_flags,
                },
            )

        # =====================================================================
        # TIER 2: ENGINEERING GOR MASS BALANCE (API Eq. 6-8 & 6-9)
        # =====================================================================
        elif resolved_tier == Tier.T2:
            self.validate_inputs(
                {"oil_production": oil_production, "gor": gor},
                ["oil_production", "gor"],
            )
            oil_val = float(oil_production)
            gor_val = float(gor)

            if oil_val < 0.0:
                raise ValueError(f"Oil production cannot be negative: {oil_val}")
            if gor_val < 0.0:
                raise ValueError(f"Gas-to-Oil Ratio (GOR) cannot be negative: {gor_val}")

            # Physical plausibility check on GOR
            if gor_val > 100_000.0:
                qa_flags.append(f"High GOR anomaly: {gor_val:.1f} scf/bbl exceeds typical crude oil range (100,000 scf/bbl).")

            # Convert oil throughput to barrels
            u_oil = str(oil_unit or "bbl").strip().lower()
            oil_is_daily_rate = u_oil in ["bbl/day", "bpd", "barrel/day", "barrels/day", "m3/day"]
            oil_is_hourly_rate = u_oil in ["bbl/hr", "bph", "barrel/hr", "m3/hr", "m3/h"]

            # Convert base volumetric rate to bbl or bbl/day
            if oil_is_daily_rate:
                oil_rate_bbl_day = convert(oil_val, u_oil.replace("/day", ""), "bbl")
            elif oil_is_hourly_rate:
                oil_rate_bbl_day = convert(oil_val, u_oil.replace("/hr", "").replace("/h", ""), "bbl") * 24.0
            else:
                oil_bbl = convert(oil_val, u_oil, "bbl")
                oil_rate_bbl_day = None

            # Convert GOR to scf/bbl
            u_gor = str(gor_unit or "scf/bbl").strip().lower()
            if u_gor in ["m3/m3", "sm3/sm3", "m3_per_m3", "sm3/m3"]:
                gor_scf_bbl = gor_val * (CONVERSIONS["m3_to_scf"] / CONVERSIONS["m3_to_bbl"])
            elif u_gor in ["sm3/barrel", "sm3/bbl", "m3/bbl"]:
                gor_scf_bbl = gor_val * CONVERSIONS["m3_to_scf"]
            else:
                gor_scf_bbl = gor_val  # already scf/bbl

            # Determine Venting Duration and Total Associated Gas Produced
            u_dur = str(duration_unit or "days").strip().lower()
            dur_days = None
            if venting_duration is not None and str(venting_duration).strip() != "":
                v_dur = float(venting_duration)
                if v_dur < 0.0:
                    raise ValueError(f"Venting duration cannot be negative: {v_dur}")
                dur_days = v_dur if u_dur in ["day", "days", "d"] else v_dur / 24.0

            # Period duration validation
            p_days = None
            if period_duration is not None and str(period_duration).strip() != "":
                p_dur = float(period_duration)
                if p_dur <= 0.0:
                    raise ValueError(f"Period duration must be positive: {p_dur}")
                p_days = p_dur if u_dur in ["day", "days", "d"] else p_dur / 24.0

            if dur_days is not None and p_days is not None and dur_days > p_days * 1.0001:
                raise ValueError(
                    f"Venting duration ({dur_days:.1f} days) cannot exceed total period duration ({p_days:.1f} days)."
                )

            # Max duration check: annual max 366 days
            if dur_days is not None and dur_days > 366.0:
                raise ValueError(f"Venting duration ({dur_days:.1f} days) exceeds maximum annual days (366 days).")

            # Calculate total produced gas during the applicable period
            if oil_rate_bbl_day is not None:
                # Exhibit 6-5 / 6-6: rate-based input
                # Total gas produced during the venting event
                active_days = dur_days if dur_days is not None else (p_days or 365.0)
                total_oil_during_vent = oil_rate_bbl_day * active_days
                total_produced_gas_scf = total_oil_during_vent * gor_scf_bbl
            else:
                # Total period volume provided
                total_period_gas_scf = oil_bbl * gor_scf_bbl
                if dur_days is not None and p_days is not None:
                    vent_frac = min(1.0, dur_days / p_days)
                    total_produced_gas_scf = total_period_gas_scf * vent_frac
                elif dur_days is not None and dur_days < 365.0:
                    # Default annual period of 365 days
                    vent_frac = min(1.0, dur_days / 365.0)
                    total_produced_gas_scf = total_period_gas_scf * vent_frac
                else:
                    total_produced_gas_scf = total_period_gas_scf

            # Disposition Partitioning (Recovered, Flared, Vented)
            u_gas = str(gas_volume_unit or "scf").strip().lower()
            rec_scf = convert(recovered_gas_volume or 0.0, u_gas, "scf") if recovered_gas_volume else 0.0
            flared_scf = convert(flared_gas_volume or 0.0, u_gas, "scf") if flared_gas_volume else 0.0

            if rec_scf < 0.0:
                raise ValueError(f"Recovered gas volume cannot be negative: {rec_scf}")
            if flared_scf < 0.0:
                raise ValueError(f"Flared gas volume cannot be negative: {flared_scf}")

            # Mass balance violation check (Recovered + Flared > Total Produced)
            if (rec_scf + flared_scf) > (total_produced_gas_scf * 1.0001):
                raise ValueError(
                    f"Mass balance violation: Recovered gas ({rec_scf:.1f} scf) + Flared gas ({flared_scf:.1f} scf) "
                    f"exceeds total produced associated gas ({total_produced_gas_scf:.1f} scf)."
                )

            # Net vented gas volume
            net_vented_gas_scf = max(0.0, total_produced_gas_scf - rec_scf - flared_scf)

            # Gas composition (default 70% CH4, 10% CO2 if unspecified per Exhibit 6-5)
            f_ch4 = c_ch4 if c_ch4 is not None else 0.70
            f_co2 = c_co2 if c_co2 is not None else 0.10

            # API Eq. 6-8: Ex = VR * Fx * (MWx / 379.3) * Tv
            # Where (VR * Tv) is net_vented_gas_scf
            ch4_lb = (net_vented_gas_scf * f_ch4 * self.MW_CH4) / self.MOLAR_VOLUME_SCF_LBMOLE
            ch4_tonnes = ch4_lb * self.LB_TO_TONNE

            co2_lb = (net_vented_gas_scf * f_co2 * self.MW_CO2) / self.MOLAR_VOLUME_SCF_LBMOLE
            co2_tonnes = co2_lb * self.LB_TO_TONNE

            total_co2e = calculate_co2e(ch4=ch4_tonnes, co2=co2_tonnes, gwp_dict=gwp_dict)

            # Uncertainty propagation (Tier 2)
            ch4_res = propagate_uncertainty(
                ch4_tonnes,
                resolve_ef_uncertainty("vented", "ch4", Tier.T2, uncertainties.get("ch4")),
                tier=Tier.T2,
                process_category="vented",
                gas="ch4",
            )
            co2_res = propagate_uncertainty(
                co2_tonnes,
                resolve_ef_uncertainty("vented", "co2", Tier.T2, uncertainties.get("co2")),
                tier=Tier.T2,
                process_category="vented",
                gas="co2",
            ) if co2_tonnes > 0 else {"value": 0.0, "uncertainty": 0.0, "lower_bound": 0.0, "upper_bound": 0.0}

            return self.format_result(
                ch4=ch4_res,
                co2=co2_res,
                total_co2e=total_co2e,
                inputs={
                    "tier": "Tier 2",
                    "method": "api_equation_6_8_6_9_gor_mass_balance",
                    "oil_production": oil_val,
                    "oil_unit": u_oil,
                    "gor": gor_val,
                    "gor_unit": u_gor,
                    "gor_scf_bbl": gor_scf_bbl,
                    "venting_duration_days": dur_days,
                    "ch4_content_mol_pct": f_ch4 * 100.0,
                    "co2_content_mol_pct": f_co2 * 100.0,
                    "total_produced_gas_scf": total_produced_gas_scf,
                    "recovered_gas_scf": rec_scf,
                    "flared_gas_scf": flared_scf,
                    "net_vented_gas_scf": net_vented_gas_scf,
                },
                metadata={
                    "standard": "API GHG Compendium 2021 Eq. 6-8 & 6-9 (Section 6.3.1)",
                    "disposition": {
                        "produced_scf": total_produced_gas_scf,
                        "recovered_scf": rec_scf,
                        "flared_scf": flared_scf,
                        "vented_scf": net_vented_gas_scf,
                        "zero_double_counting_verified": True,
                    },
                    "qa_flags": qa_flags,
                },
            )

        # =====================================================================
        # TIER 3: DIRECT / SITE-SPECIFIC MEASUREMENT (API Eq. 6-8)
        # =====================================================================
        elif resolved_tier == Tier.T3:
            # Requires either vent_rate + duration OR total measured vent_volume
            if vent_volume is not None and str(vent_volume).strip() != "":
                v_val = float(vent_volume)
                if v_val < 0.0:
                    raise ValueError(f"Measured vent volume cannot be negative: {v_val}")
                u_vol = str(vent_volume_unit or "scf").strip().lower()
                net_vented_gas_scf = convert(v_val, u_vol, "scf")
                dur_hours = float(venting_duration) if (venting_duration and float(venting_duration) > 0) else None
            elif vent_rate is not None and str(vent_rate).strip() != "":
                r_val = float(vent_rate)
                if r_val < 0.0:
                    raise ValueError(f"Measured vent rate cannot be negative: {r_val}")
                if venting_duration is None or float(venting_duration) <= 0:
                    raise ValueError("Venting duration is required when vent rate is specified for Tier 3.")
                d_val = float(venting_duration)
                u_dur = str(duration_unit or "hours").strip().lower()
                dur_hours = d_val if u_dur in ["hour", "hours", "hr", "hrs", "h"] else d_val * 24.0

                u_rate = str(vent_rate_unit or "scfh").strip().lower()
                if u_rate in ["scfh", "scf/hr", "scf/h"]:
                    rate_scfh = r_val
                elif u_rate in ["scf/day", "scfd"]:
                    rate_scfh = r_val / 24.0
                elif u_rate in ["scf/min", "scfm"]:
                    rate_scfh = r_val * 60.0
                elif u_rate in ["sm3/hr", "sm3/h", "m3/hr", "m3/h"]:
                    rate_scfh = r_val * CONVERSIONS["m3_to_scf"]
                elif u_rate in ["sm3/day", "m3/day"]:
                    rate_scfh = (r_val * CONVERSIONS["m3_to_scf"]) / 24.0
                else:
                    rate_scfh = r_val

                net_vented_gas_scf = rate_scfh * dur_hours
            else:
                raise ValueError("Tier 3 requires either measured vent rate + duration or total measured vent volume.")

            # Gas composition (default 85% CH4 if not provided)
            f_ch4 = c_ch4 if c_ch4 is not None else 0.85
            f_co2 = c_co2 if c_co2 is not None else 0.0

            # API Eq. 6-8: Ex = VR * Fx * (MWx / 379.3) * Tv
            ch4_lb = (net_vented_gas_scf * f_ch4 * self.MW_CH4) / self.MOLAR_VOLUME_SCF_LBMOLE
            ch4_tonnes = ch4_lb * self.LB_TO_TONNE

            co2_lb = (net_vented_gas_scf * f_co2 * self.MW_CO2) / self.MOLAR_VOLUME_SCF_LBMOLE
            co2_tonnes = co2_lb * self.LB_TO_TONNE

            total_co2e = calculate_co2e(ch4=ch4_tonnes, co2=co2_tonnes, gwp_dict=gwp_dict)

            # Uncertainty propagation (Tier 3 - Calibrated measurement)
            ch4_res = propagate_uncertainty(
                ch4_tonnes,
                resolve_ef_uncertainty("vented", "ch4", Tier.T3, uncertainties.get("ch4")),
                tier=Tier.T3,
                process_category="vented",
                gas="ch4",
            )
            co2_res = propagate_uncertainty(
                co2_tonnes,
                resolve_ef_uncertainty("vented", "co2", Tier.T3, uncertainties.get("co2")),
                tier=Tier.T3,
                process_category="vented",
                gas="co2",
            ) if co2_tonnes > 0 else {"value": 0.0, "uncertainty": 0.0, "lower_bound": 0.0, "upper_bound": 0.0}

            return self.format_result(
                ch4=ch4_res,
                co2=co2_res,
                total_co2e=total_co2e,
                inputs={
                    "tier": "Tier 3",
                    "method": "api_equation_6_8_direct_measurement",
                    "vent_rate": vent_rate,
                    "vent_rate_unit": vent_rate_unit,
                    "vent_volume": vent_volume,
                    "vent_volume_unit": vent_volume_unit,
                    "venting_duration_hours": dur_hours,
                    "total_vented_scf": net_vented_gas_scf,
                    "ch4_content_mol_pct": f_ch4 * 100.0,
                    "co2_content_mol_pct": f_co2 * 100.0,
                },
                metadata={
                    "standard": "API GHG Compendium 2021 Eq. 6-8 (Direct Measurement / Tier 3)",
                    "qa_flags": qa_flags,
                },
            )

        raise ValueError(f"Unknown tier for Associated Gas Venting: {resolved_tier}")


# ==============================================================================
# Re-exports of all API Compendium 2021 Section 6 Modular Calculators
# ==============================================================================
from .vented_exploration import (
    WellTestingCalculator,
    CoalSeamDrillingCalculator,
)
from .vented_production import (
    # RC-17: single implementations (Tables 6-14/6-15, 6-22/6-24, Eq 6-32 / Table 6-32)
    PneumaticDeviceCalculator,
    TankFlashingCalculator,
    BlowdownCalculator,
    WorkoverWithoutFracturingCalculator,
    CasingGasVentCalculator,
    PneumaticPumpCalculator,
    GasDehydrationCalculator,
    AcidGasRemovalCalculator,
    CO2EORVentingCalculator,
    ProductionNonRoutineVentingCalculator,
)
from .vented_midstream import (
    GatheringCompressorVentingCalculator,
    GatheringStorageTankCalculator,
    GatheringNonRoutineVentingCalculator,
    ProcessingDehydrationCalculator,
    ProcessingBlanketedTankCalculator,
    ProcessingNonRoutineCalculator,
    TransmissionCompressorCalculator,
    TransmissionNonRoutineCalculator,
)
from .vented_lng_distribution import (
    LNGVentingCalculator,
    DistributionPneumaticsCalculator,
    DistributionNonRoutineCalculator,
)
from .vented_ccus_transport import (
    CCUSVentingCalculator,
    CrudeTransportLossesCalculator,
)
from .vented_downstream import (
    RefiningCatalystRegenCalculator,
    RefiningCokerCalculator,
    RefiningHydrogenPlantCalculator,
    AsphaltBlowingCalculator,
    RefiningCokeCalciningCalculator,
    SulfurRecoveryTailGasCalculator,
    PetrochemicalManufacturingCalculator,
    FireSuppressionCalculator,
)

