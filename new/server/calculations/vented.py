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
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty
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
        super().__init__("Drilling Mud Degassing", "Section 6.2")

    def calculate(
        self, mud_volume, mud_type, uncertainties, ef_ch4=None, gwp_dict=None
    ):
        """
        API Section 6.2 - CH4 from mud degassing
        """
        self.validate_inputs({"volume": mud_volume}, ["volume"])

        # Default factors (kg CH4 / m3 mud)
        factors = {"water_based": 0.15, "oil_based": 0.35, "synthetic": 0.25}

        # Use provided EF if available (and non-zero), otherwise default based on type
        if ef_ch4 and ef_ch4 > 0:
            ef = ef_ch4
        else:
            ef = factors.get(mud_type, 0.25)

        ch4_kg = float(mud_volume) * ef
        ch4_tonnes = ch4_kg / 1000.0

        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        ch4_res = propagate_uncertainty(
            ch4_tonnes,
            resolve_ef_uncertainty("vented", "ch4", _tier, uncertainties.get("ch4")),
            tier=_tier,
            process_category="vented",
            gas="ch4",
        )
        total_co2e = calculate_co2e(ch4=ch4_tonnes, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={"mud_volume": mud_volume, "mud_type": mud_type, "ef_ch4_used": ef},
        )


class CompletionFlowbackCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Well Completion Flowback", "Section 6.3")

    def calculate(
        self,
        flowback_volume=None,
        ch4_content=0.85,
        control_efficiency=0.0,
        uncertainties=None,
        co2_content=0.0,
        ef_co2=None,
        ef_ch4=None,
        ef_n2o=None,
        calculation_method="metered_volume",
        flowback_rate=None,
        flowback_duration_hours=None,
        liquid_flowback_bbl=None,
        gas_oil_ratio=None,
        choke_size_in=None,
        well_head_pressure=None,
        hhv=1020.0,
        gwp_dict=None,
        events=1.0,
        gas_produced_sales_scf=0.0,
        rate_unit="mscf/day",
    ):
        """
        API Compendium 2021 §6.3 & EPA Subpart W §98.233(c) Completions & Workovers Flowback:
        Supports 3 rigorous calculation methodologies:
        1. 'metered_volume': Direct standard gas volume measurement (scf or m3).
        2. 'rate_duration': Flowback rate (Mcf/day or Mcf/hr) * duration (hours) * events.
        3. 'gor' / 'gor_liquid': Liquid flowback volume (bbl) * GOR (scf/bbl) * events - sales gas.
        """
        uncertainties = uncertainties or {}

        # Determine standard gas volume (in m3) based on selected method
        method = str(calculation_method).lower()
        total_gas_scf = 0.0
        num_events = float(events if events is not None else 1.0)

        if method == "rate_duration" and flowback_rate and flowback_duration_hours:
            rate_unit_norm = str(rate_unit or "mscf/day").lower().strip()
            if "hr" in rate_unit_norm or "hour" in rate_unit_norm:
                rate_scf_hr = float(flowback_rate) * 1000.0
            else:
                rate_scf_hr = (float(flowback_rate) * 1000.0) / 24.0
            total_gas_scf = rate_scf_hr * float(flowback_duration_hours) * num_events
            total_gas_m3 = convert(total_gas_scf, "scf", "m3")
        elif method in ["gor", "gor_liquid"] and liquid_flowback_bbl and gas_oil_ratio:
            gross_gas_scf = float(liquid_flowback_bbl) * float(gas_oil_ratio) * num_events
            deduct_scf = float(gas_produced_sales_scf or 0.0)
            total_gas_scf = max(0.0, gross_gas_scf - deduct_scf)
            total_gas_m3 = convert(total_gas_scf, "scf", "m3")
        else:
            # Direct flowback volume passed in m3 (or scf)
            self.validate_inputs(
                {"flowback_volume": flowback_volume}, ["flowback_volume"]
            )
            total_gas_m3 = float(flowback_volume) * num_events
            total_gas_scf = convert(total_gas_m3, "m3", "scf")

        ch4_frac = max(
            0.0, min(1.0, float(ch4_content if ch4_content is not None else 0.85))
        )
        co2_frac = max(0.0, min(1.0, float(co2_content or 0.0)))
        ctrl_eff = max(0.0, min(1.0, float(control_efficiency or 0.0)))

        # Methane mass
        ch4_vol = total_gas_m3 * ch4_frac
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        # CO2 mass
        co2_vol = total_gas_m3 * co2_frac
        co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
        co2_tonnes = co2_mass_kg / 1000.0

        split = _split_vented_and_flared(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=ch4_tonnes,
            co2_tonnes=co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]
        flared_n2o_tonnes = split["flared_n2o"]

        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o_tonnes,
            uncertainties=uncertainties,
            factor_source=uncertainties.get(
                "_factor_source",
                "site_specific" if method != "metered_volume" else "default",
            ),
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
                "method": method,
                "flowback_volume_m3": total_gas_m3,
                "flowback_volume_scf": total_gas_scf,
                "ch4_content": ch4_frac,
                "control_efficiency": ctrl_eff,
            },
            metadata={
                "standard": "API Compendium §6.3 / EPA Subpart W §98.233(c)",
                "calculation_method": method,
            },
        )


class LiquidsUnloadingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Liquids Unloading (Volume-Based)", "Section 6.4")

    def calculate(
        self,
        well_depth,
        diameter,
        pressure,
        ch4_content,
        events,
        uncertainties,
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
        hhv=1020.0,
        gwp_dict=None,
    ):
        """
        API Equation 6-3 - Volume per unloading event with temperature correction:
        V_std = (pi/4) * D^2 * Depth * (P_tubing_abs / P_std) * (T_std / T_well_abs)
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

        # Diameter conversion to meters
        d_val = float(diameter)
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

        # Depth conversion to meters
        depth_val = float(well_depth)
        dep_u = str(depth_unit or "ft").lower().strip()
        if dep_u in ["m", "meter", "meters"]:
            depth_m = depth_val
        elif dep_u in ["km", "kilometer"]:
            depth_m = depth_val * 1000.0
        else:  # 'ft', 'feet'
            depth_m = depth_val * 0.3048

        # Volume at tubing conditions (m3)
        v_tubing = (math.pi / 4.0) * (d_m**2) * depth_m

        # Pressure and temperature correction (API Eq. 6-3 & §4.2.1)
        p_abs = to_psia(pressure, press_unit)
        p_factor = p_abs / STD_PRESSURE_PSIA

        t_abs_k = to_kelvin(operating_temperature, temp_unit)
        t_factor = STD_TEMP_K / max(1.0, t_abs_k)

        v_std = v_tubing * p_factor * t_factor
        total_v_std = v_std * float(events)

        ch4_vol = total_v_std * float(ch4_content)
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        co2_vol = total_v_std * float(co2_content or 0.0)
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

        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o_tonnes,
            uncertainties=uncertainties,
            factor_source=uncertainties.get("_factor_source", "default"),
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
                "well_depth": well_depth,
                "diameter": diameter,
                "pressure": pressure,
                "events": events,
                "ch4_content": ch4_content,
                "co2_content": co2_content,
                "control_efficiency": control_efficiency,
                "operating_temperature": operating_temperature,
            },
        )


class BlowdownCalculator(BaseCalculator):
    """
    API Eq. 6-4: Vessel/Pipeline Blowdown (Depressurization)
    V_std = V_physical * (P_vessel_abs / P_std) * (T_std / T_vessel_abs) * (1 / Z) * Events
    Remediates CALC-06 by incorporating exact temperature and compressibility normalization.
    """

    def __init__(self):
        super().__init__("Blowdown Events", "Section 6.4")

    def calculate(
        self,
        blowdown_volume,
        pressure,
        events,
        ch4_content,
        uncertainties,
        co2_content=0.0,
        control_efficiency=0.0,
        ef_co2=None,
        ef_ch4=None,
        ef_n2o=None,
        operating_temperature=60.0,
        temp_unit="F",
        press_unit="psig",
        z_factor=1.0,
        hhv=1020.0,
        gwp_dict=None,
    ):
        self.validate_inputs(
            {
                "blowdown_volume": blowdown_volume,
                "pressure": pressure,
                "events": events,
            },
            ["blowdown_volume", "pressure", "events"],
        )

        # API Eq. 6-4 with complete temperature and pressure normalization (CALC-06 Remediation)
        p_abs = to_psia(pressure, press_unit)
        p_factor = p_abs / STD_PRESSURE_PSIA

        t_abs_k = to_kelvin(operating_temperature, temp_unit)
        t_factor = STD_TEMP_K / max(1.0, t_abs_k)

        z = float(z_factor) if z_factor and float(z_factor) > 0 else 1.0

        v_std_per_event = float(blowdown_volume) * p_factor * t_factor * (1.0 / z)
        total_v_std = v_std_per_event * float(events)

        ch4_vol = total_v_std * float(ch4_content)
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        co2_vol = total_v_std * float(co2_content or 0.0)
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

        ch4_res, co2_res, n2o_res = _propagate_vented_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o_tonnes,
            uncertainties=uncertainties,
            factor_source=uncertainties.get("_factor_source", "default"),
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
                "blowdown_volume": blowdown_volume,
                "pressure": pressure,
                "events": events,
                "ch4_content": ch4_content,
                "co2_content": co2_content,
                "control_efficiency": control_efficiency,
                "operating_temperature": operating_temperature,
            },
            metadata={
                "standard": "API Compendium Eq. 6-4 (T & P corrected)",
                "temp_correction_applied": True,
            },
        )


class TankFlashingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Storage Tank Emissions", "Section 6.8")

    def calculate(
        self,
        throughput,
        gas_oil_ratio,
        ch4_content,
        control_efficiency,
        uncertainties,
        process_type="tank_flashing",
        ef_ch4=0,
        co2_content=0.0,
        ef_co2=None,
        ef_n2o=None,
        hhv=1020.0,
        gwp_dict=None,
    ):
        """
        Calculates Tank Emissions (API Compendium Section 6.8 & EPA Subpart W §98.233(j)).
        If Flashing: Uses GOR method with flared combustion products when control_efficiency > 0.
        If Working/Breathing: Uses simple Factor * Throughput.
        """
        self.validate_inputs({"throughput": throughput}, ["throughput"])

        is_flashing = process_type in ["tank_flashing", "tank", "storage_tanks"] or (gas_oil_ratio and float(gas_oil_ratio) > 0 and not ef_ch4)

        if is_flashing:
            total_gas_scf = float(throughput) * float(gas_oil_ratio or 0.0)
            total_gas_m3 = convert(total_gas_scf, "scf", "m3")

            ch4_vol_scf = total_gas_scf * float(ch4_content if ch4_content is not None else 0.85)
            ch4_vol_m3 = convert(ch4_vol_scf, "scf", "m3")
            ch4_mass_kg = ch4_vol_m3 * CONVERSIONS["density_ch4"]
            ch4_tonnes = ch4_mass_kg / 1000.0

            co2_vol_scf = total_gas_scf * float(co2_content or 0.0)
            co2_vol_m3 = convert(co2_vol_scf, "scf", "m3")
            co2_mass_kg = co2_vol_m3 * CONVERSIONS["density_co2"]
            co2_tonnes = co2_mass_kg / 1000.0

            ctrl_eff = float(control_efficiency or 0.0)
            split = _split_vented_and_flared(
                total_gas_m3=total_gas_m3,
                ch4_tonnes=ch4_tonnes,
                co2_tonnes=co2_tonnes,
                ctrl_eff=ctrl_eff,
                hhv=hhv,
                ef_n2o=ef_n2o,
            )
            total_ch4 = split["total_ch4"]
            total_co2 = split["total_co2"]
            flared_n2o_tonnes = split["flared_n2o"]

            ch4_res, co2_res, n2o_res = _propagate_vented_results(
                total_ch4=total_ch4,
                total_co2=total_co2,
                flared_n2o=flared_n2o_tonnes,
                uncertainties=uncertainties,
                factor_source=uncertainties.get("_factor_source", "default"),
                process_category="tank_flashing",
            )
        else:
            ch4_kg = float(throughput) * float(ef_ch4 or 0.0)
            ch4_tonnes = ch4_kg / 1000.0
            total_ch4 = ch4_tonnes
            total_co2 = 0.0
            flared_n2o_tonnes = 0.0

            _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
            ch4_res = propagate_uncertainty(
                ch4_tonnes,
                resolve_ef_uncertainty("tank", "ch4", _tier, uncertainties.get("ch4")),
                tier=_tier,
                process_category="tank",
                gas="ch4",
            )
            co2_res = None
            n2o_res = None

        total_co2e = calculate_co2e(
            ch4=total_ch4, co2=total_co2, n2o=flared_n2o_tonnes, gwp_dict=gwp_dict
        )

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "throughput_bbl": throughput,
                "gor": gas_oil_ratio if is_flashing else None,
                "type": process_type,
                "ef_used": ef_ch4 if not is_flashing else "GOR Calc",
                "control_efficiency": control_efficiency,
            },
        )


class PneumaticDeviceCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Pneumatic Devices", "Section 6.10")

    def calculate(
        self,
        count,
        hours=8760,
        bleed_rate=None,
        ch4_content=0.85,
        uncertainties=None,
        actuations=None,
        gwp_dict=None,
    ):
        """
        API Section 6.10 & EPA Subpart W §98.233(a):
        - Continuous bleed: Device count * Hours * Bleed rate (scf/hr)
        - Intermittent / actuation-based: Device count * Actuations * Bleed per event (scf/actuation)
        """
        uncertainties = uncertainties or {}
        self.validate_inputs(
            {"count": count},
            ["count"],
        )

        is_intermittent = actuations is not None and float(actuations) > 0
        if is_intermittent:
            # Bleed rate is scf/event (default 13.5 scf/event per EPA Subpart W Table W-1 / API §6.10 if bleed_rate <= 0)
            event_bleed_scf = float(bleed_rate) if (bleed_rate and float(bleed_rate) > 0) else 13.5
            event_bleed_m3 = convert(event_bleed_scf, "scf", "m3")
            total_ch4_vol = (
                float(count) * float(actuations) * event_bleed_m3 * float(ch4_content)
            )
        else:
            self.validate_inputs(
                {"hours": hours, "bleed_rate": bleed_rate},
                ["hours", "bleed_rate"],
            )
            # Bleed rate in scf/hr -> m3/hr
            bleed_m3_hr = convert(float(bleed_rate), "scf", "m3")
            total_ch4_vol = (
                float(count) * float(hours) * bleed_m3_hr * float(ch4_content)
            )

        ch4_mass_kg = total_ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        ch4_res = propagate_uncertainty(
            ch4_tonnes,
            resolve_ef_uncertainty("pneumatic", "ch4", _tier, uncertainties.get("ch4")),
            tier=_tier,
            process_category="pneumatic",
            gas="ch4",
        )
        total_co2e = calculate_co2e(ch4=ch4_tonnes, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "device_count": count,
                "hours_operating": hours if not is_intermittent else None,
                "actuations": actuations if is_intermittent else None,
                "bleed_rate": bleed_rate,
                "mode": "intermittent_actuation" if is_intermittent else "continuous_bleed",
            },
        )
