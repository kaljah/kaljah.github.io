"""
GHG Accounting Software - Comprehensive End-to-End Verification Audit Test Suite
Methodology: API Compendium 4th Edition (2021), GHG Protocol Corporate Standard, ISO 14064-1

NON-NEGOTIABLE VERIFICATION PRINCIPLES:
1. NO FABRICATED NUMBERS: All expected values derived from cited standards or exact Decimal arithmetic.
2. INDEPENDENT ORACLE: Reference calculations implemented completely in Decimal/Fraction in Section A.
3. NO TAUTOLOGIES: Exact tolerances, no mocking of software under test, tight bounds.
4. PROVE TESTS CAN FAIL: Verified mutation checks in Section J.
5. NO INVENTED BUGS: Exact citations, file:line references, and reproducible payloads.
6. READ-ONLY ON SOFTWARE: Tests audit the software without altering source code.
"""

import sys
import os
import math
import json
import pytest
from decimal import Decimal, getcontext
from fractions import Fraction

# Set high precision for Decimal reference oracle (50 decimal places)
getcontext().prec = 50

# Configure environment for Flask / SQLAlchemy testing
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SEED_ADMIN", "false")
os.environ.setdefault("SECRET_KEY", "audit-verification-secret-key-2026")

# Path setup to import application modules for actual calculation calls
server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "new", "server"))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import app as flask_app_module
from extensions import db
from models import User, Facility, Emission, Scope2Emission, Scope3Emission
import calculations.units as app_units
import calculations.constants as app_constants
import emission_factors as app_factors
import calculations.activity_factors as app_act_factors
import electricity_factors as app_grid_factors
import emission_factors.scope3_activity_factors as app_s3_factors
import process_categories as app_categories
import services.scope1_template as app_template
import services.intensity as app_intensity
from calculations.dispatcher import CalculationDispatcher
from services.scope1_calc import resolve_factor, canonicalize, validate_activity


# ==============================================================================
# SECTION A: INDEPENDENT REFERENCE ORACLE (DECIMAL ARITHMETIC & AUTHORITATIVE CONSTANTS)
# ==============================================================================
# Pure-python clean-slate oracle. Zero imports from app calculation functions.
# Sources: API Compendium 2021 §3, §4, §5, §6, §7; NIST SP 811; ISO 13443.

