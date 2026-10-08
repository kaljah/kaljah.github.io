"""Combustion, flaring, drilling, completions and liquids-unloading branches of CalculationDispatcher._dispatch_impl.

Split out of calculations/dispatcher.py unchanged (hardening plan, task 5.5). Each function is one
branch of the process-type chain; ``self`` is the dispatcher. dispatcher.py imports them last.
"""
from .combustion import factor_hhv_unit, user_hhv


def calc_stationary_combustion(self, calculator, emission_factors, flat_inputs, gwp_dict, quantity, uncertainties, unit):
    hhv_val = self._require_float(
        flat_inputs, ["hhv"], "Higher Heating Value (HHV)"
    )
    comb_eff = self._require_float(
        flat_inputs,
        [
            "combustion_efficiency",
            "combustion_eff",
            "combustioneff",
            "comb_eff",
            "efficiency",
        ],
        "Combustion Efficiency (%)",
    )
    if comb_eff > 1.0:
        comb_eff_frac = comb_eff / 100.0
    else:
        comb_eff_frac = comb_eff

    t3_hhv, t3_hu = user_hhv(hhv_val, flat_inputs.get("hhv_unit"))
    comps = self._composition(flat_inputs)
    # Tier 3 fuel analysis needs the fuel composition or measured factors; an HHV alone
    # used to give a Verified 0 tCO2e record (Tier 3 browser test #10)
    _spec = flat_inputs.get("specific_factors") or flat_inputs.get("specificFactors") or {}
    _measured = any(
        (emission_factors.get(k) not in (None, "", "-", 0, 0.0))
        or (isinstance(_spec, dict) and str(_spec.get(k) or "").strip() not in ("", "0", "0.0", "-"))
        for k in ("co2", "ch4", "n2o")
    )
    carbon_wt = next((flat_inputs.get(k) for k in ("carbon_content", "carbon_wt_pct", "c_content")
                      if flat_inputs.get(k) not in (None, "", "-")), None)
    if (not any(comps.get(f"c{i}") for i in range(1, 11)) and not comps.get("co2_comp") and not _measured
            and carbon_wt is None):
        raise ValueError(
            "Tier 3 fuel analysis needs the fuel gas composition (Gas analysis) or measured emission factors"
        )
    if any(comps.get(f"c{i}") for i in range(1, 11)):
        # a carbon balance on the gas composition needs the gas volume (an energy or mass
        # quantity was silently calculated with the catalog factor instead)
        from .units import UnitError, gas_volume_m3
        try:
            gas_volume_m3(quantity, unit)
        except UnitError as err:
            raise ValueError(str(err))

    return calculator.calculate(
        fuel_quantity=quantity,
        ef_co2=emission_factors.get("co2", 0),
        ef_ch4=emission_factors.get("ch4", 0),
        ef_n2o=emission_factors.get("n2o", 0),
        uncertainties=uncertainties,
        hhv=t3_hhv,
        ef_unit=flat_inputs.get(
            "ef_unit", emission_factors.get("unit", "kg/unit")
        ),
        fuel_unit=unit,
        # S1K-F2: the HHV basis comes from the factor (catalog type / hhv_unit), as at
        # Tier 1; the fuel name made "Coke Oven Gas" a solid (short-ton basis)
        fuel_type=(emission_factors.get("type") if str(emission_factors.get("type") or "").lower()
                   in ("gases", "liquids", "solids") else None)
        or flat_inputs.get("fuel_type") or emission_factors.get("fuel_type", "unknown"),
        hhv_unit=t3_hu or factor_hhv_unit(emission_factors),
        density=self._fuel_density(flat_inputs),
        carbon_wt=carbon_wt,
        combustion_efficiency=comb_eff_frac,
        operating_temperature=flat_inputs.get("operating_temperature")
        or flat_inputs.get("temperature"),
        temp_unit=flat_inputs.get("temp_unit", "C"),
        operating_pressure=flat_inputs.get("operating_pressure")
        or flat_inputs.get("pressure"),
        press_unit=flat_inputs.get("press_unit", "psig"),
        z_factor=flat_inputs.get("z_factor", 1.0),
        gwp_dict=gwp_dict,
        **comps,
    )


