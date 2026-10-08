"""Fugitive, compressor seal, AGR, cogeneration, nitric acid, stoichiometry and indirect steam branches of CalculationDispatcher._dispatch_impl.

Split out of calculations/dispatcher.py unchanged (hardening plan, task 5.5). Each function is one
branch of the process-type chain; ``self`` is the dispatcher. dispatcher.py imports them last.
"""
from .fugitive_onshore import OnshoreComponentFugitiveCalculator, OnshoreEquipmentFugitiveCalculator, OnshoreScreeningMeasurementCalculator
from .stoichiometry import StoichiometricCalculator
from calculations.dispatcher import record_period


def calc_fugitive(self, emission_factors, flat_inputs, gwp_dict, process_type, uncertainties):
    # 1. Duration / Time Basis Handling with proper unit conversion
    _t = next((flat_inputs.get(k) for k in ("hours", "operating_hours", "hours_operating")
               if flat_inputs.get(k) not in (None, "")), None)
    raw_time = float(_t) if _t is not None else 0.0
    _time_given = _t is not None  # an entered 0 h is 0, not a full year
    time_unit = str(
        flat_inputs.get("time_unit")
        or flat_inputs.get("duration_unit")
        or "hours"
    ).lower()

    if not _time_given:
        raw_days = float(
            flat_inputs.get("operating_days")
            or flat_inputs.get("days")
            or 0.0
        )
        if raw_days > 0:
            op_days = raw_days
            op_hours = raw_days * 24.0
        else:
            op_hours = record_period(flat_inputs)[0]  # the record's month
            op_days = op_hours / 24.0
    else:
        if "day" in time_unit:
            op_days = raw_time
            op_hours = raw_time * 24.0
        elif "month" in time_unit:
            op_days = raw_time * (365.25 / 12.0)
            op_hours = op_days * 24.0
        elif "yr" in time_unit or "year" in time_unit:
            op_days = raw_time * 365.25
            op_hours = raw_time * 8760.0
        else:
            op_hours = raw_time
            op_days = raw_time / 24.0

    # 2. Methodology & Sub-Type Detection
    fug_tier = str(flat_inputs.get("fugitive_tier") or "").lower()
    fug_method = str(flat_inputs.get("fugitive_method") or "").lower()
    source_type = str(flat_inputs.get("factor_source") or "default").lower()
    fuel_str = str(flat_inputs.get("fuel") or "").lower()
    ef_unit_str = str(emission_factors.get("unit") or flat_inputs.get("unit") or "").lower()

    is_facility = (
        process_type in ["fugitive_facility", "facility_fugitive"]
        or fug_tier in ["tier1", "tier_1", "facility"]
        or fug_method == "facility"
        or "facility" in fuel_str
        or "facility/day" in ef_unit_str
        or "pad" in fuel_str
    )

    is_screening_measurement = (
        process_type in ["fugitive_screening", "fugitive_ogi", "fugitive_measurement"]
        or fug_tier in ["tier3", "tier_3", "measurement", "screening"]
        or fug_method in ["screening", "method21", "ogi", "measurement", "correlation"]
        # BUG-048: "specific" with a catalog leak factor and no measurement inputs is the
        # engineering count x factor x hours method, not a direct measurement of `amount`
        or (source_type == "specific" and not (emission_factors.get("ch4") or emission_factors.get("factor")
                                               or flat_inputs.get("ef") not in (None, "")))
        or flat_inputs.get("fugitive_ppm") is not None
        or flat_inputs.get("screening_ppm") is not None
        or flat_inputs.get("measured_rate") is not None
        or flat_inputs.get("leakers_count") is not None
    )

    is_component = (
        process_type in ["fugitive_component", "component_fugitive"]
        or fug_tier in ["tier2_component", "component"]
        or fug_method == "component"
        or flat_inputs.get("component_type") is not None
        or flat_inputs.get("component_counts") is not None
        or "component" in fuel_str
        or "kg/hr/source" in ef_unit_str
        or "kg toc/hr" in ef_unit_str
    )

    if is_facility:
        return self._facility_fugitive(flat_inputs, uncertainties, gwp_dict)

    elif is_screening_measurement:
        calc = OnshoreScreeningMeasurementCalculator()
        # the explicit method decides (Tier 3 browser test #3: "method21" fell through to
        # direct measurement; stale keys of another method must not re-route a record)
        sub_mode = str(flat_inputs.get("fugitive_sub_method") or fug_method or "").lower()
        if not sub_mode:
            sub_mode = ("ogi" if flat_inputs.get("leakers_count") is not None
                        else "correlation" if flat_inputs.get("corr_screened_count") is not None
                        else "measurement")
        comp_type = str(flat_inputs.get("component_type") or "valve")
        service = str(flat_inputs.get("service_type") or flat_inputs.get("service") or "gas")
        y_ch4 = self._optional_fraction(flat_inputs, ["ch4_content", "ch4_mole_pct", "ch4_fraction", "c1"], None)
        y_co2 = self._optional_fraction(flat_inputs, ["co2_content", "co2_mole_pct", "co2_fraction"], None)

        if "ogi" in sub_mode or sub_mode in ("leaker", "leakers"):
            leakers = self._require_float(flat_inputs, ["leakers_count", "detected_leakers"], "number of leakers")
            surveyed = flat_inputs.get("surveyed_count") or flat_inputs.get("total_surveyed")
            return calc.calculate_ogi_survey(
                component_type=flat_inputs.get("ogi_component") or comp_type,
                service_type=flat_inputs.get("ogi_service") or service,
                total_surveyed=surveyed,
                leakers_detected=leakers,
                operating_hours=op_hours,
                uncertainties=uncertainties,
                gwp_dict=gwp_dict,
                ch4_mol=y_ch4,
                co2_mol=y_co2,
            )
        elif "corr" in sub_mode:
            ppm_vals = flat_inputs.get("screening_values_ppm")
            if isinstance(ppm_vals, str):
                ppm_vals = [v for v in ppm_vals.replace(";", ",").split(",") if v.strip()]
            if not ppm_vals and flat_inputs.get("corr_screened_count") not in (None, ""):
                n_scr = int(float(flat_inputs.get("corr_screened_count") or 0))
                if n_scr:
                    ppm = self._require_float(flat_inputs, ["fugitive_ppm", "screening_ppm", "ppm"], "screening ppm")
                    ppm_vals = [ppm] * n_scr
            elif not ppm_vals and not any(
                flat_inputs.get(k) not in (None, "")
                for k in ("corr_zero_count", "corr_pegged_10k_count", "corr_pegged_100k_count")
            ):
                ppm = self._require_float(flat_inputs, ["fugitive_ppm", "ppm", "screening_ppm"], "screening ppm")
                count = int(float(flat_inputs.get("amount") or flat_inputs.get("quantity") or 1))
                ppm_vals = [ppm] * count
            # CH4 weight fraction of TOC (not the gas mole %); default 0.564 (Table C-1)
            return calc.calculate_correlation_equation(
                component_type=flat_inputs.get("correlation_type") or comp_type,
                service_type=service,
                screening_values_ppm=ppm_vals or [],
                operating_hours=op_hours,
                ch4_content=flat_inputs.get("ch4_wt_fraction"),
                uncertainties=uncertainties,
                gwp_dict=gwp_dict,
                zero_count=flat_inputs.get("corr_zero_count"),
                pegged_10k_count=flat_inputs.get("corr_pegged_10k_count"),
                pegged_100k_count=flat_inputs.get("corr_pegged_100k_count"),
            )
        elif "method21" in sub_mode or "range" in sub_mode or sub_mode == "screening":
            below = flat_inputs.get("m21_below_count")
            above = flat_inputs.get("m21_above_count")
            if below in (None, "") and above in (None, ""):
                # older payloads: one screening value for `amount` components
                count = self._require_float(flat_inputs, ["amount", "quantity", "component_count"], "component count")
                ppm = self._require_float(flat_inputs, ["screening_ppm", "fugitive_ppm", "ppm"], "screening value (ppmv)")
                below, above = (0, count) if ppm >= 10000 else (count, 0)
            return calc.calculate_method21_ranges(
                component_type=flat_inputs.get("m21_component") or comp_type,
                service_type=flat_inputs.get("m21_service") or service,
                non_pegged_count=below,
                pegged_count=above,
                operating_hours=op_hours,
                ch4_content=flat_inputs.get("ch4_wt_fraction"),
                uncertainties=uncertainties,
                gwp_dict=gwp_dict,
            )
        elif "measure" in sub_mode:
            meas_rate = self._require_float(
                flat_inputs, ["measured_rate", "flow_rate", "rate"], "measured leak rate"
            )
            rate_u = str(flat_inputs.get("rate_unit") or flat_inputs.get("measurement_unit") or "")
            if not rate_u:
                raise ValueError("Select the unit of the measured leak rate")
            return calc.calculate_direct_measurement(
                measured_rate=meas_rate,
                measurement_unit=rate_u,
                operating_hours=op_hours,
                ch4_mol=y_ch4,
                co2_mol=y_co2,
                uncertainties=uncertainties,
                gwp_dict=gwp_dict,
            )
        else:
            raise ValueError(f"Unknown fugitive Tier 3 method '{sub_mode}'")

    elif is_component:
        calc = OnshoreComponentFugitiveCalculator()
        comps_dict = flat_inputs.get("component_counts")
        if not comps_dict:
            c_type = flat_inputs.get("component_type") or flat_inputs.get("fuel")
            if not c_type:
                raise ValueError("Select the component type")
            c_type = str(c_type)
            c_count = self._require_float(
                flat_inputs,
                ["amount", "quantity", "count", "component_count"],
                "component count",
            )
            c_ef = float(
                emission_factors.get("ch4")
                or emission_factors.get("factor")
                or flat_inputs.get("ef")
                or 0.0
            )
            if c_ef > 0:
                c_unit = str(emission_factors.get("unit") or flat_inputs.get("ef_unit") or "kg TOC/hr/component")
                comps_dict = {c_type: {"count": c_count, "ef": c_ef, "unit": c_unit}}
            else:
                # no catalog / custom factor: Table 7-12 by component and service (the former
                # invented 0.0045 kg/hr fallback is removed)
                comps_dict = {c_type: c_count}

        service = str(flat_inputs.get("service_type") or flat_inputs.get("service") or "Gas")
        # gas mole fractions (Table 7-12 scaling, CO2) and the CH4 weight fraction of TOC
        c_ch4 = self._optional_fraction(flat_inputs, ["ch4_mole_pct", "ch4_content", "c1"], None)
        c_co2 = self._optional_fraction(flat_inputs, ["co2_mole_pct", "co2_content", "co2_fraction"], None)
        return calc.calculate(
            component_counts=comps_dict,
            service_type=service,
            operating_hours=op_hours,
            ch4_content=c_ch4,
            co2_content=c_co2,
            uncertainties=uncertainties,
            gwp_dict=gwp_dict,
            ch4_wt_fraction=flat_inputs.get("ch4_wt_fraction") or flat_inputs.get("ch4_fraction"),
        )

    else:
        # Equipment-Level (Tier 2A) or backward-compatible equipment factor
        calc = OnshoreEquipmentFugitiveCalculator()
        count = self._require_float(
            flat_inputs,
            ["equipment_count", "well_count", "separator_count", "amount", "quantity", "count"],
            "equipment count",
        )
        ef = float(
            emission_factors.get("ch4")
            or emission_factors.get("factor")
            or flat_inputs.get("ef")
            or 0.0
        )
        ef_u = str(emission_factors.get("unit") or flat_inputs.get("unit") or "tonne CH4/well/hr")
        eq_type = str(flat_inputs.get("equipment_type") or flat_inputs.get("fuel") or "Equipment")
        service = str(flat_inputs.get("service_type") or "Gas")
        return calc.calculate(
            equipment_count=count,
            equipment_type=eq_type,
            service_type=service,
            operating_hours=op_hours,
            factor_value=ef,
            factor_unit=ef_u,
            uncertainties=uncertainties,
            gwp_dict=gwp_dict,
            ch4_wt_fraction=next((flat_inputs.get(k) for k in ("ch4_wt_fraction", "ch4_content")
                                  if flat_inputs.get(k) not in (None, "")), None),
        )


