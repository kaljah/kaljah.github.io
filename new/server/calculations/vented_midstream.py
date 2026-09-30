"""
API Compendium 2021 - Sections 6.4, 6.5, 6.6: Midstream Oil & Gas
Gathering & Boosting, Natural Gas Processing, and Transmission & Storage

Governing Standard:
API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry
4th Edition, November 2021:
- §6.4 Gathering & Boosting:
    * §6.4.1 Pneumatics (Table 6-29, Exhibit 6-23)
    * §6.4.2 Compressors: Reciprocating Rod Packing (Table 6-30, Eq 6-29, Exhibit 6-24)
    * §6.4.3 Storage Tanks in G&B (Table 6-31)
    * §6.4.6 Equipment Blowdown & Non-Routine: Table 6-32, Table 6-33, Exhibits 6-25, 6-26, 6-27
- §6.5 Natural Gas Processing:
    * §6.5.1 Pneumatic Controllers (Table 6-34)
    * §6.5.2 Dehydration & Kimray Pumps (Table 6-35, Table 6-36, Exhibit 6-28)
    * §6.5.3 Blanketed Storage Tanks (Exhibit 6-29)
    * §6.5.4 Compressors: Reciprocating & Centrifugal (Table 6-37, Table 6-38)
    * §6.5.5 Non-Routine Plant Blowdowns (Table 6-39, Exhibit 6-30)
- §6.6 Natural Gas Transmission and Storage (T&S):
    * §6.6.1 Reciprocating Rod Packing (Table 6-40, Exhibit 6-31) & Centrifugal Seals (Table 6-41, Exhibit 6-32)
    * §6.6.2 Transmission Storage Tanks
    * §6.6.3 Pneumatics (Table 6-42)
    * §6.6.4 Non-Routine Releases & Pipeline Blowdowns (Table 6-43, Exhibit 6-33)
"""

import math
from .base import BaseCalculator
from .units import (
    CONVERSIONS,
    STD_PRESSURE_PSIA,
    STD_TEMP_K,
    STD_TEMP_R,
    convert,
    to_psia,
    to_kelvin,
    calculate_co2e,
    normalize_efficiency,
)
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
)

MOLAR_VOL_US = 379.3   # scf / lb-mole at 60°F, 14.696 psia
MOLAR_VOL_SI = 23.685  # Sm³ / kg-mole at 15.56°C, 101.325 kPa
MW_CH4 = 16.04
MW_CO2 = 44.01
MW_N2O = 44.013
LB_PER_TONNE = 2204.6226218487757


def _split_vent_flare(total_gas_m3, ch4_tonnes, co2_tonnes, ctrl_eff=0.0, hhv=1020.0, ef_n2o=None):
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

        flared_ch4_combusted = flared_ch4_mass * 0.98
        flared_co2 = (flared_ch4_combusted * (MW_CO2 / MW_CH4)) + flared_native_co2
        flared_unburnt_ch4 = flared_ch4_mass * 0.02

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


def _propagate_results(total_ch4, total_co2, flared_n2o, uncertainties, factor_source="default", category="vented"):
    _tier = resolve_tier(factor_source)
    ch4_res = propagate_uncertainty(
        total_ch4,
        resolve_ef_uncertainty(category, "ch4", _tier, (uncertainties or {}).get("ch4")),
        tier=_tier,
        process_category=category,
        gas="ch4",
    )
    co2_res = (
        propagate_uncertainty(
            total_co2,
            resolve_ef_uncertainty(category, "co2", _tier, (uncertainties or {}).get("co2")),
            tier=_tier,
            process_category=category,
            gas="co2",
        )
        if total_co2 > 0
        else None
    )
    n2o_res = (
        propagate_uncertainty(
            flared_n2o,
            resolve_ef_uncertainty(category, "n2o", _tier, (uncertainties or {}).get("n2o")),
            tier=_tier,
            process_category=category,
            gas="n2o",
        )
        if flared_n2o > 0
        else None
    )
    return ch4_res, co2_res, n2o_res


