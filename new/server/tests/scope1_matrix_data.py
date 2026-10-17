"""Scope 1 entry test cases: activity cases per tier, an all-pairs generator and coverage metrics.

Shared by tests/test_scope1_entry_matrix.py and scripts/gen_scope1_test_data.py, so the 10,000-row
files handed to manual / e2e testers use the same cases the suite checks.

Tiers as the API knows them (`factor_source`): Tier 1 = "default" (catalog factor), Tier 2 = "custom"
(an approved custom factor, or the catalog factor with a site HHV), Tier 3 = "specific" (entered
emission factors). Expected values come from the source tables, never from the code under test.
"""
import csv
import io
import itertools

# AR5 (the default standard): CH4 28, N2O 265. Natural gas, API Compendium 2021 Table 4-5 / 4-6.
CH4_GWP, N2O_GWP = 28, 265
NG_KG_CO2E_PER_MMBTU = 53.06 + 0.001 * CH4_GWP + 0.0001 * N2O_GWP
NG_HHV_BTU_SCF = 1020

CUSTOM_FACTOR = {"name": "Matrix Site Fuel", "co2_factor": 70.0, "ch4_factor": 0.01, "n2o_factor": 0.001,
                 "unit": "kg/MMBtu", "source": "Site lab report 2025"}
SITE_HHV = 1050          # Btu/scf
T3_FACTORS = {"co2": 1.9, "co2Unit": "kg/m3", "ch4": 0.01, "ch4Unit": "kg/m3"}

# id -> (tier, process_type, fuel, unit, extra payload fields)
CASES = {
    "t1_ng_scf": (1, "combustion", "Natural Gas", "scf", {}),
    "t1_ng_mmbtu": (1, "combustion", "Natural Gas", "MMBtu", {}),
    "t1_diesel_gal": (1, "combustion", "Diesel (No. 2 Fuel Oil)", "gal", {}),
    "t1_gasoline_mobile": (1, "mobile", "Motor Gasoline", "gal", {}),
    "t1_lpg_gal": (1, "combustion", "Propane (Liquid/LPG)", "gal", {}),
    "t1_resid_bbl": (1, "combustion", "Residual Fuel Oil (No. 6)", "bbl", {}),
    "t1_flare_m3": (1, "flaring", "Natural Gas (Flaring)", "m3", {}),
    "t1_vent_m3": (1, "venting", "Natural Gas (Venting/Blowdown)", "m3", {}),
    "t2_custom_factor": (2, "combustion", CUSTOM_FACTOR["name"], "MMBtu", {}),
    "t2_site_hhv": (2, "combustion", "Natural Gas", "scf", {"hhv": SITE_HHV, "hhv_unit": "Btu/scf"}),
    "t3_entered_factors": (3, "combustion", "Natural Gas", "m3",
                           {"hhv": 1020, "combustion_efficiency": 0.995, "specific_factors": T3_FACTORS}),
}
FACTOR_SOURCE = {1: "default", 2: "custom", 3: "specific"}

# Boundary values: zero activity (a zero record), the smallest typical reading, a typical month, a large one.
QUANTITIES = (0, 0.01, 1234.5, 250000)
MONTHS = (1, 6, 12)
YEARS = (1990, 2025, 2027)   # 2027 = current year + 1, the upper bound in 2026
ROLES = ("admin", "superuser", "user")
PATHS = ("single", "json", "file")

PARAMS = {"case": tuple(CASES), "quantity": QUANTITIES, "month": MONTHS, "year": YEARS,
          "facility": (0, 1), "role": ROLES, "path": PATHS}


def allowed(row):
    """Combinations the product does not offer: entered Tier 3 factors have no file column."""
    return not (row.get("path") == "file" and str(row.get("case", "")).startswith("t3_"))


def expected_tonnes(case, qty):
    """Independent expected values (tonnes) where the source tables give them; None = check by parity."""
    if case == "t1_ng_scf":
        return {"co2e_total": qty * NG_HHV_BTU_SCF / 1e6 * NG_KG_CO2E_PER_MMBTU / 1000}
    if case == "t1_ng_mmbtu":
        return {"co2e_total": qty * NG_KG_CO2E_PER_MMBTU / 1000}
    if case == "t2_custom_factor":
        f = CUSTOM_FACTOR
        return {"co2e_total": qty * (f["co2_factor"] + f["ch4_factor"] * CH4_GWP + f["n2o_factor"] * N2O_GWP) / 1000}
    if case == "t2_site_hhv":
        return {"co2e_total": qty * SITE_HHV / 1e6 * NG_KG_CO2E_PER_MMBTU / 1000}
    if case == "t3_entered_factors":
        return {"co2_emissions": qty * T3_FACTORS["co2"] / 1000, "ch4_emissions": qty * T3_FACTORS["ch4"] / 1000}
    return None


