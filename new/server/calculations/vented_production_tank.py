"""Tank flashing, acid gas removal and blowdown calculators.

Split out of calculations/vented_production.py unchanged (hardening plan, task 5.5).
calculations.vented_production re-exports every class, so existing imports keep working.
"""
import math
from .base import BaseCalculator
from .units import CONVERSIONS, STD_PRESSURE_PSIA, STD_TEMP_K, calculate_co2e, convert, normalize_efficiency, to_kelvin, _pressure_unit
from calculations.vented_production import LB_PER_TONNE, MOLAR_VOL_SI, MOLAR_VOL_US, MW_CH4, MW_CO2, SCF_TO_M3, _propagate_results, _split_vent_flare


class AcidGasRemovalCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.8.4 - Acid Gas Removal (AGR) Units
    Supports:
      - CH4 Emissions from Amine Units (Table 6-19, Exhibit 6-16):
          * Throughput basis: 965 scf CH4 / 10^6 scf treated gas (0.0185 tonnes CH4 / 10^6 scf)
          * Unit basis: 33,794 scfd CH4 / unit (0.6482 tonnes CH4 / day-unit)
      - CO2 Emissions via Material Balance (Equation 6-18, Exhibit 6-17):
          E_CO2 = [V_sour * (CO2%_sour) - V_sweet * (CO2%_sweet)] * [44 / 379.3] / 2204.62
    Verified against Exhibits 6-16 and 6-17.
    """

    TABLE_6_19 = {
        "throughput": {"scf_ch4_per_mmscf": 965.0, "ef_ch4_tonnes_per_mmscf": 0.0185},
        "unit": {"scfd_ch4_per_unit": 33794.0, "ef_ch4_tonnes_per_day": 0.6482},
    }

    def __init__(self):
        super().__init__("Acid Gas Removal", "Section 6.3.8.4")

    def calculate(
        self,
        # CH4 estimation inputs
        method="throughput",  # "throughput", "unit_count", "sour_sweet_balance"
        sour_gas_scf_yr=None,
        sour_gas_mmscf_yr=None,
        unit_count=1.0,
        operating_days=365.0,
        # Equation 6-18 CO2 material balance inputs
        sweet_gas_scf_yr=None,
        sweet_gas_mmscf_yr=None,
        sour_co2_content=None,  # mole fraction or % (e.g. 0.03 or 3%)
        sweet_co2_content=0.0,  # mole fraction or % (e.g. 0.02 or 2%)
        # Control & routing
        control_efficiency=None,  # not entered: flare defaults (0.0 read as a 0 % efficiency)
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        meth = str(method or "throughput").lower().strip()
        # an entered 0 days / units is 0 (they became 365 days / 1 unit)
        days = 365.0 if operating_days in (None, "") else float(operating_days)
        n_units = 1.0 if unit_count in (None, "") else float(unit_count)
        if days < 0 or n_units < 0:
            raise ValueError("operating_days and unit_count cannot be negative")

        gross_ch4_tonnes = 0.0
        gross_co2_tonnes = 0.0
        total_gas_scf = 0.0

        # Resolve sour gas throughput
        v_sour_scf = 0.0
        if sour_gas_mmscf_yr is not None:
            v_sour_scf = float(sour_gas_mmscf_yr) * 1_000_000.0
        elif sour_gas_scf_yr is not None:
            v_sour_scf = float(sour_gas_scf_yr)

        # 1. CH4 emissions
        if meth == "unit_count" or v_sour_scf <= 0:
            gross_ch4_tonnes = n_units * self.TABLE_6_19["unit"]["ef_ch4_tonnes_per_day"] * days
            total_gas_scf = n_units * self.TABLE_6_19["unit"]["scfd_ch4_per_unit"] * days
        else:
            mmscf = v_sour_scf / 1_000_000.0
            gross_ch4_tonnes = mmscf * self.TABLE_6_19["throughput"]["ef_ch4_tonnes_per_mmscf"]
            total_gas_scf = mmscf * self.TABLE_6_19["throughput"]["scf_ch4_per_mmscf"]

        if sour_co2_content is not None and v_sour_scf > 0:
            s_sour = str(sour_co2_content).replace("%", "").strip()
            pct_sour = "%" in str(sour_co2_content)
            v_sour_val = float(s_sour)

            s_sweet = str(sweet_co2_content if sweet_co2_content is not None else 0.0).replace("%", "").strip()
            pct_sweet = "%" in str(sweet_co2_content)
            v_sweet_val = float(s_sweet)

            in_pct = (not pct_sour and v_sour_val > 1.0) or (not pct_sweet and v_sweet_val > 1.0)
            c_sour_co2 = (v_sour_val / 100.0) if (pct_sour or in_pct) else v_sour_val
            c_sweet_co2 = (v_sweet_val / 100.0) if (pct_sweet or in_pct) else v_sweet_val

            if c_sour_co2 < 0 or c_sour_co2 > 1.0:
                raise ValueError(f"sour_co2_content must be between 0 and 1 (or 0% to 100%): {sour_co2_content}")
            if c_sweet_co2 < 0 or c_sweet_co2 > 1.0:
                raise ValueError(f"sweet_co2_content must be between 0 and 1 (or 0% to 100%): {sweet_co2_content}")

            v_sweet_scf = 0.0
            if sweet_gas_mmscf_yr is not None:
                v_sweet_scf = float(sweet_gas_mmscf_yr) * 1_000_000.0
            elif sweet_gas_scf_yr is not None:
                v_sweet_scf = float(sweet_gas_scf_yr)
            else:
                v_sweet_scf = v_sour_scf * (1.0 - c_sour_co2)

            # Equation 6-18: E_CO2 = [V_sour * y_sour - V_sweet * y_sweet] * (44 / 379.3) / 2204.62
            co2_scf_removed = max(0.0, (v_sour_scf * c_sour_co2) - (v_sweet_scf * c_sweet_co2))
            gross_co2_tonnes = co2_scf_removed * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        # Disposition
        from .vented_production_wells import _route  # one disposition rule (an unknown one was vented)

        disp, eff, de, gross_ch4_tonnes, gross_co2_tonnes = _route(disposition, control_efficiency, gross_ch4_tonnes,
                                                                   gross_co2_tonnes)
        split = _split_vent_flare(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=gross_ch4_tonnes,
            co2_tonnes=gross_co2_tonnes,
            ctrl_eff=eff,
            destruction_eff=de,
        )

        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]
        flared_n2o = split["flared_n2o"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o,
            uncertainties=uncertainties,
            factor_source="API_Section_6.3.8.4",
            category="acid_gas_removal",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "method": meth,
                "sour_gas_scf": v_sour_scf,
                "gross_ch4_tonnes": gross_ch4_tonnes,
                "gross_co2_tonnes": gross_co2_tonnes,
                "disposition": disp,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.8.4",
                "tables": "Table 6-19, Eq 6-18",
            },
        )


class TankFlashingCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.9 - Hydrocarbon & Produced Water Storage Tanks
    Supports:
      1. Vasquez-Beggs Equation (VBE) (Eq 6-20 & 6-21, Table 6-20, Exhibit 6-18a)
      2. Standing Correlation (Eq 6-22 & 6-23, Table 6-21, Exhibit 6-18b)
      3. EUB Rule-of-Thumb (Eq 6-24, Exhibit 6-18c)
      4. Default Flashing Emission Factors:
         - Crude Oil (Table 6-22): Large vs Small, Uncontrolled, VRU, Flared, Average
         - Condensate (Table 6-24): Large, Uncontrolled, VRU
      5. Improperly Functioning Separator Dump Valve (Eq 6-25, Table 6-25)
      6. Produced Salt Water Tanks (Table 6-26 & Table 6-27, Exhibit 6-21)
      7. Working / Standing Losses (AP-42 Chapter 7 direct EF or GOR)
    Verified against Exhibits 6-18a, 6-18b, 6-18c, 6-20, and 6-21.
    """

    TABLE_6_22_CRUDE = {
        "large_uncontrolled": {"kg_ch4_per_bbl": 0.193, "baseline_ch4_mol": 0.816},
        "large_vru": {"kg_ch4_per_bbl": 0.0283, "baseline_ch4_mol": 0.816},
        "large_flared": {"kg_ch4_per_bbl": 0.00525, "baseline_ch4_mol": 0.816},
        "small_uncontrolled": {"kg_ch4_per_bbl": 0.0184, "baseline_ch4_mol": 0.816},
        "small_flared": {"kg_ch4_per_bbl": 0.00206, "baseline_ch4_mol": 0.816},
        "average_uncontrolled": {"kg_ch4_per_bbl": 0.886, "baseline_ch4_mol": 0.788},
    }

    TABLE_6_24_CONDENSATE = {
        "large_uncontrolled": {"kg_ch4_per_bbl": 0.146, "baseline_ch4_mol": 0.816},
        "large_vru": {"kg_ch4_per_bbl": 0.00665, "baseline_ch4_mol": 0.816},
    }

    TABLE_6_25_DUMP_VALVE = {
        "crude": {"kg_ch4_per_bbl": 0.00270, "cf": 2.87, "baseline_ch4_mol": 0.816},
        "condensate": {"kg_ch4_per_bbl": 0.00264, "cf": 4.37, "baseline_ch4_mol": 0.816},
    }

    TABLE_6_26_SALT_WATER = {
        (50, "20%"): 0.0015,
        (250, "20%"): 0.00986,
        (250, "10%"): 0.0150,
        (250, "2%"): 0.0177,
        (250, "average"): 0.0142,
        (1000, "20%"): 0.0354,
        (1000, "10%"): 0.0536,
        (1000, "2%"): 0.0634,
        (1000, "average"): 0.0508,
    }

    def __init__(self):
        super().__init__("Storage Tank Emissions", "Section 6.3.9")

    def calculate(
        self,
        throughput,
        gas_oil_ratio=None,
        ch4_content=None,
        control_efficiency=0.0, destruction_efficiency=None,
        uncertainties=None,
        process_type="tank_flashing",
        ef_ch4=0.0,
        co2_content=0.0,
        ef_co2=None,
        ef_n2o=None,
        hhv=1020.0,
        gwp_dict=None,
        # API 2021 Section 6.3.9 advanced options
        method=None,  # "vbe", "standing", "eub", "table_6_22", "table_6_24", "dump_valve", "produced_water", "gor"
        liquid_type="crude",  # "crude", "condensate", "produced_water"
        tank_size="large",    # "large" (>= 10 bbl/day) or "small" (< 10 bbl/day)
        operating_days=365.0,
        # VBE / Standing inputs
        api_gravity=None,
        separator_pressure_psig=None,
        separator_temp_f=None,
        tank_temp_f=80.0,
        gas_specific_gravity=0.90,  # default SGi = 0.90
        # Dump valve inputs (Equation 6-25)
        dump_valve_hours=None,
        # Produced water inputs (Table 6-26)
        salt_content="average",  # "2%", "10%", "20%", "average"
        separator_pressure_psi=250.0,
        control_type="flare",
    ):
        uncertainties = uncertainties or {}
        self.validate_inputs({"throughput": throughput}, ["throughput"])  # >= 0
        q_bbl = float(throughput)

        # Resolve calculation method
        meth = method
        if meth is None:
            if process_type == "working_loss" or (ef_ch4 and float(ef_ch4) > 0 and not gas_oil_ratio):
                meth = "working_loss"
            elif liquid_type == "produced_water":
                meth = "produced_water"
            elif api_gravity is not None and separator_pressure_psig is not None and separator_temp_f is not None:
                meth = "vbe"
            elif gas_oil_ratio is not None and float(gas_oil_ratio) >= 0:
                meth = "gor"
            else:
                meth = "table_6_22" if liquid_type == "crude" else "table_6_24"

        meth = str(meth).lower().strip()

        # a correlation chosen without its separator data is refused: the Exhibit 6-18a sample values
        # (API 48.8, 28.6 psig, 112 F) were used in their place (bug hunt 2026-10-15 #25)
        needed = {"vbe": ("api_gravity", "separator_pressure_psig", "separator_temp_f"),
                  "standing": ("api_gravity", "separator_pressure_psig", "separator_temp_f"),
                  "eub": ("separator_pressure_psig",)}.get(meth, ())
        given = {"api_gravity": api_gravity, "separator_pressure_psig": separator_pressure_psig,
                 "separator_temp_f": separator_temp_f}
        missing = [k for k in needed if given[k] is None]
        if missing:
            raise ValueError(f"Tank method '{meth}' needs {', '.join(missing)} (separator data)")

        # Resolve compositions
        default_ch4 = (0.274 if liquid_type == "crude" else 0.363) if (
            meth in ["vbe", "standing", "eub", "gor"] and liquid_type in ("crude", "condensate")) else 0.85
        c_ch4 = _parse_frac(ch4_content, default_ch4, "ch4_content")
        c_co2 = _parse_frac(co2_content, 0.0, "co2_content")
        if (c_ch4 + c_co2) > 1.0001:
            raise ValueError(f"Sum of CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) cannot exceed 100%")
        gross_ch4_tonnes = gross_co2_tonnes = total_gas_scf = 0.0

        # ----------------------------------------------------------------------
        # Method 1: Vasquez-Beggs Equation (VBE) (Eq 6-20 & 6-21, Exhibit 6-18a)
        # ----------------------------------------------------------------------
        if meth == "vbe":
            api = max(0.0, float(api_gravity if api_gravity is not None else 48.8))
            p_sep = max(0.0, float(separator_pressure_psig if separator_pressure_psig is not None else 28.6))
            t_sep = float(separator_temp_f if separator_temp_f is not None else 112.0)
            sg_i = max(0.01, float(gas_specific_gravity or 0.90))

            # Equation 6-20: SG_X = SG_i * [1.0 + 0.00005912 * API * T_i * log10((P_i + 14.7) / 114.7)]
            p_term = max(0.001, (p_sep + 14.7) / 114.7)
            sg_x = max(0.01, sg_i * (1.0 + 0.00005912 * api * t_sep * math.log10(p_term)))

            # Equation 6-21: Coefficients
            c1, c2, c3 = (0.0362, 1.0937, 25.724) if api <= 30.0 else (0.0178, 1.187, 23.931)

            rs = max(0.0, c1 * sg_x * ((p_sep + 14.7) ** c2) * math.exp(min(700.0, max(-700.0, (c3 * api) / max(1.0, t_sep + 460.0)))))
            total_gas_scf = q_bbl * rs
            gross_ch4_tonnes = total_gas_scf * SCF_TO_M3 * c_ch4 * CONVERSIONS["density_ch4"] / 1000.0  # engine density convention
            gross_co2_tonnes = total_gas_scf * SCF_TO_M3 * c_co2 * CONVERSIONS["density_co2"] / 1000.0

        # ----------------------------------------------------------------------
        # Method 2: Standing Correlation (Eq 6-22 & 6-23, Exhibit 6-18b)
        # ----------------------------------------------------------------------
        elif meth == "standing":
            api = max(0.0, float(api_gravity if api_gravity is not None else 48.8))
            p_sep_psig = max(0.0, float(separator_pressure_psig if separator_pressure_psig is not None else 28.6))
            t_sep_f = float(separator_temp_f if separator_temp_f is not None else 112.0)
            t_tank_f = float(tank_temp_f if tank_temp_f is not None else 80.0)
            sg_gas = max(0.01, float(gas_specific_gravity or 0.90))

            # Convert to metric: kPa and Kelvin
            p_sep_kpa = (p_sep_psig + 14.7) * 6.894757
            p_tank_kpa = 101.325
            t_sep_k = max(1.0, (t_sep_f - 32.0) * (5.0 / 9.0) + 273.15)
            t_tank_k = max(1.0, (t_tank_f - 32.0) * (5.0 / 9.0) + 273.15)

            sg_oil = 141.5 / max(1.0, 131.5 + api)
            yg_sep = min(20.0, max(-20.0, 1.225 + (0.00164 * t_sep_k) - (1.769 / max(0.001, sg_oil))))
            yg_tank = min(20.0, max(-20.0, 1.225 + (0.00164 * t_tank_k) - (1.769 / max(0.001, sg_oil))))

            term_sep = (p_sep_kpa / (519.7 * (10.0 ** yg_sep))) ** 1.204
            term_tank = (p_tank_kpa / (519.7 * (10.0 ** yg_tank))) ** 1.204
            gor_m3_m3 = max(0.0, sg_gas * (term_sep - term_tank))

            # Convert throughput to m3: 1 bbl = 0.1589873 m3
            q_m3 = q_bbl * 0.1589873
            total_m3 = q_m3 * gor_m3_m3
            total_gas_scf = convert(total_m3, "m3", "scf")

            # Tonnes via molar volume SI (23.685 Sm3/kg-mole)
            gross_ch4_tonnes = total_m3 * (c_ch4 / MOLAR_VOL_SI) * (MW_CH4 / 1000.0)
            gross_co2_tonnes = total_m3 * (c_co2 / MOLAR_VOL_SI) * (MW_CO2 / 1000.0)

        # ----------------------------------------------------------------------
        # Method 3: EUB Rule-of-Thumb (Eq 6-24, Exhibit 6-18c)
        # ----------------------------------------------------------------------
        elif meth == "eub":
            p_sep_psig = float(separator_pressure_psig if separator_pressure_psig is not None else 28.6)
            dp_kpa = p_sep_psig * 6.894757  # pressure drop to atmospheric in kPa gauge
            q_m3 = q_bbl * 0.1589873
            total_m3 = 0.0257 * q_m3 * dp_kpa
            total_gas_scf = convert(total_m3, "m3", "scf")

            gross_ch4_tonnes = total_m3 * (c_ch4 / MOLAR_VOL_SI) * (MW_CH4 / 1000.0)
            gross_co2_tonnes = total_m3 * (c_co2 / MOLAR_VOL_SI) * (MW_CO2 / 1000.0)

        # ----------------------------------------------------------------------
        # Method 4 & 5: Default Flashing Factors (Table 6-22 & 6-24, Exhibit 6-20)
        # ----------------------------------------------------------------------
        elif meth in ["table_6_22", "table_6_24", "default_ef"]:
            if liquid_type == "condensate" or meth == "table_6_24":
                key = "large_uncontrolled"
                info = self.TABLE_6_24_CONDENSATE[key]
            else:
                sz = str(tank_size or "large").lower().strip()
                key = "small_uncontrolled" if sz == "small" else "large_uncontrolled"
                info = self.TABLE_6_22_CRUDE[key]

            base_kg_per_bbl = info["kg_ch4_per_bbl"]
            base_mol = info["baseline_ch4_mol"]
            # the factor is never scaled by the separator-gas CH4 content (Exhibit 6-20: flashing losses are
            # not a linear function of it, they depend on CH4 solubility in the liquid); the site content only
            # carries the CO2 ratio below. It was scaled (Exhibit 6-20 at 58 % CH4: 22.6 t instead of 31.8 t)
            if ch4_content is None:
                c_ch4 = base_mol
            gross_ch4_kg = q_bbl * base_kg_per_bbl
            gross_ch4_tonnes = gross_ch4_kg / 1000.0

            if c_ch4 > 0 and c_co2 > 0:
                gross_co2_tonnes = gross_ch4_tonnes * (1.0 / MW_CH4) * (1.0 / c_ch4) * c_co2 * MW_CO2

            total_gas_scf = (gross_ch4_tonnes * LB_PER_TONNE * MOLAR_VOL_US) / (max(0.001, c_ch4) * MW_CH4)

        # ----------------------------------------------------------------------
        # Method 6: Separator Dump Valve Malfunction (Eq 6-25, Table 6-25)
        # ----------------------------------------------------------------------
        elif meth == "dump_valve":
            ltype = "condensate" if liquid_type == "condensate" else "crude"
            info = self.TABLE_6_25_DUMP_VALVE[ltype]
            if dump_valve_hours is not None:
                # Equation 6-25: E_dump = CF * E_tank * (T / 8760)
                t_hours = float(dump_valve_hours)
                cf = info["cf"]
                # Baseline tank emissions of the same liquid (Table 6-22 crude, Table 6-24 condensate);
                # condensate used the crude factor (bug hunt 2026-10-15 #23)
                table = self.TABLE_6_24_CONDENSATE if ltype == "condensate" else self.TABLE_6_22_CRUDE
                base_ef = table["large_uncontrolled"]["kg_ch4_per_bbl"]
                base_tank_kg = q_bbl * base_ef
                gross_ch4_kg = cf * base_tank_kg * (t_hours / 8760.0)
            else:
                gross_ch4_kg = q_bbl * info["kg_ch4_per_bbl"]

            gross_ch4_tonnes = gross_ch4_kg / 1000.0
            if c_ch4 > 0 and c_co2 > 0:
                gross_co2_tonnes = gross_ch4_tonnes * (1.0 / MW_CH4) * (1.0 / c_ch4) * c_co2 * MW_CO2
            total_gas_scf = (gross_ch4_tonnes * LB_PER_TONNE * MOLAR_VOL_US) / (max(0.001, c_ch4) * MW_CH4)

        # ----------------------------------------------------------------------
        # Method 7: Produced Salt Water Tank Flashing (Table 6-26 & 6-27, Exhibit 6-21)
        # ----------------------------------------------------------------------
        elif meth == "produced_water":
            # Round pressure to nearest table key: 50, 250, 1000
            p = float(separator_pressure_psi or 250.0)
            key_p = 50 if p <= 150.0 else (1000 if p >= 600.0 else 250)
            s_key = str(salt_content or "average").lower().strip()
            if s_key not in ["2%", "10%", "20%", "average"]:
                s_key = "average"

            ef_tonnes_per_1000bbl = self.TABLE_6_26_SALT_WATER.get((key_p, s_key), 0.0142)
            gross_ch4_tonnes = (q_bbl / 1000.0) * ef_tonnes_per_1000bbl
            denom_ch4 = c_ch4 if c_ch4 > 0 else 0.80
            total_gas_scf = (gross_ch4_tonnes * LB_PER_TONNE * MOLAR_VOL_US) / (denom_ch4 * MW_CH4)
            if c_co2 > 0:
                gross_co2_tonnes = (total_gas_scf * c_co2 * MW_CO2) / (LB_PER_TONNE * MOLAR_VOL_US)
            else:
                gross_co2_tonnes = 0.0

        # ----------------------------------------------------------------------
        # Method 8: Working / Breathing Loss Direct Factor
        # ----------------------------------------------------------------------
        elif meth == "working_loss":
            gross_ch4_tonnes = (q_bbl * float(ef_ch4 or 0.0)) / 1000.0
            if gross_ch4_tonnes > 0 and c_ch4 > 0:
                total_gas_scf = gross_ch4_tonnes / (SCF_TO_M3 * c_ch4 * CONVERSIONS["density_ch4"] / 1000.0)
                gross_co2_tonnes = total_gas_scf * SCF_TO_M3 * c_co2 * CONVERSIONS["density_co2"] / 1000.0
            else:
                total_gas_scf = gross_co2_tonnes = 0.0

        # ----------------------------------------------------------------------
        # Method 9: Standard GOR Approach (Backwards Compatible)
        # ----------------------------------------------------------------------
        else:
            gor = float(gas_oil_ratio or 0.0)
            total_gas_scf = q_bbl * gor
            gross_ch4_tonnes = total_gas_scf * SCF_TO_M3 * c_ch4 * CONVERSIONS["density_ch4"] / 1000.0  # engine density convention
            gross_co2_tonnes = total_gas_scf * SCF_TO_M3 * c_co2 * CONVERSIONS["density_co2"] / 1000.0

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        # Disposition & control partitioning
        ctrl_eff = normalize_efficiency(control_efficiency, default=0.0)
        split = _split_vent_flare(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=gross_ch4_tonnes,
            co2_tonnes=gross_co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
            control_type=control_type, destruction_eff=destruction_efficiency,
        )

        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]
        flared_n2o = split["flared_n2o"]

        # a Table 6-22 / 6-24 default is a Tier 1 result whatever the record's factor source (a "specific"
        # record without a GOR or separator data was labelled Tier 3, i.e. measured)
        tier_unc = dict(uncertainties or {})
        if meth in ("table_6_22", "table_6_24"):
            tier_unc["_factor_source"] = "default"
        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o,
            uncertainties=tier_unc,
            factor_source="API_Section_6.3.9",
            category="tank_flashing",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "throughput_bbl": q_bbl,
                "gor": gas_oil_ratio,
                "type": process_type,
                "method": meth,
                "control_efficiency": ctrl_eff,
                "control_type": control_type,
                "total_gas_scf": total_gas_scf,
                "total_gas_m3": total_gas_m3,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.9",
                "tables": "Table 6-20 to 6-27, Eq 6-20 to 6-25",
            },
        )


