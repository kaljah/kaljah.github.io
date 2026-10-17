"""Pneumatic device, pneumatic pump and gas dehydration calculators.

Split out of calculations/vented_production.py unchanged (hardening plan, task 5.5).
calculations.vented_production re-exports every class, so existing imports keep working.
"""
import math
from .base import BaseCalculator
from .units import CONVERSIONS, STD_PRESSURE_PSIA, calculate_co2e, convert
from calculations.vented_production import LB_PER_TONNE, MOLAR_VOL_US, MW_CH4, MW_CO2, SCF_TO_M3, _propagate_results, _split_vent_flare
from calculations.vented_production_wells import _route


def _given(value, default):
    """An entered value (0 included) as a float, else the default."""
    return float(default) if value in (None, "") else float(value)


def _parse_frac(v, default, name):
    raw = default if v in (None, "", "-") else v
    val = float(str(raw).replace("%", "").strip())
    if "%" in str(raw) or val > 1.0:
        val /= 100.0
    if val < 0.0 or val > 1.0:
        raise ValueError(f"{name} must be between 0 and 1 (or 0% to 100%): {v}")
    return val


class PneumaticDeviceCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.6 - Natural Gas-Driven Pneumatic Controllers
    Fully backwards compatible with existing calls, while adding:
      - Continuous vent controllers (Table 6-14): High Bleed, Low Bleed
      - Intermittent vent controllers (Table 6-15): Intermittent Average, Normal, Malfunctioning
      - Unknown controller type default: 9.2 scf gas/hr (Table on p. 6-40)
      - Proactive monitoring LDAR survey model (Equation 6-14, Exhibit 6-12)
      - Physical actuation model (Equation 6-13)
      - GPSA Orifice continuous model (Equation 6-12)
    Verified against Exhibits 6-11 and 6-12.
    """

    TABLE_6_14_CONTINUOUS = {
        "high_bleed": {"api_scf_hr": 16.4, "subpart_w_scf_hr": 37.3, "baseline_ch4_mol": 0.816},
        "low_bleed": {"api_scf_hr": 2.6, "subpart_w_scf_hr": 1.39, "baseline_ch4_mol": 0.816},
    }

    TABLE_6_15_INTERMITTENT = {
        "intermittent_average": {"api_scf_hr": 9.3, "subpart_w_scf_hr": 13.5, "baseline_ch4_mol": 0.816},
        "intermittent_normal": {"api_scf_hr": 0.28, "subpart_w_scf_hr": 13.5, "baseline_ch4_mol": 0.816},
        "intermittent_malfunctioning": {"api_scf_hr": 24.1, "subpart_w_scf_hr": 13.5, "baseline_ch4_mol": 0.816},
    }

    DEFAULT_UNKNOWN_SCF_HR = 9.2  # 9.2 scf whole gas/hr/controller

    def __init__(self):
        super().__init__("Pneumatic Controllers", "Section 6.3.6")

    def _table_rate(self, controller_type, source_standard):
        """Whole gas scf/h of a controller type (Tables 6-14 / 6-15; 9.2 scf/h when the type is unknown)."""
        ctype = str(controller_type).lower().strip()
        std = str(source_standard or "api").lower().strip()
        if std not in ("api", "subpart_w"):
            raise ValueError(f"Unknown factor standard '{source_standard}': api or subpart_w")
        rows = {**self.TABLE_6_14_CONTINUOUS, **self.TABLE_6_15_INTERMITTENT}
        if ctype in ("unknown", "average", "production_average"):
            return self.DEFAULT_UNKNOWN_SCF_HR
        if ctype not in rows:  # a misspelt type took the 9.2 scf/h unknown-controller factor
            raise ValueError(f"Unknown controller type '{controller_type}': {sorted(rows) + ['unknown']}")
        return rows[ctype]["subpart_w_scf_hr" if std == "subpart_w" else "api_scf_hr"]

    def calculate(
        self,
        count=None,
        hours=8760,
        bleed_rate=None,
        ch4_content=None,          # Tables 6-14 / 6-15 basis 81.6 mol % (it was 85 %)
        uncertainties=None,
        actuations=None,
        co2_content=0.0,
        gwp_dict=None,
        # API 2021 Section 6.3.6 advanced options
        controller_type=None,  # "high_bleed", "low_bleed", "intermittent_average", "intermittent_normal", "intermittent_malfunctioning", "unknown"
        source_standard="api", # "api" or "subpart_w"
        # Equation 6-14 Monitoring / LDAR Survey inputs
        monitoring_program=False,
        normal_count=None,
        normal_fraction_year=1.0,
        malfunctioning_count=None,
        malfunctioning_fraction_year=0.0,
        # Equation 6-13 Physical actuation inputs
        id_pipe_inches=None,
        length_pipe_ft=None,
        delta_vol_bonnet_scf=None,
        p_control_psig=None,
        p_atm_psia=14.7,
        actuations_per_year=None,
    ):
        uncertainties = uncertainties or {}

        c_ch4 = _parse_frac(ch4_content, 0.816, "ch4_content")
        c_co2 = _parse_frac(co2_content, 0.0, "co2_content")
        if (c_ch4 + c_co2) > 1.0001:
            raise ValueError(f"Sum of CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) cannot exceed 100%")

        hrs = max(0.0, float(8760 if hours is None else hours))  # 0 h is zero, not a full year
        total_gas_scf = 0.0
        calc_mode = "legacy"

        # Case 1: Equation 6-14 Monitoring and Repair Survey Approach (Exhibit 6-12)
        if monitoring_program and (normal_count is not None or malfunctioning_count is not None):
            calc_mode = "monitoring_program_eq_6_14"
            n_norm, t_norm = float(normal_count or 0.0), float(1.0 if normal_fraction_year is None else normal_fraction_year)
            n_mf, t_mf = float(malfunctioning_count or 0.0), float(malfunctioning_fraction_year or 0.0)
            if n_norm < 0 or n_mf < 0:
                raise ValueError("Device counts cannot be negative")
            if t_norm < 0 or t_mf < 0:
                raise ValueError("Year fractions cannot be negative")

            # API Table 6-15: normal = 0.28 scf gas/hr (0.038 t CH4/yr at 81.6%); mf = 24.1 scf gas/hr (3.30 t CH4/yr at 81.6%)
            # Emissions can be computed directly in whole gas scf:
            ef_norm_scf_yr = 0.28 * hrs
            ef_mf_scf_yr = 24.1 * hrs
            total_gas_scf = (n_norm * ef_norm_scf_yr * t_norm) + (n_mf * ef_mf_scf_yr * t_mf)

        # Case 2: Equation 6-13 Physical actuation volume model
        elif id_pipe_inches is not None and length_pipe_ft is not None and delta_vol_bonnet_scf is not None:
            calc_mode = "physical_actuation_eq_6_13"
            n_dev = float(count if count is not None else 1.0)
            if n_dev < 0:
                raise ValueError("Device count cannot be negative")
            id_ft, l_ft, d_vol = float(id_pipe_inches) / 12.0, float(length_pipe_ft), float(delta_vol_bonnet_scf)
            pipe_vol = (math.pi / 4.0) * (id_ft ** 2) * l_ft
            v_act = pipe_vol + d_vol

            # Eq 6-13 has no default supply pressure or actuation count (30 psig / 1,000 were assumed)
            if p_control_psig in (None, ""):
                raise ValueError("Equation 6-13 needs the controller supply pressure (psig)")
            n_act_raw = actuations_per_year if actuations_per_year not in (None, "") else actuations
            if n_act_raw in (None, ""):
                raise ValueError("Equation 6-13 needs the number of actuations per year")
            p_ctrl = float(p_control_psig)
            p_atm = _given(p_atm_psia, 14.7)
            p_factor = (p_ctrl + p_atm) / STD_PRESSURE_PSIA

            n_act = float(n_act_raw)
            vol_per_controller = v_act * p_factor * n_act
            total_gas_scf = n_dev * vol_per_controller

        # Case 3: API Table 6-14 / Table 6-15 Controller Type Selection
        elif controller_type is not None:
            calc_mode = "table_factor"
            self.validate_inputs({"count": count}, ["count"])
            n_dev = float(count)
            total_gas_scf = n_dev * self._table_rate(controller_type, source_standard) * hrs

        # Case 4: Backwards compatible intermittent actuation or continuous bleed
        elif actuations is not None and float(actuations) > 0:
            calc_mode = "intermittent_actuation"
            self.validate_inputs({"count": count}, ["count"])
            n_dev = float(count)
            # BUG-100: 13.5 is the Subpart W intermittent factor in scf whole gas PER HOUR (Table 6-15),
            # not a volume per actuation. Eq 6-13 needs the gas vented per actuation.
            if not bleed_rate or float(bleed_rate) <= 0:
                raise ValueError("Actuation-based pneumatic emissions need the gas volume per actuation (scf); "
                                 "otherwise choose a controller type (Tables 6-14 / 6-15)")
            total_gas_scf = n_dev * float(actuations) * float(bleed_rate)

        else:
            calc_mode = "continuous_bleed"
            self.validate_inputs({"count": count}, ["count"])
            n_dev = float(count)
            # Default rate if bleed_rate not provided: unknown average 9.2 scf/hr
            rate = float(bleed_rate) if bleed_rate is not None and float(bleed_rate) > 0 else self.DEFAULT_UNKNOWN_SCF_HR
            total_gas_scf = n_dev * hrs * rate

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        # Mass via ideal gas law at standard conditions
        total_ch4 = total_gas_scf * SCF_TO_M3 * c_ch4 * CONVERSIONS["density_ch4"] / 1000.0  # engine density convention
        total_co2 = total_gas_scf * SCF_TO_M3 * c_co2 * CONVERSIONS["density_co2"] / 1000.0

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=0.0,
            uncertainties=uncertainties,
            factor_source="API_Section_6.3.6",
            category="pneumatic_device",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=0.0, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "count": count if count is not None else (normal_count or 0) + (malfunctioning_count or 0),
                "hours": hrs,
                "bleed_rate": bleed_rate,
                "controller_type": controller_type,
                "mode": calc_mode,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "total_gas_scf": total_gas_scf,
                "total_gas_m3": total_gas_m3,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.6",
                "tables": "Table 6-14, Table 6-15, Eq 6-13, Eq 6-14",
            },
        )


class PneumaticPumpCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.7 - Gas Driven Pneumatic Pumps (Chemical Injection Pumps)
    Methods:
      - Tier 1 / Table 6-16 default emission factors:
          * Piston pump: 48.9 scfd CH4/pump (2.59 scf gas/hr, 0.34 tonnes CH4/pump-yr at 78.8%)
          * Diaphragm pump: 446 scfd CH4/pump (23.6 scf gas/hr, 3.12 tonnes CH4/pump-yr at 78.8%)
          * Average pump: 248 scfd CH4/pump (13.1 scf gas/hr, 1.73 tonnes CH4/pump-yr at 78.8%)
          * CCAC Piston: 2.03 scf gas/hr
          * CCAC Diaphragm: 18.58 scf gas/hr
      - Tier 2 / Engineering model (Equation 6-15 & 6-16):
          V_G = [(P_O + P_A) / 14.7] * [T_A / (459.7 + T_G)] * V_L * (1 + I)
          V_L = (V_S / 7.48) * N * T
    """

    TABLE_6_16 = {
        "piston": {"scf_gas_hr": 2.59, "ef_ch4_tonnes": 0.34, "baseline_ch4_mol": 0.788, "unc": 1.41},
        "diaphragm": {"scf_gas_hr": 23.6, "ef_ch4_tonnes": 3.12, "baseline_ch4_mol": 0.788, "unc": 0.99},
        "average": {"scf_gas_hr": 13.1, "ef_ch4_tonnes": 1.73, "baseline_ch4_mol": 0.788, "unc": 1.08},
        "piston_ccac": {"scf_gas_hr": 2.03, "ef_ch4_tonnes": 0.28, "baseline_ch4_mol": 0.816, "unc": 0.50},
        "diaphragm_ccac": {"scf_gas_hr": 18.58, "ef_ch4_tonnes": 2.54, "baseline_ch4_mol": 0.816, "unc": 0.50},
    }

    def __init__(self):
        super().__init__("Chemical Injection Pneumatic Pumps", "Section 6.3.7")

    def calculate(
        self,
        method="factor",  # "factor", "engineering", "direct_measurement"
        pump_type="diaphragm",  # "piston", "diaphragm", "average", "piston_ccac", "diaphragm_ccac"
        pump_count=1.0,
        operating_hours=8760.0,
        # Equation 6-15 / 6-16 Engineering inputs
        volume_liquid_pumped_ft3=None,
        volume_per_stroke_gal=None,
        strokes_per_minute=None,
        annual_operational_minutes=None,
        pump_outlet_pressure_psig=None,  # Eq 6-15 P_O, no default (100 psig was assumed)
        atmospheric_pressure_psia=14.7,
        gas_temperature_f=60.0,
        atmospheric_temperature_r=520.0,
        pump_inefficiency=0.30,  # default 30% inefficiency -> (1 + 0.30)
        # Direct measurement inputs
        measured_gas_scf=None,
        # Common inputs
        ch4_content=0.816,
        co2_content=0.0,
        control_efficiency=None,
        disposition="vented",
        hhv=1020.0,
        ef_n2o=None,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        meth = str(method or "factor").lower().strip()
        if meth not in ("factor", "engineering", "direct_measurement"):
            raise ValueError(f"Unknown pneumatic pump method '{method}': factor, engineering or direct_measurement")
        n_pumps = _given(pump_count, 1.0)  # 0 pumps is 0 (it was 1)
        if n_pumps < 0:
            raise ValueError("pump_count cannot be negative")
        hrs = max(0.0, float(8760.0 if operating_hours is None else operating_hours))

        c_ch4 = _parse_frac(ch4_content, 0.816, "ch4_content")
        c_co2 = _parse_frac(co2_content, 0.0, "co2_content")
        if (c_ch4 + c_co2) > 1.0001:
            raise ValueError(f"Sum of CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) cannot exceed 100%")

        total_gas_scf = 0.0

        if meth == "engineering":
            # Equation 6-15 & 6-16
            if volume_liquid_pumped_ft3 is not None:
                v_liquid_ft3 = float(volume_liquid_pumped_ft3)
            elif volume_per_stroke_gal is not None and strokes_per_minute is not None:
                mins = float(annual_operational_minutes if annual_operational_minutes is not None else hrs * 60.0)
                v_s = float(volume_per_stroke_gal)
                n_strokes = float(strokes_per_minute)
                v_liquid_ft3 = (v_s / 7.48052) * n_strokes * mins
            else:
                raise ValueError("Engineering method requires volume_liquid_pumped_ft3 or volume_per_stroke_gal + strokes_per_minute")

            if v_liquid_ft3 < 0:
                raise ValueError(f"Liquid volume cannot be negative: {v_liquid_ft3}")
            if pump_outlet_pressure_psig in (None, ""):
                raise ValueError("Equation 6-15 needs the pump outlet pressure (psig)")
            p_out = float(pump_outlet_pressure_psig)
            p_atm = _given(atmospheric_pressure_psia, 14.7)
            t_g = _given(gas_temperature_f, 60.0)  # 0 F is 0 F (it was 60 F)
            if t_g <= -459.67:
                raise ValueError("Gas temperature must be above absolute zero (-459.67 °F)")
            t_atm_r = float(atmospheric_temperature_r or 519.67)
            ineff = float(pump_inefficiency if pump_inefficiency is not None else 0.30)

            # Equation 6-15: V_G = [(P_O + P_A) / 14.7] * [T_A / (459.7 + T_G)] * V_L * (1 + I)
            p_ratio = (p_out + p_atm) / 14.7
            t_ratio = t_atm_r / (459.67 + t_g)
            v_g_single = p_ratio * t_ratio * v_liquid_ft3 * (1.0 + ineff)
            total_gas_scf = n_pumps * v_g_single

        elif meth == "direct_measurement":
            self.validate_inputs({"measured_gas_scf": measured_gas_scf}, ["measured_gas_scf"])
            total_gas_scf = float(measured_gas_scf)

        else:
            # Default Table 6-16 factor
            ptype = str(pump_type or "diaphragm").lower().strip()
            if ptype not in self.TABLE_6_16:  # an unknown type took the diaphragm factor
                raise ValueError(f"Unknown pump type '{pump_type}': {sorted(self.TABLE_6_16)}")
            info = self.TABLE_6_16[ptype]
            rate_scf_hr = info["scf_gas_hr"]
            total_gas_scf = n_pumps * rate_scf_hr * hrs

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        gross_ch4_tonnes = total_gas_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        disp, eff, de, gross_ch4_tonnes, gross_co2_tonnes = _route(disposition, control_efficiency, gross_ch4_tonnes,
                                                               gross_co2_tonnes)

        split = _split_vent_flare(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=gross_ch4_tonnes,
            co2_tonnes=gross_co2_tonnes,
            ctrl_eff=eff, destruction_eff=de,
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
            factor_source="API_Section_6.3.7",
            category="chemical_injection_pump",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "method": meth,
                "pump_type": pump_type,
                "pump_count": n_pumps,
                "operating_hours": hrs,
                "total_gas_scf": total_gas_scf,
                "total_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "disposition": disp,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.7",
                "tables": "Table 6-16, Eq 6-15, Eq 6-16",
            },
        )


class GasDehydrationCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.8.1 & 6.3.8.2 - Gas Dehydration
    Supports:
      - Glycol Dehydrator Vents (Table 6-17):
          * Throughput factor: 0.0052859 tonnes CH4 / 10^6 scf gas (349.7 scf gas / 10^6 scf)
          * Unit factor: 73.4 Mscf CH4/unit-yr = 0.06149 tonnes CH4/unit-yr
      - Gas-Assisted Kimray Pump Vents (Table 6-18, Exhibit 6-14):
          * 992.0 scf CH4 / 10^6 scf gas = 0.01903 tonnes CH4 / 10^6 scf gas
      - Desiccant Dehydrator Changeout Venting (Equation 6-17, Exhibit 6-15):
          GLD = [H * D^2 * pi * P2 * G * N] / [4 * P1]
    Verified against Exhibits 6-13, 6-14, and 6-15.
    """

    TABLE_6_17_DEHY = {
        "throughput": {"ef_ch4_tonnes_per_mmscf": 0.0052859, "scf_gas_per_mmscf": 349.7, "baseline_ch4_mol": 0.788},
        "unit": {"ef_ch4_tonnes_yr": 0.06149, "scf_gas_yr": 93200.0, "baseline_ch4_mol": 0.788},
    }

    TABLE_6_18_KIMRAY = {
        "ef_ch4_tonnes_per_mmscf": 0.01903,
        "scf_gas_per_mmscf": 1258.0,
        "baseline_ch4_mol": 0.788,
    }

    def __init__(self):
        super().__init__("Gas Dehydration", "Section 6.3.8")

    def calculate(
        self,
        dehydrator_type="glycol",  # "glycol", "desiccant"
        # Glycol inputs
        gas_throughput_mmscfd=None, # MMscf/day
        gas_throughput_mmscf_yr=None,
        operating_days=365.0,
        has_gas_assisted_pump=False,
        dehydrator_count=1.0,
        use_unit_factor=False,
        # Desiccant inputs (Equation 6-17)
        vessel_height_ft=None,
        vessel_diameter_ft=None,
        vessel_pressure_psig=None,
        gas_void_fraction=None,  # G, fraction of the packed vessel that is gas (Exhibit 6-15: 0.45; no default)
        changeouts_per_year=None,
        # Gas composition
        ch4_content=None,  # mole fraction or %
        co2_content=None,  # mole fraction or %
        control_efficiency=None,
        disposition="vented",
        hhv=1020.0,
        ef_n2o=None,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        dtype = str(dehydrator_type or "glycol").lower().strip()
        if dtype not in ("glycol", "desiccant"):
            raise ValueError(f"Unknown dehydrator type '{dehydrator_type}': glycol or desiccant")
        days = _given(operating_days, 365.0)  # 0 days is 0 (it was 365)
        if days < 0:
            raise ValueError("operating_days cannot be negative")

        c_ch4 = _parse_frac(ch4_content, 0.788, "ch4_content")
        c_co2 = _parse_frac(co2_content, 0.0, "co2_content")
        if (c_ch4 + c_co2) > 1.0001:
            raise ValueError(f"Sum of CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) cannot exceed 100%")

        gross_ch4_tonnes = 0.0
        gross_co2_tonnes = 0.0
        total_gas_scf = 0.0

        if dtype == "desiccant":
            # Equation 6-17: GLD = [H * D^2 * pi * P2 * G * N] / [4 * P1]
            self.validate_inputs(
                {
                    "vessel_height_ft": vessel_height_ft,
                    "vessel_diameter_ft": vessel_diameter_ft,
                    "vessel_pressure_psig": vessel_pressure_psig,
                    "changeouts_per_year": changeouts_per_year,
                    "gas_void_fraction": gas_void_fraction,
                },
                ["vessel_height_ft", "vessel_diameter_ft", "vessel_pressure_psig", "changeouts_per_year",
                 "gas_void_fraction"],
            )
            h = float(vessel_height_ft)
            d = float(vessel_diameter_ft)
            p2 = float(vessel_pressure_psig) + 14.7  # psia
            p1 = 14.7
            g = float(gas_void_fraction)
            n = float(changeouts_per_year)

            total_gas_scf = (h * (d ** 2) * math.pi * p2 * g * n) / (4.0 * p1)
            gross_ch4_tonnes = total_gas_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
            gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        else:
            # Glycol Dehydrator
            if use_unit_factor or (gas_throughput_mmscfd is None and gas_throughput_mmscf_yr is None):
                # Count basis (Table 6-17)
                n_dehy = _given(dehydrator_count, 1.0)  # 0 dehydrators is 0 (it was 1)
                if n_dehy < 0:
                    raise ValueError(f"dehydrator_count cannot be negative ({n_dehy})")
                # 0.06149 t CH4/yr at 78.8%
                base_ef = self.TABLE_6_17_DEHY["unit"]["ef_ch4_tonnes_yr"]
                gross_ch4_tonnes = n_dehy * base_ef * (c_ch4 / 0.788)
                total_gas_scf = n_dehy * self.TABLE_6_17_DEHY["unit"]["scf_gas_yr"]
                # CO2 in glycol is negligible unless gas pump is present
                gross_co2_tonnes = 0.0

            else:
                annual_mmscf = float(gas_throughput_mmscfd) * days if gas_throughput_mmscfd is not None else float(gas_throughput_mmscf_yr)
                if annual_mmscf < 0:
                    raise ValueError("Gas throughput cannot be negative")

                # Table 6-17 Dehydrator vent emissions (Exhibit 6-13)
                base_ef = self.TABLE_6_17_DEHY["throughput"]["ef_ch4_tonnes_per_mmscf"]
                dehy_ch4_tonnes = annual_mmscf * base_ef * (c_ch4 / 0.788)
                dehy_scf = annual_mmscf * self.TABLE_6_17_DEHY["throughput"]["scf_gas_per_mmscf"]

                # Kimray gas-assisted glycol pump (Table 6-18, Exhibit 6-14)
                pump_ch4_tonnes = 0.0
                pump_co2_tonnes = 0.0
                pump_scf = 0.0
                if has_gas_assisted_pump:
                    pump_ef = self.TABLE_6_18_KIMRAY["ef_ch4_tonnes_per_mmscf"]
                    pump_ch4_tonnes = annual_mmscf * pump_ef * (c_ch4 / 0.788)
                    pump_scf = annual_mmscf * self.TABLE_6_18_KIMRAY["scf_gas_per_mmscf"]
                    # CO2 via ratio: ECO2 = ECH4 * (1/16) * (1/y_ch4) * y_co2 * 44
                    if c_ch4 > 0 and c_co2 > 0:
                        pump_co2_tonnes = pump_ch4_tonnes * (1.0 / MW_CH4) * (1.0 / c_ch4) * c_co2 * MW_CO2

                gross_ch4_tonnes = dehy_ch4_tonnes + pump_ch4_tonnes
                # In glycol regenerators, CO2 is not soluble so regenerator CO2 = 0; pump vents motive gas containing CO2
                gross_co2_tonnes = pump_co2_tonnes
                total_gas_scf = dehy_scf + pump_scf

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        disp, eff, de, gross_ch4_tonnes, gross_co2_tonnes = _route(disposition, control_efficiency, gross_ch4_tonnes,
                                                               gross_co2_tonnes)

        split = _split_vent_flare(total_gas_m3=total_gas_m3, ch4_tonnes=gross_ch4_tonnes,
                                  co2_tonnes=gross_co2_tonnes, ctrl_eff=eff, destruction_eff=de,
                                  hhv=hhv, ef_n2o=ef_n2o)
        total_ch4, total_co2, flared_n2o = split["total_ch4"], split["total_co2"], split["flared_n2o"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o,
            uncertainties=uncertainties,
            factor_source="API_Section_6.3.8",
            category="gas_dehydration",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "dehydrator_type": dtype,
                "has_gas_assisted_pump": has_gas_assisted_pump,
                "total_gas_scf": total_gas_scf,
                "total_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "disposition": disp,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.8",
                "tables": "Table 6-17, Table 6-18, Eq 6-17",
            },
        )
