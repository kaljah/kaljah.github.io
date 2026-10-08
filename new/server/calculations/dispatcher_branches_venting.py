"""Venting, associated gas, tank, pneumatic and dehydrator branches of CalculationDispatcher._dispatch_impl.

Split out of calculations/dispatcher.py unchanged (hardening plan, task 5.5). Each function is one
branch of the process-type chain; ``self`` is the dispatcher. dispatcher.py imports them last.
"""
from .units import CONVERSIONS
from calculations.dispatcher import record_period


def calc_venting(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties, unit):
    raw_vol = self._require_float(
        flat_inputs,
        ["blowdown_volume", "amount", "quantity"],
        "vessel physical volume",
    )
    if flat_inputs.get("blowdown_volume") in (None, "", "-"):   # the volume is the record quantity
        raw_unit = self._method_unit(flat_inputs, ["blowdown_unit"], flat_inputs.get("unit"), "m3")
    else:
        raw_unit = flat_inputs.get("blowdown_unit") or unit or "m3"
    vol_m3 = self._normalize_volume(raw_vol, raw_unit, "m3", flat_inputs.get("year"), flat_inputs.get("month"))
    press = self._require_float(
        flat_inputs,
        ["blowdown_pressure", "pressure"],
        "vessel pressure before blowdown (psig)",
    )
    events = int(
        self._require_float(
            flat_inputs,
            ["blowdown_events", "events"],
            "number of blowdown events",
        )
    )
    ch4_content = self._require_fraction(
        flat_inputs, ["ch4_content", "c1"], "gas CH4 content %"
    )
    co2_content = self._optional_fraction(
        flat_inputs, ["co2_content", "co2_mol"], 0.0
    )
    flare_eff = self._optional_fraction(
        flat_inputs, ["control_efficiency"], 0.0
    )

    ef_co2 = emission_factors.get("co2")
    ef_ch4 = emission_factors.get("ch4")
    ef_n2o = emission_factors.get("n2o")

    return calculator.calculate(
        blowdown_volume=vol_m3,
        pressure=press,
        events=events,
        ch4_content=ch4_content,
        uncertainties=uncertainties,
        co2_content=co2_content,
        control_efficiency=flare_eff,
        ef_co2=ef_co2,
        ef_ch4=ef_ch4,
        ef_n2o=ef_n2o,
        operating_temperature=flat_inputs.get("blowdown_temp")
        or flat_inputs.get("operating_temperature", 60.0),
        temp_unit=flat_inputs.get("temp_unit")
        or flat_inputs.get("blowdown_temp_unit", "F"),
        press_unit=flat_inputs.get("press_unit")
        or flat_inputs.get("blowdown_press_unit", "psig"),
        z_factor=flat_inputs.get("z_factor", 1.0),
        hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
        gwp_dict=gwp_dict,
        # Eq 6-32 / Exhibit 6-25 by default; a residual pressure switches to the released dP (BUG-101)
        **self._blowdown_residual(flat_inputs),
    )


