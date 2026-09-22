"""
INDEPENDENT REFERENCE MODEL: Scope 3 Value Chain Emissions
Covers all 15 categories under the GHG Protocol Corporate Value Chain Standard.
First-principles implementation - ZERO production code imports.
Governing equations:
- GHG Protocol Corporate Value Chain (Scope 3) Standard (2011)
- Technical Guidance for Calculating Scope 3 Emissions (v1.0)
- US EPA Supply Chain Greenhouse Gas Emission Factors for US Industries and Commodities (USEEIO)
"""

SCOPE3_CATEGORIES = {
    1: "Purchased Goods and Services",
    2: "Capital Goods",
    3: "Fuel- and Energy-Related Activities",
    4: "Upstream Transportation and Distribution",
    5: "Waste Generated in Operations",
    6: "Business Travel",
    7: "Employee Commuting",
    8: "Upstream Leased Assets",
    9: "Downstream Transportation and Distribution",
    10: "Processing of Sold Products",
    11: "Use of Sold Products",
    12: "End-of-Life Treatment of Sold Products",
    13: "Downstream Leased Assets",
    14: "Franchises",
    15: "Investments",
}


def ref_calculate_scope3(
    category_id,
    activity_value,
    emission_factor,
    calculation_method="activity_based",
    ef_unit="kg_per_unit",
):
    """
    Independently calculates Scope 3 emissions for any of the 15 categories.
    Returns: dict with category_id, category_name, co2e_tonnes
    """
    if activity_value is None or float(activity_value) <= 0:
        return {"category_id": category_id, "co2e": 0.0}

    act = float(activity_value)
    ef = float(emission_factor or 0.0)

    # Standard formula: E = Activity * EF
    # If EF is in kg CO2e / unit -> divide by 1000 to get tonnes
    # If EF is in tonne CO2e / unit -> no division needed
    u = str(ef_unit or "").lower()
    if "tonne" in u or "tco2" in u or "mt" in u:
        co2e_tonnes = act * ef
    else:
        co2e_tonnes = (act * ef) / 1000.0

    cat_name = SCOPE3_CATEGORIES.get(int(category_id), f"Category {category_id}")
    return {
        "category_id": int(category_id),
        "category_name": cat_name,
        "co2e": co2e_tonnes,
        "method": calculation_method,
    }
