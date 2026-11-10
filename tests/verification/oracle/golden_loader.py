"""
GOLDEN TEST CASES LOADER: EXCEL REFERENCE & API COMPENDIUM EXHIBITS
===================================================================
Loads verified golden cases strictly from `/reference/` and cites
every document, equation/table, sheet name, and cell coordinate.

ZERO INVENTED VALUES.
"""

import os
from decimal import Decimal
import openpyxl
from typing import List, Dict, Any

REFERENCE_EXCEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "reference", "comprehensive_golden_cases.xlsx")
)

def load_excel_golden_cases() -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses `reference/comprehensive_golden_cases.xlsx` and extracts
    every golden row with its explicit cell provenance.
    """
    if not os.path.exists(REFERENCE_EXCEL_PATH):
        raise FileNotFoundError(f"Missing reference Excel workbook: {REFERENCE_EXCEL_PATH}")

    wb = openpyxl.load_workbook(REFERENCE_EXCEL_PATH, data_only=True)
    dataset: Dict[str, List[Dict[str, Any]]] = {}

    # 1. Scope 1 Combustion & Venting
    ws1 = wb["Scope1_Combustion_Venting"]
    s1_cases = []
    for r in range(2, ws1.max_row + 1):
        ptype = ws1.cell(r, 1).value
        if not ptype:
            continue
        case = {
            "sheet": "Scope1_Combustion_Venting",
            "row": r,
            "process_type": str(ptype),
            "equipment": str(ws1.cell(r, 2).value or ""),
            "fuel_fluid": str(ws1.cell(r, 3).value or ""),
            "quantity": Decimal(str(ws1.cell(r, 4).value)),
            "unit": str(ws1.cell(r, 5).value),
            "combustion_eff": Decimal(str(ws1.cell(r, 6).value)) if ws1.cell(r, 6).value is not None else None,
            "ch4_mol_pct": Decimal(str(ws1.cell(r, 7).value)) if ws1.cell(r, 7).value is not None else None,
            "co2_mol_pct": Decimal(str(ws1.cell(r, 8).value)) if ws1.cell(r, 8).value is not None else None,
            "expected_co2_tonnes": Decimal(str(ws1.cell(r, 9).value)),
            "cell_co2": f"Scope1_Combustion_Venting!I{r}",
            "expected_ch4_tonnes": Decimal(str(ws1.cell(r, 10).value)),
            "cell_ch4": f"Scope1_Combustion_Venting!J{r}",
            "expected_n2o_tonnes": Decimal(str(ws1.cell(r, 11).value)),
            "cell_n2o": f"Scope1_Combustion_Venting!K{r}",
            "expected_co2e_ar5": Decimal(str(ws1.cell(r, 12).value)),
            "cell_co2e": f"Scope1_Combustion_Venting!L{r}",
            "citation": str(ws1.cell(r, 13).value),
        }
        s1_cases.append(case)
    dataset["scope1_combustion_venting"] = s1_cases

    # 2. Scope 1 Fugitives
    ws2 = wb["Scope1_Fugitives"]
    s1_fug = []
    for r in range(2, ws2.max_row + 1):
        ptype = ws2.cell(r, 1).value
        if not ptype:
            continue
        case = {
            "sheet": "Scope1_Fugitives",
            "row": r,
            "process_type": str(ptype),
            "component": str(ws2.cell(r, 2).value or ""),
            "service": str(ws2.cell(r, 3).value or ""),
            "count_hours": Decimal(str(ws2.cell(r, 4).value)),
            "ef_value": Decimal(str(ws2.cell(r, 5).value)),
            "ef_unit": str(ws2.cell(r, 6).value),
            "ch4_wt_pct": Decimal(str(ws2.cell(r, 7).value)),
            "expected_ch4_tonnes": Decimal(str(ws2.cell(r, 8).value)),
            "cell_ch4": f"Scope1_Fugitives!H{r}",
            "expected_co2e_ar5": Decimal(str(ws2.cell(r, 9).value)),
            "cell_co2e": f"Scope1_Fugitives!I{r}",
            "citation": str(ws2.cell(r, 10).value),
        }
        s1_fug.append(case)
    dataset["scope1_fugitives"] = s1_fug

    # 3. Scope 2 Electricity & Steam
    ws3 = wb["Scope2_Electricity_Steam"]
    s2_cases = []
    for r in range(2, ws3.max_row + 1):
        src = ws3.cell(r, 1).value
        if not src:
            continue
        case = {
            "sheet": "Scope2_Electricity_Steam",
            "row": r,
            "source": str(src),
            "grid_boiler": str(ws3.cell(r, 2).value or ""),
            "consumption": Decimal(str(ws3.cell(r, 3).value)),
            "unit": str(ws3.cell(r, 4).value),
            "grid_factor": Decimal(str(ws3.cell(r, 5).value)) if ws3.cell(r, 5).value is not None else None,
            "boiler_eff": Decimal(str(ws3.cell(r, 6).value)) if ws3.cell(r, 6).value is not None else None,
            "market_instrument": str(ws3.cell(r, 7).value or ""),
            "expected_location_co2e": Decimal(str(ws3.cell(r, 8).value)),
            "cell_location": f"Scope2_Electricity_Steam!H{r}",
            "expected_market_co2e": Decimal(str(ws3.cell(r, 9).value)),
            "cell_market": f"Scope2_Electricity_Steam!I{r}",
            "citation": str(ws3.cell(r, 10).value),
        }
        s2_cases.append(case)
    dataset["scope2_electricity_steam"] = s2_cases

    # 4. Scope 3 Value Chain
    ws4 = wb["Scope3_Value_Chain"]
    s3_cases = []
    for r in range(2, ws4.max_row + 1):
        cat_num = ws4.cell(r, 1).value
        if not cat_num:
            continue
        case = {
            "sheet": "Scope3_Value_Chain",
            "row": r,
            "category_number": str(cat_num),
            "category_name": str(ws4.cell(r, 2).value or ""),
            "activity_commodity": str(ws4.cell(r, 3).value or ""),
            "activity_spend": Decimal(str(ws4.cell(r, 4).value)),
            "unit": str(ws4.cell(r, 5).value),
            "emission_factor": Decimal(str(ws4.cell(r, 6).value)),
            "factor_unit": str(ws4.cell(r, 7).value),
            "expected_co2e_tonnes": Decimal(str(ws4.cell(r, 8).value)),
            "cell_co2e": f"Scope3_Value_Chain!H{r}",
            "citation": str(ws4.cell(r, 9).value),
        }
        s3_cases.append(case)
    dataset["scope3_value_chain"] = s3_cases

    # 5. Derived Intensities & Equity
    ws5 = wb["Derived_Intensities_Equity"]
    int_cases = []
    for r in range(2, ws5.max_row + 1):
        metric = ws5.cell(r, 1).value
        if not metric:
            continue
        case = {
            "sheet": "Derived_Intensities_Equity",
            "row": r,
            "metric_name": str(metric),
            "definition": str(ws5.cell(r, 2).value or ""),
            "numerator": Decimal(str(ws5.cell(r, 3).value)),
            "denominator": Decimal(str(ws5.cell(r, 4).value)),
            "expected_value": Decimal(str(ws5.cell(r, 5).value)),
            "cell_value": f"Derived_Intensities_Equity!E{r}",
            "unit": str(ws5.cell(r, 6).value),
            "target_limit": Decimal(str(ws5.cell(r, 7).value)),
            "citation": str(ws5.cell(r, 8).value),
        }
        int_cases.append(case)
    dataset["derived_intensities"] = int_cases

    # 6. Uncertainty GUM Propagation
    ws6 = wb["Uncertainty_GUM_Verification"]
    unc_cases = []
    for r in range(2, ws6.max_row + 1):
        stream = ws6.cell(r, 1).value
        if not stream:
            continue
        case = {
            "sheet": "Uncertainty_GUM_Verification",
            "row": r,
            "source_stream": str(stream),
            "emission_tonnes": Decimal(str(ws6.cell(r, 2).value)),
            "ef_1sigma": Decimal(str(ws6.cell(r, 3).value)),
            "activity_1sigma": Decimal(str(ws6.cell(r, 4).value)),
            "expected_combined_1sigma_pct": Decimal(str(ws6.cell(r, 5).value)),
            "cell_combined": f"Uncertainty_GUM_Verification!E{r}",
            "coverage_factor_k": Decimal(str(ws6.cell(r, 6).value)),
            "expected_95ci_pct": Decimal(str(ws6.cell(r, 7).value)),
            "cell_95ci": f"Uncertainty_GUM_Verification!G{r}",
            "expected_lower_t": Decimal(str(ws6.cell(r, 8).value)),
            "expected_upper_t": Decimal(str(ws6.cell(r, 9).value)),
        }
        unc_cases.append(case)
    dataset["uncertainty_gum"] = unc_cases

    return dataset


# =============================================================================
# API COMPENDIUM 2021 WORKED EXAMPLES (EXHIBITS) INVENTORY
# =============================================================================
COMPENDIUM_EXHIBITS = [
    {
        "exhibit": "Exhibit 4.1",
        "description": "Natural gas fuel combustion emissions based on fuel use and default emission factors",
        "citation": "API Compendium 2021 Exhibit 4.1, Table 4-3",
        "inputs": {"fuel_volume_mscf": Decimal("380000.0"), "fuel_type": "natural_gas"},
        "factors": {"co2_kg_per_mscf": Decimal("53.06")}, # Table 4-3
        "expected": {"co2_tonnes": Decimal("20162.8")},
        "tolerance": Decimal("1.0"),
    },
    {
        "exhibit": "Exhibit 4.2",
        "description": "Fuel gas combustion emissions based on fuel analysis (carbon content)",
        "citation": "API Compendium 2021 Exhibit 4.2, Eq. 4-4",
        "inputs": {
            "fuel_mass_kg": Decimal("10000000.0"),
            "carbon_wt_fraction": Decimal("0.748"),
            "oxidation_fraction": Decimal("1.0"),
        },
        "expected": {"co2_tonnes": Decimal("27407.8")},
        "tolerance": Decimal("1.0"),
    },
    {
        "exhibit": "Exhibit 5.1",
        "description": "Routine and non-routine flaring emissions using dual combustion efficiency",
        "citation": "API Compendium 2021 Exhibit 5.1, Eq. 5-4, 5-5",
        "inputs": {
            "flare_vol_m3": Decimal("100000.0"),
            "c1_mol_fraction": Decimal("0.80"),
            "native_co2_mol_fraction": Decimal("0.05"),
            "combustion_eff": Decimal("0.98"),
            "destruction_eff": Decimal("0.98"),
        },
        "expected": {
            "ch4_tonnes": Decimal("1.083555"),
            "co2_tonnes": Decimal("215.5011"),
        },
        "tolerance": Decimal("0.01"),
    },
    {
        "exhibit": "Exhibit 6-14",
        "description": "Continuous high-bleed pneumatic device methane emissions",
        "citation": "API Compendium 2021 Exhibit 6-14, Table 6-14",
        "inputs": {
            "device_count": Decimal("10"),
            "hours": Decimal("8760"),
            "ef_scf_hr": Decimal("37.3"),
            "ch4_mol_fraction": Decimal("0.85"),
        },
        "expected": {"ch4_tonnes": Decimal("53.2605")},
        "tolerance": Decimal("0.01"),
    },
    {
        "exhibit": "Exhibit 7-4",
        "description": "Component fugitive emissions from gas service valves and flanges",
        "citation": "API Compendium 2021 Exhibit 7-4, Table 7-11",
        "inputs": {
            "valves_count": Decimal("500"),
            "flanges_count": Decimal("2000"),
            "hours": Decimal("8760"),
            "ch4_wt_fraction": Decimal("0.85"),
        },
        "expected": {
            "valves_ch4_tonnes": Decimal("16.7535"),
            "flanges_ch4_tonnes": Decimal("2.9784"),
        },
        "tolerance": Decimal("0.01"),
    },
    {
        "exhibit": "Exhibit 8.3",
        "description": "Scope 2 indirect emissions from purchased steam with boiler efficiency and transmission loss",
        "citation": "API Compendium 2021 Exhibit 8.3, Section 8.1.5",
        "inputs": {
            "delivered_heat_mmbtu": Decimal("1000.0"),
            "ef_co2_kg_per_mmbtu": Decimal("53.1145"),
            "boiler_eff": Decimal("0.82"),
            "transmission_loss": Decimal("0.05"),
        },
        "expected": {"co2_tonnes_multiplicative": Decimal("68.1829")},
        "tolerance": Decimal("0.01"),
    },
]