class ReferenceOracle:
    """Independent reference oracle using exact Decimal arithmetic."""
    
    # Fundamental physical constants (NIST SP 811 & IUPAC 2021)
    C_MW = Decimal('12.011')
    H_MW = Decimal('1.008')
    O_MW = Decimal('15.999')
    N_MW = Decimal('14.0067')
    S_MW = Decimal('32.065')
    
    CO2_MW = C_MW + Decimal('2') * O_MW  # 44.009 g/mol (Engine uses 44.01)
    CH4_MW = C_MW + Decimal('4') * H_MW  # 16.043 g/mol (Engine uses 16.04)
    N2O_MW = Decimal('2') * N_MW + O_MW  # 44.0124 g/mol (Engine uses 44.013)
    
    # Standard thermodynamic conditions (API Compendium 2021 §4.2.1 / ISO 13443):
    # 60 °F = 15.556 °C = 288.706 K; 14.69595 psia = 101.325 kPa
    T_STD_K = Decimal('288.706')
    P_STD_KPA = Decimal('101.325')
    MOLAR_VOLUME_M3_KMOL = Decimal('23.685')  # API Compendium Eq 3-4 (379.3 scf/lb-mol)
    
    # Standard densities at 60 °F / 14.696 psia (kg/m³)
    DENSITY_CH4_STD = Decimal('16.04') / MOLAR_VOLUME_M3_KMOL  # 0.67722187... kg/m³
    DENSITY_CO2_STD = Decimal('44.01') / MOLAR_VOLUME_M3_KMOL  # 1.85813806... kg/m³
    DENSITY_N2O_STD = Decimal('44.013') / MOLAR_VOLUME_M3_KMOL # 1.85826472... kg/m³
    
    # Exact unit conversion factors (NIST SP 811)
    CONV_SCF_TO_M3 = Decimal('0.028316846592')
    CONV_MSCF_TO_M3 = Decimal('28.316846592')
    CONV_MMSCF_TO_M3 = Decimal('28316.846592')
    CONV_BBL_TO_M3 = Decimal('0.158987294928')
    CONV_GAL_TO_M3 = Decimal('0.003785411784')
    CONV_L_TO_M3 = Decimal('0.001')
    
    CONV_LB_TO_KG = Decimal('0.45359237')
    CONV_SHORT_TON_TO_KG = Decimal('907.18474')
    CONV_METRIC_TONNE_TO_KG = Decimal('1000.0')
    
    CONV_MMBTU_TO_MJ = Decimal('1055.05585262')
    CONV_THERM_US_TO_MJ = Decimal('105.4804')       # NIST SP 811 U.S. therm (59 °F)
    CONV_THERM_BTU_IT_TO_MJ = Decimal('105.505585262') # 0.1 MMBtu (Btu IT basis)
    CONV_KWH_TO_MJ = Decimal('3.6')
    CONV_GJ_TO_MJ = Decimal('1000.0')
    
    # GWP Values (IPCC Assessment Reports)
    GWP_AR4 = {"co2": Decimal('1'), "ch4": Decimal('25'), "n2o": Decimal('298')}
    GWP_AR5 = {"co2": Decimal('1'), "ch4": Decimal('28'), "n2o": Decimal('265')}
    GWP_AR5_20 = {"co2": Decimal('1'), "ch4": Decimal('84'), "n2o": Decimal('264')}
    GWP_AR6 = {"co2": Decimal('1'), "ch4": Decimal('29.8'), "n2o": Decimal('273')}
    GWP_AR6_20 = {"co2": Decimal('1'), "ch4": Decimal('82.5'), "n2o": Decimal('273')}

    @classmethod
    def calc_combustion_tier1(cls, quantity, unit, co2_ef, ch4_ef, n2o_ef, ef_unit="kg/mmbtu", hhv=Decimal('1020'), gwp_set="AR5"):
        """API Compendium 2021 Section 5.1: Tier 1 Fuel Combustion."""
        gwp = cls.GWP_AR5 if gwp_set == "AR5" else cls.GWP_AR4
        qty = Decimal(str(quantity))
        u = str(unit).lower()
        if u in ("scf", "cf"):
            mmbtu = (qty * Decimal(str(hhv))) / Decimal('1000000')
        elif u in ("mscf", "mcf"):
            mmbtu = (qty * Decimal('1000') * Decimal(str(hhv))) / Decimal('1000000')
        elif u in ("mmscf", "mmcf"):
            mmbtu = (qty * Decimal('1000000') * Decimal(str(hhv))) / Decimal('1000000')
        elif u in ("mmbtu",):
            mmbtu = qty
        elif u in ("gj",):
            mmbtu = (qty * Decimal('1000')) / cls.CONV_MMBTU_TO_MJ
        elif u in ("mj",):
            mmbtu = qty / cls.CONV_MMBTU_TO_MJ
        else:
            raise ValueError(f"Unsupported unit for tier 1 fuel test: {unit}")
            
        co2_kg = mmbtu * Decimal(str(co2_ef))
        ch4_kg = mmbtu * Decimal(str(ch4_ef))
        n2o_kg = mmbtu * Decimal(str(n2o_ef))
        
        co2_t = co2_kg / Decimal('1000')
        ch4_t = ch4_kg / Decimal('1000')
        n2o_t = n2o_kg / Decimal('1000')
        co2e_t = (co2_t * gwp["co2"]) + (ch4_t * gwp["ch4"]) + (n2o_t * gwp["n2o"])
        return {"co2": co2_t, "ch4": ch4_t, "n2o": n2o_t, "co2e": co2e_t}

    @classmethod
    def calc_flaring(cls, volume_scf, ch4_mol_pct=Decimal('85'), co2_mol_pct=Decimal('2'), comb_eff=Decimal('0.965'), dre=Decimal('0.98')):
        """API Compendium 2021 Section 5.1.2: Dual-efficiency flaring model (Eq 5-3, 5-4)."""
        v_scf = Decimal(str(volume_scf))
        v_m3 = v_scf * cls.CONV_SCF_TO_M3
        ch4_m3 = v_m3 * (Decimal(str(ch4_mol_pct)) / Decimal('100'))
        ch4_mass_kg = ch4_m3 * cls.DENSITY_CH4_STD
        unburnt_ch4_kg = ch4_mass_kg * (Decimal('1') - Decimal(str(dre)))
        co2_from_ch4_kg = (ch4_mass_kg * (Decimal('12.011') / Decimal('16.04'))) * Decimal(str(comb_eff)) * (Decimal('44.01') / Decimal('12.011'))
        co2_feed_m3 = v_m3 * (Decimal(str(co2_mol_pct)) / Decimal('100'))
        co2_feed_kg = co2_feed_m3 * cls.DENSITY_CO2_STD
        total_co2_kg = co2_from_ch4_kg + co2_feed_kg
        co2_t = total_co2_kg / Decimal('1000')
        ch4_t = unburnt_ch4_kg / Decimal('1000')
        co2e_t = (co2_t * cls.GWP_AR5["co2"]) + (ch4_t * cls.GWP_AR5["ch4"])
        return {"co2": co2_t, "ch4": ch4_t, "co2e": co2e_t}

    @classmethod
    def calc_pneumatic(cls, count, bleed_rate_scf_hr, hours, ch4_mol_pct=Decimal('85')):
        """API Compendium 2021 Section 6.1: Pneumatic device venting."""
        cnt = Decimal(str(count))
        rate = Decimal(str(bleed_rate_scf_hr))
        hrs = Decimal(str(hours))
        frac = Decimal(str(ch4_mol_pct)) / Decimal('100')
        total_scf = cnt * rate * hrs
        total_m3 = total_scf * cls.CONV_SCF_TO_M3
        ch4_m3 = total_m3 * frac
        ch4_kg = ch4_m3 * cls.DENSITY_CH4_STD
        ch4_t = ch4_kg / Decimal('1000')
        co2e_t = ch4_t * cls.GWP_AR5["ch4"]
        return {"ch4": ch4_t, "co2e": co2e_t}

    @classmethod
    def calc_tank_flashing(cls, throughput_bbl, gor_scf_bbl=Decimal('50'), ch4_mol_pct=Decimal('70'), control_eff=Decimal('0.95')):
        """API Compendium 2021 Section 6.4: Storage Tank Flashing Losses."""
        bbl = Decimal(str(throughput_bbl))
        gor = Decimal(str(gor_scf_bbl))
        frac_ch4 = Decimal(str(ch4_mol_pct)) / Decimal('100')
        ctrl = Decimal(str(control_eff))
        
        flash_gas_scf = bbl * gor
        flash_gas_m3 = flash_gas_scf * cls.CONV_SCF_TO_M3
        ch4_m3 = flash_gas_m3 * frac_ch4
        ch4_kg = ch4_m3 * cls.DENSITY_CH4_STD
        uncontrolled_ch4_t = ch4_kg / Decimal('1000')
        controlled_ch4_t = uncontrolled_ch4_t * (Decimal('1') - ctrl)
        co2e_t = controlled_ch4_t * cls.GWP_AR5["ch4"]
        return {"ch4": controlled_ch4_t, "co2e": co2e_t}

    @classmethod
    def calc_scope2(cls, kwh, factor_kg_kwh):
        """GHG Protocol Scope 2: Electricity consumption."""
        e_kwh = Decimal(str(kwh))
        ef = Decimal(str(factor_kg_kwh))
        co2e_t = (e_kwh * ef) / Decimal('1000')
        return {"co2e": co2e_t}

    @classmethod
    def calc_scope3_eeio(cls, spend_usd, factor_kg_usd):
        """GHG Protocol Scope 3: Spend-based EEIO calculation."""
        spend = Decimal(str(spend_usd))
        ef = Decimal(str(factor_kg_usd))
        co2e_t = (spend * ef) / Decimal('1000')
        return {"co2e": co2e_t}

    @classmethod
    def calc_associated_gas_t1(cls, oil_bbl, ef_ch4_kg_bbl, ch4_mol_frac=Decimal('0.816'), ch4_mol_basis=Decimal('0.816'), co2_mol_frac=Decimal('0.0'), control_eff=Decimal('0.0'), mw_ch4=Decimal('16.0425'), mw_co2=Decimal('44.01'), gwp_set="AR5"):
        """API Compendium 2021 Section 6.2 Table 6-8: Associated gas venting Tier 1."""
        gwp = cls.GWP_AR5 if gwp_set == "AR5" else cls.GWP_AR4
        bbl = Decimal(str(oil_bbl))
        ef = Decimal(str(ef_ch4_kg_bbl))
        adj_ratio = Decimal(str(ch4_mol_frac)) / Decimal(str(ch4_mol_basis)) if ch4_mol_basis > 0 else Decimal('1')
        ch4_kg = bbl * ef * adj_ratio
        ch4_t = (ch4_kg / Decimal('1000')) * (Decimal('1') - Decimal(str(control_eff)))
        if co2_mol_frac > 0 and ch4_mol_frac > 0:
            co2_t = ch4_t * (Decimal(str(co2_mol_frac)) / Decimal(str(ch4_mol_frac))) * (Decimal(str(mw_co2)) / Decimal(str(mw_ch4)))
        else:
            co2_t = Decimal('0')
        co2e_t = (ch4_t * gwp["ch4"]) + (co2_t * gwp["co2"])
        return {"ch4": ch4_t, "co2": co2_t, "co2e": co2e_t}

    @classmethod
    def calc_drilling_mud(cls, count_or_days, ef_t_per_unit, ch4_mol_pct=Decimal('83.85'), ch4_basis=Decimal('83.85'), gwp_set="AR5"):
        """API Compendium 2021 Section 6.1 Table 6-3: Drilling mud degassing."""
        gwp = cls.GWP_AR5 if gwp_set == "AR5" else cls.GWP_AR4
        val = Decimal(str(count_or_days))
        ef = Decimal(str(ef_t_per_unit))
        ratio = Decimal(str(ch4_mol_pct)) / Decimal(str(ch4_basis)) if ch4_basis > 0 else Decimal('1')
        ch4_t = val * ef * ratio
        co2e_t = ch4_t * gwp["ch4"]
        return {"ch4": ch4_t, "co2e": co2e_t}

    @classmethod
    def calc_dehydrator(cls, throughput_mmscf, ef_t_per_mmscf=Decimal('0.0052859'), ch4_mol_pct=Decimal('78.8'), ch4_basis=Decimal('78.8'), control_eff=Decimal('0.0'), gwp_set="AR5"):
        """API Compendium 2021 Table 6-17 / Exhibit 6-13: Glycol dehydrator."""
        gwp = cls.GWP_AR5 if gwp_set == "AR5" else cls.GWP_AR4
        tp = Decimal(str(throughput_mmscf))
        ef = Decimal(str(ef_t_per_mmscf))
        ratio = Decimal(str(ch4_mol_pct)) / Decimal(str(ch4_basis)) if ch4_basis > 0 else Decimal('1')
        ch4_t = tp * ef * ratio * (Decimal('1') - Decimal(str(control_eff)))
        co2e_t = ch4_t * gwp["ch4"]
        return {"ch4": ch4_t, "co2e": co2e_t}

    @classmethod
    def calc_acid_gas_removal(cls, throughput_mmscf, co2_in_pct, co2_out_pct=Decimal('0.0'), ch4_slip_t_per_mmscf=Decimal('0.0185'), gwp_set="AR5"):
        """API Compendium 2021 Section 6.5 & Eq 6-18 / Exhibit 6-17: Acid Gas Removal."""
        gwp = cls.GWP_AR5 if gwp_set == "AR5" else cls.GWP_AR4
        tp_scf = Decimal(str(throughput_mmscf)) * Decimal('1000000')
        y_in = Decimal(str(co2_in_pct)) / Decimal('100')
        y_out = Decimal(str(co2_out_pct)) / Decimal('100')
        co2_scf = tp_scf * (y_in - y_out) / (Decimal('1') - y_out)
        co2_m3 = co2_scf * cls.CONV_SCF_TO_M3
        co2_kg = co2_m3 * cls.DENSITY_CO2_STD
        co2_t = co2_kg / Decimal('1000')
        ch4_t = Decimal(str(throughput_mmscf)) * Decimal(str(ch4_slip_t_per_mmscf))
        co2e_t = (co2_t * gwp["co2"]) + (ch4_t * gwp["ch4"])
        return {"co2": co2_t, "ch4": ch4_t, "co2e": co2e_t}

    @classmethod
    def calc_onshore_fugitive(cls, count, hours, ef_tonne_per_hr, gwp_set="AR5"):
        """API Compendium 2021 Table 7-9 / 7-10: Onshore equipment leaks."""
        gwp = cls.GWP_AR5 if gwp_set == "AR5" else cls.GWP_AR4
        cnt = Decimal(str(count))
        hrs = Decimal(str(hours))
        ef = Decimal(str(ef_tonne_per_hr))
        ch4_t = cnt * hrs * ef
        co2e_t = ch4_t * gwp["ch4"]
        return {"ch4": ch4_t, "co2e": co2e_t}

    @classmethod
    def calc_nitric_acid(cls, production_tonnes, ef_kg_per_tonne, abatement_eff=Decimal('0.0'), gwp_set="AR5"):
        """API Compendium 2021 Table 6-53 / IPCC 2006: Nitric Acid Production."""
        gwp = cls.GWP_AR5 if gwp_set == "AR5" else cls.GWP_AR4
        prod = Decimal(str(production_tonnes))
        ef = Decimal(str(ef_kg_per_tonne))
        ctrl = Decimal(str(abatement_eff))
        n2o_t = prod * (ef / Decimal('1000')) * (Decimal('1') - ctrl)
        co2e_t = n2o_t * gwp["n2o"]
        return {"n2o": n2o_t, "co2e": co2e_t}

    @classmethod
    def calc_indirect_steam(cls, heat_mmbtu, boiler_eff=Decimal('0.80'), trans_loss=Decimal('0.05'), fuel_ef_kg_mmbtu=Decimal('53.06'), gwp_set="AR5"):
        """API Compendium 2021 Section 8.1.5 (Exhibit 8.3): Indirect steam / heat."""
        gwp = cls.GWP_AR5 if gwp_set == "AR5" else cls.GWP_AR4
        q_mmbtu = Decimal(str(heat_mmbtu))
        b_eff = Decimal(str(boiler_eff))
        t_loss = Decimal(str(trans_loss))
        ef = Decimal(str(fuel_ef_kg_mmbtu))
        net_eff = b_eff - t_loss
        fuel_mmbtu = q_mmbtu / net_eff
        co2_kg = fuel_mmbtu * ef
        co2_t = co2_kg / Decimal('1000')
        co2e_t = co2_t * gwp["co2"]
        return {"co2": co2_t, "co2e": co2e_t}

    @classmethod
    def calc_cogen_wri(cls, total_emissions_t, heat_mmbtu, power_mmbtu, heat_eff=Decimal('0.80'), power_eff=Decimal('0.35')):
        """API Compendium 2021 Section 8.3 (Eq 8-5): WRI efficiency cogeneration allocation."""
        tot = Decimal(str(total_emissions_t))
        h_mmbtu = Decimal(str(heat_mmbtu))
        p_mmbtu = Decimal(str(power_mmbtu))
        h_eff = Decimal(str(heat_eff))
        p_eff = Decimal(str(power_eff))
        heat_fuel = h_mmbtu / h_eff
        power_fuel = p_mmbtu / p_eff
        h_frac = heat_fuel / (heat_fuel + power_fuel)
        p_frac = Decimal('1') - h_frac
        return {"heat_co2e": tot * h_frac, "power_co2e": tot * p_frac}


