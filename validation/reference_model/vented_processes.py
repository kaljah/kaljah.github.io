"""
Independent Vented & Episodic Process Models.
Source of Truth: API Compendium 2021 §6.2, §6.3, §6.4, §6.8, §6.10, Decision D-01.
Zero production dependencies.
"""
import math
from .unit_conversions import (
    IndependentUnitConverter,
    to_psia,
    to_kelvin,
    STD_T_K,
    STD_P_PSIA,
    DENSITY_CH4_STD,
    DENSITY_CO2_STD,
)
from .gwp import IndependentGWPModel


class IndependentVentedPartition:
    @staticmethod
    def partition(total_gas_m3, ch4_tonnes, co2_tonnes, control_efficiency, hhv=1020.0, ef_n2o=0.0001):
        """
        Partitions gross episodic vented gas into uncombusted vent and flared combustion stream.
        Decision D-01 / API Compendium 2021 §5.2.
        """
        ctrl = float(control_efficiency or 0.0)
        if ctrl > 1.0:
            ctrl /= 100.0
        ctrl = max(0.0, min(1.0, ctrl))
        vented_frac = 1.0 - ctrl

        vented_ch4 = ch4_tonnes * vented_frac
        vented_co2 = co2_tonnes * vented_frac

        flared_co2 = 0.0
        flared_unburnt_ch4 = 0.0
        flared_n2o = 0.0

        if ctrl > 0:
            flared_ch4_mass = ch4_tonnes * ctrl
            flared_native_co2 = co2_tonnes * ctrl

            # 98% stoichiometric conversion of CH4 to CO2: CH4 + 2 O2 -> CO2 + 2 H2O (44.01 / 16.04)
            flared_ch4_combusted = flared_ch4_mass * 0.98
            flared_co2 = (flared_ch4_combusted * (44.01 / 16.04)) + flared_native_co2
            flared_unburnt_ch4 = flared_ch4_mass * 0.02

            # Flared N2O from energy of flared gas
            flared_m3 = total_gas_m3 * ctrl
            flared_scf = flared_m3 / 0.028316846592
            flared_mmbtu = (flared_scf * float(hhv or 1020.0)) / 1_000_000.0
            flared_n2o = (flared_mmbtu * float(ef_n2o or 0.0001)) / 1000.0

        total_ch4 = vented_ch4 + flared_unburnt_ch4
        total_co2 = vented_co2 + flared_co2

        return {
            "total_ch4": total_ch4,
            "total_co2": total_co2,
            "flared_n2o": flared_n2o,
            "vented_ch4": vented_ch4,
            "vented_co2": vented_co2,
            "flared_co2": flared_co2,
            "flared_unburnt_ch4": flared_unburnt_ch4,
        }


class IndependentMudDegassing:
    @staticmethod
    def calculate(mud_volume, mud_unit="m3", mud_type="water_based", custom_ef=None, gwp_standard="AR5", gwp_horizon="100"):
        vol_m3 = IndependentUnitConverter.convert(mud_volume, mud_unit, "m3")
        factors = {"water_based": 0.15, "oil_based": 0.35, "synthetic": 0.25}
        ef = float(custom_ef if custom_ef is not None and float(custom_ef) > 0 else factors.get(mud_type, 0.25))
        ch4_t = (vol_m3 * ef) / 1000.0
        co2e = IndependentGWPModel.calculate_co2e(ch4=ch4_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"ch4": ch4_t, "co2": 0.0, "n2o": 0.0, "co2e": co2e, "mud_volume_m3": vol_m3, "ef_used": ef}


