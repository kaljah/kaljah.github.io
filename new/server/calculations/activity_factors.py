"""API Compendium 2021 activity-based emission factors (onshore upstream + midstream).

Each row: activity count (or throughput) x factor, scaled to the site gas composition.
Values were read from the Compendium tables named in `table` (scratch/2021-API-GHG-Compendium.pdf).

  per:  "unit"      per unit (event, workover, test, unit-year, mile-year)
        "unit_day"  per unit-day   (x days, default 365)
        "unit_hr"   per unit-hour  (x hours, default 8,760)
        "mmscf"     per 10^6 scf of gas processed / treated
        "mm_m3"     per 10^6 m3 of gas processed
        "mgal"      per 10^6 gal of liquid loaded
        "bbl"       per bbl of oil produced
  ch4:   tonnes CH4 per `per` at the factor's CH4 basis (derived from gas_scf x basis when absent)
  gas:   whole-gas scf per `per` (used for CO2 = gas x site CO2 fraction)
  basis: CH4 mole fraction of the factor (site CH4 content scales the CH4 factor)
  toc:   factor is total organic compound mass; CH4 = TOC x CH4 weight fraction (default 15 %)
"""
import math
from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier

SCF_TO_M3 = 0.028316846592
RHO_CH4 = CONVERSIONS["density_ch4"]  # kg/m3 (engine convention)
RHO_CO2 = CONVERSIONS["density_co2"]


def _r(label, processes, per, table, ch4=None, gas=None, basis=None, activity="unit", toc=False):
    return {"label": label, "processes": processes, "per": per, "table": table, "ch4": ch4,
            "gas_scf": gas, "basis": basis, "activity": activity, "toc": toc}