def calc_flaring(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties, unit):
    vol_raw = self._require_float(
        flat_inputs,
        ["amount", "quantity", "gas_volume"],
        "flared gas volume",
    )
    vol_m3 = self._normalize_volume(vol_raw, unit, "m3", flat_inputs.get("year"), flat_inputs.get("month"))
    ch4_content = self._require_fraction(
        flat_inputs,
        ["c1", "ch4_content", "flare_ch4_content"],
        "flared gas CH4 content %",
    )
    flare_type = flat_inputs.get("flare_type", "elevated")
    hhv_val = flat_inputs.get("hhv") or emission_factors.get("hhv")

    comps = self._composition(flat_inputs, c1_keys=("c1", "ch4_content", "flare_ch4_content"))
    if not comps.get("c1"):
        comps["c1"] = ch4_content

    def _get_eff(keys):
        for k in keys:
            v = flat_inputs.get(k)
            if v not in [None, "", "-"]:
                return v
        return None

    # One flare efficiency (template / form "control_efficiency") is the share of the gas
    # combusted: it sets both the carbon conversion and the CH4 destruction unless those are
    # given separately (it used to be ignored and the flare-type default applied)
    single_eff = _get_eff(["control_efficiency", "flare_efficiency", "flare_eff"])
    comb_eff = _get_eff(["combustion_efficiency", "combustion_eff", "eta_c"])
    dest_eff = _get_eff(["destruction_efficiency", "destruction_eff", "eta_d"])
    if single_eff is not None:
        comb_eff = single_eff if comb_eff is None else comb_eff
        dest_eff = single_eff if dest_eff is None else dest_eff
    ef_n2o_val = emission_factors.get("n2o") if emission_factors.get("n2o") not in [None, "", "-"] else (
        emission_factors.get("ef_n2o") if emission_factors.get("ef_n2o") not in [None, "", "-"] else flat_inputs.get("ef_n2o")
    )
    # No N2O factor: the calculator's API Compendium Table 5-3 default (kg/MMBtu of gas
    # flared) applies. An explicit 0 used to be passed, so Tier 3 flaring had no N2O.
    n2o_given = ef_n2o_val not in (None, "", "-")

    return calculator.calculate(
        gas_volume=vol_m3,
        ch4_fraction=ch4_content,
        flare_type=flare_type,
        uncertainties=uncertainties,
        hhv=float(hhv_val) if hhv_val else None,
        ef_unit=flat_inputs.get(
            "ef_unit", emission_factors.get("unit", "kg/unit")
        ) if n2o_given else None,
        fuel_unit="m3",
        fuel_type=flat_inputs.get("fuel_type"),
        ef_n2o=float(ef_n2o_val) if n2o_given else None,
        combustion_efficiency=comb_eff,
        destruction_efficiency=dest_eff,
        operating_temperature=flat_inputs.get("operating_temperature")
        or flat_inputs.get("temperature"),
        temp_unit=flat_inputs.get("temp_unit", "C"),
        operating_pressure=flat_inputs.get("operating_pressure")
        or flat_inputs.get("pressure"),
        press_unit=flat_inputs.get("press_unit", "psig"),
        z_factor=flat_inputs.get("z_factor", 1.0),
        gwp_dict=gwp_dict,
        **comps,
    )


