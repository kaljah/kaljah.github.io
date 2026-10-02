"""Readable names for stored keys, shared by pages and exports (the exports printed raw keys such as
"tank_flashing" or "Scope 2: indirect_steam" while the tables showed the form's names)."""

SCOPE2_SOURCE_LABELS = {
    "electricity": "Grid Electricity",
    "indirect_steam": "Indirect Steam / Heat",
    "steam": "Indirect Steam / Heat",
    "cogen_allocation": "CHP / Cogen Allocation",
    "cogen": "CHP / Cogen Allocation",
}


def process_label(process_type, default="Other Scope 1"):
    """The Scope 1 form's process name for a stored process key ("tank_flashing" -> its form label)."""
    from services.scope1_calc import PROCESS_LABELS

    p = str(process_type or "").strip()
    if not p:
        return default
    return PROCESS_LABELS.get(p.lower()) or p.replace("_", " ").strip().capitalize()


def scope2_source_label(source_type):
    s = str(source_type or "").strip()
    return SCOPE2_SOURCE_LABELS.get(s.lower(), s.replace("_", " ").capitalize() if s else "Grid Electricity")
