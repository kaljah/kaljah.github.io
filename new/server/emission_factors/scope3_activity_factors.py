"""Scope 3 activity factors offered by the manual form (client utils/scope3Factors.js), in kg CO2e per
activity unit; the bulk import uses them when a row gives no factor. Sources are cited in the client file:
EPA Supply Chain GHG Emission Factors v1.3.0, EPA GHG Emission Factors Hub 2025 Tables 8-10, API Compendium
2021 Tables 4-5 / 4-6. None = no published default (the user gives the factor).
Kept identical to the client list by tests/test_bulk_uploaders.py."""

SCOPE3_ACTIVITY_FACTORS = {
    1: [
        ("Iron & steel products (NAICS 331110)", "USD", 0.787),
        ("Steel pipe & tube (NAICS 331210)", "USD", 0.36),
        ("Cement (NAICS 327310)", "USD", 3.924),
        ("Organic chemicals (NAICS 325199)", "USD", 1.184),
        ("Inorganic chemicals (NAICS 325180)", "USD", 1.01),
        ("Oil & gas support services (NAICS 213112)", "USD", 0.372),
        ("Engineering services (NAICS 541330)", "USD", 0.103),
    ],
    2: [
        ("Oil & gas field machinery (NAICS 333132)", "USD", 0.219),
        ("Pipeline construction (NAICS 237120)", "USD", 0.277),
        ("Commercial / industrial buildings (NAICS 236220)", "USD", 0.224),
        ("Computers (NAICS 334111)", "USD", 0.058),
    ],
    3: [
        ("Purchased refined fuels, upstream (NAICS 324110)", "USD", 0.27),
        ("Purchased natural gas, upstream (NAICS 211130)", "USD", 0.405),
        ("T&D Losses (Electricity)", "kWh", None),
    ],
    4: [
        ("Truck Transport", "ton-km", 0.12841),
        ("Rail Transport", "ton-km", 0.01451),
        ("Ship Transport", "ton-km", 0.0537),
        ("Air Freight", "ton-km", 0.74991),
    ],
    5: [
        ("Landfill (mixed MSW)", "kg", 0.6393),
        ("Incineration (mixed MSW)", "kg", 0.474),
        ("Recycling (mixed recyclables)", "kg", 0.0992),
        ("Composting (mixed organics)", "kg", 0.1433),
    ],
    6: [
        ("Air - Short Haul (< 300 mi)", "passenger-km", 0.12982),
        ("Air - Medium Haul (300-2300 mi)", "passenger-km", 0.08084),
        ("Air - Long Haul (>= 2300 mi)", "passenger-km", 0.10215),
        ("Passenger Car", "km", 0.18552),
        ("Light-Duty Truck / SUV", "km", 0.24646),
        ("Intercity Rail", "passenger-km", 0.06012),
        ("Bus", "passenger-km", 0.0414),
    ],
    7: [
        ("Passenger Car", "km", 0.18552),
        ("Light-Duty Truck / SUV", "km", 0.24646),
        ("Bus", "passenger-km", 0.0414),
        ("Commuter Rail", "passenger-km", 0.08325),
        ("Transit Rail (subway, tram)", "passenger-km", 0.05808),
    ],
    8: [
        ("Leased buildings (rent) (NAICS 531120)", "USD", 0.246),
        ("Leased Vehicles (passenger car)", "km", 0.18552),
    ],
    9: [
        ("Truck Transport", "ton-km", 0.12841),
        ("Rail Transport", "ton-km", 0.01451),
        ("Ship Transport", "ton-km", 0.0537),
        ("Air Freight", "ton-km", 0.74991),
    ],
    10: [
        ("Processing (Electricity)", "kWh", None),
        ("Processing (Natural Gas)", "mcf", 54.18),
    ],
    11: [
        ("Crude Oil", "bbl", 433.44),
        ("Natural Gas", "mcf", 54.18),
        ("NGL - Ethane", "gal", 4.07),
        ("NGL - Propane", "gal", 5.74),
        ("NGL - Butane", "gal", 6.7),
        ("NGL - Mixed (as LPG)", "gal", 5.7),
    ],
    12: [
        ("Landfill (mixed MSW)", "kg", 0.6393),
        ("Recycling (mixed recyclables)", "kg", 0.0992),
        ("Incineration (mixed MSW)", "kg", 0.474),
    ],
    13: [
        ("Downstream leased buildings (rent) (NAICS 531120)", "USD", 0.246),
    ],
    14: [
        ("Franchise operations", "USD", None),
    ],
    15: [
        ("Equity Investments", "USD", None),
        ("Project Finance", "USD", None),
    ],
}


# activity units written in different ways
_UNIT_ALIASES = {
    "ton-km": {"ton-km", "t-km", "tkm", "tonne-km", "tonne-kilometer", "tonne-kilometre", "tonnes-km"},
    "passenger-km": {"passenger-km", "pkm", "p-km", "passenger-kilometer", "passenger-kilometre"},
    "km": {"km", "vehicle-km", "vkm", "kilometer", "kilometre"},
    "mcf": {"mcf", "mscf", "thousand-scf"},
    "usd": {"usd", "$", "us$", "dollar", "dollars"},
    "kg": {"kg", "kilogram", "kilograms"},
    "kwh": {"kwh"},
    "bbl": {"bbl", "barrel", "barrels"},
    "gal": {"gal", "gallon", "gallons"},
}


def _unit_key(u):
    u = str(u or "").strip().lower().replace(" ", "")
    for key, names in _UNIT_ALIASES.items():
        if u in names:
            return key
    return u


def scope3_activity_factor(category_number, activity, unit):
    """(factor kg CO2e / unit, None) or (None, reason) for a category / activity name / unit."""
    rows = SCOPE3_ACTIVITY_FACTORS.get(int(category_number) if category_number else 0, [])
    name = str(activity or "").strip().lower()
    row = next((r for r in rows if r[0].lower() == name), None)
    if row is None:
        return None, (f"No emission factor given and '{activity or ''}' is not an activity of Category {category_number} "
                      "in the Scope 3 form; give the emission factor or use a listed activity name")
    value, row_unit, factor = row
    if factor is None:
        return None, f"'{value}' has no published default factor; give the emission factor (kg CO2e per {row_unit})"
    if _unit_key(unit) != _unit_key(row_unit):
        return None, f"The factor for '{value}' is per {row_unit}; give the amount in {row_unit} or your own emission factor"
    return factor, None