def calc_drilling(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties, unit):
    raw_tier = str(
        flat_inputs.get("tier")
        or flat_inputs.get("tier_mode")
        or flat_inputs.get("source_type")
        or uncertainties.get("_factor_source")
        or "tier1"
    ).lower().strip()

    # Mud type parsing: an explicit mud type, else the one named by the selected Table 6-2 row
    raw_mud_type = str(flat_inputs.get("mud_type") or emission_factors.get("mud_type") or "water_based").lower()
    mud_type = "oil_based" if ("oil" in raw_mud_type or "synth" in raw_mud_type) else "water_based"
    # Catalog rows carry no override: Table 6-2 is applied by mud type and location (browser test
    # F3: the rows' kg-based values were read as tonnes per day). A saved library / custom factor is
    # in kg per unit (Manage Data convention) and the calculator works in tonnes.
    if str(emission_factors.get("type") or "").lower() == "custom":
        _cf = emission_factors.get("ch4")
        drill_ef = float(_cf) / 1000.0 if _cf not in (None, "", "-") else 0
    else:
        drill_ef = 0

    # Check gas concentrations for Tier 2+
    ch4_conc = (
        flat_inputs.get("ch4_fraction")
        if flat_inputs.get("ch4_fraction") is not None
        else flat_inputs.get("ch4_concentration")
    )
    if ch4_conc is None and flat_inputs.get("ch4_pct") is not None:
        ch4_conc = float(flat_inputs.get("ch4_pct")) / 100.0

    co2_conc = (
        flat_inputs.get("co2_fraction")
        if flat_inputs.get("co2_fraction") is not None
        else flat_inputs.get("co2_concentration")
    )
    if co2_conc is None and flat_inputs.get("co2_pct") is not None:
        co2_conc = float(flat_inputs.get("co2_pct")) / 100.0

    unit_str = str(flat_inputs.get("unit") or unit or "").lower().strip()
    # Table 6-2 is per drilling day (or per well at Tier 1): a volume or mass is not an activity
    given_unit = str(flat_inputs.get("unit") or "").lower().strip()  # (not the dispatcher's "m3" default)
    if given_unit in ("h", "hr", "hrs", "hour", "hours"):
        # S1K-F16: drilling time given in hours is converted to drilling days (it was refused)
        for k in ("amount", "quantity", "drilling_days"):
            if flat_inputs.get(k) not in (None, "", "-"):
                flat_inputs[k] = float(flat_inputs[k]) / 24.0
        flat_inputs["unit"] = given_unit = unit_str = "days"
    if given_unit and given_unit not in ("days", "day", "d", "drilling_days", "well", "wells", "well_count"):
        raise ValueError(f"Drilling activity is in drilling days (or wells at Tier 1), not '{given_unit}'")

    # Determine whether Tier 1, Tier 2, or Tier 2+
    is_tier2_plus = (
        raw_tier in ["tier2_plus", "tier_2_plus", "tier2+", "tier_2+"]
        or (ch4_conc is not None and float(ch4_conc) != 0.8385)
        or (co2_conc is not None and float(co2_conc) > 0)
    )
    is_tier2 = (
        is_tier2_plus
        or raw_tier in ["tier2", "tier_2", "custom", "t2"]
        or unit_str in ["days", "day", "d"]
        or flat_inputs.get("drilling_days") is not None
        or (flat_inputs.get("mud_type") is not None and raw_tier not in ["tier1", "tier_1", "t1"])
    )

    if is_tier2_plus:
        drilling_days = self._require_float(
            flat_inputs,
            ["drilling_days", "days", "amount", "quantity", "mud_vol", "mud_volume", "volume", "activity_data"],
            "drilling days",
        )
        return calculator.calculate(
            location=self._well_location(flat_inputs),  # BUG-103: offshore Tables 6-2 / 6-7
            tier="tier2_plus",
            drilling_days=drilling_days,
            mud_type=mud_type,
            ch4_concentration=ch4_conc,
            co2_concentration=co2_conc,
            uncertainties=uncertainties,
            ef_ch4=drill_ef,
            gwp_dict=gwp_dict,
        )
    elif is_tier2:
        drilling_days = self._require_float(
            flat_inputs,
            ["drilling_days", "days", "amount", "quantity", "mud_vol", "mud_volume", "volume", "activity_data"],
            "drilling days",
        )
        return calculator.calculate(
            location=self._well_location(flat_inputs),  # BUG-103: offshore Tables 6-2 / 6-7
            tier="tier2",
            drilling_days=drilling_days,
            mud_type=mud_type,
            uncertainties=uncertainties,
            ef_ch4=drill_ef,
            gwp_dict=gwp_dict,
        )
    else:
        # Tier 1 (wells default)
        wells = self._require_float(
            flat_inputs,
            ["wells", "well_count", "amount", "quantity", "mud_vol", "mud_volume", "volume", "drilling_wells", "activity_data"],
            "well count",
        )
        return calculator.calculate(
            location=self._well_location(flat_inputs),  # BUG-103: offshore Tables 6-2 / 6-7
            tier="tier1",
            wells=wells,
            uncertainties=uncertainties,
            ef_ch4=drill_ef,
            gwp_dict=gwp_dict,
        )