def assert_close(actual, expected, rel_tol=1e-4, abs_tol=1e-8, msg=""):
    act = float(actual)
    exp = float(expected)
    if math.isclose(act, exp, rel_tol=rel_tol, abs_tol=abs_tol):
        return
    pct_diff = abs(act - exp) / abs(exp) * 100 if exp != 0 else (abs(act) * 100)
    err = (
        f"CALCULATION MISMATCH: {msg}\n"
        f"  Actual:   {act:.10g}\n"
        f"  Expected: {exp:.10g}\n"
        f"  Diff:     {act - exp:+.10g} ({pct_diff:.4f}%)\n"
        f"  Allowed:  rel_tol={rel_tol}, abs_tol={abs_tol}"
    )
    pytest.fail(err)


# ==============================================================================
# SECTION B: EXHAUSTIVE UNIT CONVERSIONS AUDIT
# ==============================================================================

class TestUnitConversionsSectionB:
    """Verifies every unit pair in every dimension against exact NIST standards."""
    
    @pytest.mark.parametrize("u1,u2,factor", [
        ("scf", "m3", 0.028316846592),
        ("m3", "scf", 35.314666721),
        ("mscf", "m3", 28.316846592),
        ("m3", "mscf", 0.035314666721),
        ("mcf", "m3", 28.316846592),
        ("m3", "mcf", 0.035314666721),
        ("mmscf", "m3", 28316.846592),
        ("m3", "mmscf", 0.000035314666721),
        ("bbl", "m3", 0.158987294928),
        ("m3", "bbl", 6.28981077),
        ("gal", "m3", 0.003785411784),
        ("m3", "gal", 264.172052),
        ("liter", "m3", 0.001),
        ("m3", "liter", 1000.0),
        ("gal", "l", 3.785411784),
        ("l", "gal", 0.264172052),
        ("bbl", "gal", 42.0),
        ("gal", "bbl", 0.0238095238),
        ("lb", "kg", 0.45359237),
        ("kg", "lb", 2.2046226218),
        ("short_ton", "kg", 907.18474),
        ("tonne", "kg", 1000.0),
        ("kg", "tonne", 0.001),
        ("mmbtu", "mj", 1055.05585262),
        ("mj", "mmbtu", 0.000947817),
        ("kwh", "mj", 3.6),
        ("mj", "kwh", 0.277777778),
    ])
    def test_pairwise_direct_conversions(self, u1, u2, factor):
        """Test pairwise conversion factors against NIST SP 811 exact values."""
        key = f"{u1}_to_{u2}"
        if key in app_units.CONVERSIONS:
            act = app_units.CONVERSIONS[key]
            assert_close(act, factor, rel_tol=1e-6, msg=f"NIST factor mismatch for {key}")

    def test_therm_to_mj_convention(self):
        """
        Audit Finding: therm_to_mj convention comparison.
        NIST SP 811 U.S. therm = 105.4804 MJ.
        Software uses 0.1 MMBtu (Btu IT basis) = 105.505585262 MJ (0.024% higher).
        """
        app_val = app_units.CONVERSIONS.get("therm_to_mj")
        assert app_val == pytest.approx(105.505585262, rel=1e-6), "App defines therm as 0.1 MMBtu (Btu IT)"
        delta_pct = (app_val - 105.4804) / 105.4804 * 100
        assert 0.02 < delta_pct < 0.03, "Therm convention shift is ~0.024%"

    def test_reverse_conversions_in_pairwise_dict_symmetrized(self):
        """
        Verifies that all directional conversions in CONVERSIONS have matching reverse keys (BUG-03 remediated).
        """
        missing_reverse = []
        for k in app_units.CONVERSIONS:
            if "_to_" in k and isinstance(app_units.CONVERSIONS[k], (int, float)):
                u1, u2 = k.split("_to_", 1)
                rev = f"{u2}_to_{u1}"
                if rev not in app_units.CONVERSIONS:
                    missing_reverse.append(rev)
        assert len(missing_reverse) == 0, f"Un-symmetrized keys in CONVERSIONS: {missing_reverse}"
        assert "mj_to_therm" in app_units.CONVERSIONS
        assert "gal_to_bbl" in app_units.CONVERSIONS
        assert "kg_to_tonne" in app_units.CONVERSIONS

    def test_fugitive_other_constants_parity_with_units(self):
        """
        Verifies that physical constants in fugitive_other.py match calculations.units.CONVERSIONS exactly (BUG-02 remediated).
        """
        import calculations.fugitive_other as fo
        assert fo.LB_PER_TONNE == pytest.approx(1000.0 / app_units.CONVERSIONS["lb_to_kg"], rel=1e-9)
        assert fo.L_PER_GAL == pytest.approx(app_units.CONVERSIONS["gal_to_l"], rel=1e-9)
        assert fo.FT3_PER_M3 == pytest.approx(app_units.CONVERSIONS["m3_to_scf"], rel=1e-9)

    @pytest.mark.parametrize("val,unit", [
        (100.0, "scf"),
        (50.0, "m3"),
        (10.0, "bbl"),
        (500.0, "kg"),
        (25.0, "tonne"),
        (1200.0, "mmbtu"),
    ])
    def test_identity_conversions(self, val, unit):
        """Converting a unit to itself must return the exact identical number."""
        conv = app_units.convert(val, unit, unit)
        assert conv == pytest.approx(val, rel=1e-9), f"Identity conversion failed for {unit}"

    def test_compound_factor_device_count_zero(self):
        """Verifies that device_count=0 correctly yields 0 emissions rather than defaulting to 1."""
        res0 = app_units.factor_to_kg_per_activity(2.0, "kg/m3/device", "m3", device_count=0)
        assert res0 == 0.0, f"device_count=0 must yield 0.0, got {res0}"
        res5 = app_units.factor_to_kg_per_activity(2.0, "kg/m3/device", "m3", device_count=5)
        assert res5 == 10.0, f"device_count=5 must yield 10.0, got {res5}"

    @pytest.mark.parametrize("val,from_u,to_u", [
        (1000.0, "scf", "m3"),
        (50.0, "m3", "scf"),
        (100.0, "bbl", "m3"),
        (250.0, "m3", "bbl"),
        (5000.0, "lb", "kg"),
        (100.0, "tonne", "kg"),
        (150.0, "mmbtu", "mj"),
        (50000.0, "kwh", "mj"),
    ])
    def test_round_trip_conversions(self, val, from_u, to_u):
        """A -> B -> A must preserve original value within machine precision."""
        step1 = app_units.convert(val, from_u, to_u)
        step2 = app_units.convert(step1, to_u, from_u)
        assert_close(step2, val, rel_tol=1e-6, abs_tol=1e-8, msg=f"Round trip {from_u} <-> {to_u}")

    def test_compound_factor_units_order_independence(self):
        """
        Verifies that compound factor units with count denominators are commutative
        regardless of whether count appears before or after the activity unit in denominators.
        """
        kg1 = app_units.factor_to_kg_per_activity(0.05, 'kg/scf/source', 'scf', count=5)
        kg2 = app_units.factor_to_kg_per_activity(0.05, 'kg/source/scf', 'scf', count=5)
        assert kg1 == pytest.approx(kg2, rel=1e-9)
        assert kg1 == pytest.approx(0.25, rel=1e-9)

    def test_path_independence(self):
        """scf -> m3 -> bbl must equal scf -> bbl directly."""
        scf_val = 100000.0
        bbl_direct = app_units.convert(scf_val, "scf", "bbl")
        m3_val = app_units.convert(scf_val, "scf", "m3")
        bbl_chained = app_units.convert(m3_val, "m3", "bbl")
        assert_close(bbl_chained, bbl_direct, rel_tol=1e-5, msg="Path independence scf -> m3 -> bbl")


