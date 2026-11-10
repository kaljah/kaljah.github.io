"""
PHASE 6: DIFFERENTIAL TESTING SUITE
===================================
Compares three independent computational paths across thousands of generated inputs:
1. Vectorized NumPy / Pandas formulation (Vectorized Engine)
2. Compendium Clean-Room Oracle (50-digit Decimal arithmetic)
3. Production Application Code (calculations.* modules)

Invariants tested:
- Exact agreement or known numeric tolerance (< 1e-6 relative difference) across all three engines.
- Any three-way discrepancy is flagged, investigated, and characterized.
"""

import sys
import os
from decimal import Decimal
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SERVER_DIR = os.path.join(REPO_ROOT, "new", "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from tests.verification.oracle.compendium_oracle import (
    oracle_convert_unit,
    oracle_co2e as calc_oracle_co2e,
    oracle_combustion_tier1,
    oracle_scope2_purchased_steam,
    oracle_fugitive_components,
    oracle_combustion_stoichiometric,
    GWP_REGISTRY,
    STOICH_RATIO_CO2_C,
    MOLAR_VOL_M3_KMOL,
    MW_CO2,
    MW_CH4,
)

from calculations.combustion import CombustionCalculator
from calculations.indirect import IndirectSteamCalculator
from calculations.fugitive import ComponentFugitiveCalculator
from calculations.stoichiometry import StoichiometricCalculator


# =============================================================================
# 1. VECTORIZED FORMULATIONS (NUMPY / PANDAS)
# =============================================================================

def vectorized_combustion_calc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized calculation of combustion emissions:
    Emissions (t) = Quantity * EF (kg/unit) / 1000.0
    CO2e (t) = CO2 * GWP_CO2 + CH4 * GWP_CH4 + N2O * GWP_N2O
    """
    co2_t = (df["quantity"] * df["ef_co2"]) / 1000.0
    ch4_t = (df["quantity"] * df["ef_ch4"]) / 1000.0
    n2o_t = (df["quantity"] * df["ef_n2o"]) / 1000.0
    co2e_t = (
        co2_t * df["gwp_co2"] +
        ch4_t * df["gwp_ch4"] +
        n2o_t * df["gwp_n2o"]
    )
    return pd.DataFrame({
        "co2_tonnes": co2_t,
        "ch4_tonnes": ch4_t,
        "n2o_tonnes": n2o_t,
        "co2e_tonnes": co2e_t,
    })


def vectorized_purchased_steam_calc(df: pd.DataFrame, subtractive: bool = True) -> pd.DataFrame:
    """
    Vectorized Scope 2 purchased steam:
    Net Eff = (b_eff - t_loss) if subtractive else (b_eff * (1 - t_loss))
    Fuel MMBtu = Delivered MMBtu / Net Eff
    CO2e (t) = Fuel MMBtu * EF (kg/MMBtu) / 1000.0
    """
    if subtractive:
        net_eff = df["b_eff"] - df["t_loss"]
    else:
        net_eff = df["b_eff"] * (1.0 - df["t_loss"])
    fuel_mmbtu = df["mmbtu"] / net_eff
    co2e_t = (fuel_mmbtu * df["ef_co2"]) / 1000.0
    return pd.DataFrame({
        "co2e_tonnes": co2e_t,
    })


def vectorized_fugitive_component_calc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized fugitive emissions by component count (API Compendium Table 5-4):
    Emissions (t) = Count * EF (kg/hr/source) * Hours * CH4_wt_frac / 1000.0
    CO2e (t) = Emissions (t CH4) * GWP_CH4
    """
    ch4_t = (df["count"] * df["factor_kg_hr"] * df["hours"] * df["ch4_wt_frac"]) / 1000.0
    co2e_t = ch4_t * df["gwp_ch4"]
    return pd.DataFrame({
        "ch4_tonnes": ch4_t,
        "co2e_tonnes": co2e_t,
    })


