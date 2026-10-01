"""Bulk-import feedback a user can act on.

A large file can be refused row by row for hundreds of distinct reasons (a 100k-row test file produced
193). The upload screen showed the first 100 messages verbatim. These helpers group the reasons by cause,
name the column to fix and say how, and count every row of each group.
"""
import re

# (pattern on the reason text, title, column to fix, how to fix). First match wins.
_RULES = [
    (r"Example row from the template",
     "Example row from the template (not imported)", "date",
     "Delete the template's example rows, or replace EXAMPLE in the date with the real month."),
    (r"is a gas volume but this fuel's heating value is per (gal|bbl|l\b|liquid)",
     "Gas volume unit used with a liquid fuel", "unit",
     "Use a liquid unit (gal, bbl, L, m3) for this fuel, or choose a gas fuel in the fuel column."),
    (r"is a liquid volume but this fuel's heating value is per (scf|m3|gas)",
     "Liquid volume unit used with a gas fuel", "unit",
     "Use a gas unit (scf, Mscf, MMscf, m3) for this fuel, or choose a liquid fuel."),
    (r"is a (mass|energy)[^;]* but this fuel's heating value",
     "Unit does not match how this fuel is measured", "unit",
     "Use the unit family of the fuel (volume for gases and liquids, mass for solids), or add the density."),
    (r"heating value \(HHV\) is required",
     "Heating value missing for this unit", "hhv",
     "Add the fuel's heating value (hhv and hhv_unit), or give the quantity in the unit of the factor."),
    (r"needs the fuel density|needs the density|needs the fuel's density",
     "Unit needs a density to convert (mass vs volume)", "unit",
     "Give the quantity in the fuel's usual unit (volume for gases and liquids, mass for solids), "
     "or add the fuel density (density and density_unit)."),
    (r"is ambiguous",
     "Ambiguous unit (ton / Mt)", "unit",
     "Write tonne or t (1,000 kg), short_ton (2,000 lb) or long_ton; never a bare ton or Mt."),
    (r"Missing unit",
     "Unit missing", "unit", "Fill in the unit of the quantity (for example MMBtu, scf, gal, tonne)."),
    (r"Tank throughput: .* (is not a liquid volume|is a gas volume)",
     "Tank throughput not in a liquid volume", "unit", "Give the tank throughput in bbl, kbbl, m3, gal or L."),
    (r"per-event factor|per well-year factor|is per (well|event|device|component)|counted in events",
     "Quantity unit does not match the factor's basis", "unit",
     "Count what the factor is per: events, wells, devices or components (see the factor's unit)."),
    (r"is a combustion factor and does not apply|does not apply to process",
     "Fuel or factor does not belong to this process", "fuel",
     "Choose a fuel or activity factor listed for this process type."),
    (r"Unknown process type",
     "Process type not recognised", "process_type",
     "Use a process key such as combustion, flaring, venting, tank_flashing, pneumatic or fugitive."),
    (r"Scope 2 \(purchased energy\) source",
     "Scope 2 row in a Scope 1 file", "process_type",
     "Import purchased electricity, steam and heat with the Scope 2 template."),
    (r"Missing process type",
     "Process type missing", "process_type", "Fill in the process column."),
    (r"Unknown factor type",
     "Tier (factor type) missing or not recognised", "factor_type",
     "Fill factor_type with default, custom or specific, or choose one tier for the whole file in step 1."),
    (r"'year' must be between|'month' must be|Invalid date|date .*not recognised|Missing date|period",
     "Date missing or out of range", "date",
     "Use YYYY-MM or YYYY-MM-DD (or year and month columns) with a real reporting period."),
    (r"Region|facility .*not found|Facility .*not found|Unknown facility|not in your allowed",
     "Facility not found or not allowed", "facility_name",
     "Use the exact facility name from Manage Data, within the regions your account can upload to."),
    (r"carries the unit .* but the unit column says",
     "Quantity cell contains a unit", "quantity",
     "Put only the number in quantity and the unit in the unit column."),
    (r"Quantity|quantity",
     "Quantity missing or not a number", "quantity",
     "Enter a plain number (no unit, no text) in quantity."),
    (r"Unknown temperature unit|Unknown pressure unit|temperature unit|pressure unit",
     "Temperature or pressure unit not recognised", "temp_unit / press_unit",
     "Use C, F, K or R for temperature and psig, psia, kPa, bar or atm for pressure."),
    (r"Unknown density unit",
     "Density unit not recognised", "density_unit", "Use kg/m3, kg/L, g/cm3, lb/gal or lb/ft3."),
    (r"Unknown .*unit|unit .*not recognised|Unsupported .*unit|Unit '.*' is not|unit must be",
     "Unit not recognised", "unit",
     "Use one of the units listed in the template (for example scf, Mscf, m3, gal, bbl, L, kg, t, MMBtu)."),
    (r"Contradicting units|Inconsistent activity",
     "Two unit columns disagree", "unit",
     "Give the activity once: keep the unit column and the method's unit column consistent."),
    (r"Duplicate record",
     "Duplicate of an existing record", "equipment_id / source_ref",
     "Tick 'Replace existing records' to overwrite, or give each source its own Equipment ID."),
    (r"Missing required (field|parameter)[^:]*: ([^(;]+)",
     "Required input missing", None, "Fill in the input named in the message."),
    (r"CH4 content|gas analysis|gas composition",
     "Gas composition missing", "ch4_content",
     "Add the gas CH4 content (mol %) or the composition columns c1..c10."),
    (r"factor .* not found|custom factor|Custom factor|No emission factor|not in the catalog|Unknown fuel",
     "Fuel or factor not found", "fuel",
     "Use a fuel name from the catalog or the exact name of a saved custom factor."),
]
_COMPILED = [(re.compile(p, re.I), t, c, f) for p, t, c, f in _RULES]


def _normalise(reason):
    """A message with its values blanked, so rows that fail the same way share one key."""
    r = re.sub(r"'[^']*'", "'…'", str(reason or ""))
    r = re.sub(r"\d[\d.,]*", "N", r)
    r = re.sub(r"^Calculation error for '…': ", "", r)
    return r.strip()[:160]


def classify(reason):
    """(group key, title, column, fix) of one skip reason."""
    for rx, title, column, fix in _COMPILED:
        m = rx.search(str(reason or ""))
        if m:
            if title == "Required input missing":
                name = m.group(2).strip().rstrip(".")
                return f"missing:{name.lower()}", f"Required input missing: {name}", None, f"Fill in {name}."
            return title, title, column, fix
    norm = _normalise(reason)
    return norm, norm or "Other", None, None


def group_skips(skipped, max_rows=20):
    """Groups of skipped rows, largest first: title, column, fix, count, example rows and message."""
    groups = {}
    for s in skipped or []:
        key, title, column, fix = classify(s.get("reason"))
        g = groups.get(key)
        if g is None:
            g = groups[key] = {"title": title, "column": column, "fix": fix, "count": 0, "rows": [],
                               "example": s.get("reason")}
        g["count"] += 1
        if len(g["rows"]) < max_rows and s.get("row") is not None:
            g["rows"].append(s.get("row"))
    return sorted(groups.values(), key=lambda g: -g["count"])