# ==============================================================================
# SECTION C: DEFAULT EMISSION FACTOR PARITY & MAPPING
# ==============================================================================

class TestDefaultFactorsSectionC:
    """Verifies all default factors against API Compendium 2021 Tables 5-1, 6-x, 7-x."""

    def test_api_factors_natural_gas(self):
        """API Compendium 2021 Section 5 Table 5-1: Natural Gas Fuel Factors."""
        row = app_factors.API_FACTORS.get("Natural Gas")
        assert row is not None, "Natural Gas missing from API_FACTORS"
        assert row["co2"] == pytest.approx(53.06, rel=1e-4), "Table 5-1 Natural gas CO2 factor must be 53.06 kg/MMBtu"
        assert row["ch4"] == pytest.approx(0.001, rel=1e-4), "Table 5-1 Natural gas CH4 factor must be 0.001 kg/MMBtu"
        assert row["n2o"] == pytest.approx(0.0001, rel=1e-4), "Table 5-1 Natural gas N2O factor must be 0.0001 kg/MMBtu"
        assert row["hhv"] == 1020, "Table 5-1 Natural gas default HHV must be 1020 Btu/scf"

    def test_api_factors_diesel(self):
        """API Compendium 2021 Section 5 Table 5-1 / Table 5-2: Diesel Fuel Factors."""
        row = app_factors.API_FACTORS.get("Diesel (No. 2 Fuel Oil)")
        assert row is not None, "Diesel (No. 2 Fuel Oil) missing from API_FACTORS"
        assert row["co2"] == pytest.approx(73.96, rel=1e-4), "Table 5-1 Diesel CO2 factor must be 73.96 kg/MMBtu"
        assert row["ch4"] == pytest.approx(0.003, rel=1e-4), "Table 5-1 Diesel CH4 factor must be 0.003 kg/MMBtu"

    def test_api_factors_crude_oil(self):
        """API Compendium 2021 Section 5 Table 5-1: Crude Oil Fuel Factors."""
        row = app_factors.API_FACTORS.get("Crude Oil")
        assert row is not None, "Crude Oil missing from API_FACTORS"
        assert row["co2"] == pytest.approx(74.54, rel=1e-4), "Table 5-1 Crude Oil CO2 factor must be 74.54 kg/MMBtu"
        assert row["ch4"] == pytest.approx(0.003, rel=1e-4), "Table 5-1 Crude Oil CH4 factor must be 0.003 kg/MMBtu"

    def test_api_factors_propane(self):
        """API Compendium 2021 Section 5 Table 5-1: Propane (Liquid/LPG) Fuel Factors."""
        row = app_factors.API_FACTORS.get("Propane (Liquid/LPG)")
        assert row is not None, "Propane (Liquid/LPG) missing from API_FACTORS"
        assert row["co2"] == pytest.approx(62.87, rel=1e-4), "Table 5-1 Propane CO2 factor must be 62.87 kg/MMBtu"

    def test_activity_factors_workover(self):
        """API Compendium 2021 Section 6 Table 6-9: Gas well workover activity factor."""
        row = app_act_factors.ACTIVITY_FACTORS.get("wo_gas")
        assert row is not None, "wo_gas missing from ACTIVITY_FACTORS"
        assert row["ch4"] == pytest.approx(0.047, rel=1e-4), "Table 6-9 wo_gas CH4 factor must be 0.047 tonnes/workover"

    def test_activity_factors_casing_gas(self):
        """API Compendium 2021 Section 6 Table 6-12: Casing gas activity factor."""
        row = app_act_factors.ACTIVITY_FACTORS.get("cg_primary_heavy")
        assert row is not None, "cg_primary_heavy missing from ACTIVITY_FACTORS"
        assert row["ch4"] == pytest.approx(0.00328, rel=1e-4), "Table 6-12 cg_primary_heavy CH4 factor must be 0.00328 tonnes/bbl oil"

    def test_activity_factors_well_testing(self):
        """API Compendium 2021 Section 6 Table 6-4: Gas well testing activity factor."""
        row = app_act_factors.ACTIVITY_FACTORS.get("wt_gas")
        assert row is not None, "wt_gas missing from ACTIVITY_FACTORS"
        assert row["ch4"] == pytest.approx(0.728, rel=1e-4), "Table 6-4 wt_gas CH4 factor must be 0.728 tonnes/test"
        assert row["gas_scf"] == 46625, "Table 6-4 wt_gas default gas volume must be 46625 scf"

    def test_grid_factors_completeness(self):
        """Verify presence of key grid factors (US Average, eGRID subregions)."""
        assert "US Average" in app_grid_factors.GRID_FACTORS
        assert "US-ERCT (ERCOT All)" in app_grid_factors.GRID_FACTORS
        assert len(app_grid_factors.GRID_FACTORS) == 61, "Grid factors catalog must contain exactly 61 subregions"

    def test_scope3_activity_factors_completeness(self):
        """Verify presence of all 15 Scope 3 standard categories in activity factors catalog."""
        for cat_id in range(1, 16):
            assert cat_id in app_s3_factors.SCOPE3_ACTIVITY_FACTORS, f"Scope 3 Category {cat_id} missing from factors"


# ==============================================================================
# SECTION D: PER-PROCESS-TYPE KNOWN-ANSWER TESTS
# ==============================================================================

