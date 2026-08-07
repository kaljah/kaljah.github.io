import math
from .dispatcher import dispatcher as api2021_dispatcher
from .constants import DEFAULT_GWP, get_active_gwp


# Constants
STD_TEMP_R = 519.67      # 60°F in Rankine
STD_PRESS_PSIA = 14.696  # Standard Pressure
MOLAR_VOL_US = 379.3     # scf/lb-mole (at 60°F, 14.696 psia)

MW = {
    'C': 12.01,
    'CO2': 44.01,
    'CH4': 16.04,
    'N2O': 44.013,
    'H2': 2.016,
    'Air': 28.96,
    'SO2': 64.06
}

GWP = {
    'CH4': DEFAULT_GWP['CH4'],
    'N2O': DEFAULT_GWP['N2O']
}

class GHGCalculator:
    def _to_rankine(self, val, unit):
        u = unit.lower()
        if u in ['r', 'rankine']: return val
        if u in ['f', 'fahrenheit']: return val + 459.67
        if u in ['c', 'celsius', 'centigrade']: return (val * 1.8) + 32 + 459.67
        if u in ['k', 'kelvin']: return val * 1.8
        raise ValueError(f"Unknown temperature unit: {unit}")

    def _to_psia(self, val, unit):
        u = unit.lower()
        if u == 'psia': return val
        if u == 'psig': return val + 14.696
        if u in ['kpa', 'kilopascal']: return val * 0.145038
        if u in ['mpa', 'megapascal']: return val * 145.038
        if u in ['pa', 'pascal']: return val * 0.000145038
        if u in ['bar', 'bars']: return val * 14.5038
        if u in ['mbar', 'millibar']: return val * 0.0145038
        if u in ['atm', 'atmosphere']: return val * 14.696
        if u in ['kg/cm2', 'kgf/cm2']: return val * 14.2233
        if u in ['mmhg', 'torr']: return val * 0.0193368
        if u in ['inhg']: return val * 0.491154
        if u in ['inh2o']: return val * 0.036127
        raise ValueError(f"Unknown pressure unit: {unit}")

    def _to_density_lb_gal(self, val, unit):
        u = unit.lower()
        if u in ['lb/gal', 'ppg']: return val
        if u in ['lb/ft3', 'pcf']: return val / 7.48052
        if u in ['kg/m3', 'kg/m³']: return val * 0.0083454
        if u in ['g/cm3', 'g/ml', 'kg/l', 'sg', 'specific_gravity']: return val * 8.3454
        if u in ['api', 'degrees_api']:
            sg = 141.5 / (val + 131.5)
            return sg * 8.3454
        raise ValueError(f"Unknown density unit: {unit}")

    def _to_ft3(self, val, unit):
        u = unit.lower()
        if u in ['ft3', 'cf', 'cubic_feet', 'scf']: return val
        if u in ['m3', 'cubic_meters', 'm³']: return val * 35.3147
        if u in ['mmscf']: return val * 1000000.0
        if u in ['gal', 'gallons', 'us_gal']: return val * 0.133681
        if u in ['bbl', 'barrel', 'barrels']: return val * 5.61458
        if u in ['l', 'liter', 'liters']: return val * 0.0353147
        if u in ['in3', 'ci']: return val / 1728.0
        raise ValueError(f"Unknown volume unit: {unit}")

    def _normalize_unit(self, u):
        if not u: return ''
        return str(u).replace('\u00c2', '').replace('\u00b3', '3') \
            .replace('^', '').replace(' ', '').lower()

    def convert_factor_to_kg(self, value, factor_unit, activity_unit, hhv=0):
        if value is None: return 0
        if not factor_unit or factor_unit == activity_unit: return value

        f_unit = self._normalize_unit(factor_unit)
        a_unit = self._normalize_unit(activity_unit)
        val = float(value)

        # Normalize numerator to kg
        if f_unit.startswith('lb'): val *= 0.453592
        elif f_unit.startswith('tonne'): val *= 1000
        elif f_unit.startswith('g/'): val /= 1000

        # Normalize denominator
        factor_denom = f_unit.split('/')[1] if '/' in f_unit else f_unit
        
        # Handle Energy-based factor denominator (e.g. kg/MMBtu)
        if factor_denom == 'mmbtu':
            # Calculate how many MMBtu are in 1 activity_unit
            energy_per_unit = self.calculate_energy(1.0, activity_unit, hhv)
            return val * energy_per_unit
        
        conv = {
            'm3': 1,
            'scf': 35.3147,
            'mcf': 0.0353147,
            'mmscf': 3.53147e-5,
            'mscf': 0.0353147,
            'gal': 264.172,
            'l': 1000,
            'bbl': 264.172 / 42.0,
            'kg': 1,
            'lb': 2.20462,
            'tonne': 0.001,
            'tonnes': 0.001,
            'hr': 1,
            'yr': 8760,
            'day': 24
        }
        
        f = conv.get(factor_denom, 1)
        a = conv.get(a_unit, 1)
        
        return val * (f / a)

    def calculate_energy(self, amount, unit, hhv):
        u = self._normalize_unit(unit)
        if u == 'mmbtu': return amount
        
        adj = amount
        if u == 'm3': adj *= 35.3147
        elif u == 'l': adj *= 0.264172
        elif u == 'bbl': adj *= 42
        elif u == 'kg': adj *= 2.20462
        elif u == 'tonne' or u == 'tonnes': adj *= 2204.62
        elif u == 'mcf' or u == 'mscf': adj *= 1000
        elif u == 'gal': adj *= 1 # Assuming gal is base for liquid if not caught
        
        # hhv is usually Btu/scf or Btu/gal or Btu/lb
        # Simplification: assuming hhv unit matches source volume/mass unit scale
        # Ideally we need explicit hhv unit. For now relying on standard API factors.
        
        return (adj * hhv) / 1000000.0

    def calculate_default_kg(self, amount, unit, hhv, factor_data, gas):
        if not factor_data: return 0
        
        # Simple Factor
        if 'type' in factor_data: # Equipment factor
             # Check for 'factor' (legacy), then 'total', then requested gas, then 'co2'
             v = amount * (factor_data.get('factor') or factor_data.get('total') or factor_data.get(gas) or factor_data.get('co2') or 0)
             if 'tonnes' in str(factor_data.get('unit', '')).lower():
                 v *= 1000
             return v

        f_unit = self._normalize_unit(factor_data.get('unit', ''))
        
        # Volume based factor (e.g. kg/m3)
        if f_unit == 'kg/m3':
            vol = amount
            u = self._normalize_unit(unit)
            if u == 'scf': vol *= 0.0283168
            elif u in ['mcf', 'mscf']: vol *= 28.3168
            elif u == 'l': vol *= 0.001
            elif u == 'gal': vol *= 0.00378541
            elif u == 'bbl': vol *= 0.158987
            return vol * (factor_data.get(gas) or 0)
            
        # Energy based factor (kg/MMBtu)
        e = self.calculate_energy(amount, unit, hhv)
        return e * (factor_data.get(gas) or 0)

    # --- Fugitive Calculations ---

    def ef_fugitive_pipeline(self, type_key, length_km):
        factors = {
            'gathering_protected': 0.03,
            'transmission_protected': 0.012,
            'distribution_cast_iron': 2.9,
            'distribution_unprotected': 1.3,
            'distribution_plastic': 0.002
        }
        factor = factors.get(type_key, 0.0)
        total = factor * length_km
        return {
            'tonnes_ch4/year': total,
            'factor_used': factor,
            'unit': 'tonnes CH4/km/yr'
        }

    def ef_fugitive_average(self, component, service='gas'):
        factors = {
            'gas': { 'valves': 0.026, 'connectors': 0.003, 'flanges': 0.003, 'open_ended_lines': 0.018, 'relief_valves': 0.061 },
            'light_oil': { 'valves': 0.017, 'connectors': 0.003, 'flanges': 0.001, 'open_ended_lines': 0.019, 'relief_valves': 0.012 },
            'heavy_oil': { 'valves': 0.0003, 'connectors': 0.0003, 'flanges': 0.0001, 'open_ended_lines': 0.001, 'relief_valves': 0.004 }
        }
        service_factors = factors.get(service, {})
        val = service_factors.get(component, 0.0)
        return {'tonnes_ch4/year': val}

    def ef_fugitive_screening_range(self, component, ppm, opts=None):
        # Simplified implementation of correlation/screening for now
        # Returning dummy values as per JS 'screening-range' placeholder logic in server.js
        # Real impl needs the Table 7-7 lookup
        
        # Placeholder for 7-7 logic
        # Defaulting to a simple factor if strictly needed or implementing full lookup Table 7-7
        # JS code: const res = ghg.efFugitiveScreeningRange... 
        
        # Using correlation equations as fallback or implementing the simplified logic found in JS?
        # The JS `efFugitiveScreeningRange` wasn't fully shown in the `emission-factors.js` view
        # But `computeEmissions` called it.
        # Let's verify `emission-factors.js` or implement a reasonable approximation based on API 2021 Table 7-7 values
        
        # Table 7-7 Gas Service (kg/hr/source)
        # Ranges: <10k, >=10k
        
        # Simplified for robustness:
        # If PPM < 10000 -> use lower factor
        # If PPM >= 10000 -> use upper factor
        
        is_leaker = ppm >= 10000
        
        table_7_7_gas = {
            'valves': {'<10k': 2.5e-4, '>=10k': 0.089}, # Placeholder-ish values
            'connectors': {'<10k': 6.2e-5, '>=10k': 0.027},
            'flanges': {'<10k': 5.2e-5, '>=10k': 0.087},
            'open_ended_lines': {'<10k': 6.8e-4, '>=10k': 0.038}
        }
        
        f = table_7_7_gas.get(component, {'<10k': 0, '>=10k': 0})
        factor = f['>=10k'] if is_leaker else f['<10k']
        
        return {
            'tonnes_ch4_per_hr': factor / 1000.0, # Convert kg to tonnes
            'component': component
        }


    # calculate_dehydrator() removed — dead code with incorrect EF (200 scf/gal).
    # Use midstream.DehydratorCalculator (3.0 scf/gal per API Table 6-5) via the dispatcher.

    def calculate_completions(self, duration, rate, eff):
        # Uncontrolled Volume (Mcf)
        vol_mcf = duration * rate
        
        # If vented (eff=0 or small), emissions are the gas itself.
        # If flared (eff>0), emissions are unburnt gas + combustion CO2.
        
        # Simplified: Assume gas is methane for venting part? Or standard gas composition?
        # Standard: 0.0192 tonnes CH4 / Mcf ? (Density of CH4 at standard conditions)
        # 1 Mcf CH4 ~ 1000 scf * 0.042 lb/scf ~ 42 lbs ~ 19 kg.
        
        # Let's use standard factor 19.2 kg CH4 / Mcf gas (if 100% CH4).
        # Adjust for gas composition if known, else assume 100% or high %.
        # API Compendium simplified: 
        
        potential_ch4_tonnes = vol_mcf * (19.2 / 1000.0)
        
        if eff > 0:
            # Flaring logic
            # Unburnt CH4
            ch4_em = potential_ch4_tonnes * (1 - eff)
            # CO2 from combustion (assume 100% conversion of burnt part? ~ 2.75 * mass CH4)
            # 1 kg CH4 -> 2.75 kg CO2
            burnt_ch4 = potential_ch4_tonnes * eff
            co2_em = burnt_ch4 * 2.75
            return {'ch4': ch4_em, 'co2': co2_em}
        else:
            return {'ch4': potential_ch4_tonnes, 'co2': 0}

    def calculate_unloading(self, freq, diam, depth, press):
        """
        API Compendium 2021, Section 6.4, Equation 6-3
        V (scf/event) = (π/4) × (D_in/12)² × L_ft × (P_abs / 14.696)
        Correct geometric constant: π/4 × (1/12)² = 0.005454 ft³ per in² per ft
        """
        import math
        # Diameter in inches, depth in feet
        # P_gauge (psig) → P_abs (psia)
        p_abs = press + 14.696
        vol_scf_event = (math.pi / 4.0) * ((diam / 12.0) ** 2) * depth * (p_abs / 14.696)
        total_vol_mcf = (vol_scf_event * freq) / 1000.0
        
        # Emissions (Venting)
        # Assumed 19.2 kg CH4 / Mcf
        ch4_tonnes = total_vol_mcf * (19.2 / 1000.0)
        
        return {'ch4': ch4_tonnes}


