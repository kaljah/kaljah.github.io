"""Well-site venting calculators (workover, casing gas, CO2-EOR, non-routine).

Split out of calculations/vented_production.py unchanged (hardening plan, task 5.5).
calculations.vented_production re-exports every class, so existing imports keep working.
"""
from .base import BaseCalculator
from .units import calculate_co2e, convert
from calculations.vented_production import LB_PER_TONNE, MOLAR_VOL_US, MW_CH4, MW_CO2, _propagate_results, _split_vent_flare


class WorkoverWithoutFracturingCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.2 - Workovers without Hydraulic Fracturing
    Table 6-9:
      - Gas well workovers: 2,454 scf CH4/workover (3,114 scf gas/workover, 0.0470 tonnes CH4/workover at 78.8 mol% CH4)
      - Oil well workovers: 96 scf CH4/workover (122 scf gas/workover, 0.0018 tonnes CH4/workover at 78.8 mol% CH4)
    Verified against Exhibit 6-7.
    """

    FACTORS = {
        "gas_well": {
            "scf_gas_per_event": 3114.0,
            "default_ch4_scf": 2454.0,
            "ef_ch4_tonnes": 0.0470,
            "baseline_ch4_mol": 0.788,
            "uncertainty": {"ch4": 9.24, "co2": 9.24},  # 924% uncertainty from Table 6-9
        },
        "oil_well": {
            "scf_gas_per_event": 122.0,
            "default_ch4_scf": 96.0,
            "ef_ch4_tonnes": 0.0018,
            "baseline_ch4_mol": 0.788,
            "uncertainty": {"ch4": 0.50, "co2": 0.50},
        },
    }

    def __init__(self):
        super().__init__("Well Workovers without Hydraulic Fracturing", "Section 6.3.2")

    def calculate(
        self,
        workovers=1.0,
        well_type="gas_well",  # "gas_well" or "oil_well"
        ch4_content=None,      # mole fraction or % (default 78.8%)
        co2_content=None,      # mole fraction or %
        control_efficiency=0.0,
        disposition="vented",  # "vented", "flared", "recovered"
        hhv=1020.0,
        ef_n2o=None,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        self.validate_inputs({"workovers": workovers}, ["workovers"])

        wtype = str(well_type or "gas_well").lower().strip()
        factor_info = self.FACTORS.get(wtype, self.FACTORS["gas_well"])

        events = max(0.0, float(workovers))
        scf_per_event = factor_info["scf_gas_per_event"]
        total_scf = events * scf_per_event
        total_m3 = convert(total_scf, "scf", "m3")

        # Composition resolution
        c_ch4 = factor_info["baseline_ch4_mol"] if ch4_content is None else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0
        c_ch4 = max(0.0, min(1.0, c_ch4))

        c_co2 = 0.0 if co2_content is None else float(co2_content)
        if c_co2 > 1.0:
            c_co2 /= 100.0
        c_co2 = max(0.0, min(1.0, c_co2))

        # Mass via ideal gas law at standard conditions
        # tonnes = scf * mol_frac * (MW / 379.3) / 2204.6226
        gross_ch4_tonnes = total_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
        gross_co2_tonnes = total_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        # Disposition routing
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
            total_gas_m3=total_m3,
            ch4_tonnes=gross_ch4_tonnes,
            co2_tonnes=gross_co2_tonnes,
            ctrl_eff=eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )

        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]
        flared_n2o = split["flared_n2o"]

        unc = uncertainties.copy()
        if "ch4" not in unc and "ch4" in factor_info["uncertainty"]:
            unc["ch4"] = factor_info["uncertainty"]["ch4"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=flared_n2o,
            uncertainties=unc,
            factor_source="API_Table_6_9",
            category="workover_no_hf",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "workovers": events,
                "well_type": wtype,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "total_gas_scf": total_scf,
                "total_gas_m3": total_m3,
                "disposition": disp,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.2, Table 6-9",
                "table": "Table 6-9",
            },
        )


class CasingGasVentCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.5 - Casing Gas Vents
    Covers:
      - Heavy Oil and Bitumen Throughput Basis (Table 6-12)
          * Primary Heavy Oil: 210 scf gas/bbl (37.4 m3 THC/m3, 3.28 t CH4/1000 bbl, 63.2% vented default)
          * Thermal Heavy Oil: 14.2 scf gas/bbl (2.53 m3 THC/m3, 0.223 t CH4/1000 bbl, 4.7% vented default)
          * Crude Bitumen: 12.9 scf gas/bbl (2.3 m3 THC/m3, 0.207 t CH4/1000 bbl, 18.0% vented default)
      - Heavy Oil and Bitumen Well Basis (Table 6-13)
          * Active Wells: 1,310 scf gas/well-day (37.1 m3 THC/well-day, 0.0205 t CH4/well-day)
          * Suspended Wells: 710 scf gas/well-day (20.1 m3 THC/well-day, 0.0111 t CH4/well-day)
      - Low Pressure Gas Well Casing Gas Migration (§6.3.5.2, Exhibit 6-10)
          * 3.85 m3 gas/well-day (0.00213 tonnes CH4/well-day at 81.6 mol% CH4)
    Verified against Exhibits 6-9 and 6-10.
    """

    TABLE_6_12_THROUGHPUT = {
        "primary_heavy_oil": {
            "scf_gas_per_bbl": 210.0,
            "m3_thc_per_m3": 37.4,
            "ef_ch4_tonnes_per_1000bbl": 3.28,
            "default_vent_pct": 63.2,
            "baseline_ch4_mol": 0.816,
        },
        "thermal_heavy_oil": {
            "scf_gas_per_bbl": 14.2,
            "m3_thc_per_m3": 2.53,
            "ef_ch4_tonnes_per_1000bbl": 0.223,
            "default_vent_pct": 4.7,
            "baseline_ch4_mol": 0.816,
        },
        "crude_bitumen": {
            "scf_gas_per_bbl": 12.9,
            "m3_thc_per_m3": 2.30,
            "ef_ch4_tonnes_per_1000bbl": 0.207,
            "default_vent_pct": 18.0,
            "baseline_ch4_mol": 0.816,
        },
    }

    TABLE_6_13_WELL_BASIS = {
        "active_wells": {
            "scf_gas_per_well_day": 1310.0,
            "m3_thc_per_well_day": 37.1,
            "ef_ch4_tonnes_per_well_day": 0.0205,
            "baseline_ch4_mol": 0.816,
        },
        "suspended_wells": {
            "scf_gas_per_well_day": 710.0,
            "m3_thc_per_well_day": 20.1,
            "ef_ch4_tonnes_per_well_day": 0.0111,
            "baseline_ch4_mol": 0.816,
        },
    }

    LOW_PRESSURE_CASING_MIGRATION = {
        "m3_gas_per_well_day": 3.85,
        "ef_ch4_tonnes_per_well_day": 0.00213,
        "baseline_ch4_mol": 0.816,
    }

    def __init__(self):
        super().__init__("Casing Gas Vents", "Section 6.3.5")

    def calculate(
        self,
        method="throughput",  # "throughput", "well_count", "migration", "direct_measurement"
        oil_type="primary_heavy_oil",  # "primary_heavy_oil", "thermal_heavy_oil", "crude_bitumen"
        well_status="active_wells",    # "active_wells", "suspended_wells"
        throughput=None,      # bbl/yr or bbl/day
        throughput_rate=None, # bbl/day
        operating_days=365.0,
        throughput_unit="bbl/yr",
        well_count=None,
        measured_gas_volume=None,  # scf or m3
        volume_unit="scf",
        actual_vent_fraction=None, # if known, e.g. 0.632 or 63.2%
        ch4_content=None,          # mole fraction or % (default 81.6%)
        co2_content=None,          # mole fraction or %
        control_efficiency=0.0,
        disposition="vented",
        hhv=1020.0,
        ef_n2o=None,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        meth = str(method or "throughput").lower().strip()
        days = max(1.0, float(operating_days or 365.0))

        c_ch4 = 0.816 if ch4_content is None else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0
        c_ch4 = max(0.0, min(1.0, c_ch4))

        c_co2 = 0.0 if co2_content is None else float(co2_content)
        if c_co2 > 1.0:
            c_co2 /= 100.0
        c_co2 = max(0.0, min(1.0, c_co2))

        total_gas_scf = 0.0

        if meth == "throughput":
            self.validate_inputs(
                {"throughput": throughput if throughput is not None else throughput_rate},
                ["throughput"],
            )
            otype = str(oil_type or "primary_heavy_oil").lower().strip()
            factor_info = self.TABLE_6_12_THROUGHPUT.get(otype, self.TABLE_6_12_THROUGHPUT["primary_heavy_oil"])

            # Determine total annual bbl
            if throughput_rate is not None:
                annual_bbl = float(throughput_rate) * days
            elif throughput_unit == "bbl/day":
                annual_bbl = float(throughput) * days
            else:
                annual_bbl = float(throughput)

            # Check venting adjustment if custom actual_vent_fraction provided
            factor_scf = factor_info["scf_gas_per_bbl"]
            if actual_vent_fraction is not None:
                act = float(actual_vent_fraction)
                if act > 1.0:
                    act /= 100.0
                def_pct = factor_info["default_vent_pct"] / 100.0
                factor_scf = factor_scf * (act / def_pct)

            total_gas_scf = annual_bbl * factor_scf

        elif meth == "well_count":
            self.validate_inputs({"well_count": well_count}, ["well_count"])
            wstat = str(well_status or "active_wells").lower().strip()
            factor_info = self.TABLE_6_13_WELL_BASIS.get(wstat, self.TABLE_6_13_WELL_BASIS["active_wells"])
            scf_per_day = factor_info["scf_gas_per_well_day"]
            total_gas_scf = float(well_count) * scf_per_day * days

        elif meth == "migration":
            # Low pressure gas well casing migration (Exhibit 6-10)
            self.validate_inputs({"well_count": well_count}, ["well_count"])
            m3_day = self.LOW_PRESSURE_CASING_MIGRATION["m3_gas_per_well_day"]
            scf_day = convert(m3_day, "m3", "scf")
            total_gas_scf = float(well_count) * scf_day * days

        elif meth == "direct_measurement":
            self.validate_inputs({"measured_gas_volume": measured_gas_volume}, ["measured_gas_volume"])
            vol = float(measured_gas_volume)
            if volume_unit == "m3":
                total_gas_scf = convert(vol, "m3", "scf")
            else:
                total_gas_scf = vol

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        # Tonnes from molar volume: scf * mol_frac * (MW / 379.3) / 2204.6226
        gross_ch4_tonnes = total_gas_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        # Routing
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
            factor_source="API_Section_6.3.5",
            category="casing_gas",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "method": meth,
                "oil_type": oil_type,
                "total_gas_scf": total_gas_scf,
                "total_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "disposition": disp,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.5",
                "tables": "Table 6-12 / Table 6-13",
            },
        )