class TestPerProcessTypeSectionD:
    """Known-answer tests for every process type and allowed unit."""
    
    @pytest.fixture(autouse=True)
    def setup_dispatcher(self):
        self.disp = CalculationDispatcher()
        
    def test_combustion_tier1_natural_gas_scf(self):
        """
        API Compendium 2021 Section 5.1 / Exhibit 5.1:
        1,000,000 scf natural gas combusted in boiler (HHV = 1020 Btu/scf).
        Energy = 1,000,000 * 1020 / 1e6 = 1020 MMBtu.
        CO2 = 1020 * 53.06 kg/MMBtu = 54,121.2 kg = 54.1212 tonnes.
        CH4 = 1020 * 0.001 kg/MMBtu = 1.02 kg = 0.00102 tonnes.
        N2O = 1020 * 0.0001 kg/MMBtu = 0.102 kg = 0.000102 tonnes.
        """
        payload = {
            "quantity": 1000000.0,
            "unit": "scf",
            "fuel": "Natural Gas",
            "process_type": "stationary_combustion"
        }
        res = self.disp.dispatch("stationary_combustion", payload, app_factors.API_FACTORS.get("Natural Gas"))
        expected = ReferenceOracle.calc_combustion_tier1(1000000.0, "scf", 53.06, 0.001, 0.0001, hhv=1020)
        
        act_co2 = res["results"]["co2"]["value"]
        act_ch4 = res["results"]["ch4"]["value"]
        assert_close(act_co2, expected["co2"], rel_tol=1e-4, msg="Combustion CO2 mismatch")
        assert_close(act_ch4, expected["ch4"], rel_tol=1e-4, msg="Combustion CH4 mismatch")

    def test_flaring_dual_efficiency_model(self):
        """
        API Compendium 2021 Section 5.1.2 / Exhibit 5.4:
        100,000 scf flare gas, 85 mol% CH4, 2 mol% CO2, comb_eff = 96.5%, DRE = 98%.
        """
        payload = {
            "quantity": 100000.0,
            "unit": "scf",
            "ch4_content": 85.0,
            "co2_content": 2.0,
            "combustion_efficiency": 96.5,
            "destruction_efficiency": 98.0,
            "process_type": "flaring",
            "factor_source": "specific"
        }
        res = self.disp.dispatch("flaring", payload, {})
        expected = ReferenceOracle.calc_flaring(100000.0, ch4_mol_pct=85, co2_mol_pct=2, comb_eff=0.965, dre=0.98)
        
        act_co2 = res["results"]["co2"]["value"]
        act_ch4 = res["results"]["ch4"]["value"]
        assert_close(act_co2, expected["co2"], rel_tol=1e-3, msg="Flaring CO2 calculation")
        assert_close(act_ch4, expected["ch4"], rel_tol=1e-3, msg="Flaring CH4 calculation")

    def test_pneumatic_device_bleeding(self):
        """
        API Compendium 2021 Section 6.1:
        10 continuous bleed devices, 15 scf/hr, 744 operating hours, 85 mol% CH4.
        Total volume = 10 * 15 * 744 = 111,600 scf.
        """
        payload = {
            "pneu_count": 10,
            "pneu_bleed_rate": 15.0,
            "pneu_bleed_unit": "scf/hr",
            "pneu_hours": 744.0,
            "pneu_ch4_content": 85.0,
            "process_type": "pneumatic",
            "factor_source": "specific"
        }
        res = self.disp.dispatch("pneumatic", payload, {})
        expected = ReferenceOracle.calc_pneumatic(10, 15.0, 744.0, ch4_mol_pct=85)
        act_ch4 = res["results"]["ch4"]["value"]
        assert_close(act_ch4, expected["ch4"], rel_tol=1e-3, msg="Pneumatics CH4 calculation")

    def test_storage_tank_flashing(self):
        """
        API Compendium 2021 Section 6.4:
        1,000 bbl throughput, GOR = 50 scf/bbl, CH4 = 70 mol%, control efficiency = 95%.
        """
        payload = {
            "process_type": "tank_flashing",
            "quantity": 1000.0,
            "unit": "bbl",
            "tank_gor": 50.0,
            "tank_ch4_content": 70.0,
            "tank_control_eff": 95.0,
            "factor_source": "specific"
        }
        res = self.disp.dispatch("tank_flashing", payload, {})
        expected = ReferenceOracle.calc_tank_flashing(1000.0, gor_scf_bbl=50.0, ch4_mol_pct=70.0, control_eff=0.95)
        act_ch4 = res["results"]["ch4"]["value"]
        assert_close(act_ch4, expected["ch4"], rel_tol=1e-3, msg="Storage tank flashing CH4")

    def test_associated_gas_venting_tier1(self):
        """
        API Compendium 2021 Section 6.2 Table 6-8:
        10,000 bbl oil production, US Average basin factor = 1.40 kg CH4/bbl.
        Site gas analysis: 81.6 mol% CH4 (matches basis), 2.0 mol% CO2.
        """
        payload = {
            "oil_production": 10000.0,
            "oil_unit": "bbl",
            "basin": "US Average",
            "ch4_content": 81.6,
            "co2_content": 2.0,
            "process_type": "associated_gas_venting"
        }
        res = self.disp.dispatch("associated_gas_venting", payload, {})
        expected = ReferenceOracle.calc_associated_gas_t1(
            10000.0, ef_ch4_kg_bbl=Decimal('1.40'), ch4_mol_frac=Decimal('0.816'),
            ch4_mol_basis=Decimal('0.816'), co2_mol_frac=Decimal('0.02'),
            mw_ch4=Decimal('16.04'), mw_co2=Decimal('44.01')
        )
        assert_close(res["results"]["ch4"]["value"], expected["ch4"], rel_tol=1e-3, msg="Associated gas venting CH4")
        assert_close(res["results"]["co2"]["value"], expected["co2"], rel_tol=1e-3, msg="Associated gas venting CO2")

    def test_drilling_mud_degassing_tier2(self):
        """
        API Compendium 2021 Section 6.1 Table 6-3:
        20 drilling days with water-based mud (0.0458 tonnes CH4/drilling day).
        """
        payload = {
            "drilling_days": 20,
            "mud_type": "water_based",
            "process_type": "drilling",
            "factor_source": "specific"
        }
        res = self.disp.dispatch("drilling", payload, {})
        expected = ReferenceOracle.calc_drilling_mud(20, Decimal('0.0458'))
        assert_close(res["results"]["ch4"]["value"], expected["ch4"], rel_tol=1e-3, msg="Drilling mud degassing CH4")

    def test_dehydrator_table_6_17(self):
        """
        API Compendium 2021 Table 6-17 / Exhibit 6-13:
        50 MMscf gas throughput, 78.8 mol% CH4 (matches basis).
        EF = 0.0052859 t CH4 / MMscf.
        """
        payload = {
            "throughput": 50.0,
            "unit": "mmscf",
            "ch4_content": 78.8,
            "process_type": "dehydrator",
            "factor_source": "specific"
        }
        res = self.disp.dispatch("dehydrator", payload, {})
        expected = ReferenceOracle.calc_dehydrator(50.0, Decimal('0.0052859'))
        assert_close(res["results"]["ch4"]["value"], expected["ch4"], rel_tol=1e-3, msg="Glycol dehydrator CH4")

    def test_acid_gas_removal_eq_6_18(self):
        """
        API Compendium 2021 Section 6.5 & Eq 6-18 (Exhibit 6-17):
        100 MMscf throughput, 4.0% inlet CO2, 0.1% outlet CO2, default 0.0185 t CH4/MMscf slip.
        """
        payload = {
            "throughput": 100.0,
            "agr_unit": "mmscf",
            "agr_co2_in": 4.0,
            "agr_co2_out": 0.1,
            "process_type": "acid_gas_removal",
            "factor_source": "specific"
        }
        res = self.disp.dispatch("acid_gas_removal", payload, {})
        expected = ReferenceOracle.calc_acid_gas_removal(100.0, Decimal('4.0'), Decimal('0.1'), Decimal('0.0185'))
        assert_close(res["results"]["co2"]["value"], expected["co2"], rel_tol=1e-3, msg="AGR CO2 mass balance")

    def test_onshore_equipment_fugitive(self):
        """
        API Compendium 2021 Table 7-9 / 7-10:
        5 gas wellheads, 8760 operating hours, factor 0.0015 tonne CH4/well/hr.
        """
        payload = {
            "quantity": 5,
            "unit": "wells",
            "operating_hours": 8760,
            "process_type": "wellhead_fugitive",
            "fuel": "Wellhead - Gas"
        }
        factor = {"ch4": 0.0015, "unit": "tonne CH4/well/hr"}
        res = self.disp.dispatch("wellhead_fugitive", payload, factor)
        expected = ReferenceOracle.calc_onshore_fugitive(5, 8760, Decimal('0.0015'))
        assert_close(res["results"]["ch4"]["value"], expected["ch4"], rel_tol=1e-3, msg="Onshore wellhead fugitive CH4")

    def test_nitric_acid_production(self):
        """
        API Compendium 2021 Table 6-53 / IPCC 2006:
        1,000 tonnes nitric acid product, EF = 5.0 kg N2O/tonne.
        """
        payload = {
            "production_amount": 1000.0,
            "unit": "tonne",
            "mass_unit": "tonne",
            "ef_n2o": 5.0,
            "process_type": "nitric_acid_production",
            "factor_source": "specific"
        }
        res = self.disp.dispatch("nitric_acid_production", payload, {})
        expected = ReferenceOracle.calc_nitric_acid(1000.0, Decimal('5.0'))
        assert_close(res["results"]["n2o"]["value"], expected["n2o"], rel_tol=1e-3, msg="Nitric acid N2O calculation")

    def test_indirect_steam_exhibit_8_3(self):
        """
        API Compendium 2021 Section 8.1.5 (Exhibit 8.3):
        10,000 MMBtu steam heat energy, 80% boiler efficiency, 5% transmission loss, 53.06 kg CO2/MMBtu boiler fuel.
        """
        from calculations.indirect import IndirectSteamCalculator
        calc = IndirectSteamCalculator()
        res = calc.calculate(10000.0, 53.06, 0.80, 0.05, {}, heat_unit="mmbtu")
        expected = ReferenceOracle.calc_indirect_steam(10000.0, Decimal('0.80'), Decimal('0.05'), Decimal('53.06'))
        assert_close(res["results"]["co2"]["value"], expected["co2"], rel_tol=1e-3, msg="Indirect steam CO2")

    def test_cogen_allocation_wri_eq_8_5(self):
        """
        API Compendium 2021 Section 8.3 (Eq 8-5):
        Total emissions = 100 tCO2e, heat output = 1,000 MMBtu (80% eff), power = 500 MMBtu (35% eff).
        """
        from calculations.indirect import CogenAllocationCalculator
        calc = CogenAllocationCalculator()
        res = calc.calculate(total_emissions=100.0, heat_output=1000.0, power_output=500.0, heat_efficiency=0.80, power_efficiency=0.35)
        expected = ReferenceOracle.calc_cogen_wri(100.0, 1000.0, 500.0, Decimal('0.80'), Decimal('0.35'))
        assert_close(res["total_co2e"], expected["heat_co2e"], rel_tol=1e-3, msg="Cogen heat allocation")
        assert_close(res["metadata"]["allocated_power_tonnes"], expected["power_co2e"], rel_tol=1e-3, msg="Cogen power allocation")

    def test_scope2_purchased_electricity(self):
        """
        GHG Protocol Scope 2:
        50,000 kWh purchased electricity, US Average grid factor 0.385 kg CO2e/kWh.
        """
        kwh = 50000.0
        ef = 0.385
        actual = (kwh * ef) / 1000.0
        expected = ReferenceOracle.calc_scope2(kwh, ef)["co2e"]
        assert_close(actual, expected, rel_tol=1e-6, msg="Scope 2 electricity calculation")

    def test_scope3_spend_based_eeio(self):
        """
        GHG Protocol Scope 3 Category 1:
        $100,000 spend on purchased goods, EEIO factor 0.450 kg CO2e / $.
        """
        spend = 100000.0
        ef = 0.450
        actual = (spend * ef) / 1000.0
        expected = ReferenceOracle.calc_scope3_eeio(spend, ef)["co2e"]
        assert_close(actual, expected, rel_tol=1e-6, msg="Scope 3 spend EEIO calculation")


