"""Mud degassing calculator.

Split out of calculations/vented.py unchanged (hardening plan, task 5.5). calculations.vented
re-exports the class, so existing imports keep working.
"""
from .base import BaseCalculator
from .uncertainty import Tier, propagate_uncertainty, resolve_ef_uncertainty
from .units import calculate_co2e


def _parse_conc(v, default):
    if v in (None, ""):
        return default
    s = str(v).strip()
    val = float(s.replace("%", "").strip())
    if val < 0:
        raise ValueError(f"Gas concentration cannot be negative: {v}")
    return (val / 100.0) if ("%" in s or val > 1.0) else val


def _resolve_ef(ef_ch4, default_ef):
    if ef_ch4 is not None:
        if float(ef_ch4) < 0:
            raise ValueError(f"ef_ch4 cannot be negative: {ef_ch4}")
        return float(ef_ch4)
    return default_ef


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
        if wells is None and drilling_days is None and mud_volume is None:  # it took 1 well / 0 days
            raise ValueError("Drilling needs the number of wells (Tier 1) or of drilling days (Table 6-2)")
        mud_key = str(mud_type or "water_based").lower().strip().replace(" ", "_").replace("-", "_")
        mud_key = {"water": "water_based", "oil": "oil_based", "synthetic_based": "synthetic"}.get(mud_key, mud_key)
        if mud_key not in self.TABLE_6_2_ONSHORE:  # an unknown mud took the water-based factor
            raise ValueError(f"Unknown mud type '{mud_type}': water_based, oil_based or synthetic")
        loc = str(location or "onshore").lower().strip()
        if loc not in ("onshore", "offshore"):  # an unknown location took the onshore factors
            raise ValueError(f"Unknown well location '{location}': onshore or offshore")

        # Determine calculation tier mode
        raw_tier = str(tier or "").lower().strip()
        raw_source = str(uncertainties.get("_factor_source") or "").lower().strip()
        parsed_ch4 = _parse_conc(ch4_concentration, self.DEFAULT_CH4_CONCENTRATION)
        parsed_co2 = _parse_conc(co2_concentration, 0.0)

        if (
            raw_tier in ["tier2_plus", "tier_2_plus", "tier2+", "tier_2+"]
            or raw_source in ["tier2_plus", "tier_2_plus", "tier2+", "tier_2+"]
            or (
                ch4_concentration is not None
                and (
                    parsed_ch4 != self.DEFAULT_CH4_CONCENTRATION
                    or parsed_co2 > 0
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
            ef = _resolve_ef(ef_ch4, self.TIER1_WELL_EF)
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

            norm_type = "oil_based" if mud_key in ("oil_based", "synthetic") else "water_based"
            is_offshore = loc == "offshore"
            mud_table = self.TABLE_6_2_OFFSHORE if is_offshore else self.TABLE_6_2_ONSHORE
            ef = _resolve_ef(ef_ch4, mud_table[norm_type])
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

            norm_type = "oil_based" if mud_key in ("oil_based", "synthetic") else "water_based"
            is_offshore = loc == "offshore"
            mud_table = self.TABLE_6_2_OFFSHORE if is_offshore else self.TABLE_6_2_ONSHORE
            ef = _resolve_ef(ef_ch4, mud_table[norm_type])

            x_ch4 = parsed_ch4

            x_co2 = parsed_co2
            if (x_ch4 + x_co2) > 1.0001:
                raise ValueError(f"Sum of gas concentrations cannot exceed 100%: {(x_ch4 + x_co2)*100:.1f}%")

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