class CO2EORVentingCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.10 - CO2 Enhanced Oil Recovery (EOR) Operations
    Covers:
      - Dissolved CO2 retention in hydrocarbon liquids beyond tankage (Equation 6-26):
          E_CO2 = S_h1 * V_h1
      - Supercritical CO2 injection pump blowdown (Equation 6-27, Exhibit 6-22):
          E_CO2 = N * V_v * R_c * GHG_CO2 * 0.001
    Verified against Exhibit 6-22.
    """

    def __init__(self):
        super().__init__("CO2 EOR Operations", "Section 6.3.10")

    def calculate(
        self,
        activity="pump_blowdown",  # "pump_blowdown", "dissolved_retention"
        # Equation 6-27 Injection pump blowdown inputs (Exhibit 6-22)
        events=1.0,
        physical_volume_m3=None,
        physical_volume_ft3=None,
        co2_density_kg_m3=650.0,  # approximate density of supercritical CO2 at 14 MPa, 60°C is ~650 kg/m3
        co2_weight_fraction=0.985, # default 98.5 wt% CO2
        # Equation 6-26 Dissolved CO2 inputs
        oil_production_bbl=None,
        co2_retained_tonnes_per_bbl=None,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        act = str(activity or "pump_blowdown").lower().strip()
        gross_co2_tonnes = 0.0

        if act == "pump_blowdown":
            self.validate_inputs({"events": events}, ["events"])
            n_events = float(events)

            if physical_volume_m3 is not None:
                v_m3 = float(physical_volume_m3)
            elif physical_volume_ft3 is not None:
                v_m3 = convert(float(physical_volume_ft3), "scf", "m3")
            else:
                raise ValueError("physical_volume_m3 or physical_volume_ft3 must be provided")

            rho = float(co2_density_kg_m3 if co2_density_kg_m3 is not None else 650.0)
            wt_frac = float(co2_weight_fraction if co2_weight_fraction is not None else 0.985)
            if wt_frac > 1.0:
                wt_frac /= 100.0

            # Equation 6-27: E_CO2 = N * V_v * R_c * GHG_CO2 * 0.001 (tonnes)
            gross_co2_tonnes = n_events * v_m3 * rho * wt_frac * 0.001

        elif act == "dissolved_retention":
            # Equation 6-26: E_CO2 = S_h1 * V_h1
            self.validate_inputs(
                {
                    "oil_production_bbl": oil_production_bbl,
                    "co2_retained_tonnes_per_bbl": co2_retained_tonnes_per_bbl,
                },
                ["oil_production_bbl", "co2_retained_tonnes_per_bbl"],
            )
            v_h1 = float(oil_production_bbl)
            s_h1 = float(co2_retained_tonnes_per_bbl)
            gross_co2_tonnes = s_h1 * v_h1

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=0.0,
            total_co2=gross_co2_tonnes,
            flared_n2o=0.0,
            uncertainties=uncertainties,
            factor_source="API_Section_6.3.10",
            category="co2_eor",
        )

        total_co2e = calculate_co2e(ch4=0.0, co2=gross_co2_tonnes, n2o=0.0, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "activity": act,
                "events": events,
                "gross_co2_tonnes": gross_co2_tonnes,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.10",
                "equations": "Equation 6-26, Equation 6-27",
            },
        )


class ProductionNonRoutineVentingCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.3.11 - Other Production Related Venting
    Covers:
      - Intermittent non-routine venting events (Equation 6-28):
          E_x = VR * F_x * [MW_x / Molar_Volume] * Tv * n
      - Pressure relief valve releases (Table 6-28):
          34 scfy CH4/PRV = 0.00065 tonnes CH4/PRV-yr (at 78.8 mol% CH4)
      - Offshore Emergency Shutdown (ESD) releases (Table 6-28):
          256,888 scfy CH4/platform = 4.9276 tonnes CH4/platform-yr (at 78.8 mol% CH4)
    """

    TABLE_6_28 = {
        "prv": {"scf_gas_yr": 43.0, "scf_ch4_yr": 34.0, "ef_ch4_tonnes": 0.00065, "baseline_ch4_mol": 0.788, "unc": 3.10},
        "esd_platform": {"scf_gas_yr": 326000.0, "scf_ch4_yr": 256888.0, "ef_ch4_tonnes": 4.9276, "baseline_ch4_mol": 0.788, "unc": 2.76},
    }

    def __init__(self):
        super().__init__("Production Non-Routine Venting", "Section 6.3.11")

    def calculate(
        self,
        source_type="event",  # "event", "prv", "esd_platform"
        # Equation 6-28 event inputs
        vent_rate_scfm=None,
        duration_minutes=None,
        events=1.0,
        # Table 6-28 count inputs
        equipment_count=1.0,
        # Composition
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
        stype = str(source_type or "event").lower().strip()

        c_ch4 = 0.788 if ch4_content is None else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0
        c_ch4 = max(0.0, min(1.0, c_ch4))

        c_co2 = 0.0 if co2_content is None else float(co2_content)
        if c_co2 > 1.0:
            c_co2 /= 100.0
        c_co2 = max(0.0, min(1.0, c_co2))

        total_gas_scf = 0.0
        gross_ch4_tonnes = 0.0
        gross_co2_tonnes = 0.0

        if stype in ["prv", "esd_platform"]:
            n_eq = float(equipment_count or 1.0)
            info = self.TABLE_6_28[stype]
            total_gas_scf = n_eq * info["scf_gas_yr"]
            gross_ch4_tonnes = n_eq * info["ef_ch4_tonnes"] * (c_ch4 / 0.788)
            if c_ch4 > 0 and c_co2 > 0:
                gross_co2_tonnes = gross_ch4_tonnes * (1.0 / MW_CH4) * (1.0 / c_ch4) * c_co2 * MW_CO2

        else:
            # Equation 6-28
            self.validate_inputs(
                {"vent_rate_scfm": vent_rate_scfm, "duration_minutes": duration_minutes},
                ["vent_rate_scfm", "duration_minutes"],
            )
            vr = float(vent_rate_scfm)
            tv = float(duration_minutes)
            n = max(0.0, float(1.0 if events is None else events))
            total_gas_scf = vr * tv * n
            gross_ch4_tonnes = total_gas_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
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
            factor_source="API_Section_6.3.11",
            category="production_non_routine",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "source_type": stype,
                "total_gas_scf": total_gas_scf,
                "total_gas_m3": total_gas_m3,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
                "disposition": disp,
            },
            metadata={
                "standard": "API Compendium 2021 Section 6.3.11",
                "tables": "Table 6-28, Eq 6-28",
            },
        )