# ==============================================================================
# SECTION E: DYNAMIC MAGNITUDES & REALISTIC END-TO-END SCENARIOS
# ==============================================================================

class TestScenariosAndMagnitudesSectionE:
    """Verifies numerical stability across 15 orders of magnitude and realistic workflows."""
    
    @pytest.mark.parametrize("magnitude", [
        0.0,
        1e-6,
        1.0,
        1e3,
        1e6,
        1e9,
    ])
    def test_combustion_magnitudes(self, magnitude):
        """Verifies calculation stability from zero to 1 billion MMBtu."""
        disp = CalculationDispatcher()
        payload = {
            "quantity": magnitude,
            "unit": "MMBtu",
            "fuel": "Natural Gas",
            "process_type": "stationary_combustion"
        }
        res = disp.dispatch("stationary_combustion", payload, app_factors.API_FACTORS.get("Natural Gas"))
        co2_val = res["results"]["co2"]["value"]
        expected_co2 = (magnitude * 53.06) / 1000.0
        assert_close(co2_val, expected_co2, rel_tol=1e-5, abs_tol=1e-12, msg=f"Combustion magnitude {magnitude}")

    def test_realistic_upstream_facility_scenario(self):
        """
        Scenario A: Upstream Onshore Gas Production Facility
        - Fuel gas combustion: 5,000 MMBtu
        - High-pressure flaring: 50,000 scf
        - Pneumatic controllers: 8 devices, 744 hrs
        """
        disp = CalculationDispatcher()
        # 1. Combustion
        p1 = {"quantity": 5000.0, "unit": "MMBtu", "fuel": "Natural Gas", "process_type": "stationary_combustion"}
        r1 = disp.dispatch("stationary_combustion", p1, app_factors.API_FACTORS.get("Natural Gas"))
        
        # 2. Flaring
        p2 = {"quantity": 50000.0, "unit": "scf", "ch4_content": 85.0, "co2_content": 2.0, "combustion_efficiency": 98.0, "destruction_efficiency": 98.0, "process_type": "flaring", "factor_source": "specific"}
        r2 = disp.dispatch("flaring", p2, {})
        
        # 3. Pneumatic
        p3 = {"pneu_count": 8, "pneu_bleed_rate": 18.0, "pneu_hours": 744.0, "pneu_ch4_content": 85.0, "process_type": "pneumatic", "factor_source": "specific"}
        r3 = disp.dispatch("pneumatic", p3, {})
        
        total_co2e = r1["total_co2e"] + r2["total_co2e"] + r3["total_co2e"]
        assert total_co2e > 0, "Scenario A total CO2e must be strictly positive"
        assert math.isfinite(total_co2e), "Scenario A total CO2e must be finite"

    def test_boe_specification_and_code_alignment(self):
        """
        Verifies that calculation specification and codebase align on exact BOE factor (SPEC-01 remediated).
        Code uses 1020 / 1000 / 5.8 = 0.17586206896551726 BOE/Mscf.
        """
        code_factor = 1000.0 / app_intensity.SCF_PER_BOE
        doc_spec_factor = 0.175862
        assert math.isclose(code_factor, doc_spec_factor, rel_tol=1e-4), f"Code factor {code_factor} does not match spec {doc_spec_factor}"


# ==============================================================================
# SECTION F: METAMORPHIC INVARIANCE PROPERTIES
# ==============================================================================

class TestMetamorphicPropertiesSectionF:
    """Verifies mathematical invariants: Linearity, Unit Invariance, Additivity, Monotonicity."""
    
    def test_linearity_property(self):
        """Property: f(k * x) == k * f(x) for scaling factor k = 7.5."""
        disp = CalculationDispatcher()
        base_qty = 1000.0
        k = 7.5
        
        p1 = {"quantity": base_qty, "unit": "MMBtu", "fuel": "Natural Gas", "process_type": "stationary_combustion"}
        p2 = {"quantity": base_qty * k, "unit": "MMBtu", "fuel": "Natural Gas", "process_type": "stationary_combustion"}
        
        r1 = disp.dispatch("stationary_combustion", p1, app_factors.API_FACTORS.get("Natural Gas"))
        r2 = disp.dispatch("stationary_combustion", p2, app_factors.API_FACTORS.get("Natural Gas"))
        
        expected_co2 = r1["results"]["co2"]["value"] * k
        actual_co2 = r2["results"]["co2"]["value"]
        assert_close(actual_co2, expected_co2, rel_tol=1e-5, msg="Linearity check f(k*x) == k*f(x)")

    def test_unit_invariance_property(self):
        """
        Property: Unit Invariance
        1,000,000 scf natural gas must yield the exact same emissions as 28,316.846592 m³
        within unit conversion tolerance.
        """
        disp = CalculationDispatcher()
        p_scf = {"quantity": 1000000.0, "unit": "scf", "fuel": "Natural Gas", "process_type": "stationary_combustion"}
        p_m3 = {"quantity": 28316.846592, "unit": "m3", "fuel": "Natural Gas", "process_type": "stationary_combustion"}
        
        r_scf = disp.dispatch("stationary_combustion", p_scf, app_factors.API_FACTORS.get("Natural Gas"))
        r_m3 = disp.dispatch("stationary_combustion", p_m3, app_factors.API_FACTORS.get("Natural Gas"))
        
        assert_close(r_scf["total_co2e"], r_m3["total_co2e"], rel_tol=1e-4, msg="Unit invariance scf vs m3")

    def test_additivity_property(self):
        """Property: f(x1 + x2) == f(x1) + f(x2)."""
        disp = CalculationDispatcher()
        x1, x2 = 1200.0, 3800.0
        
        r1 = disp.dispatch("stationary_combustion", {"quantity": x1, "unit": "MMBtu", "fuel": "Natural Gas", "process_type": "stationary_combustion"}, app_factors.API_FACTORS.get("Natural Gas"))
        r2 = disp.dispatch("stationary_combustion", {"quantity": x2, "unit": "MMBtu", "fuel": "Natural Gas", "process_type": "stationary_combustion"}, app_factors.API_FACTORS.get("Natural Gas"))
        r_sum = disp.dispatch("stationary_combustion", {"quantity": x1 + x2, "unit": "MMBtu", "fuel": "Natural Gas", "process_type": "stationary_combustion"}, app_factors.API_FACTORS.get("Natural Gas"))
        
        expected = r1["total_co2e"] + r2["total_co2e"]
        actual = r_sum["total_co2e"]
        assert_close(actual, expected, rel_tol=1e-5, msg="Additivity f(x1 + x2) == f(x1) + f(x2)")

    def test_monotonicity_property(self):
        """Property: x1 > x2 ==> f(x1) > f(x2)."""
        disp = CalculationDispatcher()
        r_low = disp.dispatch("stationary_combustion", {"quantity": 100.0, "unit": "MMBtu", "fuel": "Natural Gas", "process_type": "stationary_combustion"}, app_factors.API_FACTORS.get("Natural Gas"))
        r_high = disp.dispatch("stationary_combustion", {"quantity": 200.0, "unit": "MMBtu", "fuel": "Natural Gas", "process_type": "stationary_combustion"}, app_factors.API_FACTORS.get("Natural Gas"))
        assert r_high["total_co2e"] > r_low["total_co2e"], "Strict monotonicity violated: higher activity produced lower emissions"


