"""Activity amount, unit and label of a Scope 2 record for exports and reports.

Scope 2 records keep their activity in one of four columns depending on the source type; indirect
steam / heat is stored as delivered energy (heat_mmbtu). Exports used electricity_kwh for every
record, so a steam entry read "Grid Electricity, 0 kWh" (browser test #11).
"""


def scope2_activity(e):
    st = str(getattr(e, "source_type", "") or "electricity").strip().lower()
    elec = float(getattr(e, "electricity_kwh", 0) or 0)
    heat = float(getattr(e, "heat_mmbtu", 0) or 0)
    steam = float(getattr(e, "steam_ton", 0) or 0)
    cool = float(getattr(e, "cooling_ton", 0) or 0)
    if "cool" in st:
        return cool, "ton cooling", "Purchased cooling"
    if "cogen" in st or "chp" in st:
        if heat > 0:
            return heat, "MMBtu", "CHP / cogeneration allocation"
        return elec, "kWh", "CHP / cogeneration allocation"
    if "steam" in st or "heat" in st:
        if heat > 0 or steam == 0:
            return heat, "MMBtu", "Purchased steam / heat"
        return steam, "t steam", "Purchased steam / heat"
    return elec, "kWh", getattr(e, "grid_region", None) or "Grid electricity"