def calc_compressor_seal(self, calculator, flat_inputs, gwp_dict, uncertainties):
    count = self._require_float(
        flat_inputs,
        ["compressor_count", "count", "amount", "quantity"],
        "compressor count",
    )
    raw_seal = str(
        flat_inputs.get("seal_type")
        or flat_inputs.get("comp_mode")
        or flat_inputs.get("compressor_type")
        or "reciprocating"
    ).lower().strip()
    if "dry" in raw_seal:
        seal_type = "centrifugal_dry"
    elif "wet" in raw_seal:
        seal_type = "centrifugal_wet"
    else:
        seal_type = "reciprocating"

    raw_hours = float(flat_inputs.get("hours") or flat_inputs.get("operating_hours") or record_period(flat_inputs)[0])
    return calculator.calculate(
        compressor_count=count,
        seal_type=seal_type,
        hours=raw_hours,
        uncertainties=uncertainties,
        gwp_dict=gwp_dict,
        segment=flat_inputs.get("compressor_segment") or flat_inputs.get("segment") or "production",
        measured_kg_hr=next((flat_inputs.get(k) for k in ("leak_rate_kg_hr", "measured_kg_hr")
                             if flat_inputs.get(k) not in (None, "")), None),
    )


def calc_agr(self, calculator, flat_inputs, gwp_dict, uncertainties, unit):
    agr_vol = self._require_float(
        flat_inputs,
        ["agr_throughput", "gas_throughput", "amount", "quantity", "throughput"],
        "gas throughput",
    )
    if flat_inputs.get("agr_throughput") in (None, "", "-") and flat_inputs.get("gas_throughput") in (None, "", "-"):
        agr_unit = self._method_unit(flat_inputs, ["agr_unit"], flat_inputs.get("unit"), None) or unit
    else:
        agr_unit = flat_inputs.get("agr_unit") or unit
    vol_mmscf = self._normalize_volume(
        agr_vol, agr_unit, "mmscf", flat_inputs.get("year"), flat_inputs.get("month")
    )
    raw_co2_in = self._require_float(
        flat_inputs, ["agr_co2_in", "co2_in", "co2_content"], "inlet CO2 mole %"
    )
    raw_co2_out_val = flat_inputs.get("agr_co2_out") or flat_inputs.get("co2_out")
    raw_co2_out = float(raw_co2_out_val) if raw_co2_out_val not in [None, "", "-"] else 0.001

    if flat_inputs.get("agr_co2_in") not in (None, ""):
        # the form's fields are labelled "%": always percentages (0.9 % is not 90 %)
        co2_in, co2_out = raw_co2_in / 100.0, (raw_co2_out / 100.0 if raw_co2_out_val not in [None, "", "-"] else 0.0)
    elif raw_co2_in > 1.0 or raw_co2_out > 1.0:
        co2_in = raw_co2_in / 100.0 if raw_co2_in > 1.0 else raw_co2_in
        co2_out = (raw_co2_out / 100.0) if raw_co2_in > 1.0 else (raw_co2_out / 100.0 if raw_co2_out > 1.0 else raw_co2_out)
    else:
        co2_in = raw_co2_in
        co2_out = raw_co2_out

    if co2_out > co2_in:
        raise ValueError("Outlet CO2 cannot exceed inlet CO2")

    ch4_in = self._optional_fraction(
        flat_inputs, ["agr_ch4_in", "ch4_in", "c1", "ch4_mole_pct"], 0.85
    )
    ch4_slip = self._optional_fraction(
        flat_inputs,
        ["agr_ch4_slip_pct", "ch4_slip_pct", "agr_ch4_slip", "ch4_slip_fraction", "methane_slip_factor", "ch4_slip"],
        None,
    )
    ctrl_eff = self._optional_fraction(
        flat_inputs, ["agr_control_eff", "control_efficiency", "removal_efficiency"], 0.0
    )
    ctrl_type = (
        flat_inputs.get("agr_control_type")
        or flat_inputs.get("acid_gas_control_type")
        or flat_inputs.get("control_type")
        # BUG-090: older clients sent a bare "routed to flare" flag
        or ("flare" if str(flat_inputs.get("offgas_to_flare", "")).lower() in ("true", "1", "yes") else "vent")
    )
    if str(ctrl_type).strip().lower() != "vent" and ctrl_eff <= 0:
        raise ValueError(
            f"Acid gas control '{ctrl_type}' needs a control / destruction efficiency (agr_control_eff, %)"
        )

    return calculator.calculate(
        throughput=vol_mmscf,
        co2_in=co2_in,
        co2_out=co2_out,
        uncertainties=uncertainties,
        ch4_in=ch4_in,
        ch4_slip_fraction=ch4_slip,
        acid_gas_control_eff=ctrl_eff,
        acid_gas_control_type=ctrl_type,
        gwp_dict=gwp_dict,
    )