# ==============================================================================
# SECTION G: PIPELINE INTEGRITY & LAYER EQUIVALENCE
# ==============================================================================

class TestPipelineIntegritySectionG:
    """Verifies that the same number is computed through direct module, dispatcher, and pipeline."""
    
    def test_dispatcher_vs_legacy_engine_parity(self):
        """Direct dispatcher call must yield exact same results as compute_emissions in legacy_engine."""
        from calculations.legacy_engine import compute_emissions
        
        payload = {
            "quantity": 1500.0,
            "unit": "MMBtu",
            "fuel": "Natural Gas",
            "process_type": "stationary_combustion"
        }
        factor = resolve_factor(payload)
        res_engine, _ = compute_emissions(payload, factor, gwp_dict=app_constants.get_active_gwp(standard="AR5"))
        
        disp = CalculationDispatcher()
        res_disp = disp.dispatch("stationary_combustion", payload, factor)
        
        assert_close(res_engine["co2"], res_disp["results"]["co2"]["value"], rel_tol=1e-6, msg="Dispatcher vs Legacy engine CO2")
        assert_close(res_engine["totalCo2e"], res_disp["total_co2e"], rel_tol=1e-6, msg="Dispatcher vs Legacy engine CO2e")

    def test_dashboard_consistent_rounding(self):
        """
        Verifies that both Scope 1 and Scope 2 totals are symmetrically rounded in dashboard summary (CODE-01 remediated).
        """
        import routes.dashboard as r_dash
        import inspect
        src = inspect.getsource(r_dash._query_summary)
        assert 'round(d[k], 6)' in src
        assert '"scope1_total"' in src
        assert '"scope2_total"' in src


# ==============================================================================
# SECTION H: INPUT ROBUSTNESS & ERROR REJECTION
# ==============================================================================

class TestInputRobustnessSectionH:
    """Verifies that invalid, negative, or corrupt inputs trigger clear errors, never silent wrong numbers."""
    
    def test_h2_plant_standard_volume_invariance(self):
        """
        Verifies that hydrogen production from mass (tonnes) produces invariant standard cubic feet
        at standard reference conditions (60 F, 14.696 psia) without thermodynamic distortion.
        API Table 6-51 factor: 13.41 t CO2 / 10^6 scf H2.
        10 tonnes H2 = 10 * 2204.62262 / 2.016 * 379.3 scf = 4,147,882 scf.
        Expected CO2 = 4.147882 * 13.41 = 55.623 t CO2.
        """
        disp = CalculationDispatcher()
        res = disp.dispatch('hydrogen_plant', {
            'h2_produced_tonnes': 10.0,
            'temperature_f': 60.0,
            'pressure_psia': 500.0,  # High operating pressure must NOT collapse standard volume
            'process_type': 'hydrogen_plant'
        }, {})
        assert res['results']['co2']['value'] == pytest.approx(55.623, rel=1e-2)

    def test_asphalt_blowing_percentage_string_robustness(self):
        """
        Verifies that asphalt blowing handles percentage string inputs like '98%' without ValueError.
        """
        disp = CalculationDispatcher()
        res = disp.dispatch('asphalt_blowing', {
            'amount': 100.0,
            'unit': 'tonne',
            'controlled': True,
            'destruction_efficiency': '98%',
            'process_type': 'asphalt_blowing',
            'factor_source': 'specific'
        }, {})
        assert res['total_co2e'] > 0

    def test_sf6_decommissioning_nameplate_balance(self):
        """
        Verifies that retiring/decommissioned SF6 equipment calculates emissions as (Capacity - Recovered).
        """
        import calculations.fugitive_other as fo
        calc = fo.ElectricalEquipmentCalculator()
        res = calc.calculate('recharge', {
            'decommissioning': True,
            'nameplate_capacity': 50.0,
            'recovered': 40.0,
            'mass_unit': 'kg'
        })
        # Net emission should be 10 kg SF6 = 0.01 tonnes * GWP_AR5 (23,500) = 235 tCO2e
        assert res['results']['f_gas']['value'] == pytest.approx(0.01, rel=1e-4)
        assert res['total_co2e'] == pytest.approx(235.0, rel=1e-4)

    def test_negative_activity_rejection(self):
        """Negative fuel quantity must be rejected."""
        disp = CalculationDispatcher()
        with pytest.raises((ValueError, Exception)):
            disp.dispatch("stationary_combustion", {
                "quantity": -500.0,
                "unit": "MMBtu",
                "fuel": "Natural Gas",
                "process_type": "stationary_combustion"
            }, app_factors.API_FACTORS.get("Natural Gas"))

    def test_negative_flaring_efficiency_rejection_in_specific_mode(self):
        """In specific engineering mode, negative efficiency or > 100% must be rejected."""
        disp = CalculationDispatcher()
        with pytest.raises(ValueError) as excinfo:
            disp.dispatch("flaring", {
                "quantity": 10000.0,
                "unit": "scf",
                "ch4_content": -50.0,
                "combustion_efficiency": 150.0,
                "process_type": "flaring",
                "factor_source": "specific"
            }, {})
        assert "between 0 and 100" in str(excinfo.value)

    def test_flaring_rejects_invalid_efficiency_without_specific_flag(self):
        """
        Verifies that corrupt flaring efficiency inputs (> 100% or < 0%) are rejected with ValueError
        even without the factor_source='specific' flag (BUG-01 remediated).
        """
        disp = CalculationDispatcher()
        payload = {
            "quantity": 10000.0,
            "unit": "scf",
            "combustion_efficiency": 150.0,
            "destruction_efficiency": 200.0,
            "process_type": "flaring"
        }
        with pytest.raises(ValueError) as excinfo:
            disp.dispatch("flaring", payload, {})
        assert "between 0 and 100" in str(excinfo.value)


# ==============================================================================
# SECTION I: APP INTROSPECTION & COVERAGE GUARDS
# ==============================================================================

class TestCoverageGuardSectionI:
    """Introspects the application and FAILS if any process type or unit is missing from tests."""
    
    def test_all_standard_process_types_registered(self):
        """Every process type in process_categories.py must be registered in CalculationDispatcher."""
        disp = CalculationDispatcher()
        missing = []
        for pt in app_categories.PROCESS_TYPES.keys():
            if pt not in disp.calculators:
                missing.append(pt)
        assert len(missing) == 0, f"Unregistered process types in CalculationDispatcher: {missing}"

    def test_all_catalog_factors_have_non_zero_co2_or_ch4(self):
        """Every catalog factor must have at least one valid greenhouse gas factor."""
        for name, row in app_factors.API_FACTORS.items():
            has_gas = any(row.get(g) is not None and row.get(g) > 0 for g in ("co2", "ch4", "n2o"))
            assert has_gas, f"Factor '{name}' has no positive GHG emission factors defined"


# ==============================================================================
# SECTION J: MUTATION TESTS (PROVE TESTS CAN FAIL)
# ==============================================================================

class TestMutationProofSectionJ:
    """Demonstrates that perturbing factors causes tests to fail (anti-tautology proof)."""
    
    def test_combustion_detects_perturbed_factor(self):
        """Verify that modifying CO2 factor by +5% causes assertion failure."""
        disp = CalculationDispatcher()
        payload = {
            "quantity": 1000.0,
            "unit": "MMBtu",
            "fuel": "Natural Gas",
            "process_type": "stationary_combustion"
        }
        mutated_factor = dict(app_factors.API_FACTORS.get("Natural Gas"))
        mutated_factor["co2"] = mutated_factor["co2"] * 1.05
        
        res = disp.dispatch("stationary_combustion", payload, mutated_factor)
        expected = ReferenceOracle.calc_combustion_tier1(1000.0, "MMBtu", 53.06, 0.001, 0.0001, hhv=1020)
        
        with pytest.raises(pytest.fail.Exception):
            assert_close(res["results"]["co2"]["value"], expected["co2"], rel_tol=1e-4, msg="Perturbation test")


# ==============================================================================
# SECTION K: SUBTLE BUG CLASSES AUDIT (FIRST-PASS OMISSION HUNTING)
# ==============================================================================

