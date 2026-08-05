from .combustion import CombustionCalculator, FlaringCalculator
from .vented import (
    PneumaticDeviceCalculator, LiquidsUnloadingCalculator, 
    MudDegassingCalculator, TankFlashingCalculator,
    CompletionFlowbackCalculator, BlowdownCalculator
)
from .fugitive import ComponentFugitiveCalculator, EquipmentFugitiveCalculator, CompressorSealCalculator
from .midstream import AGRCalculator, DehydratorCalculator
from .indirect import IndirectSteamCalculator, CogenAllocationCalculator
from .stoichiometry import StoichiometricCalculator
from .units import CONVERSIONS, calculate_co2e
from .uncertainty import (
    propagate_uncertainty, resolve_tier, resolve_ef_uncertainty,
    PROCESS_CATEGORY, Tier
)

class CalculationDispatcher:
    """
    Routes a calculation request to the appropriate API 2021 calculator.
    """
    def __init__(self):
        self.calculators = {
            "stationary_combustion": CombustionCalculator(),
            "combustion": CombustionCalculator(),
            "flaring": FlaringCalculator(),
            "drilling": MudDegassingCalculator(),
            "completions": CompletionFlowbackCalculator(),
            "liquids_unloading": LiquidsUnloadingCalculator(),
            "unloading": LiquidsUnloadingCalculator(),
            "tank": TankFlashingCalculator(),
            "tank_flashing": TankFlashingCalculator(),
            "tank_working": TankFlashingCalculator(), 
            "tank_breathing": TankFlashingCalculator(),
            "pneumatic_devices": PneumaticDeviceCalculator(),
            "pneumatic_device": PneumaticDeviceCalculator(),
            "pneumatic": PneumaticDeviceCalculator(),
            "fugitive_component": ComponentFugitiveCalculator(),
            "equipment_fugitive": EquipmentFugitiveCalculator(),
            "compressor_fugitive": CompressorSealCalculator(),
            "fugitive": EquipmentFugitiveCalculator(),
            "agr": AGRCalculator(),
            "dehydrator": DehydratorCalculator(),
            "indirect_steam": IndirectSteamCalculator(),
            "cogen_allocation": CogenAllocationCalculator(),
            "stoichiometry": StoichiometricCalculator(),
            "venting": BlowdownCalculator(),
            "blowdown": BlowdownCalculator(),
            "storage_tanks": TankFlashingCalculator()
        }

    def _require(self, key, inputs, description):
        val = inputs.get(key)
        if val in [None, '', '-']:
            from flask import current_app, has_app_context
            if has_app_context():
                current_app.logger.warning(f"Missing required field: {key} ({description})")
            else:
                import logging
                logging.warning(f"Missing required field: {key} ({description})")
            raise ValueError(f"Missing required field: {key} ({description})")
        return float(val)

    def _normalize_volume(self, value, unit, target_unit="m3"):
        """Normalizes a volume value to the specified target unit."""
        u = str(unit or "m3").lower()
        if target_unit == "m3":
            if u in ["scf", "cf", "ft3"]: return value * CONVERSIONS["scf_to_m3"]
            if u in ["mcf", "mscf"]: return value * 1000.0 * CONVERSIONS["scf_to_m3"]
            if u == "mmscf": return value * 1000000.0 * CONVERSIONS["scf_to_m3"]
            if u in ["bbl", "barrel", "barrels"]: return value * CONVERSIONS["bbl_to_m3"]
            if u in ["gal", "gallon", "gallons"]: return value * CONVERSIONS["gal_to_m3"]
            if u in ["l", "liter", "liters"]: return value * CONVERSIONS["liter_to_m3"]
            return value # Default m3
        elif target_unit == "mmscf":
            if u in ["scf", "cf", "ft3"]: return value / 1_000_000.0
            if u in ["mcf", "mscf"]: return value / 1000.0
            if u == "m3": return (value / CONVERSIONS["scf_to_m3"]) / 1_000_000.0
            if u in ["bbl", "barrel", "barrels"]: return (value * CONVERSIONS["bbl_to_m3"] / CONVERSIONS["scf_to_m3"]) / 1_000_000.0
            return value # Default mmscf
        return value

    def _require_float(self, flat_inputs, keys, desc):
        """Strictly extracts a required float parameter without falling back to defaults."""
        if isinstance(keys, str):
            keys = [keys]
        for k in keys:
            val = flat_inputs.get(k)
            if val not in [None, '', '-']:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid numeric value for '{k}' ({desc}): {val}")
        raise ValueError(f"Missing required parameter for Tier 3 specific calculation: '{keys[0]}' ({desc})")

    def _require_fraction(self, flat_inputs, keys, desc):
        """Extracts a percentage (0-100) or fraction (0-1) strictly and converts to 0-1."""
        raw = self._require_float(flat_inputs, keys, desc)
        if raw > 1.0:
            return raw / 100.0
        return raw

    def _optional_fraction(self, flat_inputs, keys, default=0.0):
        """Extracts an optional percentage (0-100) or fraction (0-1) converted to 0-1."""
        if isinstance(keys, str):
            keys = [keys]
        for k in keys:
            val = flat_inputs.get(k)
            if val not in [None, '', '-']:
                try:
                    num = float(val)
                    return num / 100.0 if num > 1.0 else num
                except (ValueError, TypeError):
                    pass
        return default

    def dispatch(self, process_type, inputs, emission_factors, uncertainties, gwp_dict=None):
        """
        Executes the calculation for the given process type.
        - Tier 1 (default / custom): Requires only activity data (quantity & unit) and uses catalog emission factors.
        - Tier 3 (specific): Requires all physical engineering parameters with zero silent defaults.
        """
        from .constants import DEFAULT_GWP
        if gwp_dict is None:
            gwp_dict = DEFAULT_GWP
        calculator = self.calculators.get(process_type)
        
        # Extract process-specific inputs if nested
        calc_inputs = inputs.get('calc_inputs', {}).get(process_type, {})
        flat_inputs = {**inputs, **calc_inputs}
        
        factor_source = flat_inputs.get('factor_source', 'default')

        if not calculator:
            return self._generic_calculation(flat_inputs, emission_factors, uncertainties, process_type)

        # Inject tier info into uncertainties dict so calculators can call resolve_tier()
        uncertainties = dict(uncertainties)
        uncertainties.setdefault('_factor_source', factor_source)

        # Inject dynamic uncertainty overrides for Tier 3 calculations
        if flat_inputs.get('meter_uncertainty_pct') not in [None, '', '-']:
            try: uncertainties['_activity_uncertainty'] = float(flat_inputs['meter_uncertainty_pct']) / 100.0
            except ValueError: pass
            
        if flat_inputs.get('gc_uncertainty_pct') not in [None, '', '-']:
            try: uncertainties['_composition_uncertainty'] = float(flat_inputs['gc_uncertainty_pct']) / 100.0
            except ValueError: pass
            
        user_unc = flat_inputs.get('user_uncertainty')
        if isinstance(user_unc, dict):
            for g in ['co2', 'ch4', 'n2o']:
                if user_unc.get(g) not in [None, '', '-']:
                    try: uncertainties[g] = float(user_unc[g]) / 100.0
                    except ValueError: pass

        # Bypass dispatcher if specific factors are provided without full composition
        if process_type in ['stationary_combustion', 'combustion', 'mobile', 'flaring', 'separation']:
            if factor_source == 'specific' and (flat_inputs.get('specific_factors') or flat_inputs.get('specificFactors')):
                if flat_inputs.get('c1') in [None, '', '-']:
                    return None

        # Extract common quantity
        quantity = float(flat_inputs.get('amount') or flat_inputs.get('quantity') or 0)
        if quantity < 0:
            raise ValueError(f"Quantity/Amount cannot be negative: {quantity}")
        unit = str(flat_inputs.get('unit', 'm3')).lower()

        # =========================================================================
        # TIER 1 / TIER 2 ROUTING: default or custom factor sources
        # Only requires standard activity data; never fails on missing engineering inputs.
        # =========================================================================
        if factor_source in ['default', 'custom']:
            if process_type in ["stationary_combustion", "combustion"]:
                hhv_val = flat_inputs.get('hhv') or emission_factors.get('hhv')
                if hhv_val:
                    return calculator.calculate(
                        fuel_quantity=quantity,
                        ef_co2=emission_factors.get('co2', 0),
                        ef_ch4=emission_factors.get('ch4', 0),
                        ef_n2o=emission_factors.get('n2o', 0),
                        uncertainties=uncertainties,
                        hhv=float(hhv_val),
                        ef_unit=flat_inputs.get('ef_unit', emission_factors.get('unit', 'kg/unit')),
                        fuel_unit=unit,
                        fuel_type=flat_inputs.get('fuel_type') or emission_factors.get('fuel_type', 'unknown'),
                        combustion_efficiency=float(flat_inputs.get('combustion_efficiency') or 100.0)
                    )
            # Default / Custom for all processes uses standard catalog multiplication
            return self._generic_calculation(flat_inputs, emission_factors, uncertainties, process_type)

        # =========================================================================
        # TIER 3 ROUTING: factor_source == 'specific' (Engineering Mode)
        # Strict validation with zero silent defaults.
        # =========================================================================
        try:
            if process_type in ["stationary_combustion", "combustion"]:
                hhv_val = self._require_float(flat_inputs, ['hhv'], "Higher Heating Value (HHV)")
                comb_eff = self._require_float(flat_inputs, ['combustion_efficiency'], "Combustion Efficiency (%)")
                if comb_eff > 1.0:
                    comb_eff_pct = comb_eff
                else:
                    comb_eff_pct = comb_eff * 100.0

                def safe_frac(key):
                    val = flat_inputs.get(key)
                    try:
                        return float(val) / 100.0 if val not in [None, '', '-'] else 0.0
                    except:
                        return 0.0

                comps = {
                    'c1': safe_frac('c1'),
                    'c2': safe_frac('c2'),
                    'c3': safe_frac('c3'),
                    'c4': safe_frac('c4'),
                    'c5': safe_frac('c5'),
                    'c6': safe_frac('c6'),
                    'c7': safe_frac('c7'),
                    'c8': safe_frac('c8'),
                    'c9': safe_frac('c9'),
                    'c10': safe_frac('c10'),
                    'co2_comp': safe_frac('co2_mol') or safe_frac('co2_content'),
                    'n2_comp': safe_frac('n2') or safe_frac('n2_mol')
                }

                return calculator.calculate(
                    fuel_quantity=quantity,
                    ef_co2=emission_factors.get('co2', 0),
                    ef_ch4=emission_factors.get('ch4', 0),
                    ef_n2o=emission_factors.get('n2o', 0),
                    uncertainties=uncertainties,
                    hhv=hhv_val,
                    ef_unit=flat_inputs.get('ef_unit', emission_factors.get('unit', 'kg/unit')),
                    fuel_unit=unit,
                    fuel_type=flat_inputs.get('fuel_type') or emission_factors.get('fuel_type', 'unknown'),
                    combustion_efficiency=comb_eff_pct,
                    **comps
                )

            elif process_type == "flaring":
                vol_raw = self._require_float(flat_inputs, ['amount', 'quantity', 'gas_volume'], "flared gas volume")
                vol_m3 = self._normalize_volume(vol_raw, unit, "m3")
                ch4_content = self._require_fraction(flat_inputs, ['c1', 'ch4_content', 'flare_ch4_content'], "flared gas CH4 content %")
                flare_type = flat_inputs.get("flare_type", "elevated")
                hhv_val = flat_inputs.get('hhv') or emission_factors.get('hhv')

                def safe_frac(key):
                    val = flat_inputs.get(key)
                    try:
                        return float(val) / 100.0 if val not in [None, '', '-'] else 0.0
                    except:
                        return 0.0

                comps = {
                    'c1': ch4_content,
                    'c2': safe_frac('c2'),
                    'c3': safe_frac('c3'),
                    'c4': safe_frac('c4'),
                    'c5': safe_frac('c5'),
                    'c6': safe_frac('c6'),
                    'c7': safe_frac('c7'),
                    'c8': safe_frac('c8'),
                    'c9': safe_frac('c9'),
                    'c10': safe_frac('c10'),
                    'co2_comp': safe_frac('co2_mol') or safe_frac('co2_content'),
                    'n2_comp': safe_frac('n2') or safe_frac('n2_mol')
                }

                return calculator.calculate(
                    gas_volume=vol_m3,
                    ch4_fraction=ch4_content,
                    flare_type=flare_type,
                    uncertainties=uncertainties,
                    hhv=float(hhv_val) if hhv_val else None,
                    ef_unit=flat_inputs.get('ef_unit', emission_factors.get('unit', 'kg/unit')),
                    fuel_unit=unit,
                    fuel_type=flat_inputs.get('fuel_type'),
                    ef_n2o=emission_factors.get('n2o', 0.0),
                    **comps
                )

            elif process_type in ["drilling", "mud_degassing"]:
                mud_vol = self._require_float(flat_inputs, ['mud_vol', 'mud_volume', 'amount', 'quantity'], "drilling mud volume")
                vol_m3 = self._normalize_volume(mud_vol, flat_inputs.get('mud_unit') or unit, "m3")
                mud_type = flat_inputs.get("mud_type") or "water_based"
                return calculator.calculate(
                    mud_volume=vol_m3,
                    mud_type=mud_type,
                    uncertainties=uncertainties,
                    ef_ch4=emission_factors.get('ch4', 0)
                )

            elif process_type == "completions":
                # Require duration and rate or total flowback volume
                if flat_inputs.get('comp_rate') is not None and flat_inputs.get('comp_duration') is not None:
                    rate_mcf = self._require_float(flat_inputs, ['comp_rate'], "average gas rate (Mcf/hr)")
                    dur_hr = self._require_float(flat_inputs, ['comp_duration'], "flowback duration (hours)")
                    events = float(flat_inputs.get('amount') or flat_inputs.get('comp_events') or 1)
                    vol_m3 = rate_mcf * dur_hr * events * 28.3168
                else:
                    vol_raw = self._require_float(flat_inputs, ['amount', 'quantity', 'flowback_volume', 'comp_volume'], "flowback volume")
                    vol_m3 = self._normalize_volume(vol_raw, unit, "m3")

                ch4_content = self._require_fraction(flat_inputs, ['ch4_content', 'c1', 'comp_ch4_content'], "gas CH4 content %")
                co2_content = self._optional_fraction(flat_inputs, ['co2_content', 'co2_mol'], 0.0)
                flare_eff = self._optional_fraction(flat_inputs, ['comp_flare_eff', 'control_efficiency'], 0.0)

                ef_co2 = emission_factors.get('co2')
                ef_ch4 = emission_factors.get('ch4')
                ef_n2o = emission_factors.get('n2o')

                return calculator.calculate(
                    flowback_volume=vol_m3,
                    ch4_content=ch4_content,
                    control_efficiency=flare_eff,
                    uncertainties=uncertainties,
                    co2_content=co2_content,
                    ef_co2=ef_co2,
                    ef_ch4=ef_ch4,
                    ef_n2o=ef_n2o
                )

            elif process_type in ["liquids_unloading", "unloading"]:
                depth = self._require_float(flat_inputs, ['unload_depth', 'well_depth'], "well depth (ft)")
                diam = self._require_float(flat_inputs, ['unload_diam', 'diameter'], "casing diameter (in)")
                press = self._require_float(flat_inputs, ['unload_press', 'pressure'], "shut-in surface pressure (psig)")
                events = int(self._require_float(flat_inputs, ['unload_freq', 'unload_events', 'events', 'amount'], "annual unloading event count"))
                ch4_content = self._require_fraction(flat_inputs, ['ch4_content', 'c1', 'unload_ch4_content'], "gas CH4 content %")
                co2_content = self._optional_fraction(flat_inputs, ['co2_content', 'co2_mol'], 0.0)
                flare_eff = self._optional_fraction(flat_inputs, ['unload_flare_eff', 'control_efficiency'], 0.0)

                ef_co2 = emission_factors.get('co2')
                ef_ch4 = emission_factors.get('ch4')
                ef_n2o = emission_factors.get('n2o')

                return calculator.calculate(
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
                    ef_n2o=ef_n2o
                )

            elif process_type in ["venting", "blowdown"]:
                raw_vol = self._require_float(flat_inputs, ['blowdown_volume', 'amount', 'quantity'], "vessel physical volume")
                raw_unit = flat_inputs.get('blowdown_unit') or unit or 'm3'
                vol_m3 = self._normalize_volume(raw_vol, raw_unit, "m3")
                press = self._require_float(flat_inputs, ['blowdown_pressure', 'pressure'], "vessel pressure before blowdown (psig)")
                events = int(self._require_float(flat_inputs, ['blowdown_events', 'events'], "number of blowdown events"))
                ch4_content = self._require_fraction(flat_inputs, ['ch4_content', 'c1'], "gas CH4 content %")
                co2_content = self._optional_fraction(flat_inputs, ['co2_content', 'co2_mol'], 0.0)
                flare_eff = self._optional_fraction(flat_inputs, ['control_efficiency'], 0.0)

                ef_co2 = emission_factors.get('co2')
                ef_ch4 = emission_factors.get('ch4')
                ef_n2o = emission_factors.get('n2o')

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
                    ef_n2o=ef_n2o
                )

            elif process_type in ["tank", "tank_flashing", "storage_tanks", "tank_working", "tank_breathing"]:
                throughput = self._require_float(flat_inputs, ['amount', 'quantity', 'throughput'], "tank liquid throughput (bbl)")
                gor = self._require_float(flat_inputs, ['tank_gor', 'gor'], "Gas-Oil Ratio (GOR scf/bbl)")
                ch4_content = self._require_fraction(flat_inputs, ['tank_ch4_content', 'ch4_content', 'c1'], "tank flash gas CH4 content %")
                tank_eff = self._optional_fraction(flat_inputs, ['tank_control_eff', 'control_efficiency'], 0.0)

                return calculator.calculate(
                    throughput=throughput,
                    gas_oil_ratio=gor,
                    ch4_content=ch4_content,
                    control_efficiency=tank_eff,
                    uncertainties=uncertainties,
                    process_type="tank_flashing",
                    ef_ch4=emission_factors.get('ch4', 0)
                )

            elif process_type in ["pneumatic_devices", "pneumatic"]:
                count = self._require_float(flat_inputs, ['pneu_count', 'amount', 'quantity'], "device count")
                hours = self._require_float(flat_inputs, ['pneu_hours', 'hours_operating'], "annual operating hours")
                bleed_rate = self._require_float(flat_inputs, ['pneu_bleed_rate', 'bleed_rate'], "measured bleed rate")
                bleed_unit = flat_inputs.get('pneu_bleed_unit', 'scf')
                if bleed_unit == 'm3':
                    bleed_rate *= 35.3147  # convert m3/hr to scf/hr
                ch4_content = self._require_fraction(flat_inputs, ['pneu_ch4_content', 'ch4_content', 'c1'], "gas CH4 content %")

                return calculator.calculate(
                    count=count,
                    hours=hours,
                    bleed_rate=bleed_rate,
                    ch4_content=ch4_content,
                    uncertainties=uncertainties
                )

            elif process_type == "fugitive":
                fugitive_method = flat_inputs.get('fugitive_method', 'average')
                if fugitive_method == 'screening':
                    count = quantity
                    ppm = self._require_float(flat_inputs, ['fugitive_ppm'], "screening concentration (PPM)")
                    ef_base = emission_factors.get('ch4', 0)
                    screening_mult = 2.5 if ppm >= 10000 else 1.0
                    ch4_kg = count * ef_base * screening_mult * 8760
                    ch4_tonnes = ch4_kg / 1000.0

                    def _wrap_unc(val, gas):
                        u = propagate_uncertainty(
                            val,
                            ef_uncertainty=resolve_ef_uncertainty('fugitive', gas,
                                resolve_tier(flat_inputs.get('factor_source', 'default')),
                                uncertainties.get(gas)),
                            tier=resolve_tier(flat_inputs.get('factor_source', 'default')),
                            process_category='fugitive', gas=gas
                        )
                        return u

                    return {
                        "results": {
                            "co2": _wrap_unc(0, "co2"),
                            "ch4": _wrap_unc(ch4_tonnes, "ch4"),
                            "n2o": _wrap_unc(0, "n2o")
                        },
                        "total_co2e": calculate_co2e(0, ch4_tonnes, 0),
                        "method": "api2021_fugitive_screening"
                    }
                else:
                    return self._generic_calculation(flat_inputs, emission_factors, uncertainties, process_type)

            elif process_type == "agr":
                agr_vol = self._require_float(flat_inputs, ['agr_throughput', 'amount', 'quantity'], "gas throughput")
                vol_mmscf = self._normalize_volume(agr_vol, flat_inputs.get('agr_unit') or unit, "mmscf")
                co2_in = self._require_fraction(flat_inputs, ['agr_co2_in', 'co2_in'], "inlet CO2 mole %")
                co2_out = self._require_fraction(flat_inputs, ['agr_co2_out', 'co2_out'], "outlet CO2 mole %")

                return calculator.calculate(
                    throughput=vol_mmscf,
                    co2_in=co2_in,
                    co2_out=co2_out,
                    uncertainties=uncertainties
                )

            elif process_type == "dehydrator":
                throughput = self._require_float(flat_inputs, ["dehy_throughput", "amount", "quantity"], "dehydrator throughput")
                pump_rate = self._require_float(flat_inputs, ["dehy_pump_rate", "pump_rate"], "glycol pump circulation rate")
                pump_unit = flat_inputs.get("dehy_pump_unit", "gph")
                hours = self._require_float(flat_inputs, ["dehy_hours", "hours_operating"], "annual operating hours")
                ch4_content = self._require_fraction(flat_inputs, ["dehy_ch4_content", "ch4_content", "c1"], "gas CH4 content %")
                control_eff = self._optional_fraction(flat_inputs, ["dehy_eff", "control_efficiency"], 0.0)

                return calculator.calculate(
                    throughput=throughput,
                    pump_rate=pump_rate,
                    pump_unit=pump_unit,
                    hours=hours,
                    ch4_content=ch4_content,
                    control_eff=control_eff,
                    uncertainties=uncertainties
                )

            elif process_type == "indirect_steam":
                heat = self._require_float(flat_inputs, ['quantity', 'amount', 'heat_energy'], "heat energy")
                boiler_eff = self._require_float(flat_inputs, ['boiler_eff', 'boiler_efficiency'], "boiler efficiency fraction (e.g. 0.80)")
                trans_loss = self._optional_fraction(flat_inputs, ['trans_loss', 'transmission_loss'], 0.0)

                return calculator.calculate(
                    heat_energy=heat,
                    ef_co2=emission_factors.get('co2', 0),
                    boiler_efficiency=boiler_eff,
                    transmission_loss=trans_loss,
                    uncertainties=uncertainties,
                    heat_unit=flat_inputs.get('heat_unit', 'btu')
                )

            elif process_type == "stoichiometry":
                fuel_mass = self._require_float(flat_inputs, ['quantity', 'amount', 'fuel_mass'], "fuel mass")
                carbon_content = self._require_float(flat_inputs, ['carbon_content'], "fuel carbon mass fraction (e.g. 0.85)")

                return calculator.calculate(
                    fuel_mass=fuel_mass,
                    carbon_content=carbon_content,
                    uncertainties=uncertainties,
                    mass_unit=unit
                )

            else:
                return self._generic_calculation(flat_inputs, emission_factors, uncertainties, process_type)
                
        except Exception as e:
            # NEW-02 FIX: no longer silently swallow exceptions and return 0 tCO2e
            # Re-raise so the calling route can return a proper 422 to the client.
            from flask import current_app, has_app_context
            if has_app_context():
                current_app.logger.error(
                    f"[Dispatcher] Calculation failed for process_type='{process_type}': {e}",
                    exc_info=True
                )
            else:
                import logging
                logging.error(f"[Dispatcher] Calculation failed for process_type='{process_type}': {e}", exc_info=True)
            raise ValueError(
                f"Calculation error for '{process_type}': {str(e)}"
            ) from e

    def _generic_calculation(self, inputs, emission_factors, uncertainties, process_type='combustion'):
        """Standard Quantity * EF fallback with unit handling and tier-aware uncertainty."""
        quantity = float(inputs.get("quantity") or inputs.get("amount") or 0)
        unit = str(inputs.get("unit") or 'm3').lower()
        f_unit = str(emission_factors.get("unit") or 'kg/m3').lower()
        
        if 'm3' in f_unit or 'm³' in f_unit:
            if unit == 'scf': quantity *= CONVERSIONS['scf_to_m3']
            elif unit in ['mcf', 'mscf']: quantity *= (CONVERSIONS['scf_to_m3'] * 1000.0)
            elif unit == 'mmscf': quantity *= (CONVERSIONS['scf_to_m3'] * 1000000.0)
            elif unit in ['l', 'liter', 'liters']: quantity *= CONVERSIONS['liter_to_m3']
            elif unit == 'gal': quantity *= CONVERSIONS['gal_to_m3']
            elif unit == 'bbl': quantity *= CONVERSIONS['bbl_to_m3']
        # Energy-based normalization (Standard EFs are usually kg/MMBtu)
        elif 'mmbtu' in f_unit:
            hhv = float(inputs.get('hhv') or emission_factors.get('hhv') or 1.0)
            if unit in ['m3', 'm³']: quantity *= CONVERSIONS['m3_to_scf']
            if unit == 'mmscf': quantity *= 1000000.0
            energy_mmbtu = (quantity * hhv) / 1_000_000.0
            quantity = energy_mmbtu
            
        # Calculate raw values (Usually EF is kg/unit)
        co2_ef = float(emission_factors.get("co2") or emission_factors.get("ef_co2") or 0)
        ch4_ef = float(emission_factors.get("ch4") or emission_factors.get("ef_ch4") or 0)
        n2o_ef = float(emission_factors.get("n2o") or emission_factors.get("ef_n2o") or 0)
        co2_val = quantity * co2_ef
        ch4_val = quantity * ch4_ef
        n2o_val = quantity * n2o_ef
        
        # Determine result unit based on factor unit
        is_tonne = 'tonne' in f_unit or ' mt' in f_unit or 'metric ton' in f_unit
        if is_tonne:
            co2_tonnes, ch4_tonnes, n2o_tonnes = co2_val, ch4_val, n2o_val
        else:
            co2_tonnes = co2_val / 1000.0
            ch4_tonnes = ch4_val / 1000.0
            n2o_tonnes = n2o_val / 1000.0

        # Tier-aware uncertainty propagation — 95% CI, non-negative bounds
        _tier = resolve_tier(inputs.get('factor_source') or uncertainties.get('_factor_source', 'default'))
        _cat = PROCESS_CATEGORY.get(str(process_type).lower(), 'combustion')

        def wrap(val, gas):
            return propagate_uncertainty(
                val,
                ef_uncertainty=resolve_ef_uncertainty(_cat, gas, _tier, uncertainties.get(gas)),
                tier=_tier, process_category=_cat, gas=gas
            )

        total_co2e = calculate_co2e(co2_tonnes, ch4_tonnes, n2o_tonnes)
            
        return {
            "results": {
                "co2": wrap(co2_tonnes, "co2"),
                "ch4": wrap(ch4_tonnes, "ch4"),
                "n2o": wrap(n2o_tonnes, "n2o")
            },
            "total_co2e": total_co2e,
            "method": "api2021_generic"
        }

# Global dispatcher instance
dispatcher = CalculationDispatcher()


