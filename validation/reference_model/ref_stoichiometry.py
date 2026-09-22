"""
INDEPENDENT REFERENCE MODEL: Chemical Stoichiometry & Mass Balance
First-principles implementation - ZERO production code imports.
Governing equations:
- Conservation of Atomic Mass (Lavoisier Principle)
- Reaction Stoichiometry: C_n H_m + (n + m/4) O2 -> n CO2 + (m/2) H2O
- Molecular weights based on NIST IUPAC 2021 atomic weights
"""

from .ref_constants import MW_C, MW_H, MW_O, MW_CO2

MW_H2O = 2 * MW_H + MW_O
MW_O2 = 2 * MW_O


def ref_calculate_hydrocarbon_stoichiometry(n_carbons, m_hydrogens):
    """
    Independently calculates stoichiometric properties for any C_n H_m hydrocarbon.
    """
    n = float(n_carbons)
    m = float(m_hydrogens)

    mw_fuel = n * MW_C + m * MW_H
    o2_moles_required = n + m / 4.0
    co2_moles_produced = n
    h2o_moles_produced = m / 2.0

    # Yield factors (kg product / kg fuel)
    kg_co2_per_kg_fuel = (co2_moles_produced * MW_CO2) / mw_fuel
    kg_o2_per_kg_fuel = (o2_moles_required * MW_O2) / mw_fuel
    kg_h2o_per_kg_fuel = (h2o_moles_produced * MW_H2O) / mw_fuel

    # Mass balance closure: Reactants == Products
    mass_reactants = mw_fuel + o2_moles_required * MW_O2
    mass_products = co2_moles_produced * MW_CO2 + h2o_moles_produced * MW_H2O
    balance_error = abs(mass_reactants - mass_products)

    carbon_fraction = (n * MW_C) / mw_fuel

    return {
        "mw_fuel": mw_fuel,
        "carbon_fraction": carbon_fraction,
        "kg_co2_per_kg_fuel": kg_co2_per_kg_fuel,
        "kg_o2_per_kg_fuel": kg_o2_per_kg_fuel,
        "kg_h2o_per_kg_fuel": kg_h2o_per_kg_fuel,
        "mass_balance_error": balance_error,
    }