# ==============================================================================
# §6.4 Gathering & Boosting
# ==============================================================================
class GatheringCompressorVentingCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.4.2 - Reciprocating Compressor Rod Packing in G&B
    Table 6-30 & Equation 6-29.
    Supports:
      - US Zimmerle 2019: 28.4 scf whole gas / compressor-hr (4.43e-4 t CH4/hr at 81.6%)
      - US GHGRP Subpart W (EPA/GRI): 1.37 scf whole gas / compressor-hr (2.07e-5 t CH4/hr at 78.8%)
      - Alberta Canada: 10.2 scf whole gas / compressor-hr (1.39e-4 t CH4/hr at 81.6%)
    Verified against Exhibit 6-24.
    """

    TABLE_6_30 = {
        "us_zimmerle": {"scf_gas_hr": 28.4, "ef_ch4_tonnes_hr": 4.43e-4, "baseline_ch4_mol": 0.816, "unc": 0.21},
        "us_ghgrp": {"scf_gas_hr": 1.37, "ef_ch4_tonnes_hr": 2.07e-5, "baseline_ch4_mol": 0.788, "unc": 0.85},
        "canada_alberta": {"scf_gas_hr": 10.2, "ef_ch4_tonnes_hr": 1.39e-4, "baseline_ch4_mol": 0.816, "unc": 0.88},
    }

    def __init__(self):
        super().__init__("Gathering Compressor Venting", "Section 6.4.2")

    def calculate(
        self,
        compressor_count=1.0,
        pressurized_hours=8760.0,
        source_standard="us_ghgrp",  # "us_ghgrp", "us_zimmerle", "canada_alberta"
        ch4_content=None,
        co2_content=None,
        control_efficiency=0.0,
        disposition="vented",
        hhv=1020.0,
        ef_n2o=None,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        self.validate_inputs({"compressor_count": compressor_count}, ["compressor_count"])
        n_comp = float(compressor_count)
        hrs = max(0.0, float(8760.0 if pressurized_hours is None else pressurized_hours))

        std = str(source_standard or "us_ghgrp").lower().strip()
        factor_info = self.TABLE_6_30.get(std, self.TABLE_6_30["us_ghgrp"])

        c_ch4 = factor_info["baseline_ch4_mol"] if ch4_content is None else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0
        c_ch4 = max(0.0, min(1.0, c_ch4))

        c_co2 = 0.0 if co2_content is None else float(co2_content)
        if c_co2 > 1.0:
            c_co2 /= 100.0
        c_co2 = max(0.0, min(1.0, c_co2))

        # Equation 6-29 & Exhibit 6-24:
        # E_CH4 = n * EF_CH4 * T_press * (y_CH4 / y_base)
        base_ef = factor_info["ef_ch4_tonnes_hr"]
        base_mol = factor_info["baseline_ch4_mol"]
        gross_ch4_tonnes = n_comp * base_ef * hrs * (c_ch4 / base_mol)

        # CO2 calculated using whole gas factor and relative mole %:
        # E_CO2 = n * scf_gas_hr * (1/379.3) * y_CO2 * (44 / 2204.62) * hrs
        rate_scf_hr = factor_info["scf_gas_hr"]
        total_gas_scf = n_comp * rate_scf_hr * hrs
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        # Disposition
        disp = str(disposition or "vented").lower().strip()
        eff = 0.0
        if disp == "recovered":
            gross_ch4_tonnes = 0.0
            gross_co2_tonnes = 0.0
        elif disp == "flared":
            eff = float(control_efficiency if control_efficiency is not None else 0.98)
            eff = max(0.95, eff)
        else:
            eff = float(control_efficiency or 0.0)

        split = _split_vent_flare(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=gross_ch4_tonnes,
            co2_tonnes=gross_co2_tonnes,
            ctrl_eff=eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )

        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]
        flared_n2o = split["flared_n2o"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o,
            uncertainties=uncertainties,
            factor_source="API_Table_6_30",
            category="gathering_compressor",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "compressor_count": n_comp,
                "pressurized_hours": hrs,
                "source_standard": std,
                "total_gas_scf": total_gas_scf,
                "total_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "disposition": disp,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.4.2",
                "table": "Table 6-30",
                "equation": "Equation 6-29",
            },
        )


class GatheringStorageTankCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.4.3 - Storage Tanks in Gathering & Boosting
    Table 6-31:
      - Average Storage Tank in G&B: 39.3 scf gas / hr-tank (33.6 scf CH4 / hr-tank)
      - Common Single Unit Vent: 9.21 scf gas / hr-vent (8.52 scf CH4 / hr-vent)
      - Thief Hatch: 9.85 scf gas / hr-tank (8.77 scf CH4 / hr-vent)
    """

    TABLE_6_31 = {
        "average_tank": {"scf_gas_hr": 39.3, "scf_ch4_hr": 33.6, "baseline_ch4_mol": 0.855},
        "single_unit_vent": {"scf_gas_hr": 9.21, "scf_ch4_hr": 8.52, "baseline_ch4_mol": 0.925},
        "thief_hatch": {"scf_gas_hr": 9.85, "scf_ch4_hr": 8.77, "baseline_ch4_mol": 0.890},
    }

    def __init__(self):
        super().__init__("Gathering Storage Tanks", "Section 6.4.3")

    def calculate(
        self,
        tank_count=1.0,
        hours=8760.0,
        component_type="average_tank",  # "average_tank", "single_unit_vent", "thief_hatch"
        ch4_content=None,
        co2_content=0.0,
        control_efficiency=0.0,
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        n_tanks = max(1.0, float(tank_count or 1.0))
        hrs = max(0.0, float(8760.0 if hours is None else hours))

        ctype = str(component_type or "average_tank").lower().strip()
        factor_info = self.TABLE_6_31.get(ctype, self.TABLE_6_31["average_tank"])

        c_ch4 = factor_info["baseline_ch4_mol"] if ch4_content is None else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0

        c_co2 = float(co2_content or 0.0)
        if c_co2 > 1.0:
            c_co2 /= 100.0

        total_gas_scf = n_tanks * factor_info["scf_gas_hr"] * hrs
        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        gross_ch4_tonnes = total_gas_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        disp = str(disposition or "vented").lower().strip()
        eff = 0.0
        if disp == "recovered":
            gross_ch4_tonnes = 0.0
            gross_co2_tonnes = 0.0
        elif disp == "flared":
            eff = float(control_efficiency if control_efficiency is not None else 0.98)
            eff = max(0.95, eff)
        else:
            eff = float(control_efficiency or 0.0)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Table_6_31",
            category="gathering_tanks",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"tank_count": n_tanks, "hours": hrs, "component_type": ctype},
            metadata={"standard": "API Compendium 2021 Section 6.4.3", "table": "Table 6-31"},
        )


class GatheringNonRoutineVentingCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.4.6 - Gathering Segment Non-Routine Releases
    Table 6-33 & Exhibit 6-27:
      - PRV releases: 34 scf CH4/PRV-yr (43 scf gas/yr, 0.00065 t CH4/yr)
      - Gathering pipeline dig-in mishaps: 669 scf CH4/mile-yr (849 scf gas/yr, 0.0128 t CH4/yr)
      - Compressor engine starts: 8,443 scf CH4/start (10,714 scf gas/start, 0.16 t CH4/start)
      - Oil pump stations maintenance: 1.56 lb CH4/station-yr (46.9 scf gas/yr, 0.00071 t CH4/yr)
    Verified against Exhibit 6-27.
    """

    TABLE_6_33 = {
        "prv_releases": {"scf_gas": 43.0, "scf_ch4": 34.0, "ef_ch4_tonnes": 0.00065, "baseline_ch4_mol": 0.788},
        "pipeline_dig_in": {"scf_gas": 849.0, "scf_ch4": 669.0, "ef_ch4_tonnes": 0.0128, "baseline_ch4_mol": 0.788},
        "compressor_starts": {"scf_gas": 10714.0, "scf_ch4": 8443.0, "ef_ch4_tonnes": 0.160, "baseline_ch4_mol": 0.788},
        "oil_pump_station": {"scf_gas": 46.9, "scf_ch4": 37.0, "ef_ch4_tonnes": 0.00071, "baseline_ch4_mol": 0.788},
    }

    def __init__(self):
        super().__init__("Gathering Non-Routine Venting", "Section 6.4.6")

    def calculate(
        self,
        activity="prv_releases",  # "prv_releases", "pipeline_dig_in", "compressor_starts", "oil_pump_station"
        events_or_count=1.0,
        ch4_content=None,
        co2_content=0.0,
        control_efficiency=0.0,
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        act = str(activity or "prv_releases").lower().strip()
        factor_info = self.TABLE_6_33.get(act, self.TABLE_6_33["prv_releases"])
        n = max(0.0, float(1.0 if events_or_count is None else events_or_count))

        c_ch4 = factor_info["baseline_ch4_mol"] if ch4_content is None else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0

        c_co2 = float(co2_content or 0.0)
        if c_co2 > 1.0:
            c_co2 /= 100.0

        total_gas_scf = n * factor_info["scf_gas"]
        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        gross_ch4_tonnes = total_gas_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        disp = str(disposition or "vented").lower().strip()
        eff = 0.0
        if disp == "recovered":
            gross_ch4_tonnes = 0.0
            gross_co2_tonnes = 0.0
        elif disp == "flared":
            eff = float(control_efficiency if control_efficiency is not None else 0.98)
            eff = max(0.95, eff)
        else:
            eff = float(control_efficiency or 0.0)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Table_6_33",
            category="gathering_non_routine",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"activity": act, "count": n, "total_gas_scf": total_gas_scf},
            metadata={"standard": "API Compendium 2021 Section 6.4.6", "table": "Table 6-33"},
        )


# ==============================================================================
# §6.5 Natural Gas Processing
# ==============================================================================
class ProcessingDehydrationCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.5.2 - Gas Processing Dehydration & Kimray Pump
    Table 6-35 & Table 6-36.
    Supports:
      - Processing Glycol Dehydrator Vents (Table 6-35):
          0.0023315 tonnes CH4 / 10^6 scf gas (at 86.8% CH4)
      - Processing Kimray Pump Vents (Table 6-36):
          0.0034096 tonnes CH4 / 10^6 scf gas (179 scf CH4 / 10^6 scf at 86.8% CH4)
    Verified against Exhibit 6-28.
    """

    TABLE_6_35 = {"ef_ch4_tonnes_per_mmscf": 0.0023315, "baseline_ch4_mol": 0.868}
    TABLE_6_36 = {"ef_ch4_tonnes_per_mmscf": 0.0034096, "baseline_ch4_mol": 0.868}

    def __init__(self):
        super().__init__("Processing Dehydration", "Section 6.5.2")

    def calculate(
        self,
        gas_throughput_mmscfd=None,
        gas_throughput_mmscf_yr=None,
        operating_days=365.0,
        has_gas_assisted_pump=False,
        ch4_content=None,
        co2_content=None,
        control_efficiency=0.0,
        disposition="vented",
        hhv=1020.0,
        ef_n2o=None,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        days = max(1.0, float(operating_days or 365.0))
        if gas_throughput_mmscfd is not None:
            annual_mmscf = float(gas_throughput_mmscfd) * days
        elif gas_throughput_mmscf_yr is not None:
            annual_mmscf = float(gas_throughput_mmscf_yr)
        else:
            raise ValueError("gas_throughput_mmscfd or gas_throughput_mmscf_yr must be provided")

        c_ch4 = 0.868 if ch4_content is None else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0

        c_co2 = 0.0 if co2_content is None else float(co2_content)
        if c_co2 > 1.0:
            c_co2 /= 100.0

        # Exhibit 6-28:
        # Dehydrator CH4: annual_mmscf * 0.0023315 * (c_ch4 / 0.868)
        dehy_ch4_tonnes = annual_mmscf * self.TABLE_6_35["ef_ch4_tonnes_per_mmscf"] * (c_ch4 / 0.868)

        # Kimray pump CH4: annual_mmscf * 0.0034096 * (c_ch4 / 0.868)
        pump_ch4_tonnes = 0.0
        pump_co2_tonnes = 0.0
        if has_gas_assisted_pump:
            pump_ch4_tonnes = annual_mmscf * self.TABLE_6_36["ef_ch4_tonnes_per_mmscf"] * (c_ch4 / 0.868)
            if c_ch4 > 0 and c_co2 > 0:
                pump_co2_tonnes = pump_ch4_tonnes * (1.0 / MW_CH4) * (1.0 / c_ch4) * c_co2 * MW_CO2

        gross_ch4_tonnes = dehy_ch4_tonnes + pump_ch4_tonnes
        gross_co2_tonnes = pump_co2_tonnes

        total_gas_scf = (gross_ch4_tonnes * LB_PER_TONNE * MOLAR_VOL_US) / (max(0.001, c_ch4) * MW_CH4)
        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        disp = str(disposition or "vented").lower().strip()
        eff = 0.0
        if disp == "recovered":
            gross_ch4_tonnes = 0.0
            gross_co2_tonnes = 0.0
        elif disp == "flared":
            eff = float(control_efficiency if control_efficiency is not None else 0.98)
            eff = max(0.95, eff)
        else:
            eff = float(control_efficiency or 0.0)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff, hhv=hhv, ef_n2o=ef_n2o)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Section_6.5.2",
            category="processing_dehydration",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "annual_mmscf": annual_mmscf,
                "has_gas_assisted_pump": has_gas_assisted_pump,
                "dehy_ch4_tonnes": dehy_ch4_tonnes,
                "pump_ch4_tonnes": pump_ch4_tonnes,
                "disposition": disp,
            },
            metadata={"standard": "API Compendium 2021 Section 6.5.2", "tables": "Table 6-35, Table 6-36"},
        )


class ProcessingBlanketedTankCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.5.3 - Blanketed Storage Tanks in Processing
    Exhibit 6-29:
    Calculates displacement volume when liquid is pumped into natural gas blanketed tanks.
    V_scf = V_acf * [STD_TEMP_R / (459.7 + T_vapor)]
    """

    def __init__(self):
        super().__init__("Blanketed Storage Tanks", "Section 6.5.3")

    def calculate(
        self,
        liquid_displacement_bbl=None,
        liquid_displacement_m3=None,
        vapor_temperature_f=75.0,
        ch4_content=0.82,
        co2_content=0.01,
        control_efficiency=0.0,
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        if liquid_displacement_bbl is not None:
            v_bbl = float(liquid_displacement_bbl)
            # 1 bbl = 42 gal; 7.4805 gal = 1 ft3
            v_acf = v_bbl * 42.0 / 7.48052
        elif liquid_displacement_m3 is not None:
            v_acf = convert(float(liquid_displacement_m3), "m3", "scf")
        else:
            raise ValueError("liquid_displacement_bbl or liquid_displacement_m3 must be provided")

        t_f = float(vapor_temperature_f or 75.0)
        t_r = t_f + 459.67
        # Convert acf to scf at 60°F (519.67 °R)
        v_scf = v_acf * (519.67 / t_r)
        total_gas_m3 = convert(v_scf, "scf", "m3")

        c_ch4 = float(ch4_content if ch4_content is not None else 0.82)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0

        c_co2 = float(co2_content if co2_content is not None else 0.01)
        if c_co2 > 1.0:
            c_co2 /= 100.0

        gross_ch4_tonnes = v_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
        gross_co2_tonnes = v_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        disp = str(disposition or "vented").lower().strip()
        eff = 0.0
        if disp == "recovered":
            gross_ch4_tonnes = 0.0
            gross_co2_tonnes = 0.0
        elif disp == "flared":
            eff = float(control_efficiency if control_efficiency is not None else 0.98)
            eff = max(0.95, eff)
        else:
            eff = float(control_efficiency or 0.0)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Section_6.5.3",
            category="blanketed_tanks",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"v_acf": v_acf, "v_scf": v_scf, "vapor_temperature_f": t_f},
            metadata={"standard": "API Compendium 2021 Section 6.5.3", "exhibit": "Exhibit 6-29"},
        )


class ProcessingNonRoutineCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.5.5 - Gas Processing Plant Blowdowns
    Table 6-39 & Exhibit 6-30:
      - Gas Processing Plant Blowdowns: 0.1244 tonnes CH4 / 10^6 m3 gas treated
    Verified against Exhibit 6-30.
    """

    TABLE_6_39_EF = 0.1244  # tonnes CH4 / 10^6 m3 gas treated

    def __init__(self):
        super().__init__("Processing Plant Blowdowns", "Section 6.5.5")

    def calculate(
        self,
        gas_throughput_m3_day=None,
        gas_throughput_mmscfd=None,
        operating_days=365.0,
        ch4_content=None,
        co2_content=0.0,
        control_efficiency=0.0,
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        days = max(1.0, float(operating_days or 365.0))

        if gas_throughput_m3_day is not None:
            m3_yr = float(gas_throughput_m3_day) * days
        elif gas_throughput_mmscfd is not None:
            scf_yr = float(gas_throughput_mmscfd) * 1_000_000.0 * days
            m3_yr = convert(scf_yr, "scf", "m3")
        else:
            raise ValueError("gas_throughput_m3_day or gas_throughput_mmscfd must be provided")

        gross_ch4_tonnes = (m3_yr / 1_000_000.0) * self.TABLE_6_39_EF
        gross_co2_tonnes = 0.0

        total_gas_scf = (gross_ch4_tonnes * LB_PER_TONNE * MOLAR_VOL_US) / (0.868 * MW_CH4)
        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        disp = str(disposition or "vented").lower().strip()
        eff = 0.0
        if disp == "recovered":
            gross_ch4_tonnes = 0.0
        elif disp == "flared":
            eff = float(control_efficiency if control_efficiency is not None else 0.98)
            eff = max(0.95, eff)
        else:
            eff = float(control_efficiency or 0.0)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Table_6_39",
            category="processing_blowdown",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"annual_m3": m3_yr, "gross_ch4_tonnes": gross_ch4_tonnes},
            metadata={"standard": "API Compendium 2021 Section 6.5.5", "table": "Table 6-39"},
        )