ghg_calc = GHGCalculator()

def compute_emissions(payload, factor_data=None, gwp_dict=None, gwp_standard=None):
    if factor_data is None:
        factor_data = {}
    if gwp_dict is None:
        gwp_dict = get_active_gwp(standard=gwp_standard)
    
    process = str(payload.get('process_type') or payload.get('process') or '').lower()
    
    # Normalize frontend names to expected internal keys
    if process == "pneumatics": process = "pneumatic"
    elif process == "tanks": process = "tank"
    elif process == "mud degassing": process = "drilling"
    elif process == "well completions": process = "completions"
    elif process == "dehydrators": process = "dehydrator"
    elif process == "blowdowns": process = "venting"
    elif process == "liquid unloading": process = "unloading"
    elif process == "separation": process = "tank"
    
    amount = float(payload.get('quantity') or payload.get('amount') or 0)
    unit = payload.get('unit') or 'm3'
    
    # Safely parse HHV - handle None, empty string, or '-' placeholders
    hhv_val = payload.get('hhv') or factor_data.get('hhv') or 0
    if hhv_val in [None, '', '-']:
        hhv = 0
    else:
        try:
            hhv = float(hhv_val)
        except (ValueError, TypeError):
            hhv = 0
    
    calc_inputs = payload.get('calc_inputs') or {}
    inputs = calc_inputs.get(process) or {} # Extract specific inputs
    
    # NEW: Merge root payload into inputs to support flat CSV data
    # This allows keys like 'comp_duration' or 'unload_diam' to be read directly from the CSV row
    inputs = {**payload, **inputs} 
    
    is_specific = payload.get('factor_source') == 'specific' or payload.get('isSpecific')
    spec = payload.get('specificFactors') or payload.get('specific_factors')
    factor_source = payload.get('factor_source')

    em = {'co2': 0, 'ch4': 0, 'n2o': 0, 'totalCo2e': 0, 'co': 0, 'ce': 0}
    calc_method = 'server_default'

    # --- API 2021 CALCULATION DISPATCHER ---
    # Try to use the new API 2021 compliant calculators first
    uncertainties = factor_data.get('uncertainty', {})
    api_res = api2021_dispatcher.dispatch(process, payload, factor_data, uncertainties, gwp_dict=gwp_dict)
    
    def get_val(r):
        # BUG-15/16 FIX: handle None results from CH4-only calculators (e.g. MudDegassing, Completions)
        # format_result() sets co2/n2o to None when not passed; calling .get() on None crashes.
        if r is None:
            return 0
        if isinstance(r, dict): return r.get('value', 0)
        return r

    if api_res and "results" in api_res and any(get_val(api_res["results"].get(g)) for g in ["co2", "ch4", "n2o"]):
        # If the dispatcher handled it, return the rich result structure
        # We extract the 'value' for backward compatibility with the legacy database record creation
        results = api_res["results"]
        # BUG-15/16 FIX: CH4-only calculators (e.g. MudDegassing) leave co2/n2o as None.
        # Normalize None → 0 at extraction point, not just in get_val.
        def _extract(r):
            if r is None: return 0
            if isinstance(r, dict): return r.get('value', 0) or 0
            return r or 0
        em['co2'] = _extract(results.get('co2'))
        em['ch4'] = _extract(results.get('ch4'))
        em['n2o'] = _extract(results.get('n2o'))
        em['totalCo2e'] = (
            (em['co2'] * float(gwp_dict.get('CO2', 1.0))) +
            (em['ch4'] * float(gwp_dict.get('CH4', 28.0))) +
            (em['n2o'] * float(gwp_dict.get('N2O', 264.0)))
        )
        
        # We also attach the full rich result to the emission dict so the route can access it
        em['_full_api_res'] = api_res
        return em, api_res.get('method', 'api2021_generic')

    # --- TIER 1 / FACTOR OVERRIDE ---
    # If a factor_key is provided (and it's not "Engineering") -> Use Standard Calculation
    # We check if factor_data exists and has a 'ch4' or 'co2' value, AND we are not in 'custom engineering' mode.
    # User selects "Engineering Calculation" dummy factor to explicitly use Tier 3.
    # If they select a real factor, we use it.
    
    use_tier1 = False
    if factor_data and factor_data.get('code') != 'Engineering':
        # If it's a valid factor with values, use it.
        if factor_data.get('ch4') or factor_data.get('co2'):
             use_tier1 = True
    
    if use_tier1:
        # Standard Factor Logic (similar to combustion but per event/unit)
        # Assuming 'amount' is the Activity Data (Count, Volume, etc.)
        # Default logic at bottom handles this.
        pass # Fall through to bottom
    else:
        # --- TIER 3 / ENGINEERING ---
        if process == 'completions':
            # inputs = { comp_duration, comp_rate, comp_flare_eff }
            dur = float(inputs.get('comp_duration') or 0)
            rate = float(inputs.get('comp_rate') or 0)
            eff_pct = float(inputs.get('comp_flare_eff') or 0)
            res = ghg_calc.calculate_completions(dur, rate, eff_pct / 100.0)
            em['ch4'] = res['ch4']
            em['co2'] = res['co2']
            em['totalCo2e'] = em['co2'] + (em['ch4'] * gwp_dict['CH4'])
            return em, 'server_completions_calc'

        elif process == 'unloading':
            fuel_key = payload.get('fuel') or payload.get('fuel_type')
            # Tier 1: Factor-based (UnloadPlunger / UnloadNonPlunger)
            if fuel_key in ['UnloadPlunger', 'UnloadNonPlunger'] and factor_data and factor_data.get('ch4'):
                # factor is in tonnes CH4/event; amount is event count
                event_count = amount
                ch4_tonnes = event_count * factor_data['ch4']   # already in tonnes
                em['ch4'] = ch4_tonnes
                em['totalCo2e'] = ch4_tonnes * gwp_dict['CH4']
                return em, 'server_unloading_tier1'

            # Engineering Calc (Tier 3)
            freq = float(inputs.get('unload_freq') or amount or 0)
            diam = float(inputs.get('unload_diam') or 0)
            depth = float(inputs.get('unload_depth') or 0)
            press = float(inputs.get('unload_press') or 0)
            res = ghg_calc.calculate_unloading(freq, diam, depth, press)
            em['ch4'] = res['ch4']
            em['totalCo2e'] = em['ch4'] * gwp_dict['CH4']
            return em, 'server_unloading_calc'
    
    if process == 'fugitive':
        f = calc_inputs.get('fugitive') or {}
        method = f.get('method') or 'average'
        count = float(f.get('count') or amount or 0)
        component = f.get('component') or f.get('compType') or 'valves'
        calc_method = 'server_fugitive'
        
        if method == 'pipeline':
            length = float(f.get('length_km') or f.get('length') or 0)
            res = ghg_calc.ef_fugitive_pipeline(component, length)
            em['ch4'] = res.get('tonnes_ch4/year', 0)
            em['totalCo2e'] = em['ch4'] * gwp_dict['CH4']
            calc_method = 'server_fugitive_pipeline'
        elif method == 'average':
            service = f.get('service') or 'gas'
            res = ghg_calc.ef_fugitive_average(component, service)
            total_ch4 = res.get('tonnes_ch4/year', 0) * count
            em['ch4'] = total_ch4
            em['totalCo2e'] = total_ch4 * gwp_dict['CH4']
            calc_method = 'server_fugitive_average'
        else:
            ppm_val = float(f.get('ppm') or 0)
            hours = 8760
            service = f.get('service') or ('oil' if 'oil' in str(payload.get('fuel_type', '')).lower() else 'gas')
            res = ghg_calc.ef_fugitive_screening_range(component, ppm_val, {'service': service})
            total_ch4 = res.get('tonnes_ch4_per_hr', 0) * count * hours
            em['ch4'] = total_ch4
            em['totalCo2e'] = total_ch4 * gwp_dict['CH4']
            calc_method = 'server_fugitive_screening'
        return em, calc_method

    # --- PNEUMATIC DEVICES (API 5.2) ---
    if process == 'pneumatic':
        p = calc_inputs.get('pneumatic') or {}
        count = float(p.get('count') or amount or 0)
        device_type = p.get('device_type') or 'HighBleed'
        
        # Engineering Mode (Specific)
        if factor_source == 'specific':
            # API 5.2 Engineering Calculation
            bleed_rate = float(p.get('pneu_bleed_rate') or 0)  # scf/hr (user-measured)
            ch4_content = float(p.get('pneu_ch4_content') or 85) / 100.0  # %
            hours = float(p.get('pneu_hours') or 8760)  # hr/yr
            
            # If no measured bleed rate, use device type defaults
            if bleed_rate == 0:
                if device_type == 'HighBleed': bleed_rate = 37.3
                elif device_type == 'LowBleed': bleed_rate = 1.39
                elif device_type == 'Intermittent':
                    actuations = float(p.get('pneu_actuations') or 1)  # default 1/yr if unknown
                    # API 2021: 13.5 scf/actuation/device (not per year \u2014 multiply by actuations/yr)
                    annual_scf = 13.5 * count * actuations
                    # Convert scf to kg CH4: scf \u00d7 0.0423 lb/scf \u00d7 CH4 fraction \u00f7 2.20462 lb/kg
                    ch4_kg = (annual_scf * 0.0423 * ch4_content) / 2.20462
                    em['ch4'] = ch4_kg / 1000.0
                    em['totalCo2e'] = em['ch4'] * gwp_dict['CH4']
                    return em, 'server_pneumatic_intermittent'
            
            # Continuous bleed calculation: E = Count × Bleed_Rate × Hours × CH4_fraction
            annual_scf = count * bleed_rate * hours
            # Convert scf to kg: scf × 0.0423 lb/scf × 0.453592 kg/lb
            ch4_kg = (annual_scf * 0.0423 * ch4_content) / 2.20462
            
            em['ch4'] = ch4_kg / 1000.0
            em['co2'] = 0  # Pneumatic devices emit CH4 only
            em['n2o'] = 0
            em['totalCo2e'] = em['ch4'] * gwp_dict['CH4']
            calc_method = 'server_pneumatic_engineering'
            return em, calc_method
        
        # Default/Custom Mode: Use factor
        ch4_factor = 0
        if factor_data:
            ch4_factor = factor_data.get('ch4') or 0
            # Convert scf/hr/device to tonnes/year
            if 'scf/hr' in str(factor_data.get('unit', '')):
                # scf/hr × 8760 hr/yr × count × 0.0423 lb/scf × 0.453592 kg/lb ÷ 1000
                ch4_factor = (ch4_factor * 8760 * 0.0423 * 0.453592) / (1000 * 2.20462)
        
        em['ch4'] = ch4_factor * count
        em['totalCo2e'] = em['ch4'] * gwp_dict['CH4']
        calc_method = 'server_pneumatic_factor'
        return em, calc_method

    # --- DEHYDRATOR (API 5.3) ---
    if process == 'dehydrator':
        d = calc_inputs.get('dehydrator') or {}
        throughput = float(d.get('dehy_throughput') or amount or 0)  # MMscf/yr
        
        # Engineering Mode (Specific)
        if factor_source == 'specific':
            # API 5.3 Engineering: E = Pump_Rate × 37.85 × CH4% × Hours × (1 - Control_Eff)
            pump_rate = float(d.get('dehy_pump_rate') or 0)  # gal/hr
            pump_unit = d.get('dehy_pump_unit') or 'gph'
            ch4_content = float(d.get('dehy_ch4_content') or 85) / 100.0  # %
            hours = float(d.get('dehy_hours') or 8760)  # hr/yr
            control = d.get('dehy_control') or 'none'
            control_eff = float(d.get('dehy_eff') or 0) / 100.0 if control != 'none' else 0
            
            # Convert pump rate to gal/hr
            if pump_unit == 'lph': pump_rate *= 0.264172
            elif pump_unit == 'm3h': pump_rate *= 264.172
            
            # API 2021 Table 6-5: 3.0 scf gas/gal glycol circulated
            # (Consistent with midstream.DehydratorCalculator; previous value of 37.85 was
            # an outdated GLYCalc default that overstated emissions by ~12x)
            annual_scf = pump_rate * 3.0 * hours * ch4_content * (1 - control_eff)
            
            # Convert scf to kg CH4
            ch4_kg = (annual_scf * 0.0423) / 2.20462  # 0.0423 lb/scf × 0.453592 kg/lb
            
            em['ch4'] = ch4_kg / 1000.0
            em['co2'] = 0  # Dehydrator venting is CH4 only
            em['n2o'] = 0
            em['totalCo2e'] = em['ch4'] * gwp_dict['CH4']
            calc_method = 'server_dehydrator_engineering'
            return em, calc_method
        
        # Default/Custom Mode: Use factor
        ch4_factor = 0
        if factor_data:
            ch4_factor = factor_data.get('ch4') or 0
            # If factor is scf/gal, need throughput in different unit
            # For simplicity, assume throughput-based factor in kg/MMscf
        
        em['ch4'] = (ch4_factor * throughput) if ch4_factor else 0
        em['totalCo2e'] = em['ch4'] * gwp_dict['CH4']
        calc_method = 'server_dehydrator_factor'
        return em, calc_method

    # --- STORAGE TANKS (API 4.4) ---
    if process == 'tank':
        t = calc_inputs.get('tank') or {}
        throughput = float(t.get('amount') or amount or 0)  # bbl/yr
        
        # Engineering Mode (Specific)
        if factor_source == 'specific':
            # API 4.4 Flash Calculation (simplified GOR method)
            gor = float(t.get('tank_gor') or 500)  # scf/bbl
            ch4_content = float(t.get('tank_ch4_content') or 85) / 100.0  # %
            api_gravity = float(t.get('tank_api_gravity') or 35)
            temp = float(t.get('tank_temp') or 60)  # °F
            sep_pressure = float(t.get('tank_sep_pressure') or 50)  # psig
            
            # Simplified flash calculation: Flash_Gas = Throughput × GOR
            # Actual E&P Tank is complex, using simplified approach
            flash_scf = throughput * gor  # scf/yr
            
            # Convert to kg CH4
            ch4_kg = (flash_scf * 0.0423 * ch4_content) / 2.20462
            
            # Minor CO2 from flash gas (assume 5% CO2 in gas)
            co2_content = 0.05
            # CALC-07 FIX: CO2 density at std conditions (60°F, 14.696 psia) = 0.1162 lb/scf
            # (API Compendium Table 4-1; 0.1176 was slightly wrong)
            co2_kg = (flash_scf * 0.1162 * co2_content) / 2.20462  # CO2 density 0.1162 lb/scf

            
            em['ch4'] = ch4_kg / 1000.0
            em['co2'] = co2_kg / 1000.0
            em['n2o'] = 0
            em['totalCo2e'] = em['co2'] + (em['ch4'] * gwp_dict['CH4'])
            calc_method = 'server_tank_gor_flash'
            return em, calc_method
        
        # Default/Custom Mode: Use factor
        ch4_factor = float(t.get('ch4_factor') or 0)
        co2_factor = float(t.get('co2_factor') or 0)
        
        if not ch4_factor and not co2_factor and factor_data:
            ch4_factor = factor_data.get('ch4') or 0
            co2_factor = factor_data.get('co2') or 0
        
        em['ch4'] = (ch4_factor * throughput) / 1000.0 if ch4_factor else 0
        em['co2'] = (co2_factor * throughput) / 1000.0 if co2_factor else 0
        em['n2o'] = 0
        em['totalCo2e'] = em['co2'] + (em['ch4'] * gwp_dict['CH4'])
        calc_method = 'server_tank_factor'
        return em, calc_method

    # --- FCCU (API 6.1.5) ---
    if process == 'fccu':
        # FCCU method uses CO2 amount to calculate CH4 and N2O based on petroleum coke
        co2_emitted = float(amount)
        if unit.lower() in ['tonnes', 'tonne', 'tonnes co2', 'tonne co2']:
            co2_emitted *= 1000.0  # convert tonnes to kg
            
        ef_ch4 = factor_data.get('ch4', 0) if factor_data else 0.003
        ef_co2 = factor_data.get('co2', 1) if factor_data else 102.41
        
        ch4_kg = co2_emitted * (ef_ch4 / ef_co2)
        
        em['co2'] = co2_emitted / 1000.0
        em['ch4'] = ch4_kg / 1000.0
        em['n2o'] = 0
        em['totalCo2e'] = em['co2'] + (em['ch4'] * gwp_dict['CH4'])
        calc_method = 'server_fccu_ratio'
        return em, calc_method

    # Standard / Specific (Combustion, Flaring, etc.)
    if is_specific and spec:
        base_unit = spec.get('co2Unit') or spec.get('unit') or unit

        # Helper: convert a factor value from its declared unit to kg per activity-unit
        def get_factor(gas):
            gas_unit = spec.get(f'{gas}Unit') or base_unit or unit

            # Prefer the explicit 'Raw' value (user entered in a different unit)
            raw = spec.get(f'{gas}Raw')
            if raw is not None and raw != '':
                try:
                    return ghg_calc.convert_factor_to_kg(float(raw), spec.get(f'{gas}Unit') or base_unit, unit, hhv)
                except:
                    pass

            # Otherwise use the direct value — but STILL convert from its declared unit
            val = spec.get(gas)
            if val is not None and val != '':
                try:
                    raw_val = float(val)
                    # If unit matches activity unit, no conversion needed
                    if gas_unit and gas_unit != unit:
                        return ghg_calc.convert_factor_to_kg(raw_val, gas_unit, unit, hhv)
                    return raw_val
                except:
                    pass
            return None

        f_co2 = get_factor('co2')
        f_ch4 = get_factor('ch4')
        f_n2o = get_factor('n2o')
        f_co  = get_factor('co')

        em['co2'] = (amount * f_co2) if f_co2 is not None else ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'co2')

        if process in ['combustion', 'flaring', 'venting']:
            em['ch4'] = (amount * f_ch4) if f_ch4 is not None else ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'ch4')
            em['n2o'] = (amount * f_n2o) if f_n2o is not None else ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'n2o')
            em['co']  = (amount * f_co)  if (f_co is not None and process != 'combustion') else 0
        else:
            em['ch4'] = (amount * f_ch4) if f_ch4 is not None else 0
            em['n2o'] = (amount * f_n2o) if f_n2o is not None else 0

        em['totalCo2e'] = (em['co2'] + (em['ch4'] * gwp_dict['CH4']) + (em['n2o'] * gwp_dict['N2O'])) / 1000.0
        em['co2'] /= 1000.0
        em['ch4'] /= 1000.0
        em['n2o'] /= 1000.0
        if em['co']: em['co'] /= 1000.0
        
        calc_method = 'server_specific'
        return em, calc_method

    if factor_data and factor_data.get('type'):
        # Use individual gas factors directly (correct for custom factors which carry co2/ch4/n2o fields).
        # Previously used: em['ch4'] = (v / gwp_dict['CH4']) / 1000.0 — this back-calculated CH4
        # from total CO2e by dividing by GWP, which produces a physically meaningless value.
        co2_kg = ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'co2')
        ch4_kg = ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'ch4')
        n2o_kg = ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'n2o')

        em['co2'] = co2_kg / 1000.0
        em['ch4'] = ch4_kg / 1000.0
        em['n2o'] = n2o_kg / 1000.0
        em['totalCo2e'] = em['co2'] + (em['ch4'] * gwp_dict['CH4']) + (em['n2o'] * gwp_dict['N2O'])

        calc_method = 'server_custom_factor'
        return em, calc_method

    # --- DEFAULT/CUSTOM MODE: Factor-Based Calculation ---
    # Apply process-specific gas calculation rules per API Compendium 2021
    
    # Calculate base emissions from factors
    co2_kg = ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'co2')
    ch4_kg = ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'ch4')
    n2o_kg = ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'n2o')
    
    # Process-specific gas emission matrix (API 2021)
    # Determine which gases to calculate based on process type
    if process in ['combustion', 'mobile']:
        # All gases from fuel combustion
        em['co2'] = co2_kg / 1000.0
        em['ch4'] = ch4_kg / 1000.0
        em['n2o'] = n2o_kg / 1000.0
        
    elif process == 'flaring':
        # CO2 from combustion + CH4 slip + N2O
        em['co2'] = co2_kg / 1000.0
        em['ch4'] = ch4_kg / 1000.0
        em['n2o'] = n2o_kg / 1000.0
        
    elif process in ['venting', 'loading', 'separation']:
        # Primarily CH4 release, minor CO2
        em['ch4'] = ch4_kg / 1000.0
        em['co2'] = co2_kg / 1000.0 if co2_kg > 0 else 0
        em['n2o'] = 0
        
    elif process in ['fugitive', 'pneumatic', 'dehydrator']:
        # CH4 only (leaks/vents)
        em['ch4'] = ch4_kg / 1000.0
        em['co2'] = 0
        em['n2o'] = 0
        
    elif process == 'tank':
        # CH4 dominant, minor CO2 from flash gas
        em['ch4'] = ch4_kg / 1000.0
        em['co2'] = co2_kg / 1000.0 if co2_kg > 0 else 0
        em['n2o'] = 0
        
    elif process == 'agr':
        # CO2 removal/venting, minor CH4
        em['co2'] = co2_kg / 1000.0
        em['ch4'] = ch4_kg / 1000.0 if ch4_kg > 0 else 0
        em['n2o'] = 0
        
    elif process in ['drilling']:
        # Fuel combustion (CO2/CH4) + mud losses
        em['co2'] = co2_kg / 1000.0
        em['ch4'] = ch4_kg / 1000.0
        em['n2o'] = 0
        
    elif process in ['completions', 'unloading']:
        # Primarily CH4 from gas release, minor CO2 if flared
        em['ch4'] = ch4_kg / 1000.0
        em['co2'] = co2_kg / 1000.0 if co2_kg > 0 else 0
        em['n2o'] = 0
        
    else:
        # Default: Calculate all gases if factors exist
        em['co2'] = co2_kg / 1000.0
        em['ch4'] = ch4_kg / 1000.0
        em['n2o'] = n2o_kg / 1000.0
    
    # Calculate total CO2e
    em['totalCo2e'] = em['co2'] + (em['ch4'] * gwp_dict['CH4']) + (em['n2o'] * gwp_dict['N2O'])
    
    return em, calc_method