ACTIVITY_FACTORS = {
    # ---- 6.2.2 well testing (Table 6-4) ----
    "wt_gas": _r("Gas well test, vented", ["well_testing"], "unit", "Table 6-4", ch4=0.728, gas=46625, basis=0.816, activity="test"),
    "wt_oil": _r("Oil well test, vented", ["well_testing"], "unit", "Table 6-4", ch4=0.057, gas=3613, basis=0.816, activity="test"),
    # ---- 6.3.2 workovers without hydraulic fracturing (Table 6-9) ----
    "wo_gas": _r("Gas well workover (no HF)", ["workovers"], "unit", "Table 6-9", ch4=0.0470, gas=3114, basis=0.788, activity="workover"),
    "wo_oil": _r("Oil well workover (no HF)", ["workovers"], "unit", "Table 6-9", ch4=0.0018, gas=122, basis=0.788, activity="workover"),
    # ---- 6.3.5 casing gas (Table 6-12; low-pressure migration, CAPP) ----
    "cg_primary_heavy": _r("Primary heavy oil casing gas", ["casing_gas"], "bbl", "Table 6-12", ch4=3.28e-3, gas=210, basis=0.816, activity="bbl oil"),
    "cg_thermal_heavy": _r("Thermal heavy oil casing gas", ["casing_gas"], "bbl", "Table 6-12", ch4=0.223e-3, gas=14.2, basis=0.816, activity="bbl oil"),
    "cg_bitumen": _r("Crude bitumen casing gas", ["casing_gas"], "bbl", "Table 6-12", ch4=0.207e-3, gas=12.9, basis=0.816, activity="bbl oil"),
    "cg_migration": _r("Low-pressure well casing gas migration", ["casing_gas"], "unit_day", "Section 6.3.5.2 (CAPP)", ch4=0.00213, gas=3.85 / SCF_TO_M3, basis=0.816, activity="well"),
    # ---- 6.3.8 / 6.5.2 dehydration (Tables 6-17, 6-18, 6-35, 6-36) ----
    "dh_glycol_production": _r("Glycol dehydrator vent, production (no gas pump)", ["dehydrator"], "mmscf", "Table 6-17", ch4=0.0052859, gas=349.7, basis=0.788),
    "dh_kimray_production": _r("Kimray / gas-assisted glycol pump, production", ["dehydrator"], "mmscf", "Table 6-18", ch4=0.01903, gas=1258, basis=0.788),
    "dh_glycol_processing": _r("Glycol dehydrator vent, processing", ["dehydrator"], "mmscf", "Table 6-35", ch4=0.0023315, gas=140.03, basis=0.868),
    "dh_kimray_processing": _r("Kimray / gas-assisted glycol pump, processing", ["dehydrator"], "mmscf", "Table 6-36", ch4=0.0034096, gas=205, basis=0.868),
    # ---- 6.3.8.4 acid gas removal (Table 6-19) ----
    "agr_throughput": _r("AGR vent, per treated gas", ["agr"], "mmscf", "Table 6-19", ch4=0.0185),
    "agr_unit": _r("AGR vent, per AGR unit", ["agr"], "unit_day", "Table 6-19", ch4=0.6482, activity="AGR unit"),
    # ---- 6.4.1 gathering & boosting pneumatic controllers (Table 6-29, scf whole gas / h) ----
    "gb_pc_high_bleed": _r("G&B high-bleed controller", ["pneumatic"], "unit_hr", "Table 6-29", gas=19.25, basis=0.816, activity="controller"),
    "gb_pc_low_bleed_normal": _r("G&B low-bleed, normal operation", ["pneumatic"], "unit_hr", "Table 6-29", gas=0.68, basis=0.816, activity="controller"),
    "gb_pc_low_bleed_malf": _r("G&B low-bleed, malfunctioning", ["pneumatic"], "unit_hr", "Table 6-29", gas=34, basis=0.816, activity="controller"),
    "gb_pc_low_bleed_avg": _r("G&B low-bleed, average", ["pneumatic"], "unit_hr", "Table 6-29", gas=6.42, basis=0.816, activity="controller"),
    "gb_pc_int_normal": _r("G&B intermittent, normal operation", ["pneumatic"], "unit_hr", "Table 6-29", gas=2.82, basis=0.816, activity="controller"),
    "gb_pc_int_malf": _r("G&B intermittent, malfunctioning", ["pneumatic"], "unit_hr", "Table 6-29", gas=16.11, basis=0.816, activity="controller"),
    "gb_pc_int_avg": _r("G&B intermittent, average", ["pneumatic"], "unit_hr", "Table 6-29", gas=11.13, basis=0.816, activity="controller"),
    "gb_pc_avg_normal": _r("G&B controller, type unknown, normal operation", ["pneumatic"], "unit_hr", "Table 6-29", gas=4.98, basis=0.816, activity="controller"),
    "gb_pc_avg_malf": _r("G&B controller, type unknown, malfunctioning", ["pneumatic"], "unit_hr", "Table 6-29", gas=19.09, basis=0.816, activity="controller"),
    "gb_pc_avg": _r("G&B controller, type and condition unknown", ["pneumatic"], "unit_hr", "Table 6-29", ch4=7.45 * SCF_TO_M3 * RHO_CH4 / 1000.0, gas=9.13, basis=0.816, activity="controller"),
    # ---- 6.3.6 production pneumatic controllers (Table 6-14 continuous, Table 6-15 intermittent;
    #      scf whole gas / controller-hr at 81.6 mol % CH4) ----
    "prod_pc_high_bleed_api": _r("Production high-bleed controller (API study)", ["pneumatic"], "unit_hr", "Table 6-14", gas=16.4, basis=0.816, activity="controller"),
    "prod_pc_low_bleed_api": _r("Production low-bleed controller (API study)", ["pneumatic"], "unit_hr", "Table 6-14", gas=2.6, basis=0.816, activity="controller"),
    "prod_pc_high_bleed_ghgrp": _r("Production high-bleed controller (EPA GHGRP)", ["pneumatic"], "unit_hr", "Table 6-14", gas=37.3, basis=0.816, activity="controller"),
    "prod_pc_low_bleed_ghgrp": _r("Production low-bleed controller (EPA GHGRP)", ["pneumatic"], "unit_hr", "Table 6-14", gas=1.39, basis=0.816, activity="controller"),
    "prod_pc_int_avg_api": _r("Production intermittent controller, average (API study)", ["pneumatic"], "unit_hr", "Table 6-15", gas=9.3, basis=0.816, activity="controller"),
    "prod_pc_int_normal_api": _r("Production intermittent controller, normal operation (API study)", ["pneumatic"], "unit_hr", "Table 6-15", gas=0.28, basis=0.816, activity="controller"),
    "prod_pc_int_malf_api": _r("Production intermittent controller, malfunctioning (API study)", ["pneumatic"], "unit_hr", "Table 6-15", gas=24.1, basis=0.816, activity="controller"),
    "prod_pc_int_ghgrp": _r("Production intermittent controller (EPA GHGRP)", ["pneumatic"], "unit_hr", "Table 6-15", gas=13.5, basis=0.816, activity="controller"),
    # ---- 6.3.7 gas-driven chemical injection pumps (Table 6-16, scf whole gas / pump-hr) ----
    "cip_piston_gri": _r("Chemical injection pump, piston (GRI/EPA)", ["pneumatic"], "unit_hr", "Table 6-16", gas=2.59, basis=0.788, activity="pump"),
    "cip_piston_api": _r("Chemical injection pump, piston (API study)", ["pneumatic"], "unit_hr", "Table 6-16", gas=2.03, basis=0.816, activity="pump"),
    "cip_piston_ghgrp": _r("Chemical injection pump, piston (EPA GHGRP)", ["pneumatic"], "unit_hr", "Table 6-16", gas=20.9, basis=0.816, activity="pump"),
    "cip_diaphragm_gri": _r("Chemical injection pump, diaphragm (GRI/EPA)", ["pneumatic"], "unit_hr", "Table 6-16", gas=23.6, basis=0.788, activity="pump"),
    "cip_diaphragm_api": _r("Chemical injection pump, diaphragm (API study)", ["pneumatic"], "unit_hr", "Table 6-16", gas=18.6, basis=0.816, activity="pump"),
    "cip_diaphragm_ghgrp": _r("Chemical injection pump, diaphragm (EPA GHGRP)", ["pneumatic"], "unit_hr", "Table 6-16", gas=37.3, basis=0.816, activity="pump"),
    "cip_avg_gri": _r("Chemical injection pump, type unknown (GRI/EPA)", ["pneumatic"], "unit_hr", "Table 6-16", gas=13.1, basis=0.788, activity="pump"),
    "cip_avg_api": _r("Chemical injection pump, type unknown (API study)", ["pneumatic"], "unit_hr", "Table 6-16", gas=14.1, basis=0.816, activity="pump"),
    "cip_avg_ghgrp": _r("Chemical injection pump, type unknown (EPA GHGRP)", ["pneumatic"], "unit_hr", "Table 6-16", gas=34.4, basis=0.816, activity="pump"),
    # ---- 6.5.1 gas processing pneumatic controllers (Table 6-34, tonnes CH4 / controller-yr) ----
    "proc_pc_continuous": _r("Processing continuous-bleed controller", ["pneumatic"], "unit_hr", "Table 6-34", ch4=8.304 / 8760, gas=56.8, basis=0.868, activity="controller"),
    "proc_pc_piston_operator": _r("Processing piston valve operator", ["pneumatic"], "unit_hr", "Table 6-34", ch4=8.010e-4 / 8760, gas=5.48e-3, basis=0.868, activity="controller"),
    "proc_pc_hydraulic_operator": _r("Processing pneumatic / hydraulic valve operator", ["pneumatic"], "unit_hr", "Table 6-34", ch4=0.0939 / 8760, gas=0.642, basis=0.868, activity="controller"),
    "proc_pc_turbine_operator": _r("Processing turbine valve operator", ["pneumatic"], "unit_hr", "Table 6-34", ch4=1.128 / 8760, gas=7.72, basis=0.868, activity="controller"),
    # ---- 6.6.3 transmission & storage pneumatic controllers (Table 6-42, tonnes CH4 / controller-yr) ----
    "ts_pc_continuous": _r("Transmission / storage continuous-vent controller", ["pneumatic"], "unit_hr", "Table 6-42", ch4=3.5 / 8760, gas=22.3, basis=0.934, activity="controller"),
    "ts_pc_intermittent": _r("Transmission / storage intermittent-vent controller", ["pneumatic"], "unit_hr", "Table 6-42", ch4=0.4 / 8760, gas=2.5, basis=0.934, activity="controller"),
    "ts_pc_avg": _r("Transmission / storage controller, type unknown", ["pneumatic"], "unit_hr", "Table 6-42", ch4=3.0 / 8760, gas=19.3, basis=0.934, activity="controller"),
    # ---- 6.3.9 separator dump valves and produced water (Tables 6-25, 6-26, 6-27), per bbl ----
    "sep_dump_valve_crude": _r("Malfunctioning separator dump valve, crude service", ["separation"], "bbl", "Table 6-25", ch4=2.70e-6, basis=0.816, activity="bbl oil"),
    "sep_dump_valve_condensate": _r("Malfunctioning separator dump valve, condensate service", ["separation"], "bbl", "Table 6-25", ch4=2.64e-6, basis=0.816, activity="bbl condensate"),
    "pw_50psi_20salt": _r("Produced water tank flashing, 50 psi separator, 20 % salt", ["separation"], "bbl", "Table 6-26", ch4=0.0015e-3, activity="bbl water"),
    "pw_250psi_20salt": _r("Produced water tank flashing, 250 psi separator, 20 % salt", ["separation"], "bbl", "Table 6-26", ch4=0.00986e-3, activity="bbl water"),
    "pw_250psi_10salt": _r("Produced water tank flashing, 250 psi separator, 10 % salt", ["separation"], "bbl", "Table 6-26", ch4=0.0150e-3, activity="bbl water"),
    "pw_250psi_2salt": _r("Produced water tank flashing, 250 psi separator, 2 % salt", ["separation"], "bbl", "Table 6-26", ch4=0.0177e-3, activity="bbl water"),
    "pw_250psi_avg": _r("Produced water tank flashing, 250 psi separator, salt unknown", ["separation"], "bbl", "Table 6-26", ch4=0.0142e-3, activity="bbl water"),
    "pw_1000psi_20salt": _r("Produced water tank flashing, 1,000 psi separator, 20 % salt", ["separation"], "bbl", "Table 6-26", ch4=0.0354e-3, activity="bbl water"),
    "pw_1000psi_10salt": _r("Produced water tank flashing, 1,000 psi separator, 10 % salt", ["separation"], "bbl", "Table 6-26", ch4=0.0536e-3, activity="bbl water"),
    "pw_1000psi_2salt": _r("Produced water tank flashing, 1,000 psi separator, 2 % salt", ["separation"], "bbl", "Table 6-26", ch4=0.0634e-3, activity="bbl water"),
    "pw_1000psi_avg": _r("Produced water tank flashing, 1,000 psi separator, salt unknown", ["separation"], "bbl", "Table 6-26", ch4=0.0508e-3, activity="bbl water"),
    "pw_shallow_gas_well": _r("Produced water, shallow gas well (76 psi or less)", ["separation"], "bbl", "Table 6-27", ch4=0.0057e-3, activity="bbl water"),
    # ---- compressor venting (Tables 6-30, 6-37, 6-38, 6-40, 6-41) ----
    "gb_cent_wet": _r("Centrifugal wet seal degassing, G&B / production (GHGRP)", ["compressor_venting"], "unit_hr", "Section 6.4.3", ch4=0.026, gas=1738, basis=0.788, activity="compressor"),
    "gb_rp_us": _r("Reciprocating rod packing, G&B / production (US)", ["compressor_venting"], "unit_hr", "Table 6-30", ch4=4.43e-4, gas=28.4, basis=0.816, activity="compressor"),
    "gb_rp_ghgrp": _r("Reciprocating rod packing, G&B / production (GHGRP)", ["compressor_venting"], "unit_hr", "Table 6-30", ch4=2.07e-5, gas=1.37, basis=0.788, activity="compressor"),
    "gb_rp_alberta": _r("Reciprocating rod packing, G&B / production (Alberta)", ["compressor_venting"], "unit_hr", "Table 6-30", ch4=1.39e-4, gas=10.2, basis=0.816, activity="compressor"),
    "proc_recip": _r("Reciprocating compressor, processing (all modes)", ["compressor_venting"], "unit", "Table 6-37", ch4=16.3, gas=9.81e5, basis=0.868, activity="compressor-year"),
    "proc_rod_packing": _r("Reciprocating rod packing, processing", ["compressor_venting"], "unit_hr", "Table 6-37", ch4=0.0027, gas=163.8, basis=0.87, activity="compressor"),
    "proc_cent_wet": _r("Centrifugal wet seal, processing", ["compressor_venting"], "unit", "Table 6-38", ch4=86.43, gas=593 * 8760, basis=0.868, activity="compressor-year"),
    "proc_cent_dry": _r("Centrifugal dry seal, processing", ["compressor_venting"], "unit", "Table 6-38", ch4=28.19, gas=194 * 8760, basis=0.868, activity="compressor-year"),
    "ts_rp_operating": _r("Reciprocating rod packing, transmission & storage, operating", ["compressor_venting"], "unit_hr", "Table 6-40", ch4=4.72e-3, gas=263, basis=0.934, activity="compressor"),
    "ts_rp_standby": _r("Reciprocating rod packing, transmission & storage, standby pressurized", ["compressor_venting"], "unit_hr", "Table 6-40", ch4=6.91e-3, gas=385, basis=0.934, activity="compressor"),
    "trans_rp_operating": _r("Reciprocating rod packing, transmission, operating", ["compressor_venting"], "unit_hr", "Table 6-40", ch4=1.96e-3, gas=110, basis=0.934, activity="compressor"),
    "stor_rp_operating": _r("Reciprocating rod packing, storage, operating", ["compressor_venting"], "unit_hr", "Table 6-40", ch4=2.41e-3, gas=134, basis=0.934, activity="compressor"),
    "ts_cent_wet_operating": _r("Centrifugal wet seal, operating", ["compressor_venting"], "unit_hr", "Table 6-41", ch4=3.04e-2, gas=1696, basis=0.934, activity="compressor"),
    "ts_cent_wet_degassing": _r("Centrifugal wet seal degassing vent, operating", ["compressor_venting"], "unit_hr", "Table 6-41", ch4=2.87e-3, gas=160, basis=0.934, activity="compressor"),
    "ts_cent_wet_avg": _r("Centrifugal wet seal, average", ["compressor_venting"], "unit_hr", "Table 6-41", ch4=1.84e-2, gas=1028, basis=0.934, activity="compressor"),
    "ts_cent_dry_avg": _r("Centrifugal dry seal, average", ["compressor_venting"], "unit_hr", "Table 6-41", ch4=5.75e-3, gas=321, basis=0.934, activity="compressor"),
    # ---- non-routine venting (Tables 6-32, 6-33, 6-39, 6-43, 6-46), per unit-year ----
    "gb_bd_vessel": _r("Vessel blowdowns (G&B)", ["non_routine_venting"], "unit", "Table 6-32", ch4=0.0015, gas=99, basis=0.788, activity="vessel-year"),
    "gb_bd_compressor": _r("Compressor blowdowns (G&B)", ["non_routine_venting"], "unit", "Table 6-32", ch4=0.07239, gas=4789, basis=0.788, activity="compressor-year"),
    "gb_bd_pipeline": _r("Gathering pipeline blowdowns", ["non_routine_venting"], "unit", "Table 6-32", ch4=0.00593, gas=392, basis=0.788, activity="mile-year"),
    "gb_prv": _r("Pressure relief valve releases (G&B)", ["non_routine_venting"], "unit", "Table 6-33", ch4=0.00065, gas=43, basis=0.788, activity="PRV-year"),
    "gb_digins": _r("Gathering pipeline mishaps (dig-ins)", ["non_routine_venting"], "unit", "Table 6-33", ch4=0.0128, gas=849, basis=0.788, activity="mile-year"),
    "gb_compressor_starts": _r("Compressor starts (G&B)", ["non_routine_venting"], "unit", "Table 6-33", ch4=0.16, gas=10714, basis=0.788, activity="compressor-year"),
    "gb_oil_pump_station": _r("Oil pump station maintenance", ["non_routine_venting"], "unit", "Table 6-33", ch4=0.00071, gas=46.9, basis=0.788, activity="station-year"),
    "proc_non_routine": _r("Gas processing non-routine emissions", ["non_routine_venting"], "mmscf", "Table 6-39", ch4=3.524e-3, gas=212, basis=0.868),
    "proc_non_routine_m3": _r("Gas processing non-routine emissions (per 10^6 m3)", ["non_routine_venting"], "mm_m3", "Table 6-39", ch4=0.1244, gas=212 / SCF_TO_M3, basis=0.868),  # 212 Sm3 gas / 10^6 Sm3
    "proc_blowdown_plant": _r("Gas processing blowdown venting", ["non_routine_venting"], "unit", "Table 6-39", ch4=54.4, gas=3.27e6, basis=0.868, activity="plant-year"),
    "ts_station_bd": _r("Transmission station blowdowns", ["non_routine_venting"], "unit", "Table 6-43", ch4=54, gas=3014e3, basis=0.934, activity="station-year"),
    "stor_station_bd": _r("Storage station blowdowns", ["non_routine_venting"], "unit", "Table 6-43", ch4=43, gas=2400e3, basis=0.934, activity="station-year"),
    "ts_pipeline_venting": _r("Transmission pipeline venting", ["non_routine_venting"], "unit", "Table 6-43", ch4=0.6135, gas=34.2e3, basis=0.934, activity="mile-year"),
    "ts_compressor_bd": _r("Transmission compressor blowdowns", ["non_routine_venting"], "unit", "Table 6-43", ch4=47.14, gas=2631e3, basis=0.934, activity="station-year"),
    "ts_engine_starts": _r("Transmission engine starts", ["non_routine_venting"], "unit", "Table 6-43", ch4=29.06, gas=1622e3, basis=0.934, activity="station-year"),
    "ts_prv_lifts": _r("Transmission PRV lifts", ["non_routine_venting"], "unit", "Table 6-43", ch4=3.68, gas=206e3, basis=0.934, activity="station-year"),
    "ts_esd": _r("Transmission ESD activation", ["non_routine_venting"], "unit", "Table 6-43", ch4=7.97, gas=444e3, basis=0.934, activity="station-year"),
    "ts_mr_bd": _r("Transmission M&R station blowdowns", ["non_routine_venting"], "unit", "Table 6-43", ch4=13.75, gas=756e3, basis=0.934, activity="station-year"),
    "dist_mr": _r("Distribution M&R station maintenance / upsets", ["non_routine_venting"], "unit", "Table 6-46", ch4=0.002895, gas=159, basis=0.948, activity="station-year"),
    "dist_odorizer": _r("Distribution odorizer and gas sampling vents", ["non_routine_venting"], "unit", "Table 6-46", ch4=0.02275, gas=1251, basis=0.948, activity="station-year"),
    "dist_pipeline_bd": _r("Distribution pipeline blowdowns", ["non_routine_venting"], "unit", "Table 6-46", ch4=0.03220, gas=1798, basis=0.934, activity="mile-year"),
    "dist_digins": _r("Distribution pipeline mishaps (dig-ins)", ["non_routine_venting"], "unit", "Table 6-46", ch4=0.03040, gas=1697, basis=0.934, activity="mile-year"),
    "dist_prv": _r("Distribution pressure relief valves", ["non_routine_venting"], "unit", "Table 6-46", ch4=9.591e-4, gas=54, basis=0.934, activity="mile-year"),
    # ---- 6.10.1 crude loading losses (Table 6-47, tonne TOC / 10^6 gal) ----
    "load_submerged_dedicated": _r("Rail/truck submerged loading, dedicated service", ["loading"], "mgal", "Table 6-47", ch4=0.91, toc=True),
    "load_submerged_vapor_balance": _r("Rail/truck submerged loading, vapor balance", ["loading"], "mgal", "Table 6-47", ch4=1.51, toc=True),
    "load_splash_dedicated": _r("Rail/truck splash loading, dedicated service", ["loading"], "mgal", "Table 6-47", ch4=2.20, toc=True),
    "load_splash_vapor_balance": _r("Rail/truck splash loading, vapor balance", ["loading"], "mgal", "Table 6-47", ch4=1.51, toc=True),
    "load_marine_ship": _r("Marine loading, ships / ocean barges", ["loading"], "mgal", "Table 6-47", ch4=0.28, toc=True),
    "load_marine_barge": _r("Marine loading, barges", ["loading"], "mgal", "Table 6-47", ch4=0.45, toc=True),
}