# ---------------------------------------------------------------- all-pairs generation
def _pairs(params, ok=allowed):
    names = list(params)
    out = set()
    for a, b in itertools.combinations(names, 2):
        for va in params[a]:
            for vb in params[b]:
                if ok({a: va, b: vb}):
                    out.add(((a, va), (b, vb)))
    return out


def _row_pairs(row, names):
    return {((a, row[a]), (b, row[b])) for a, b in itertools.combinations(names, 2) if a in row and b in row}


def pairwise(params, ok=allowed):
    """Greedy all-pairs: every allowed pair of values of any two parameters appears in at least one row.
    Deterministic (no randomness), so a failing row is reproducible by its index."""
    names = list(params)
    todo = _pairs(params, ok)
    rows = []
    while todo:
        (a, va), (b, vb) = min(todo, key=repr)
        row = {a: va, b: vb}
        for n in names:
            if n in row:
                continue
            best, gain = None, -1
            for v in params[n]:
                cand = {**row, n: v}
                if not ok(cand):
                    continue
                g = len(_row_pairs(cand, names) & todo)
                if g > gain:
                    best, gain = v, g
            row[n] = best
        todo -= _row_pairs(row, names)
        rows.append(row)
    return rows


def with_triples(rows, params, triple=("case", "role", "path"), ok=allowed):
    """Adds rows until every allowed combination of the three critical parameters is present."""
    have = {tuple(r[k] for k in triple) for r in rows}
    others = [n for n in params if n not in triple]
    i = 0
    for combo in itertools.product(*(params[k] for k in triple)):
        row = dict(zip(triple, combo))
        if combo in have or not ok(row):
            continue
        for n in others:
            row[n] = params[n][i % len(params[n])]
        i += 1
        rows.append(row)
    return rows


def coverage(rows, params, ok=allowed):
    """Coverage metrics: share of allowed pairs covered, per-parameter value coverage."""
    universe = _pairs(params, ok)
    covered = set().union(*(_row_pairs(r, list(params)) for r in rows)) & universe if rows else set()
    values = {n: len({r[n] for r in rows}) / len(params[n]) for n in params}
    return {"pairs_total": len(universe), "pairs_covered": len(covered),
            "pair_coverage": len(covered) / len(universe) if universe else 1.0, "value_coverage": values}


def matrix_rows():
    rows = with_triples(pairwise(PARAMS), PARAMS)
    for i, r in enumerate(rows):
        r["eq"] = f"MX{i:04d}"
    return rows


# ---------------------------------------------------------------- payloads
def payload(case, qty, year, month, facility_ref, eq, custom_factor_id=None):
    """The JSON body of a single POST / a JSON import record."""
    tier, process, fuel, unit, extra = CASES[case]
    body = {"year": year, "month": month, "facility_id": facility_ref, "process_type": process, "fuel": fuel,
            "amount": qty, "unit": unit, "factor_source": FACTOR_SOURCE[tier], "equipment_id": eq, **extra}
    if case == "t2_custom_factor":
        body["custom_factor_id"] = custom_factor_id
    return body


FILE_HEADER = ["Date", "Facility", "Process Type", "Fuel", "Quantity", "Unit", "Factor Type", "Equipment ID",
               "hhv", "hhv_unit"]


def file_row(case, qty, year, month, facility_name, eq):
    tier, process, fuel, unit, extra = CASES[case]
    if tier == 3:
        raise ValueError("entered Tier 3 factors have no file column")
    return [f"{year}-{month:02d}", facility_name, process, fuel, qty, unit, FACTOR_SOURCE[tier], eq,
            extra.get("hhv", ""), extra.get("hhv_unit", "")]


def to_csv(rows, header=FILE_HEADER):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def volume_rows(n, facility_names, role_tag, cases=None):
    """n unique file rows for one role: unique (facility, month, equipment) keys, every case and
    quantity class cycled, so the natural-key duplicate rule never fires."""
    cases = cases or [c for c in CASES if not c.startswith("t3_")]
    out = []
    for i in range(n):
        case = cases[i % len(cases)]
        qty = QUANTITIES[(i // len(cases)) % len(QUANTITIES)] or 1   # no zero rows in volume files
        month = MONTHS[i % len(MONTHS)]
        out.append((case, qty, 2025, month, facility_names[i % len(facility_names)], f"V{role_tag}{i:06d}"))
    return out