def calc_completions(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties):
    comp_tier = (
        flat_inputs.get("tier")
        or flat_inputs.get("comp_tier")
        or ("tier1" if emission_factors.get("code") in [
            "CompGasHF_Uncontrolled", "CompGasHF_REC",
            "CompOilHF_Uncontrolled", "CompOilHF_REC",
            "CompGasNoHF_Vented", "CompOilNoHF_Vented",
            "CompGasNoFlare", "WorkoverGasNoFlare"
        ] else None)
    )
    comp_method = (
        flat_inputs.get("comp_method")
        or flat_inputs.get("calc_method")
        or flat_inputs.get("calculation_method")
    )
    if not comp_method and flat_inputs.get("comp_rate") not in (None, "") and flat_inputs.get("comp_duration") not in (None, ""):
        comp_method = "rate_duration"  # BUG-012: the method the form shows by default
    unit = flat_inputs.get("unit") or "m3"

    # Events determination
    events_val = float(
        flat_inputs.get("events")
        or flat_inputs.get("num_events")
        or (flat_inputs.get("amount") if str(unit).lower() in ["count", "event", "events", "completions", "wells"] else (
            flat_inputs.get("amount") if comp_tier == "tier1" else 1.0
        ))
        or 1.0
    )

    gas_sales_mcf = float(flat_inputs.get("comp_gas_produced_mcf") or flat_inputs.get("gas_produced_sales_mcf") or 0.0)
    gas_sales_scf = gas_sales_mcf * 1000.0 if gas_sales_mcf else float(flat_inputs.get("gas_produced_sales_scf") or 0.0)

    # Flowback volume for Tier 3
    vol_val = None
    vol_unit_val = str(unit or "m3").lower().strip()
    if comp_tier in ["tier3", "3"] or (not comp_tier and not flat_inputs.get("comp_rate") and not flat_inputs.get("comp_liquid_bbl") and not flat_inputs.get("daily_production_rate")):
        raw_vol = flat_inputs.get("flowback_volume") or flat_inputs.get("comp_volume") or (
            flat_inputs.get("amount") if vol_unit_val not in ["count", "event", "events", "completions"] else None
        ) or flat_inputs.get("quantity")
        if raw_vol is not None:
            vol_val = float(raw_vol)
            # the flowback volume carries its own unit (the record's unit may be "events");
            # an unknown unit is an error, never a silent m3 (Exhibit 6-3 check)
            explicit = flat_inputs.get("volume_unit") or flat_inputs.get("comp_volume_unit")
            if explicit:
                vol_unit_val = str(explicit).lower().strip()
            if vol_unit_val not in ["scf", "m3", "sm3", "mcf", "mscf", "mmscf"]:
                raise ValueError("Tier 3 completions need the flowback volume unit (scf, Mcf, MMscf or m3)")

    ch4_content = self._optional_fraction(
        flat_inputs, ["ch4_content", "c1", "comp_ch4_content"], None
    )
    co2_content = self._optional_fraction(
        flat_inputs, ["co2_content", "co2_mol", "comp_co2_content"], 0.0
    )
    default_eff = 0.98 if str(flat_inputs.get("disposition") or flat_inputs.get("comp_disposition") or "").lower() == "flared" else 0.0
    flare_eff = self._optional_fraction(
        flat_inputs, ["comp_flare_eff", "control_efficiency", "flare_efficiency"], default_eff
    )

    # Rate unit: UI default is Mcf/hr
    # BUG-011: the form collects "Avg Gas Rate (Mcf/hr)"; default to that unit
    rate_u = flat_inputs.get("comp_rate_unit") or flat_inputs.get("rate_unit") or "mcf/hr"

    return calculator.calculate(
        location=self._well_location(flat_inputs),  # BUG-103: offshore Tables 6-2 / 6-7
        flowback_volume=vol_val,
        volume_unit=vol_unit_val,
        ch4_content=ch4_content,
        co2_content=co2_content,
        control_efficiency=flare_eff,
        uncertainties=uncertainties,
        ef_co2=emission_factors.get("co2"),
        ef_ch4=emission_factors.get("ch4"),
        ef_n2o=emission_factors.get("n2o"),
        calculation_method=comp_method,
        tier=comp_tier,
        well_type=flat_inputs.get("well_type") or emission_factors.get("well_type", "gas"),
        fracturing=flat_inputs.get("fracturing") if flat_inputs.get("fracturing") is not None else emission_factors.get("fracturing"),
        control_type=flat_inputs.get("control_type") or emission_factors.get("control_type"),
        flowback_rate=flat_inputs.get("comp_rate") or flat_inputs.get("flowback_rate"),
        rate_unit=rate_u,
        flowback_duration_hours=flat_inputs.get("comp_duration") or flat_inputs.get("flowback_duration_hours"),
        daily_production_rate=flat_inputs.get("daily_production_rate") or flat_inputs.get("comp_daily_prod_rate"),
        prod_rate_unit=flat_inputs.get("prod_rate_unit") or flat_inputs.get("comp_prod_rate_unit", "mcf/day"),
        vent_duration_hours=flat_inputs.get("vent_duration_hours"),
        vent_duration_days=flat_inputs.get("vent_duration_days"),
        liquid_flowback_bbl=flat_inputs.get("comp_liquid_bbl") or flat_inputs.get("liquid_flowback_bbl"),
        gas_oil_ratio=flat_inputs.get("comp_gor") or flat_inputs.get("gas_oil_ratio"),
        gas_produced_sales_scf=gas_sales_scf,
        c2plus_content=self._optional_fraction(flat_inputs, ["comp_c2plus_content", "c2plus_content"], 0.0),
        injected_n2_volume=flat_inputs.get("comp_injected_n2") or flat_inputs.get("injected_n2_volume") or 0.0,
        injected_n2_unit=flat_inputs.get("comp_injected_n2_unit") or flat_inputs.get("injected_n2_unit", "scf"),
        injected_gas_type=flat_inputs.get("comp_injected_gas_type") or flat_inputs.get("injected_gas_type", "n2"),
        initial_flowback_hours=flat_inputs.get("comp_initial_flowback_hours") or flat_inputs.get("initial_flowback_hours"),
        disposition=flat_inputs.get("comp_disposition") or flat_inputs.get("disposition"),
        frac_vented=flat_inputs.get("frac_vented") or flat_inputs.get("comp_frac_vented"),
        frac_flared=flat_inputs.get("frac_flared") or flat_inputs.get("comp_frac_flared"),
        frac_recovered=flat_inputs.get("frac_recovered") or flat_inputs.get("comp_frac_recovered"),
        hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
        gwp_dict=gwp_dict,
        events=events_val,
        factor_code=emission_factors.get("code"),
    )