def calc_associated_gas_venting(self, calculator, emission_factors, flat_inputs, gwp_dict, uncertainties):
    tier_val = flat_inputs.get("tier") or flat_inputs.get("tier_level")
    factor_src = flat_inputs.get("factor_source")

    # Activity Data (oil production, vent rate, or vent volume)
    raw_oil = self._optional_float(
        flat_inputs,
        ["oil_production", "oil_amount", "amount", "quantity", "oil_rate"],
        None,
    )
    oil_unit = flat_inputs.get("oil_unit") or flat_inputs.get("unit") or "bbl"

    # Basin / regional factor
    basin = (
        flat_inputs.get("basin")
        or flat_inputs.get("region")
        or flat_inputs.get("fuel")
        or flat_inputs.get("fuel_type")
        or emission_factors.get("name")
        or "US Average"
    )

    # Tier 2 parameters: GOR, venting duration, mass balance
    gor = self._optional_float(
        flat_inputs,
        ["gor", "gas_oil_ratio", "gas_to_oil_ratio"],
        None,
    )
    gor_unit = flat_inputs.get("gor_unit") or "scf/bbl"

    venting_duration = self._optional_float(
        flat_inputs,
        ["venting_duration", "duration", "hours", "days", "vent_duration"],
        None,
    )
    # S1K-F20: the Tier 3 venting time is in hours (form "Venting time (h)", calculator
    # default); a file without duration_unit was read in days (24x high)
    is_t3 = str(tier_val or "").strip().lower() in ("tier3", "tier_3", "3", "t3") or \
        str(factor_src or "").strip().lower() == "specific"
    duration_unit = flat_inputs.get("duration_unit") or ("hours" if is_t3 else "days")
    period_duration = self._optional_float(
        flat_inputs,
        ["period_duration", "total_period", "period_days", "operating_days"],
        None,
    )
    if period_duration is None and str(flat_inputs.get("duration_unit") or "days").lower().startswith("d"):
        period_duration = record_period(flat_inputs)[1]  # the record's month, not a year

    rec_gas = self._optional_float(
        flat_inputs,
        ["recovered_gas_volume", "recovered_gas", "gas_recovered"],
        0.0,
    )
    flared_gas = self._optional_float(
        flat_inputs,
        ["flared_gas_volume", "flared_gas", "gas_flared"],
        0.0,
    )
    gas_vol_unit = flat_inputs.get("gas_volume_unit") or flat_inputs.get("gas_unit") or "scf"

    # Tier 3 parameters: direct measurement
    vent_rate = self._optional_float(
        flat_inputs,
        ["vent_rate", "measured_vent_rate", "flow_rate"],
        None,
    )
    vent_rate_unit = flat_inputs.get("vent_rate_unit") or "scfh"
    vent_volume = self._optional_float(
        flat_inputs,
        ["vent_volume", "measured_vent_volume"],
        None,
    )
    vent_volume_unit = flat_inputs.get("vent_volume_unit") or "scf"

    # Gas composition
    ch4_content = self._optional_fraction(
        flat_inputs, ["ch4_content", "c1", "ch4_mol_pct", "ch4"], None
    )
    co2_content = self._optional_fraction(
        flat_inputs, ["co2_content", "co2_mol", "co2_mol_pct", "co2"], None
    )

    ef_co2 = emission_factors.get("co2")
    ef_ch4 = emission_factors.get("ch4")

    return calculator.calculate(
        tier=tier_val,
        factor_source=factor_src,
        oil_production=raw_oil,
        oil_unit=oil_unit,
        basin=basin,
        gor=gor,
        gor_unit=gor_unit,
        venting_duration=venting_duration,
        duration_unit=duration_unit,
        period_duration=period_duration,
        recovered_gas_volume=rec_gas,
        flared_gas_volume=flared_gas,
        gas_volume_unit=gas_vol_unit,
        vent_rate=vent_rate,
        vent_rate_unit=vent_rate_unit,
        vent_volume=vent_volume,
        vent_volume_unit=vent_volume_unit,
        ch4_content=ch4_content,
        co2_content=co2_content,
        ef_ch4=ef_ch4,
        ef_co2=ef_co2,
        uncertainties=uncertainties,
        gwp_dict=gwp_dict,
    )


def calc_tank(self, calculator, emission_factors, flat_inputs, gwp_dict, process_type, uncertainties, unit):
    if process_type in ("tank_working", "tank_breathing"):
        # Section 6.3.9.3: working / standing losses are the total hydrocarbon loss (AP-42
        # Chapter 7 or simulation) x the vent CH4 / CO2 weight fraction, not flashing
        raise ValueError(
            "Working and breathing losses: enter the total hydrocarbon loss and the vent CH4 / CO2 weight % (vent_method 'thc_mass')"
        )
    raw_throughput = self._require_float(
        flat_inputs,
        ["amount", "quantity", "throughput"],
        "tank liquid throughput",
    )
    t_unit = self._method_unit(flat_inputs, ["tank_unit", "throughput_unit"], flat_inputs.get("unit"), "bbl")
    throughput_bbl = self._liquid_bbl(raw_throughput, t_unit, "Tank throughput")

    # BUG-102: GOR is one of several methods; without it the Table 6-22 / 6-24 defaults (or
    # VBE / Standing / EUB when separator data are given) apply instead of zero emissions
    def _opt(keys):
        for k in keys:
            v = flat_inputs.get(k)
            if v not in (None, "", "-"):
                return v
        return None

    gor = _opt(["tank_gor", "gor"])
    ch4_raw = _opt(["tank_ch4_content", "ch4_content", "c1"])
    tank_eff = self._optional_fraction(
        flat_inputs, ["tank_control_eff", "control_efficiency"], 0.0
    )
    co2_content = self._optional_fraction(
        flat_inputs, ["tank_co2_content", "co2_content", "co2_mol"], 0.0
    )
    liquid = str(_opt(["tank_liquid_type", "liquid_type"]) or "crude").lower()
    if liquid not in ("crude", "condensate", "produced_water"):
        raise ValueError("tank liquid type must be crude, condensate or produced_water")
    api_g = _opt(["api_gravity", "tank_api_gravity"])
    sep_p = _opt(["separator_pressure_psig", "sep_pressure"])
    sep_t = _opt(["separator_temp_f", "sep_temp"])

    return calculator.calculate(
        throughput=throughput_bbl,
        gas_oil_ratio=float(gor) if gor is not None else None,
        ch4_content=self._parse_fraction_value(ch4_raw, key_name="ch4_content") if ch4_raw is not None else None,
        control_efficiency=tank_eff,
        uncertainties=uncertainties,
        process_type=process_type,
        ef_ch4=emission_factors.get("ch4", 0),
        co2_content=co2_content,
        hhv=float(flat_inputs.get("hhv") or emission_factors.get("hhv") or 1020.0),
        gwp_dict=gwp_dict,
        method=_opt(["tank_method", "flashing_method"]),
        liquid_type=liquid,
        tank_size=str(_opt(["tank_size"]) or "large").lower(),
        api_gravity=float(api_g) if api_g is not None else None,
        separator_pressure_psig=float(sep_p) if sep_p is not None else None,
        separator_temp_f=float(sep_t) if sep_t is not None else None,
    )