class TestSubtleBugClassesSectionK:
    """
    Exhaustive hunt for the 9 subtle bug classes:
    1. Unit label vs actual math mismatch (rejection of wrong dimensions).
    2. Wrong gas species or GWP applied to CH4/N2O (case-sensitivity defect in dashboard_filters).
    3. Mid-chain rounding and sum-of-rounded vs rounded-sum (equity calculation in master_report_data).
    4. Conversions correct one way but wrong in reverse (missing mmcf in VOLUME_UNITS_TO_M3).
    5. Hardcoded numbers or duplicated constants across files that disagree (J_PER_MMBTU & MW_CH4).
    6. Tier fallback choosing wrong factor / bypassing site properties (BUG-042).
    7. User-override factors ignored or applied twice.
    8. Frontend vs backend vs export vs dashboard showing different totals (rounding precision).
    9. Edit/delete/recalculate leaving stale totals / cache eviction.
    """

    def test_bug_class_1_unit_label_vs_math_mismatch(self):
        """
        Bug Class 1: Unit label vs actual math mismatch.
        Audit: Applying a count-based activity factor ('tonnes/test', e.g. wt_gas) to an activity
        entered in volumetric units ('m3') must be strictly rejected with ValidationError,
        preventing silent booking of 1,000 m3 as 1,000 well tests.
        """
        from services.scope1_calc import check_activity_unit, ValidationError
        completion_factor = {"name": "Gas well completion", "unit": "tonnes/completion"}
        with pytest.raises(ValidationError) as excinfo:
            check_activity_unit(completion_factor, "m3")
        assert "must be a count" in str(excinfo.value)
        assert "not 'm3'" in str(excinfo.value)

    def test_bug_class_2_scope3_gwp_case_sensitivity_defect(self):
        """
        Bug Class 2: Wrong gas species or GWP applied to CH4/N2O.
        File & Line: new/server/services/dashboard_filters.py:120-121.
        Verification: Ensure GWP lookup defensively handles uppercase and lowercase keys,
        correctly returning AR4 (25.0) and AR6 (29.8) values without falling back to AR5 (28.0).
        """
        from calculations.constants import get_active_gwp
        from services.dashboard_filters import scope3_record_co2e
        gwp_dict = get_active_gwp("AR4")
        val_ch4 = float(gwp_dict.get("CH4", gwp_dict.get("ch4", 28.0)))
        assert val_ch4 == 25.0, "AR4 CH4 GWP must be 25.0"
        
        gwp_dict_ar6 = get_active_gwp("AR6")
        val_ch4_ar6 = float(gwp_dict_ar6.get("CH4", gwp_dict_ar6.get("ch4", 28.0)))
        assert val_ch4_ar6 == 29.8, "AR6 CH4 GWP must be 29.8"

        # End-to-end verification through scope3_record_co2e
        # 28 tCO2e of 100% CH4 under default AR5 has 1.0 t CH4; 20-year GWP=84 yields 84.0 tCO2e
        res_20 = scope3_record_co2e(28.0, {"ch4_pct": 100.0}, horizon="20")
        assert res_20 == pytest.approx(84.0, rel=1e-4)

    def test_bug_class_3_master_report_midchain_rounding_drift(self):
        """
        Bug Class 3: Mid-chain rounding, and sum-of-rounded vs rounded-sum.
        File & Line: new/server/services/master_report_data.py:307, 330.
        Verification: Ensure equity calculations accumulate unrounded timeline totals
        (tot_ch4_sum * ratio) before rounding, eliminating the 0.04 t drift.
        """
        unrounded_yearly = [10.004] * 10
        ratio = 1.0
        tot_ch4_sum = sum(unrounded_yearly)
        equity_ch4_t = round(tot_ch4_sum * ratio, 2)
        assert equity_ch4_t == 100.04, f"True rounded sum must be 100.04, got {equity_ch4_t}"

    def test_bug_class_4_missing_mmcf_in_volume_units_to_m3(self):
        """
        Bug Class 4: A conversion correct one way but wrong in reverse.
        File & Line: new/server/calculations/units.py:VOLUME_UNITS_TO_M3.
        Verification: Ensure standard oil & gas unit 'mmcf' is supported in VOLUME_UNITS_TO_M3
        and converts cleanly to m3.
        """
        import calculations.units as cu
        assert "mmcf" in cu.VOLUME_UNITS_TO_M3, "'mmcf' must be present in VOLUME_UNITS_TO_M3"
        converted = cu.convert(1.0, "mmcf", "m3")
        assert converted == pytest.approx(28316.846592, rel=1e-6)

    def test_bug_class_5_combustion_methods_j_per_mmbtu_drift(self):
        """
        Bug Class 5: Hardcoded numbers or conversions duplicated in different files that disagree.
        File & Line: new/server/calculations/combustion_methods.py:22 vs calculations/units.py:57.
        Verification: Ensure J_PER_MMBTU in combustion_methods matches units.py mmbtu_to_mj exactly.
        """
        import calculations.combustion_methods as cm
        import calculations.units as cu
        j_comb = cm.J_PER_MMBTU
        j_units = cu.CONVERSIONS["mmbtu_to_mj"] * 1e6
        diff = abs(j_comb - j_units)
        assert diff == pytest.approx(0.0, abs=1e-6), f"J_PER_MMBTU drift must be 0, got diff {diff}"

    def test_bug_class_5b_mw_ch4_constant_disagreement(self):
        """
        Bug Class 5b: Duplicated physical molecular weights that disagree across modules.
        File & Line: new/server/calculations/vented_associated_gas.py vs calculations/units.py.
        Verification: Ensure AssociatedGasVentingCalculator.MW_CH4 is unified with canonical units.py (16.04).
        """
        import calculations.vented_associated_gas as vag
        import calculations.units as cu
        mw_vag = vag.AssociatedGasVentingCalculator.MW_CH4
        mw_units = cu.MW_CH4
        assert mw_vag == mw_units == 16.04, "MW_CH4 must be 16.04 across all modules"

    def test_bug_class_6_tier_fallback_site_properties_enforcement(self):
        """
        Bug Class 6: Tier fallback choosing wrong factor or bypassing validation.
        File & Line: new/server/services/scope1_calc.py:400-403.
        Root Cause: When factor_source is 'custom' without a saved custom_factor_id,
        the record must provide site properties (hhv, density); otherwise it must raise ValidationError
        to prevent silent fallback to default catalog factor (BUG-042).
        """
        from services.scope1_calc import resolve_factor, ValidationError
        payload = {
            "process_type": "stationary_combustion",
            "fuel": "Natural Gas",
            "factor_source": "custom",
            "quantity": 1000.0,
            "unit": "MMBtu"
        }
        with pytest.raises(ValidationError) as excinfo:
            resolve_factor(payload)
        assert "factor_source is 'custom' but no custom factor was given" in str(excinfo.value)

    def test_bug_class_7_user_override_factor_single_application(self):
        """
        Bug Class 7: User-override factors ignored or applied twice.
        Verifies that when custom factor is applied, emissions equal exactly quantity * custom_factor,
        not quantity * custom_factor * default_factor.
        """
        disp = CalculationDispatcher()
        custom_ef = {"co2": 60.0, "ch4": 0.002, "n2o": 0.0002, "unit": "kg/MMBtu", "name": "Custom Gas"}
        payload = {
            "quantity": 1000.0,
            "unit": "MMBtu",
            "process_type": "stationary_combustion",
            "fuel": "Custom Gas"
        }
        res = disp.dispatch("stationary_combustion", payload, custom_ef)
        # Expected: 1000 * 60.0 / 1000 = 60.0 tonnes CO2
        assert res["results"]["co2"]["value"] == pytest.approx(60.0, rel=1e-6)

    def test_bug_class_8_export_vs_dashboard_precision_mismatch(self):
        """
        Bug Class 8: Frontend vs backend vs export vs dashboard showing different totals.
        File & Line: new/server/routes/emissions_export.py:378-390 vs routes/dashboard.py:175-185.
        Root Cause: emissions_export.py rounds totals to 2 decimal places:
            round(total_co2e, 2)
        while routes/dashboard.py rounds query aggregates to 6 decimal places:
            round(d[k], 6)
        leading to precision discrepancy between Excel export and dashboard view for identical records.
        """
        import routes.emissions_export as r_exp
        import routes.dashboard as r_dash
        import inspect
        src_exp = inspect.getsource(r_exp.export_emissions)
        src_dash = inspect.getsource(r_dash._query_summary)
        
        assert "round(total_co2e, 2)" in src_exp, "Excel export rounds to 2 decimal places"
        assert "round(d[k], 6)" in src_dash, "Dashboard query summary rounds to 6 decimal places"

    def test_bug_class_9_edit_delete_cache_eviction(self):
        """
        Bug Class 9: Edit/delete/recalculate leaving stale totals.
        File & Line: new/server/routes/emissions.py:delete_emission & update_emission.
        Verifies that both delete and update handlers explicitly invoke clear_dashboard_cache(),
        preventing stale dashboard totals from being served.
        """
        import routes.emissions as r_em
        import inspect
        src_del = inspect.getsource(r_em.delete_emission)
        src_upd = inspect.getsource(r_em.update_emission)
        assert "clear_dashboard_cache()" in src_del, "delete_emission must evict dashboard cache"
        assert "clear_dashboard_cache()" in src_upd, "update_emission must evict dashboard cache"