def calc_cogen_allocation(self, calculator, flat_inputs, uncertainties):
    tot_em = self._require_float(
        flat_inputs,
        ["total_emissions", "amount", "quantity"],
        "total emissions",
    )
    heat_out = self._require_float(
        flat_inputs, ["heat_output"], "heat output"
    )
    power_out = self._require_float(
        flat_inputs, ["power_output"], "power output"
    )
    c_method = flat_inputs.get("cogen_method") or flat_inputs.get(
        "method", "wri_efficiency"
    )
    return calculator.calculate(
        total_emissions=tot_em,
        heat_output=heat_out,
        power_output=power_out,
        method=c_method,
        uncertainties=uncertainties,
        heat_efficiency=flat_inputs.get("heat_efficiency"),
        power_efficiency=flat_inputs.get("power_efficiency"),
    )


def calc_nitric_acid_production(self, calculator, emission_factors, flat_inputs, gwp_dict, process_type, uncertainties, unit):
    if flat_inputs.get("carbon_content") is not None or flat_inputs.get("c_content") is not None:
        stoich_calc = StoichiometricCalculator()
        raw_amt = self._require_float(
            flat_inputs,
            ["quantity", "amount", "fuel_mass", "production_amount"],
            "mass / production amount",
        )
        carbon_content = self._optional_fraction(
            flat_inputs,
            ["carbon_content", "c_content"],
            0.85,
        )
        oxidation_factor = self._optional_fraction(
            flat_inputs,
            ["oxidation_factor", "ox_factor"],
            1.0,
        )
        return stoich_calc.calculate(
            fuel_mass=raw_amt,
            carbon_content=carbon_content,
            oxidation_factor=oxidation_factor,
            uncertainties=uncertainties,
            mass_unit=unit,
            gwp_dict=gwp_dict,
        )
    else:
        raw_amt = self._require_float(
            flat_inputs,
            ["production_amount", "amount", "quantity", "fuel_mass"],
            "production amount",
        )
        ef_n2o = (
            emission_factors.get("n2o")
            or emission_factors.get("ef_n2o")
            or flat_inputs.get("ef_n2o")
            or flat_inputs.get("n2o")
        )
        abatement_eff = self._optional_fraction(
            flat_inputs,
            ["abatement_efficiency", "abatement_eff", "control_efficiency", "eta_abatement"],
            0.0,
        )
        return calculator.calculate(
            production_amount=raw_amt,
            ef_n2o=ef_n2o,
            abatement_efficiency=abatement_eff,
            mass_unit=unit,
            uncertainties=uncertainties,
            gwp_dict=gwp_dict,
            process_type=process_type,
        )