def calc_pneumatic_devices(self, calculator, flat_inputs, gwp_dict, uncertainties):
    # BUG-100: API 2021 section 6.3.6 - controller type (Tables 6-14 / 6-15), Eq 6-14 monitoring
    # survey, Eq 6-13 actuation volume, or a measured bleed rate
    count = self._require_float(
        flat_inputs,
        ["pneu_count", "device_count", "count", "amount", "quantity"],
        "device count",
    )
    hours_raw = next((flat_inputs.get(k) for k in ("pneu_hours", "hours_operating", "hours", "operating_hours")
                      if flat_inputs.get(k) not in (None, "", "-")), None)
    hours = float(hours_raw) if hours_raw is not None else record_period(flat_inputs)[0]
    if not (0 <= hours <= 8784):
        raise ValueError("annual operating hours must be between 0 and 8,784")
    ctype = flat_inputs.get("pneu_controller_type") or flat_inputs.get("controller_type")
    monitoring = str(flat_inputs.get("pneu_monitoring") or "").lower() in ("true", "1", "yes")
    bleed_raw = flat_inputs.get("pneu_bleed_rate") or flat_inputs.get("bleed_rate")
    if not ctype and not monitoring and bleed_raw in (None, "", "-"):
        raise ValueError("Missing required parameter for Tier 3 specific calculation: pneumatic "
                         "controllers need a controller type (Tables 6-14 / 6-15), monitoring "
                         "survey counts, or a measured bleed rate")
    bleed_rate = float(bleed_raw) if bleed_raw not in (None, "", "-") else None
    if bleed_rate is not None:
        # S1K-F4: every volume-rate spelling (scf, scf/hr, m3, m³, Sm3, m3/hr ...) -> scf/h;
        # a mass rate or an unknown unit is refused (only the exact "m3" was converted)
        from .units import UnitError, volume_rate_m3_per_hour
        try:
            bleed_rate *= volume_rate_m3_per_hour(flat_inputs.get("pneu_bleed_unit") or "scf") / CONVERSIONS["scf_to_m3"]
        except UnitError as err:
            raise ValueError(f"Pneumatic bleed rate unit: {err} (use scf/hr or m3/hr)")
    ch4_raw = next((flat_inputs.get(k) for k in ("pneu_ch4_content", "ch4_content", "c1", "gas_content")
                    if flat_inputs.get(k) not in (None, "", "-")), None)
    if ch4_raw is None and bleed_rate is not None and not ctype:
        raise ValueError("Missing required field: gas CH4 content % (measured bleed rate method)")
    # Table factors are on an 81.6 mol % CH4 basis; without a site analysis that basis is used
    ch4_content = (self._parse_fraction_value(ch4_raw, key_name="ch4_content")
                   if ch4_raw is not None else 0.816)
    actuations = flat_inputs.get("pneu_actuations") or flat_inputs.get("actuations")
    actuations_val = float(actuations) if actuations not in [None, "", "-"] else None

    def _f(k):
        v = flat_inputs.get(k)
        return float(v) if v not in (None, "", "-") else None

    return calculator.calculate(
        count=count,
        hours=hours,
        bleed_rate=bleed_rate,
        ch4_content=ch4_content,
        uncertainties=uncertainties,
        actuations=actuations_val,
        co2_content=self._optional_fraction(flat_inputs, ["pneu_co2_content", "co2_content"], 0.0),
        gwp_dict=gwp_dict,
        controller_type=str(ctype).lower() if ctype else None,
        source_standard=str(flat_inputs.get("pneu_factor_standard") or "api").lower(),
        monitoring_program=monitoring,
        normal_count=_f("pneu_normal_count"),
        normal_fraction_year=_f("pneu_normal_fraction") if _f("pneu_normal_fraction") is not None else 1.0,
        malfunctioning_count=_f("pneu_malfunction_count"),
        malfunctioning_fraction_year=_f("pneu_malfunction_fraction") or 0.0,
    )