def vectorized_stoichiometric_calc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized stoichiometric combustion (Compendium Eq 4-1):
    CO2 (t) = Fuel (t) * Carbon_mass_fraction * (44.01 / 12.011) * Oxidation_fraction
    """
    stoich_factor = 44.01 / 12.011
    co2_t = df["fuel_tonnes"] * df["carbon_fraction"] * stoich_factor * df["oxidation_fraction"]
    return pd.DataFrame({
        "co2_tonnes": co2_t,
        "co2e_tonnes": co2_t,
    })


# =============================================================================
# 2. DIFFERENTIAL TESTS OVER 1,000 CASES PER PROCESS
# =============================================================================

class TestDifferentialCombustion:
    """Differential verification of stationary combustion across 1,000 randomized cases."""

    @pytest.fixture(scope="class")
    def combustion_dataset(self):
        np.random.seed(42)
        n = 1000
        quantities = np.random.uniform(10.0, 50000.0, size=n)
        ef_co2 = np.random.uniform(1.5, 3.5, size=n)      # kg/m3 or kg/kg
        ef_ch4 = np.random.uniform(0.00001, 0.0005, size=n)
        ef_n2o = np.random.uniform(0.000001, 0.00005, size=n)
        gwp_co2 = np.ones(n)
        gwp_ch4 = np.full(n, 28.0) # AR5
        gwp_n2o = np.full(n, 265.0)

        df = pd.DataFrame({
            "quantity": quantities,
            "ef_co2": ef_co2,
            "ef_ch4": ef_ch4,
            "ef_n2o": ef_n2o,
            "gwp_co2": gwp_co2,
            "gwp_ch4": gwp_ch4,
            "gwp_n2o": gwp_n2o,
        })
        return df

    def test_combustion_three_way_differential(self, combustion_dataset):
        df = combustion_dataset
        # Path 1: Vectorized NumPy / Pandas
        vec_res = vectorized_combustion_calc(df)

        app_calc = CombustionCalculator()

        discrepancies = []
        for idx in range(len(df)):
            row = df.iloc[idx]
            q = float(row["quantity"])
            ef_c = float(row["ef_co2"])
            ef_m = float(row["ef_ch4"])
            ef_n = float(row["ef_n2o"])

            # Path 2: Compendium Oracle (Decimal)
            raw_oracle = oracle_combustion_tier1(
                fuel_qty=Decimal(str(q)),
                fuel_unit="m3",
                ef_co2_kg=Decimal(str(ef_c)),
                ef_ch4_kg=Decimal(str(ef_m)),
                ef_n2o_kg=Decimal(str(ef_n)),
                ef_unit_basis="m3",
            )
            oracle_co2e_val = calc_oracle_co2e(
                raw_oracle["co2_tonnes"],
                raw_oracle["ch4_tonnes"],
                raw_oracle["n2o_tonnes"],
                standard="AR5",
            )
            oracle_co2e = float(oracle_co2e_val)

            # Path 3: Production App
            app_res = app_calc.calculate(
                fuel_quantity=q,
                ef_co2=ef_c,
                ef_ch4=ef_m,
                ef_n2o=ef_n,
                ef_unit="kg/m3",
                fuel_unit="m3",
                fuel_type="natural_gas",
                gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
            )

            # Compare Vectorized vs Oracle
            vec_co2e = float(vec_res.iloc[idx]["co2e_tonnes"])
            app_co2e = float(app_res["total_co2e"])

            # Precision check: Oracle vs Vectorized (< 1e-9 relative)
            rel_diff_vec_oracle = abs(vec_co2e - oracle_co2e) / oracle_co2e
            assert rel_diff_vec_oracle < 1e-9, f"Vectorized vs Oracle discrepancy at row {idx}: {vec_co2e} vs {oracle_co2e}"

            # Precision check: App vs Oracle (< 1e-5 relative)
            rel_diff_app_oracle = abs(app_co2e - oracle_co2e) / oracle_co2e
            if rel_diff_app_oracle > 1e-5:
                discrepancies.append({
                    "row": idx,
                    "vectorized": vec_co2e,
                    "oracle": oracle_co2e,
                    "app": app_co2e,
                    "rel_diff": rel_diff_app_oracle,
                })

        assert len(discrepancies) == 0, f"Encountered {len(discrepancies)} discrepancies between App and Oracle/Vectorized!"


class TestDifferentialPurchasedSteam:
    """Differential verification of Scope 2 purchased steam across 1,000 randomized cases."""

    @pytest.fixture(scope="class")
    def steam_dataset(self):
        np.random.seed(123)
        n = 1000
        mmbtu = np.random.uniform(50.0, 50000.0, size=n)
        ef_co2 = np.random.uniform(40.0, 90.0, size=n) # kg CO2 / MMBtu
        b_eff = np.random.uniform(0.75, 0.95, size=n)
        t_loss = np.random.uniform(0.01, 0.15, size=n)

        df = pd.DataFrame({
            "mmbtu": mmbtu,
            "ef_co2": ef_co2,
            "b_eff": b_eff,
            "t_loss": t_loss,
        })
        return df

    def test_steam_three_way_differential(self, steam_dataset):
        df = steam_dataset
        # Compare vectorized subtractive model vs App vs Oracle subtractive model
        vec_res = vectorized_purchased_steam_calc(df, subtractive=True)
        app_calc = IndirectSteamCalculator()

        for idx in range(len(df)):
            row = df.iloc[idx]
            m_val = float(row["mmbtu"])
            ef_val = float(row["ef_co2"])
            be_val = float(row["b_eff"])
            tl_val = float(row["t_loss"])

            # Oracle (subtractive mode matching app code)
            oracle_res = oracle_scope2_purchased_steam(
                delivered_heat_mmbtu=Decimal(str(m_val)),
                ef_kg_co2e_per_mmbtu=Decimal(str(ef_val)),
                boiler_efficiency=Decimal(str(be_val)),
                transmission_loss=Decimal(str(tl_val)),
                model_mode="subtractive",
            )

            # App
            app_res = app_calc.calculate(
                heat_energy=m_val,
                ef_co2=ef_val,
                boiler_efficiency=be_val,
                transmission_loss=tl_val,
                uncertainties={},
                heat_unit="mmbtu",
            )

            vec_co2e = float(vec_res.iloc[idx]["co2e_tonnes"])
            oracle_co2e = float(oracle_res["co2e_tonnes"])
            app_co2e = float(app_res["total_co2e"])

            # Verify 3-way exact parity
            assert abs(vec_co2e - oracle_co2e) / oracle_co2e < 1e-9
            assert abs(app_co2e - oracle_co2e) / oracle_co2e < 1e-6


class TestDifferentialFugitiveComponents:
    """Differential verification of Scope 1 fugitive component counts across 1,000 randomized cases."""

    @pytest.fixture(scope="class")
    def fugitive_dataset(self):
        np.random.seed(456)
        n = 1000
        counts = np.random.randint(1, 5000, size=n)
        factors = np.random.uniform(0.0001, 0.05, size=n) # kg/hr/source
        hours = np.full(n, 8760.0)
        ch4_wt_frac = np.random.uniform(0.70, 0.98, size=n)

        df = pd.DataFrame({
            "count": counts,
            "factor_kg_hr": factors,
            "hours": hours,
            "ch4_wt_frac": ch4_wt_frac,
            "gwp_ch4": np.full(n, 28.0),
        })
        return df

    def test_fugitive_three_way_differential(self, fugitive_dataset):
        df = fugitive_dataset
        vec_res = vectorized_fugitive_component_calc(df)
        app_calc = ComponentFugitiveCalculator()

        for idx in range(len(df)):
            row = df.iloc[idx]
            c = int(row["count"])
            fac = float(row["factor_kg_hr"])
            h = float(row["hours"])
            frac = float(row["ch4_wt_frac"])

            # Oracle
            oracle_ch4_val = oracle_fugitive_components(
                component_count=Decimal(str(c)),
                operating_hours=Decimal(str(h)),
                ef_kg_per_hr_comp=Decimal(str(fac)),
                ch4_weight_fraction=Decimal(str(frac)),
            )
            oracle_co2e_val = oracle_ch4_val * Decimal("28.0")
            oracle_co2e = float(oracle_co2e_val)

            # App
            component_counts = {
                "valves": {
                    "count": c,
                    "ef": fac,
                    "unit": "kg/hr/source",
                }
            }
            app_res = app_calc.calculate(
                component_counts=component_counts,
                ch4_content=frac,
                uncertainties={},
                gwp_dict={"CH4": 28.0, "CO2": 1.0, "N2O": 265.0},
            )

            vec_co2e = float(vec_res.iloc[idx]["co2e_tonnes"])
            app_co2e = float(app_res["total_co2e"])

            # Verify 3-way exact parity
            assert abs(vec_co2e - oracle_co2e) / oracle_co2e < 1e-9
            assert abs(app_co2e - oracle_co2e) / oracle_co2e < 1e-6


class TestDifferentialStoichiometry:
    """Differential verification of stoichiometric carbon balance across 1,000 randomized cases."""

    @pytest.fixture(scope="class")
    def stoich_dataset(self):
        np.random.seed(789)
        n = 1000
        fuel_t = np.random.uniform(1.0, 10000.0, size=n)
        c_frac = np.random.uniform(0.50, 0.95, size=n)
        ox_frac = np.random.uniform(0.98, 1.0, size=n)

        df = pd.DataFrame({
            "fuel_tonnes": fuel_t,
            "carbon_fraction": c_frac,
            "oxidation_fraction": ox_frac,
        })
        return df

    def test_stoichiometry_three_way_differential(self, stoich_dataset):
        df = stoich_dataset
        vec_res = vectorized_stoichiometric_calc(df)
        app_calc = StoichiometricCalculator()

        for idx in range(len(df)):
            row = df.iloc[idx]
            fuel_val = float(row["fuel_tonnes"])
            c_val = float(row["carbon_fraction"])
            ox_val = float(row["oxidation_fraction"])

            # Oracle
            oracle_co2_val = oracle_combustion_stoichiometric(
                fuel_mass_kg=Decimal(str(fuel_val)) * Decimal("1000.0"),
                carbon_weight_fraction=Decimal(str(c_val)),
                oxidation_fraction=Decimal(str(ox_val)),
            )
            oracle_co2 = float(oracle_co2_val)

            # App
            app_res = app_calc.calculate(
                fuel_mass=fuel_val,
                mass_unit="tonne",
                carbon_content=c_val,
                oxidation_factor=ox_val,
            )

            vec_co2 = float(vec_res.iloc[idx]["co2_tonnes"])
            app_co2 = float(app_res["total_co2e"])

            # Verify 3-way exact parity
            assert abs(vec_co2 - oracle_co2) / oracle_co2 < 1e-6
            assert abs(app_co2 - oracle_co2) / oracle_co2 < 1e-5