def calc_stoichiometry(self, calculator, flat_inputs, gwp_dict, uncertainties, unit):
    raw_amt = self._require_float(
        flat_inputs,
        ["quantity", "amount", "fuel_mass", "production_amount"],
        "mass / production amount",
    )
    carbon_content = self._optional_fraction(
        flat_inputs,
        ["carbon_content", "c_content"],
        0.85,
    )
    oxidation_factor = self._optional_fraction(
        flat_inputs,
        ["oxidation_factor", "ox_factor"],
        1.0,
    )

    return calculator.calculate(
        fuel_mass=raw_amt,
        carbon_content=carbon_content,
        oxidation_factor=oxidation_factor,
        uncertainties=uncertainties,
        mass_unit=unit,
        gwp_dict=gwp_dict,
    )


def calc_indirect_steam(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties):
    heat = self._require_float(
        flat_inputs, ["quantity", "amount", "heat_energy"], "heat energy"
    )
    boiler_eff = self._require_float(
        flat_inputs,
        ["boiler_eff", "boiler_efficiency"],
        "boiler efficiency fraction (e.g. 0.80)",
    )
    trans_loss = self._optional_fraction(
        flat_inputs, ["trans_loss", "transmission_loss"], 0.0
    )

    return calculator.calculate(
        heat_energy=heat,
        ef_co2=emission_factors.get("co2", 0),
        boiler_efficiency=boiler_eff,
        transmission_loss=trans_loss,
        uncertainties=uncertainties,
        heat_unit=flat_inputs.get("heat_unit", "btu"),
        ef_ch4=emission_factors.get("ch4", 0) or 0,
        ef_n2o=emission_factors.get("n2o", 0) or 0,
        gwp_dict=gwp_dict,
    )