# ==============================================================================
# §6.6 Natural Gas Transmission and Storage (T&S)
# ==============================================================================
class TransmissionCompressorCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.6.1 - Transmission Compressor Venting
    Supports:
      - Reciprocating Compressor Rod Packing (Table 6-40, Exhibit 6-31):
          * Operating mode: 263.0 scf gas / compressor-hr
          * Standby pressurized mode: 385.0 scf gas / compressor-hr (or Table 6-40 factor)
      - Centrifugal Compressor Degassing Vents (Table 6-41, Exhibit 6-32):
          * Wet seal operating: 334.0 scf gas / hr (or 16.0 scf CH4 / min average = 163.7 t CH4/yr)
          * Dry seal average: 5.0 scf CH4 / min average (51.1 t CH4/yr)
    Verified against Exhibits 6-31 and 6-32.
    """

    TABLE_6_40_RECIP = {
        "operating": 263.0,          # scf whole gas / compressor-hr
        "standby_pressurized": 385.0, # scf whole gas / compressor-hr (used in Exhibit 6-31)
    }

    TABLE_6_41_CENTRIFUGAL = {
        "wet_seal_operating": {"scf_gas_hr": 334.0, "scf_ch4_min": 26.4},
        "wet_seal_average": {"scf_gas_hr": 1028.0, "scf_ch4_min": 16.0, "ef_tonnes_yr": 163.7},
        "dry_seal_average": {"scf_gas_hr": 321.0, "scf_ch4_min": 5.0, "ef_tonnes_yr": 51.1},
    }

    def __init__(self):
        super().__init__("Transmission Compressor Venting", "Section 6.6.1")

    def calculate(
        self,
        compressor_type="reciprocating",  # "reciprocating", "centrifugal"
        compressor_count=1.0,
        # Reciprocating operating hours (Exhibit 6-31)
        operating_hours=7970.0,
        standby_pressurized_hours=630.0,
        # Centrifugal seal inputs (Exhibit 6-32)
        wet_seal_count=None,
        dry_seal_count=None,
        use_annual_average_factor=True,
        # Gas composition
        ch4_content=0.90,
        co2_content=0.0,
        control_efficiency=0.0,
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        ctype = str(compressor_type or "reciprocating").lower().strip()

        c_ch4 = float(ch4_content if ch4_content is not None else 0.90)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0

        c_co2 = float(co2_content or 0.0)
        if c_co2 > 1.0:
            c_co2 /= 100.0

        gross_ch4_tonnes = 0.0
        gross_co2_tonnes = 0.0
        total_gas_scf = 0.0

        if ctype == "centrifugal":
            # Exhibit 6-32: Centrifugal compressors with wet and dry seals
            n_wet = float(wet_seal_count if wet_seal_count is not None else compressor_count)
            n_dry = float(dry_seal_count or 0.0)

            # Table 6-41 Zimmerle 2015 average factor scaled by site CH4 mole fraction:
            # 163.7 tonnes CH4/compressor-yr for wet seal, 51.1 for dry seal (at 95% CH4)
            wet_tonnes = n_wet * 163.7 * (c_ch4 / 0.95)
            dry_tonnes = n_dry * 51.1 * (c_ch4 / 0.95)
            gross_ch4_tonnes = wet_tonnes + dry_tonnes

            wet_scf = n_wet * self.TABLE_6_41_CENTRIFUGAL["wet_seal_average"]["scf_gas_hr"] * 8760.0
            dry_scf = n_dry * self.TABLE_6_41_CENTRIFUGAL["dry_seal_average"]["scf_gas_hr"] * 8760.0
            total_gas_scf = wet_scf + dry_scf

        else:
            # Exhibit 6-31: Reciprocating compressor rod packing
            n_comp = float(compressor_count or 1.0)
            hrs_op = float(operating_hours or 0.0)
            hrs_stby = float(standby_pressurized_hours or 0.0)

            scf_op = n_comp * self.TABLE_6_40_RECIP["operating"] * hrs_op
            scf_stby = n_comp * self.TABLE_6_40_RECIP["standby_pressurized"] * hrs_stby
            total_gas_scf = scf_op + scf_stby

            gross_ch4_tonnes = total_gas_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
            gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        disp = str(disposition or "vented").lower().strip()
        eff = 0.0
        if disp == "recovered":
            gross_ch4_tonnes = 0.0
            gross_co2_tonnes = 0.0
        elif disp == "flared":
            eff = float(control_efficiency if control_efficiency is not None else 0.98)
            eff = max(0.95, eff)
        else:
            eff = float(control_efficiency or 0.0)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Section_6.6.1",
            category="transmission_compressors",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"compressor_type": ctype, "total_gas_scf": total_gas_scf},
            metadata={"standard": "API Compendium 2021 Section 6.6.1", "tables": "Table 6-40, Table 6-41"},
        )


class TransmissionNonRoutineCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.6.4 - Transmission & Storage Non-Routine Releases
    Table 6-43 & Exhibit 6-33:
      - Transmission station blowdowns: 54.0 tonnes CH4 / station-yr
      - Storage station blowdowns: 43.0 tonnes CH4 / station-yr
      - Transmission pipeline blowdowns: 0.6135 tonnes CH4 / mile-yr (34,200 scf gas/mile-yr)
      - Compressor blowdowns: 47.14 tonnes CH4 / station-yr
      - PRV lifts: 3.68 tonnes CH4 / station-yr
      - ESD activation: 7.97 tonnes CH4 / station-yr
      - M&R station blowdowns: 13.75 tonnes CH4 / station-yr
    Verified against Exhibit 6-33.
    """

    TABLE_6_43 = {
        "transmission_station": {"ef_tonnes_ch4": 54.0, "scf_gas": 3014000.0, "baseline_ch4_mol": 0.934},
        "storage_station": {"ef_tonnes_ch4": 43.0, "scf_gas": 2400000.0, "baseline_ch4_mol": 0.934},
        "pipeline_blowdown": {"ef_tonnes_ch4": 0.6135, "scf_gas": 34200.0, "baseline_ch4_mol": 0.934},
        "compressor_blowdowns": {"ef_tonnes_ch4": 47.14, "scf_gas": 2631000.0, "baseline_ch4_mol": 0.934},
        "prv_lifts": {"ef_tonnes_ch4": 3.68, "scf_gas": 206000.0, "baseline_ch4_mol": 0.934},
        "esd_activation": {"ef_tonnes_ch4": 7.97, "scf_gas": 444000.0, "baseline_ch4_mol": 0.934},
        "mr_station": {"ef_tonnes_ch4": 13.75, "scf_gas": 756000.0, "baseline_ch4_mol": 0.934},
    }

    def __init__(self):
        super().__init__("Transmission Non-Routine Releases", "Section 6.6.4")

    def calculate(
        self,
        activity="transmission_station",  # "transmission_station", "pipeline_blowdown", "storage_station", etc.
        count_or_miles=1.0,
        ch4_content=None,
        co2_content=0.0,
        control_efficiency=0.0,
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        act = str(activity or "transmission_station").lower().strip()
        factor_info = self.TABLE_6_43.get(act, self.TABLE_6_43["transmission_station"])
        n = max(0.0, float(count_or_miles or 1.0))

        c_ch4 = factor_info["baseline_ch4_mol"] if ch4_content is None else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0

        c_co2 = float(co2_content or 0.0)
        if c_co2 > 1.0:
            c_co2 /= 100.0

        # Exhibit 6-33 uses factor uncorrected if composition is typical
        gross_ch4_tonnes = n * factor_info["ef_tonnes_ch4"] * (c_ch4 / factor_info["baseline_ch4_mol"])
        total_gas_scf = n * factor_info["scf_gas"]
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE
        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        disp = str(disposition or "vented").lower().strip()
        eff = 0.0
        if disp == "recovered":
            gross_ch4_tonnes = 0.0
            gross_co2_tonnes = 0.0
        elif disp == "flared":
            eff = float(control_efficiency if control_efficiency is not None else 0.98)
            eff = max(0.95, eff)
        else:
            eff = float(control_efficiency or 0.0)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Table_6_43",
            category="transmission_non_routine",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"activity": act, "count_or_miles": n, "gross_ch4_tonnes": gross_ch4_tonnes},
            metadata={"standard": "API Compendium 2021 Section 6.6.4", "table": "Table 6-43"},
        )