def calc_liquids_unloading(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties):
    calc_method = str(
        flat_inputs.get("calc_method")
        or flat_inputs.get("calculation_method")
        or flat_inputs.get("method")
        or flat_inputs.get("unloading_method")
        or ""
    ).lower().strip()

    # API Equation 6-11: Automated plunger lift
    if (
        calc_method in ["api_equation_6_11", "equation_6_11", "eq_6_11", "automated_plunger"]
        or (flat_inputs.get("p_shut") is not None and flat_inputs.get("p_sep") is not None)
    ):
        p_shut = self._require_float(flat_inputs, ["p_shut", "shut_pressure"], "shut-in pressure (Pshut)")
        p_line = self._require_float(flat_inputs, ["p_line", "line_pressure"], "flow-line pressure (Pline)")
        p_sep = self._require_float(flat_inputs, ["p_sep", "separator_pressure"], "separator pressure (Psep)")
        sfr_p = self._require_float(flat_inputs, ["sfr_p", "sfr", "production_rate"], "daily gas production rate (SFRp)")
        t_p = self._require_float(flat_inputs, ["t_p", "hours_open", "venting_time"], "hours vented per event (Tp)")
        events = int(self._require_float(flat_inputs, ["unload_freq", "unload_events", "events", "amount"], "annual unloading events"))
        # the gas CH4 content is a site input, as for Eq 6-3 / 6-10 (it defaulted to an invented 85 %)
        ch4_content = self._require_fraction(flat_inputs, ["ch4_content", "c1", "unload_ch4_content"], "gas CH4 content %")
        co2_content = self._optional_fraction(flat_inputs, ["co2_content", "co2_mol"], 0.0)
        flare_eff = self._optional_fraction(flat_inputs, ["unload_flare_eff", "control_efficiency"], 0.0)
        press_unit = flat_inputs.get("unload_press_unit") or flat_inputs.get("press_unit", "psia")

        return calculator.calculate_tier3_equation_6_11(
            p_shut=p_shut,
            p_line=p_line,
            p_sep=p_sep,
            sfr_p=sfr_p,
            t_p=t_p,
            events=events,
            well_count=float(flat_inputs.get("well_count") or flat_inputs.get("wells") or 1),
            ch4_content=ch4_content,
            co2_content=co2_content,
            control_efficiency=flare_eff,
            press_unit=press_unit,
            sfr_unit=flat_inputs.get("sfr_unit", "scf/hr"),
            uncertainties=uncertainties,
            hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
            gwp_dict=gwp_dict,
        )

    # API Equation 6-10: EPA Subpart W (W-8 / W-9)
    elif (
        calc_method in ["api_equation_6_10", "equation_6_10", "eq_6_10", "subpart_w"]
        or (flat_inputs.get("sfr") is not None and flat_inputs.get("hours_open") is not None)
    ):
        depth = self._require_float(flat_inputs, ["unload_depth", "well_depth"], "well depth (ft)")
        diam = self._require_float(flat_inputs, ["unload_diam", "diameter"], "casing diameter (in)")
        press = self._require_float(flat_inputs, ["unload_press", "pressure"], "shut-in surface pressure (psig)")
        events = int(self._require_float(flat_inputs, ["unload_freq", "unload_events", "events", "amount"], "annual unloading events"))
        sfr = self._require_float(flat_inputs, ["sfr", "subpart_w_sfr"], "sales flow rate (SFR)")
        hours_open = self._require_float(flat_inputs, ["hours_open", "hrs_open", "venting_hours"], "hours venting during unloading (HR)")
        ch4_content = self._require_fraction(flat_inputs, ["ch4_content", "c1", "unload_ch4_content"], "gas CH4 content %")
        co2_content = self._optional_fraction(flat_inputs, ["co2_content", "co2_mol"], 0.0)
        flare_eff = self._optional_fraction(flat_inputs, ["unload_flare_eff", "control_efficiency"], 0.0)
        depth_unit = flat_inputs.get("unload_depth_unit") or flat_inputs.get("depth_unit", "ft")
        diam_unit = flat_inputs.get("unload_diam_unit") or flat_inputs.get("diameter_unit", "in")
        press_unit = flat_inputs.get("unload_press_unit") or flat_inputs.get("press_unit", "psig")
        # X (0.5 h plunger / 1 h non-plunger) and what D and Depth mean depend on the lift type: it is
        # required (it defaulted to non-plunger while the form displayed "Plunger lift")
        lift = str(flat_inputs.get("unloading_type") or flat_inputs.get("unload_type") or "").strip().lower()
        lift = {"plunger_lift": "plunger", "non-plunger": "non_plunger", "nonplunger": "non_plunger"}.get(lift, lift)
        if lift not in ("plunger", "non_plunger"):
            raise ValueError("Missing required field: lift type (unloading_type: plunger or non_plunger) for Eq 6-10")

        return calculator.calculate_tier3_equation_6_10(
            events=events,
            well_depth=depth,
            diameter=diam,
            pressure=press,
            sfr=sfr,
            hours_open=hours_open,
            unloading_type=lift,
            well_count=float(flat_inputs.get("well_count") or flat_inputs.get("wells") or 1),
            ch4_content=ch4_content,
            co2_content=co2_content,
            control_efficiency=flare_eff,
            depth_unit=depth_unit,
            diameter_unit=diam_unit,
            press_unit=press_unit,
            sfr_unit=flat_inputs.get("sfr_unit", "scf/hr"),
            uncertainties=uncertainties,
            hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
            gwp_dict=gwp_dict,
        )

    # Default Tier 3: API Equation 6-3 (Volume-based wellbore decompression geometry)
    else:
        depth = self._require_float(
            flat_inputs, ["unload_depth", "well_depth"], "well depth (ft)"
        )
        diam = self._require_float(
            flat_inputs, ["unload_diam", "diameter"], "casing diameter (in)"
        )
        press = self._require_float(
            flat_inputs,
            ["unload_press", "pressure"],
            "shut-in surface pressure (psig)",
        )
        events = int(
            self._require_float(
                flat_inputs,
                ["unload_freq", "unload_events", "events", "amount"],
                "annual unloading event count",
            )
        )
        ch4_content = self._require_fraction(
            flat_inputs,
            ["ch4_content", "c1", "unload_ch4_content"],
            "gas CH4 content %",
        )
        co2_content = self._optional_fraction(
            flat_inputs, ["co2_content", "co2_mol"], 0.0
        )
        flare_eff = self._optional_fraction(
            flat_inputs, ["unload_flare_eff", "control_efficiency"], 0.0
        )

        ef_co2 = emission_factors.get("co2")
        ef_ch4 = emission_factors.get("ch4")
        ef_n2o = emission_factors.get("n2o")

        depth_unit = (
            flat_inputs.get("unload_depth_unit")
            or flat_inputs.get("depth_unit", "ft")
        )
        diam_unit = (
            flat_inputs.get("unload_diam_unit")
            or flat_inputs.get("diameter_unit", "in")
        )
        press_unit = (
            flat_inputs.get("unload_press_unit")
            or flat_inputs.get("press_unit", "psig")
        )

        return calculator.calculate_volume_based(
            well_depth=depth,
            diameter=diam,
            pressure=press,
            ch4_content=ch4_content,
            events=events,
            uncertainties=uncertainties,
            co2_content=co2_content,
            control_efficiency=flare_eff,
            ef_co2=ef_co2,
            ef_ch4=ef_ch4,
            ef_n2o=ef_n2o,
            operating_temperature=flat_inputs.get("unload_temp")
            or flat_inputs.get("operating_temperature", 60.0),
            temp_unit=flat_inputs.get("temp_unit", "F"),
            depth_unit=depth_unit,
            diameter_unit=diam_unit,
            press_unit=press_unit,
            hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
            well_count=float(flat_inputs.get("well_count") or flat_inputs.get("wells") or 1),
            unloading_type=flat_inputs.get("unloading_type") or flat_inputs.get("unload_type", "plunger"),
            gwp_dict=gwp_dict,
        )