GAS_SCALE = {"scf": 1.0, "mcf": 1e3, "mscf": 1e3, "mmscf": 1e6, "m3": 1 / SCF_TO_M3, "sm3": 1 / SCF_TO_M3}
LIQ_TO_GAL = {"gal": 1.0, "bbl": 42.0, "m3": 264.172052, "l": 0.264172052}
LIQ_TO_BBL = {"bbl": 1.0, "gal": 1 / 42.0, "m3": 6.28981077, "l": 6.28981077e-3}


def activity_factor_list(process=None):
    return [{"key": k, **{kk: vv for kk, vv in v.items()}} for k, v in ACTIVITY_FACTORS.items()
            if process is None or process in v["processes"]]


def _frac(v):
    """Normalize gas composition input whether provided as decimal fraction (0-1.0) or percentage (0-100%)."""
    if v in (None, ""):
        return None
    s = str(v).replace("%", "").strip()
    try:
        x = float(s)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid gas content: {v}")
    if not math.isfinite(x) or x < 0:
        raise ValueError("Gas content must be a non-negative number")
    if x > 100.0:
        raise ValueError("Gas content cannot exceed 100 %")
    if "%" in str(v) or x > 1.0:
        return x / 100.0
    return x


class ActivityFactorCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("API Compendium activity factor", "Section 6")

    def calculate(self, key, amount, unit=None, days=None, hours=None, ch4_content=None, co2_content=None,
                  toc_ch4_wt=None, uncertainties=None, gwp_dict=None, year_fraction=1.0):
        row = ACTIVITY_FACTORS.get(key)
        if row is None:
            raise ValueError(f"Unknown activity factor '{key}'")
        amount = float(amount)
        if amount < 0:
            raise ValueError("Activity amount cannot be negative")
        per = row["per"]
        u = str(unit or "").strip().lower().replace("³", "3")
        if per == "unit":
            n = amount
            if "-year" in str(row.get("activity") or ""):
                # factors per unit-year (compressor-, station-, mile-year): the record's share of a year
                yf = float(year_fraction if year_fraction not in (None, "") else 1.0)
                if not 0 < yf <= 1:
                    raise ValueError("The period must be a fraction of a year between 0 and 1")
                n = amount * yf
        elif per == "unit_day":
            n = amount * float(days if days not in (None, "") else 365)
        elif per == "unit_hr":
            n = amount * float(hours if hours not in (None, "") else 8760)
        elif per == "mmscf":
            if u not in GAS_SCALE:
                raise ValueError("Gas throughput unit must be scf, Mcf, MMscf or m3")
            n = amount * GAS_SCALE[u] / 1e6
        elif per == "mm_m3":
            if u not in GAS_SCALE:
                raise ValueError("Gas throughput unit must be scf, Mcf, MMscf or m3")
            n = amount * GAS_SCALE[u] * SCF_TO_M3 / 1e6
        elif per == "mgal":
            if u not in LIQ_TO_GAL:
                raise ValueError("Liquid volume unit must be gal, bbl, L or m3")
            n = amount * LIQ_TO_GAL[u] / 1e6
        elif per == "bbl":
            if u not in LIQ_TO_BBL:
                raise ValueError("Oil volume unit must be bbl, gal, L or m3")
            n = amount * LIQ_TO_BBL[u]
        else:
            raise ValueError(f"Unsupported factor basis '{per}'")

        basis = row["basis"]
        x_ch4 = _frac(ch4_content)
        if x_ch4 is not None and ch4_content not in (None, "") and float(ch4_content) <= 1.0:
            # a CH4 content of 0.85 is the fraction 85 %, not 0.85 % (it made CH4 100x low); vented
            # gas under 1 % CH4 does not occur for these factors
            x_ch4 = float(ch4_content)
        x_co2 = _frac(co2_content) or 0.0
        if x_co2 > 0 and co2_content not in (None, ""):
            # Consistent basis: if CH4 is entered as a fraction (<= 1.0) and CO2 <= 1.0, retain as fraction
            if float(ch4_content or 0) <= 1.0 and float(co2_content) <= 1.0:
                x_co2 = float(co2_content)

        gas = row["gas_scf"]
        if row["toc"]:
            w = _frac(toc_ch4_wt)
            ch4 = n * row["ch4"] * (w if w is not None else 0.15)
            co2 = 0.0
        else:
            ch4_f = row["ch4"]
            if ch4_f is None:
                ch4_f = gas * basis * SCF_TO_M3 * RHO_CH4 / 1000.0
            scale = (x_ch4 / basis) if (x_ch4 is not None and basis) else 1.0
            ch4 = n * ch4_f * scale
            if x_co2 > 0:
                if gas:
                    co2 = n * gas * x_co2 * SCF_TO_M3 * RHO_CO2 / 1000.0
                else:
                    x_used = x_ch4 if x_ch4 else (basis or None)
                    if not x_used or x_used <= 0:
                        raise ValueError("CO2 needs a positive site CH4 content for this factor")
                    co2 = ch4 * (x_co2 / x_used) * (44.01 / 16.04)
            else:
                co2 = 0.0

        _tier = resolve_tier((uncertainties or {}).get("_factor_source", "default"))
        ch4_res = propagate_uncertainty(ch4, 0.30, tier=_tier, gas="ch4")
        co2_res = propagate_uncertainty(co2, 0.30 if co2 else 0.0, tier=_tier, gas="co2")
        total = calculate_co2e(co2=co2, ch4=ch4, gwp_dict=gwp_dict)
        return {
            "results": {"ch4": ch4_res, "co2": co2_res, "n2o": 0.0},
            "total_co2e": total,
            "intermediate": {"api_table": row["table"], "factor": row["label"], "activity_basis": per,
                             "normalized_activity": n, "ch4_scale": (x_ch4 / basis) if (x_ch4 and basis) else 1.0},
        }