def calc_dehydrator(self, calculator, flat_inputs, gwp_dict, uncertainties):
    # Tier 3 browser test #12: the former "parametric solubility" model had no source in the
    # API Compendium. Section 6.3.8.1 methods: Tables 6-17/6-18/6-35/6-36 (Tier 1 activity
    # factors), a process simulation (GRI-GLYCalc) or measurement (vent_method routes)
    if any(flat_inputs.get(k) not in (None, "") for k in ("dehy_pump_rate", "pump_rate", "teg_pump_rate")):
        raise ValueError(
            "Glycol dehydrator Tier 3: enter the measured vent volume or the simulation (GLYCalc) result; "
            "use Tier 1 for the Compendium factors"
        )
    throughput = (
        flat_inputs.get("dehy_throughput")
        or flat_inputs.get("amount")
        or flat_inputs.get("quantity")
    )
    pump_rate = (
        flat_inputs.get("dehy_pump_rate")
        or flat_inputs.get("teg_pump_rate")
        or flat_inputs.get("pump_rate")
    )
    pump_unit = (
        flat_inputs.get("dehy_pump_unit")
        or flat_inputs.get("teg_pump_unit")
        or "gph"
    )
    hours = float(
        flat_inputs.get("dehy_hours")
        or flat_inputs.get("hours_operating")
        or flat_inputs.get("annual_hours")
        or record_period(flat_inputs)[0]
    )
    ch4_content = self._optional_fraction(
        flat_inputs, ["dehy_ch4_content", "ch4_content", "c1", "gas_ch4_mole_pct"], 0.85
    )
    control_eff = self._optional_fraction(
        flat_inputs, ["dehy_eff", "control_efficiency"], 0.0
    )
    contactor_press = float(
        flat_inputs.get("dehy_press")
        or flat_inputs.get("dehy_pressure")  # BUG-090: key the form used to send
        or flat_inputs.get("contactor_pressure")
        or 800.0
    )
    press_u = flat_inputs.get("dehy_press_unit", "psig")
    contactor_t = float(
        flat_inputs.get("dehy_temp")
        or flat_inputs.get("contactor_temperature")
        or 100.0
    )
    temp_u = flat_inputs.get("dehy_temp_unit", "F")
    has_flash = flat_inputs.get("dehy_has_flash", True)
    if isinstance(has_flash, str):
        has_flash = has_flash.lower() in ["true", "1", "yes"]
    flash_eff = self._optional_fraction(
        flat_inputs, ["dehy_flash_eff", "flash_control_eff"], 0.0
    )
    still_type = flat_inputs.get("dehy_still_type") or flat_inputs.get("still_vent_control") or "none"
    flash_type = flat_inputs.get("dehy_flash_type", "none")
    stripping_rate = (
        flat_inputs.get("dehy_stripping_rate")
        or flat_inputs.get("stripping_rate")
        or flat_inputs.get("stripping_gas_rate")
    )
    stripping_unit = (
        flat_inputs.get("dehy_stripping_unit")
        or flat_inputs.get("stripping_unit")
        or flat_inputs.get("stripping_gas_unit")
        or "scf/hr"
    )
    stripping_scf = (
        flat_inputs.get("dehy_stripping_scf")
        or flat_inputs.get("stripping_scf")
        or flat_inputs.get("stripping_gas_scf")
    )

    return calculator.calculate(
        throughput=throughput,
        pump_rate=pump_rate,
        pump_unit=pump_unit,
        hours=hours,
        ch4_content=ch4_content,
        control_eff=control_eff,
        uncertainties=uncertainties,
        contactor_pressure=contactor_press,
        press_unit=press_u,
        contactor_temperature=contactor_t,
        temp_unit=temp_u,
        has_flash_tank=has_flash,
        flash_control_eff=flash_eff,
        still_control_type=still_type,
        flash_control_type=flash_type,
        stripping_gas_rate=float(stripping_rate) if stripping_rate not in [None, "", "-"] else 0.0,
        stripping_gas_unit=stripping_unit,
        stripping_gas_scf=float(stripping_scf) if stripping_scf not in [None, "", "-"] else None,
        gwp_dict=gwp_dict,
    )