class IndependentCompletions:
    @staticmethod
    def calculate(
        method="metered_volume",
        flowback_volume=None,
        volume_unit="m3",
        flowback_rate=None,
        duration_hours=None,
        liquid_bbl=None,
        gor=None,
        ch4_content=0.85,
        co2_content=0.0,
        control_efficiency=0.0,
        hhv=1020.0,
        ef_n2o=0.0001,
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        m = str(method or "metered_volume").lower().strip()
        if m == "rate_duration" and flowback_rate and duration_hours:
            rate_scf_hr = (float(flowback_rate) * 1000.0) / 24.0
            scf = rate_scf_hr * float(duration_hours)
            total_gas_m3 = scf * 0.028316846592
        elif m == "gor_liquid" and liquid_bbl and gor:
            scf = float(liquid_bbl) * float(gor)
            total_gas_m3 = scf * 0.028316846592
        else:
            total_gas_m3 = IndependentUnitConverter.convert(flowback_volume, volume_unit, "m3")

        c1 = float(ch4_content or 0.85)
        if c1 > 1.0:
            c1 /= 100.0
        co2_frac = float(co2_content or 0.0)
        if co2_frac > 1.0:
            co2_frac /= 100.0

        gross_ch4_t = (total_gas_m3 * c1 * DENSITY_CH4_STD) / 1000.0
        gross_co2_t = (total_gas_m3 * co2_frac * DENSITY_CO2_STD) / 1000.0

        split = IndependentVentedPartition.partition(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=gross_ch4_t,
            co2_tonnes=gross_co2_t,
            control_efficiency=control_efficiency,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )
        co2e = IndependentGWPModel.calculate_co2e(
            co2=split["total_co2"], ch4=split["total_ch4"], n2o=split["flared_n2o"], standard=gwp_standard, horizon=gwp_horizon
        )
        return {
            "ch4": split["total_ch4"],
            "co2": split["total_co2"],
            "n2o": split["flared_n2o"],
            "co2e": co2e,
            "total_gas_m3": total_gas_m3,
        }


class IndependentLiquidsUnloading:
    @staticmethod
    def calculate(
        well_depth,
        diameter,
        pressure,
        events,
        depth_unit="ft",
        diameter_unit="in",
        press_unit="psig",
        temp=60.0,
        temp_unit="F",
        ch4_content=0.85,
        co2_content=0.0,
        control_efficiency=0.0,
        hhv=1020.0,
        ef_n2o=0.0001,
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        depth_m = IndependentUnitConverter.convert(well_depth, depth_unit, "m")
        diam_m = IndependentUnitConverter.convert(diameter, diameter_unit, "m")
        v_tubing = (math.pi / 4.0) * (diam_m**2) * depth_m

        p_abs = to_psia(pressure, press_unit)
        p_factor = p_abs / STD_P_PSIA

        t_abs = to_kelvin(temp, temp_unit)
        t_factor = STD_T_K / max(1.0, t_abs)

        v_std_per_event = v_tubing * p_factor * t_factor
        total_gas_m3 = v_std_per_event * float(events)

        c1 = float(ch4_content or 0.85)
        if c1 > 1.0:
            c1 /= 100.0
        co2_frac = float(co2_content or 0.0)
        if co2_frac > 1.0:
            co2_frac /= 100.0

        gross_ch4_t = (total_gas_m3 * c1 * DENSITY_CH4_STD) / 1000.0
        gross_co2_t = (total_gas_m3 * co2_frac * DENSITY_CO2_STD) / 1000.0

        split = IndependentVentedPartition.partition(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=gross_ch4_t,
            co2_tonnes=gross_co2_t,
            control_efficiency=control_efficiency,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )
        co2e = IndependentGWPModel.calculate_co2e(
            co2=split["total_co2"], ch4=split["total_ch4"], n2o=split["flared_n2o"], standard=gwp_standard, horizon=gwp_horizon
        )
        return {
            "ch4": split["total_ch4"],
            "co2": split["total_co2"],
            "n2o": split["flared_n2o"],
            "co2e": co2e,
            "total_gas_m3": total_gas_m3,
        }


class IndependentBlowdown:
    @staticmethod
    def calculate(
        blowdown_volume,
        pressure,
        events,
        volume_unit="m3",
        press_unit="psig",
        temp=60.0,
        temp_unit="F",
        z_factor=1.0,
        ch4_content=0.85,
        co2_content=0.0,
        control_efficiency=0.0,
        hhv=1020.0,
        ef_n2o=0.0001,
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        v_phys = IndependentUnitConverter.convert(blowdown_volume, volume_unit, "m3")
        p_abs = to_psia(pressure, press_unit)
        p_factor = p_abs / STD_P_PSIA

        t_abs = to_kelvin(temp, temp_unit)
        t_factor = STD_T_K / max(1.0, t_abs)

        z = float(z_factor) if z_factor and float(z_factor) > 0 else 1.0
        v_std_per_event = v_phys * p_factor * t_factor * (1.0 / z)
        total_gas_m3 = v_std_per_event * float(events)

        c1 = float(ch4_content or 0.85)
        if c1 > 1.0:
            c1 /= 100.0
        co2_frac = float(co2_content or 0.0)
        if co2_frac > 1.0:
            co2_frac /= 100.0

        gross_ch4_t = (total_gas_m3 * c1 * DENSITY_CH4_STD) / 1000.0
        gross_co2_t = (total_gas_m3 * co2_frac * DENSITY_CO2_STD) / 1000.0

        split = IndependentVentedPartition.partition(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=gross_ch4_t,
            co2_tonnes=gross_co2_t,
            control_efficiency=control_efficiency,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )
        co2e = IndependentGWPModel.calculate_co2e(
            co2=split["total_co2"], ch4=split["total_ch4"], n2o=split["flared_n2o"], standard=gwp_standard, horizon=gwp_horizon
        )
        return {
            "ch4": split["total_ch4"],
            "co2": split["total_co2"],
            "n2o": split["flared_n2o"],
            "co2e": co2e,
            "total_gas_m3": total_gas_m3,
        }


class IndependentStorageTanks:
    @staticmethod
    def calculate(
        throughput,
        throughput_unit="bbl",
        process_type="tank_flashing",
        gas_oil_ratio=None,
        ch4_content=0.85,
        co2_content=0.0,
        control_efficiency=0.0,
        ef_ch4=0.0,
        hhv=1020.0,
        ef_n2o=0.0001,
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        bbl = IndependentUnitConverter.convert(throughput, throughput_unit, "bbl")
        is_flashing = process_type in ["tank_flashing", "tank", "storage_tanks"]

        if is_flashing:
            scf = bbl * float(gas_oil_ratio or 0.0)
            total_gas_m3 = scf * 0.028316846592

            c1 = float(ch4_content or 0.85)
            if c1 > 1.0:
                c1 /= 100.0
            co2_frac = float(co2_content or 0.0)
            if co2_frac > 1.0:
                co2_frac /= 100.0

            gross_ch4_t = (total_gas_m3 * c1 * DENSITY_CH4_STD) / 1000.0
            gross_co2_t = (total_gas_m3 * co2_frac * DENSITY_CO2_STD) / 1000.0

            split = IndependentVentedPartition.partition(
                total_gas_m3=total_gas_m3,
                ch4_tonnes=gross_ch4_t,
                co2_tonnes=gross_co2_t,
                control_efficiency=control_efficiency,
                hhv=hhv,
                ef_n2o=ef_n2o,
            )
            ch4_t = split["total_ch4"]
            co2_t = split["total_co2"]
            n2o_t = split["flared_n2o"]
        else:
            ch4_t = (bbl * float(ef_ch4 or 0.0)) / 1000.0
            co2_t = 0.0
            n2o_t = 0.0
            total_gas_m3 = 0.0

        co2e = IndependentGWPModel.calculate_co2e(co2=co2_t, ch4=ch4_t, n2o=n2o_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"ch4": ch4_t, "co2": co2_t, "n2o": n2o_t, "co2e": co2e, "total_gas_m3": total_gas_m3}


class IndependentPneumatics:
    @staticmethod
    def calculate(
        count,
        hours=8760,
        bleed_rate=None,
        bleed_unit="scf",
        actuations=None,
        ch4_content=0.85,
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        cnt = float(count or 0.0)
        c1 = float(ch4_content or 0.85)
        if c1 > 1.0:
            c1 /= 100.0

        is_intermittent = actuations is not None and float(actuations) > 0
        if is_intermittent:
            rate_scf = float(bleed_rate) if (bleed_rate and float(bleed_rate) > 0) else 13.5
            rate_m3 = rate_scf * 0.028316846592
            total_ch4_m3 = cnt * float(actuations) * rate_m3 * c1
        else:
            rate = float(bleed_rate or 0.0)
            rate_scf_hr = rate * 35.314666721 if str(bleed_unit).lower() == "m3" else rate
            rate_m3_hr = rate_scf_hr * 0.028316846592
            total_ch4_m3 = cnt * float(hours or 8760.0) * rate_m3_hr * c1

        ch4_t = (total_ch4_m3 * DENSITY_CH4_STD) / 1000.0
        co2e = IndependentGWPModel.calculate_co2e(ch4=ch4_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"ch4": ch4_t, "co2": 0.0, "n2o": 0.0, "co2e": co2e, "ch4_vol_m3": total_ch4_m3}