def _parse_frac(v, default, name):
    raw = default if v in (None, "", "-") else v
    x = float(str(raw).replace("%", "").strip())
    if "%" in str(raw) or x > 1.0:
        x /= 100.0
    if x < 0.0 or x > 1.0:
        raise ValueError(f"{name} must be between 0 and 1 (or 0% to 100%): {v}")
    return x


def estimate_gas_z_factor(p_psia, t_kelvin, specific_gravity=0.65):
    """
    Real gas compressibility factor Z(P, T, SG) using Papay / Standing correlations.
    API Compendium Section 6.4; ISO 14064-1 Cl. 5.2.2.
    """
    sg = float(specific_gravity or 0.65)
    p_pc = 756.8 - 131.0 * sg - 3.6 * (sg ** 2)
    t_pc_r = 169.2 + 349.5 * sg - 74.0 * (sg ** 2)
    t_r = t_kelvin * 1.8
    p_pr = max(0.01, p_psia / max(10.0, p_pc))
    t_pr = max(1.05, t_r / max(10.0, t_pc_r))
    z = 1.0 - (3.52 * p_pr / (10 ** (0.9813 * t_pr))) + (0.274 * (p_pr ** 2) / (10 ** (0.8157 * t_pr)))
    return max(0.2, min(1.5, round(z, 4)))


class BlowdownCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.4.6.1 - Equipment and Process Blowdowns
    Equations 6-30 to 6-33 & Table 6-32.
    Remediates BUG-101 while preserving full backwards compatibility:
      - Depressurization Mode: Accounts for differential blowdown pressure (P_1 - P_final) / P_std
        when venting to atmospheric pressure without purge.
      - Evacuation / Purged Mode: Accounts for full contents evacuation (P_1 / P_std).
      - Table 6-32 Default Factors:
          * Vessel blowdowns: 78 scf CH4/vessel-yr (0.0015 tonnes CH4/vessel-yr)
          * Compressor blowdowns: 3,774 scf CH4/compressor-yr (0.07239 tonnes CH4/compressor-yr)
          * Gathering pipeline blowdowns: 309 scf CH4/mile-yr (0.00593 tonnes CH4/mile-yr)
    Verified against Exhibits 6-25 and 6-26.
    """

    TABLE_6_32 = {
        "vessel": {"scf_gas_yr": 99.0, "scf_ch4_yr": 78.0, "ef_ch4_tonnes": 0.0015, "baseline_ch4_mol": 0.788, "unc": 3.26},
        "compressor": {"scf_gas_yr": 4789.0, "scf_ch4_yr": 3774.0, "ef_ch4_tonnes": 0.07239, "baseline_ch4_mol": 0.788, "unc": 1.79},
        "pipeline_mile": {"scf_gas_yr": 392.0, "scf_ch4_yr": 309.0, "ef_ch4_tonnes": 0.00593, "baseline_ch4_mol": 0.788, "unc": 0.395},
    }

    def __init__(self):
        super().__init__("Blowdown Events", "Section 6.4.6.1")

    def calculate(
        self,
        blowdown_volume=None,
        pressure=None,
        events=1,
        ch4_content=0.85,
        uncertainties=None,
        co2_content=0.0,
        control_efficiency=0.0, destruction_efficiency=None,
        ef_co2=None,
        ef_ch4=None,
        ef_n2o=None,
        operating_temperature=60.0,
        temp_unit="F",
        press_unit="psig",
        z_factor=None,
        hhv=1020.0,
        gwp_dict=None,
        # API 2021 Section 6.4.6.1 advanced options
        blowdown_mode="depressurization", # "depressurization", "evacuation", "differential", "table_6_32"
        activity_type=None,               # "vessel", "compressor", "pipeline_mile"
        equipment_count=None,
        final_pressure=None,              # gauge pressure remaining after blowdown
        diameter_ft=None,
        length_ft=None,
        liquid_volume_fraction=0.0,       # fraction occupied by liquid (Exhibit 6-25)
        gas_specific_gravity=0.65,
        control_type="flare",
    ):
        uncertainties = uncertainties or {}
        bmode = str(blowdown_mode or "depressurization").lower().strip()

        c_ch4 = _parse_frac(ch4_content, 0.85, "ch4_content")
        c_co2 = _parse_frac(co2_content, 0.0, "co2_content")
        if (c_ch4 + c_co2) > 1.0001:
            raise ValueError(f"Sum of CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) cannot exceed 100%")

        total_v_std_m3 = 0.0
        total_gas_scf = 0.0
        gross_ch4_tonnes = 0.0
        gross_co2_tonnes = 0.0

        if activity_type in self.TABLE_6_32 or bmode == "table_6_32":
            act = activity_type or "vessel"
            info = self.TABLE_6_32.get(act, self.TABLE_6_32["vessel"])
            n_eq = float(equipment_count if equipment_count is not None else events)
            if n_eq < 0:
                raise ValueError(f"Equipment count / events cannot be negative: {n_eq}")
            total_gas_scf = n_eq * info["scf_gas_yr"]
            total_v_std_m3 = convert(total_gas_scf, "scf", "m3")
            gross_ch4_tonnes = n_eq * info["ef_ch4_tonnes"] * (c_ch4 / 0.788)
            if c_ch4 > 0 and c_co2 > 0:
                gross_co2_tonnes = gross_ch4_tonnes * (1.0 / MW_CH4) * (1.0 / c_ch4) * c_co2 * MW_CO2

        else:
            self.validate_inputs(
                {
                    "pressure": pressure,
                    "events": events,
                },
                ["pressure", "events"],
            )  # both >= 0

            # Resolve physical volume
            v_phys_m3 = 0.0
            if diameter_ft is not None and length_ft is not None:
                # Cylindrical volume (Exhibit 6-25)
                self.validate_inputs({"diameter_ft": diameter_ft, "length_ft": length_ft}, ["diameter_ft", "length_ft"])
                r_ft = float(diameter_ft) / 2.0
                l_ft = float(length_ft)
                v_cyl_ft3 = math.pi * (r_ft ** 2) * l_ft
                liq_frac = float(liquid_volume_fraction or 0.0)
                if not 0.0 <= liq_frac <= 1.0:
                    raise ValueError(f"liquid_volume_fraction must be between 0 and 1: {liquid_volume_fraction}")
                v_gas_ft3 = v_cyl_ft3 * (1.0 - liq_frac)
                v_phys_m3 = convert(v_gas_ft3, "scf", "m3")
            else:
                self.validate_inputs({"blowdown_volume": blowdown_volume}, ["blowdown_volume"])
                v_phys_m3 = float(blowdown_volume)

            # Thermodynamic correction
            per, gauge = _pressure_unit(press_unit, "psig")
            p_val = float(pressure)
            p_initial_psia = p_val * per + (STD_PRESSURE_PSIA if gauge else 0.0)  # pressure >= 0 (validated)
            t_abs_k = to_kelvin(operating_temperature, temp_unit)
            t_factor = STD_TEMP_K / max(1.0, t_abs_k)
            # Real gas compressibility factor Z (API Section 6.4 / ISO 14064-1 Cl. 5.2.2 / BUG-0014)
            if z_factor is not None and float(z_factor) > 0:
                z = float(z_factor)
            elif p_initial_psia >= 1000.0:  # High-pressure regime (>= ~70 bar)
                z = estimate_gas_z_factor(p_initial_psia, t_abs_k, gas_specific_gravity)
            else:
                z = 1.0

            # Differential depressurization vs full evacuation (BUG-101 / BUG-0015 remediation):
            # If final_pressure is specified (including 0.0 psig = atmospheric vent), or blowdown_mode is "differential":
            if bmode == "differential" or final_pressure is not None:
                pf_per, pf_gauge = _pressure_unit(press_unit, "psig")
                pf_val = float(final_pressure if final_pressure is not None else 0.0)
                raw_pf_psia = pf_val * pf_per + (STD_PRESSURE_PSIA if pf_gauge else 0.0)
                if raw_pf_psia < 0:
                    raise ValueError(f"Final pressure is below absolute vacuum ({raw_pf_psia:.2f} psia)")
                p_final_psia = raw_pf_psia
                p_factor = max(0.0, p_initial_psia - p_final_psia) / STD_PRESSURE_PSIA
            else:
                p_factor = p_initial_psia / STD_PRESSURE_PSIA

            v_std_per_event = v_phys_m3 * p_factor * t_factor * (1.0 / z)
            total_v_std_m3 = v_std_per_event * float(events)
            total_gas_scf = convert(total_v_std_m3, "m3", "scf")

            ch4_vol = total_v_std_m3 * c_ch4
            ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
            gross_ch4_tonnes = ch4_mass_kg / 1000.0

            co2_vol = total_v_std_m3 * c_co2
            co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
            gross_co2_tonnes = co2_mass_kg / 1000.0

        # Split vented and flared
        ctrl_eff = normalize_efficiency(control_efficiency, default=0.0)
        split = _split_vent_flare(
            total_gas_m3=total_v_std_m3,
            ch4_tonnes=gross_ch4_tonnes,
            co2_tonnes=gross_co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
            control_type=control_type, destruction_eff=destruction_efficiency,
        )

        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]
        flared_n2o = split["flared_n2o"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o,
            uncertainties=uncertainties,
            factor_source="API_Section_6.4.6.1",
            category="blowdown",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "blowdown_volume": blowdown_volume,
                "pressure": pressure,
                "events": events,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "control_efficiency": ctrl_eff,
                "operating_temperature": operating_temperature,
                "mode": bmode,
                "total_v_std_m3": total_v_std_m3,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.4.6.1",
                "equations": "Equation 6-30 to 6-33, Table 6-32",
                "temp_correction_applied": True,
            },
        )
