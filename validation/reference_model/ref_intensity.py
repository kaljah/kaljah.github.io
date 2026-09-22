"""
INDEPENDENT REFERENCE MODEL: Intensity Metrics & OGMP 2.0 Levels
First-principles implementation - ZERO production code imports.
Governing standards:
- OGMP 2.0 Reporting Framework (UNEP / IMEO)
- IOGP Report 634: Carbon intensity indicators
"""

from .ref_constants import DENSITY_CH4, CONV_MSCF_TO_M3


def ref_calculate_carbon_intensity(scope1_tco2e, scope2_tco2e, oil_bbl, gas_mscf):
    """
    Independently calculates carbon intensity in kg CO2e / boe.
    BOE formula: Oil (bbl) + Gas (mscf) / 5.8
    """
    total_tco2e = float(scope1_tco2e or 0.0) + float(scope2_tco2e or 0.0)
    boe = float(oil_bbl or 0.0) + (float(gas_mscf or 0.0) / 5.8)
    if boe <= 0:
        return 0.0
    return (total_tco2e * 1000.0) / boe


def ref_calculate_methane_loss_rate(methane_emissions_tonnes, gas_production_mscf, ch4_mole_fraction=0.90):
    """
    Independently calculates methane loss rate (% of produced gas).
    Loss Rate = (CH4 emissions tonnes / Total CH4 produced tonnes) * 100
    """
    ch4_t = float(methane_emissions_tonnes or 0.0)
    prod_mscf = float(gas_production_mscf or 0.0)
    if prod_mscf <= 0:
        return 0.0

    prod_m3 = prod_mscf * CONV_MSCF_TO_M3
    prod_ch4_kg = prod_m3 * float(ch4_mole_fraction or 0.90) * DENSITY_CH4
    prod_ch4_tonnes = prod_ch4_kg / 1000.0
    if prod_ch4_tonnes <= 0:
        return 0.0

    return (ch4_t / prod_ch4_tonnes) * 100.0


def ref_evaluate_ogmp_level(has_top_down, top_down_reconciled, has_site_specific_ef, has_generic_ef):
    """
    OGMP 2.0 Gold Standard Level Evaluation:
    Level 5: Level 4 + reconciled top-down measurement
    Level 4: Site-specific direct measurement (bottom-up source level)
    Level 3: Generic source-level factors
    Level 2: Facility / regional top-level estimates
    Level 1: Venture / aggregate level
    """
    if has_top_down and top_down_reconciled:
        return 5
    elif has_site_specific_ef:
        return 4
    elif has_generic_ef:
        return 3
    else:
        return 1
