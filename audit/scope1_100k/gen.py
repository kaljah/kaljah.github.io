"""Generate the 100,000-row Scope 1 bulk-import audit dataset.

Outputs (in --out, default ./out):
  scope1_audit_100k.csv      the file to import (one header row, 100,000 data rows)
  scope1_audit_part1.csv     rows 1-50,000      (the importer caps a file at 50,000 rows)
  scope1_audit_part2.csv     rows 50,001-100,000
  expected.jsonl             one line per row: family, tier, expectation and oracle values

Every row is unique (asserted): a unique source_ref and a unique combination of the other cells.

Three kinds of expectation per row:
  * oracle   - expected CO2 / CH4 / N2O (tonnes), computed here with an independent unit table
               (NIST / API Compendium constants), never with the application's code
  * group    - metamorphic: the rows of a group describe the same physical activity in different
               units / spellings (and a known scale k), so emission / k must be equal across the group
  * reject   - the row is invalid and must be refused (the reason class is recorded)
Rows that a reasonable user could write but that are physically ambiguous are marked "ambiguous":
the correct behaviour is a rejection; a silent acceptance is reported.
"""
import argparse
import csv
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "new", "server"))
sys.path.insert(0, HERE)

from harness import CUSTOM_FACTORS, FACILITIES  # noqa: E402

# Catalog DATA (values) are read from the application; the conversion arithmetic below is independent.
from emission_factors import API_FACTORS as CATALOG  # noqa: E402
from calculations.activity_factors import ACTIVITY_FACTORS  # noqa: E402

GWP = {"co2": 1.0, "ch4": 28.0, "n2o": 265.0}  # AR5 (the platform default)

# --------------------------------------------------------------------------------------------
# Independent unit table: spelling -> (dimension, factor to base). Bases: m3 (standard m3 at
# 60 F / 14.696 psia), kg, MJ, h, count. Sources: NIST SP 811, API Compendium 2021 Table 3-3/3-4.
# --------------------------------------------------------------------------------------------
FT3 = 0.028316846592            # m3 per ft3 (exact)
GAL = 0.003785411784            # m3 per US gal (exact)
BBL = 42 * GAL                  # m3 per bbl
LB = 0.45359237                 # kg per lb (exact)
BTU = 1.05505585262e-3          # MJ per IT Btu
NM3 = 288.705555 / 273.15       # standard m3 (60 F) per normal m3 (0 C), same pressure

GAS_VOL = {
    "scf": FT3, "SCF": FT3, "Scf": FT3, "cf": FT3, "ft3": FT3,
    "Mscf": 1e3 * FT3, "MSCF": 1e3 * FT3, "mscf": 1e3 * FT3, "Mcf": 1e3 * FT3, "mcf": 1e3 * FT3, "MCF": 1e3 * FT3,
    "MMscf": 1e6 * FT3, "MMSCF": 1e6 * FT3, "mmscf": 1e6 * FT3,
    "Sm3": 1.0, "sm3": 1.0, "SM3": 1.0, "Sm³": 1.0,
    "Nm3": NM3, "nm3": NM3, "Nm³": NM3,
    "m3": 1.0, "m³": 1.0, "M3": 1.0,
    "ksm3": 1e3, "mmsm3": 1e6,
    "cubic_meters": 1.0,
    "MMcf": 1e6 * FT3, "kscf": 1e3 * FT3,
}
LIQ_VOL = {
    "gal": GAL, "gallon": GAL, "gallons": GAL, "GAL": GAL,
    "bbl": BBL, "BBL": BBL, "barrel": BBL, "barrels": BBL,
    "kbbl": 1e3 * BBL, "Mbbl": 1e3 * BBL, "MMbbl": 1e6 * BBL,
    "L": 1e-3, "l": 1e-3, "liter": 1e-3, "liters": 1e-3,
    "m3": 1.0, "m³": 1.0, "M3": 1.0, "cubic_meters": 1.0,
}
MASS = {
    "kg": 1.0, "KG": 1.0, "kgs": 1.0, "kilogram": 1.0, "kilograms": 1.0,
    "g": 1e-3, "gram": 1e-3, "grams": 1e-3,
    "tonne": 1e3, "tonnes": 1e3, "t": 1e3, "metric_ton": 1e3, "metric_tons": 1e3, "metric ton": 1e3,
    "lb": LB, "lbs": LB, "LB": LB, "pound": LB, "pounds": LB,
    "short ton": 2000 * LB, "short_ton": 2000 * LB, "short_tons": 2000 * LB, "us_ton": 2000 * LB,
    "long ton": 2240 * LB, "long_ton": 2240 * LB,
}
ENERGY = {
    "MMBtu": 1e6 * BTU, "mmbtu": 1e6 * BTU, "MMBTU": 1e6 * BTU, "MM Btu": 1e6 * BTU, "mm_btu": 1e6 * BTU,
    "Btu": BTU, "BTU": BTU, "btu": BTU, "kBtu": 1e3 * BTU,
    "MJ": 1.0, "mj": 1.0, "megajoule": 1.0, "megajoules": 1.0, "kJ": 1e-3,
    "GJ": 1e3, "gj": 1e3, "gigajoule": 1e3, "gigajoules": 1e3, "TJ": 1e6, "terajoule": 1e6,
    "kWh": 3.6, "KWH": 3.6, "kwh": 3.6, "kilowatt_hour": 3.6, "MWh": 3600.0, "megawatt_hour": 3600.0,
    "therm": 100000 * BTU, "therms": 100000 * BTU,
}
COUNT = {"events": 1, "event": 1, "completions": 1, "completion": 1, "wells": 1, "well": 1, "count": 1,
         "devices": 1, "components": 1, "each": 1, "units": 1, "sources": 1, "pcs": 1}
DAYS = {"days": 1.0, "day": 1.0, "d": 1.0}

# Spellings a user may reasonably write but that the platform's table does not list (or lists with
# another meaning): correct behaviour is a clean rejection; a silent acceptance is a finding.
AMBIGUOUS = {
    "Mt": ("mass", "megatonne (1e9 kg) or metric ton?"),
    "MT": ("mass", "metric ton or megatonne?"),
    "mt": ("mass", "metric ton or megatonne?"),
    "Mm3": ("volume", "thousand or million m3?"),
    "Dth": ("energy", "dekatherm = 1 MMBtu (not in table)"),
    "Gcal": ("energy", "gigacalorie (not in table)"),
    "toe": ("energy", "tonne of oil equivalent (not in table)"),
    "litre": ("volume", "British spelling of liter (not in table)"),
    "litres": ("volume", "British spelling of liters (not in table)"),
    "MMSCFD": ("volume", "a daily RATE given as a monthly volume"),
    "ton": ("mass", "short or metric ton"),
    "tons": ("mass", "short or metric tons"),
}
UNKNOWN = ["furlong", "cubic yards", "kWh/yr/x", "acre-ft", "xyz", "%", "scf/scf", "barrels per moon"]


def g(dim):
    return {"gas": GAS_VOL, "liq": LIQ_VOL, "mass": MASS, "energy": ENERGY, "count": COUNT, "days": DAYS}[dim]


# ------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------
class Gen:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.rows, self.meta = [], []
        self.n = 0
        self.group_n = 0
        self.seen = set()
        self.dup_rejects = 0
        self.group_period = {}

    # ----- formatting of "other data" (dates, facilities, labels) --------------------------
    def date(self, year=None, month=None):
        r = self.rng
        y = year or r.randint(2019, 2025)
        m = month or r.randint(1, 12)
        fmt = r.choice(["%Y-%m", "%Y-%m", "%Y-%m-%d", "%m/%Y", "%Y/%m"])
        if fmt == "%Y-%m":
            s = f"{y}-{m:02d}"
        elif fmt == "%Y-%m-%d":
            s = f"{y}-{m:02d}-{r.randint(1, 28):02d}"
        elif fmt == "%m/%Y":
            s = f"{m:02d}/{y}"
        else:
            s = f"{y}/{m:02d}"
        return s, y, m

    def facility(self):
        name = self.rng.choice(FACILITIES)[0]
        v = self.rng.random()
        if v < 0.06:
            return name.upper()
        if v < 0.12:
            return name.lower()
        if v < 0.16:
            return "  " + name + " "
        return name

    def tier_label(self, tier):
        opts = {"default": ["default", "default", "Default", "tier1", "Tier 1", "T1", "1", "api", "catalog"],
                "custom": ["custom", "custom", "Custom", "tier2", "Tier 2", "T2", "2", "regional"],
                "specific": ["specific", "specific", "Specific", "tier3", "Tier 3", "T3", "3", "engineering",
                             "site-specific"]}[tier]
        return self.rng.choice(opts)

    def process_label(self, key):
        from services.scope1_calc import PROCESS_LABELS

        if self.rng.random() < 0.2 and key in PROCESS_LABELS:
            return PROCESS_LABELS[key]
        return key

    def qty_str(self, x):
        """Numbers written in the forms people use: plain, scientific, thousands separators."""
        r = self.rng.random()
        if x >= 1e4 and r < 0.06:
            return f"{x:,.6f}".rstrip("0").rstrip(".")       # 12,345.678 (quoted by csv)
        if r < 0.10:
            return f"{x:.10e}"                                # 1.2345678900e+04
        return repr(float(f"{x:.12g}"))

    def new_group(self):
        self.group_n += 1
        return f"G{self.group_n:05d}"

    def add(self, fam, tier, cells, expect="accept", oracle=None, group=None, k=None, reason=None, note=None,
            year=None, month=None):
        """Add one row. `cells` are the method columns; identity / bookkeeping columns are added here."""
        self.n += 1
        ref = f"AUD-{self.n:06d}"
        if group and year is None and month is None:
            if group not in self.group_period:
                self.group_period[group] = (self.rng.randint(2019, 2025), self.rng.randint(1, 12))
            year, month = self.group_period[group]
        date, y, m = self.date(year, month)
        row = {"source_ref": ref, "date": date, "facility_name": self.facility(),
               "equipment_id": f"EQ-{fam}-{self.n:06d}", "group": f"Audit {fam}"}
        row.update({k2: v for k2, v in cells.items() if v is not None})
        if "factor_type" not in row:
            row["factor_type"] = self.tier_label(tier)
        sig = hashlib.sha1(json.dumps({k2: v for k2, v in row.items() if k2 not in ("source_ref", "equipment_id")},
                                      sort_keys=True).encode()).hexdigest()
        if sig in self.seen:      # never emit two rows with the same data
            self.dup_rejects += 1
            self.n -= 1
            return False
        self.seen.add(sig)
        self.rows.append(row)
        self.meta.append({"ref": ref, "family": fam, "tier": tier, "expect": expect, "oracle": oracle,
                          "group": group, "k": k, "reason": reason, "note": note, "year": y, "month": m})
        return True

    def fill(self, fam, target, maker):
        """Call maker() until `target` rows of the family exist."""
        start = len(self.rows)
        guard = 0
        while len(self.rows) - start < target:
            maker(target - (len(self.rows) - start))
            guard += 1
            if guard > target * 50:
                raise RuntimeError(f"family {fam} cannot reach {target}")
        # trim overshoot
        extra = len(self.rows) - start - target
        if extra > 0:
            for _ in range(extra):
                self.rows.pop()
                self.meta.pop()
            self.n -= extra


def oracle(co2_kg, ch4_kg, n2o_kg):
    return {"co2": co2_kg / 1e3, "ch4": ch4_kg / 1e3, "n2o": n2o_kg / 1e3,
            "co2e": (co2_kg * GWP["co2"] + ch4_kg * GWP["ch4"] + n2o_kg * GWP["n2o"]) / 1e3}


# ------------------------------------------------------------------------------------------
# Tier 1: catalog factors
# ------------------------------------------------------------------------------------------
def hhv_basis(f):
    """(dimension, base units per basis unit, Btu multiplier) of a catalog HHV - API Compendium
    convention: gases Btu/scf, liquids Btu/gal, solids MMBtu/short ton x 1000 (kBtu/short ton)."""
    hu = (f.get("hhv_unit") or "").lower()
    bu = (f.get("baseUnit") or "").lower()
    if hu == "btu/gal" or bu == "gal":
        return "liq", GAL, 1.0
    if hu == "btu/scf" or bu == "scf":
        return "gas", FT3, 1.0
    if bu in ("ton", "short_ton"):
        return "mass", 2000 * LB, 1e3
    t = (f.get("type") or "").lower()
    return {"gases": ("gas", FT3, 1.0), "liquids": ("liq", GAL, 1.0), "solids": ("mass", 2000 * LB, 1e3)}[t]


def comb_fuels(usage):
    out = []
    for name, f in CATALOG.items():
        u = f.get("usage") or []
        u = [u] if isinstance(u, str) else u
        if usage in u and "MMBtu" in str(f.get("unit")) and f.get("hhv"):
            out.append(name)
    return sorted(out)


def unit_pool(dims, ambiguous=0.0, rng=None):
    pool = []
    for d in dims:
        pool += [(d, s) for s in g(d)]
    return pool


def t1_combustion(G, fam, process, target, fuels):
    dims = ["energy", "gas", "liq", "mass"]

    def mk(remaining):
        fuel = G.rng.choice(fuels)
        f = CATALOG[fuel]
        bdim, bfac, mult = hhv_basis(f)
        mj_per_base = f["hhv"] * mult * BTU / bfac           # MJ per m3 (volume) or per kg (mass)
        grp = G.new_group()
        # physical activity of the group, in MJ
        target_mj = G.rng.uniform(5e3, 5e6)
        members = G.rng.sample(unit_pool(dims), 6)
        for dim, unit in members:
            k = G.rng.choice([1, 1, 2, 0.5, 3, 10, 0.1])
            if dim == "energy":
                qty = target_mj * k / ENERGY[unit]
                ok = True
            else:
                same = (dim == bdim) or (dim in ("gas", "liq") and unit in ("m3", "m³", "M3", "cubic_meters")
                                          and bdim in ("gas", "liq"))
                if dim == "gas" and bdim == "gas" or dim == "liq" and bdim == "liq" or same:
                    base_amt = target_mj * k / mj_per_base                       # m3 or kg
                    qty = base_amt / (g(dim)[unit])
                    ok = True
                else:
                    qty = G.rng.uniform(10, 1e5)
                    ok = False
            cells = {"process_type": G.process_label(process), "fuel": fuel, "quantity": G.qty_str(qty), "unit": unit}
            if ok:
                mj = target_mj * k
                mmbtu = mj / (1e6 * BTU)
                orc = oracle(mmbtu * f["co2"], mmbtu * f["ch4"], mmbtu * f["n2o"])
                G.add(fam, "default", cells, "accept", orc, grp, k)
            else:
                G.add(fam, "default", cells, "reject", None, None, None,
                      reason=f"{dim} activity with a fuel whose HHV is per {bdim}")
    G.fill(fam, target, mk)


def t1_simple(G, fam, process, target, factor_names, dims, per_unit_kg):
    """Catalog factor x converted activity. per_unit_kg(f, base_amount) -> (co2, ch4, n2o) kg."""
    def mk(remaining):
        fuel = G.rng.choice(factor_names)
        f = CATALOG[fuel]
        grp = G.new_group()
        base = G.rng.uniform(1, 5e4)
        pool = unit_pool(dims)
        for dim, unit in G.rng.sample(pool, min(5, len(pool))):
            k = G.rng.choice([1, 2, 0.5, 4, 0.25, 7])
            qty = base * k / g(dim)[unit]
            if dim == "count":
                qty = max(1, round(base / 2000 * k + G.rng.randint(1, 40)))
                kk = qty
            cells = {"process_type": G.process_label(process), "fuel": fuel, "quantity": G.qty_str(qty), "unit": unit}
            amt = qty * g(dim)[unit]
            co2, ch4, n2o = per_unit_kg(f, amt, dim)
            orc = oracle(co2, ch4, n2o)
            if "year" in str(f.get("unit")):
                orc["prorate_year"] = True    # annual factor booked on a monthly record
            G.add(fam, "default", cells, "accept", orc, grp if dim != "count" else None,
                  k if dim != "count" else None)
    G.fill(fam, target, mk)


def per_m3(f, amt, dim):          # kg/m3 factors on a standard m3 volume
    return f["co2"] * amt, f["ch4"] * amt, (f.get("n2o") or 0) * amt


def per_bbl_kg(f, amt, dim):      # kg CH4/bbl factor; amt in m3
    b = amt / BBL
    return (f.get("co2") or 0) * b, f["ch4"] * b, (f.get("n2o") or 0) * b


def per_count_t(f, amt, dim):     # tonnes per event / completion / well-year
    return (f.get("co2") or 0) * amt * 1e3, f["ch4"] * amt * 1e3, (f.get("n2o") or 0) * amt * 1e3


def per_tonne_product(gas_scale):
    def fn(f, amt_kg, dim):
        t = amt_kg / 1e3
        return (f.get("co2") or 0) * t * gas_scale["co2"], (f.get("ch4") or 0) * t * gas_scale["ch4"], \
            (f.get("n2o") or 0) * t * gas_scale["n2o"]
    return fn


def t1_component_hours(G, fam, target):
    names = [n for n, f in CATALOG.items() if "/hr" in str(f.get("unit")) and not f.get("unverified_basis")]

    def mk(remaining):
        fuel = G.rng.choice(names)
        f = CATALOG[fuel]
        grp = G.new_group()
        hours = G.rng.choice([744, 720, 672, 696, 500, 100, 24])
        n0 = G.rng.randint(1, 400)
        for k in G.rng.sample([1, 2, 3, 5, 10], 3):
            unit = G.rng.choice(["components", "count", "sources", "each", "units"])
            cells = {"process_type": "fugitive", "fuel": fuel, "quantity": str(n0 * k), "unit": unit,
                     "operating_hours": str(hours)}
            ch4 = f["ch4"] * n0 * k * hours * 1e3
            G.add(fam, "default", cells, "accept", oracle(0, ch4, 0), grp, k,
                  note="per-hour factor x count x operating_hours")
    G.fill(fam, target, mk)


def t1_activity(G, fam, target):
    """API Compendium Section 6 activity tables: the activity unit follows the factor basis."""
    keys = sorted(ACTIVITY_FACTORS)
    liq = {"bbl": BBL, "gal": GAL, "L": 1e-3, "m3": 1.0, "barrels": BBL, "gallons": GAL}
    gas = {"scf": FT3, "Mcf": 1e3 * FT3, "MMscf": 1e6 * FT3, "m3": 1.0, "Mscf": 1e3 * FT3}

    def mk(remaining):
        key = G.rng.choice(keys)
        a = ACTIVITY_FACTORS[key]
        proc = a["processes"][0]
        per = a.get("per")
        grp = G.new_group()
        hours = G.rng.choice([744, 720, 168, 400])
        days = G.rng.choice([28, 30, 31, 10])
        base = G.rng.uniform(1, 300)
        for k in G.rng.sample([1, 2, 3, 4, 6, 8], 3):
            ident = {"activity_key": key} if G.rng.random() < 0.5 else {"fuel": a["label"]}
            if per in ("bbl", "mgal"):
                u = G.rng.choice(list(liq))
                vol_m3 = base * k * (BBL if per == "bbl" else 1e3 * GAL) * 100
                cells = {"quantity": G.qty_str(vol_m3 / liq[u]), "unit": u}
            elif per in ("mmscf", "mm_m3"):
                u = G.rng.choice(list(gas))
                vol_m3 = base * k * (1e6 * FT3 if per == "mmscf" else 1e6) / 50
                cells = {"quantity": G.qty_str(vol_m3 / gas[u]), "unit": u}
            else:
                cells = {"quantity": str(int(base) * k + 0), "unit": G.rng.choice(["count", "units", "each"])}
                if per == "unit_hr":
                    cells["operating_hours"] = str(hours)
                if per == "unit_day":
                    cells["activity_days"] = str(days)
            cells.update(ident)
            cells["process_type"] = proc
            G.add(fam, "default", cells, "accept", None, grp, k, note=f"activity factor {key} (per {per})")
    G.fill(fam, target, mk)


def t1_unloading(G, fam, target):
    """Per-event factors take events, per-well-year factors take wells; any other count word (or the
    other basis) is ambiguous and should be refused rather than silently re-interpreted."""
    names = sorted(n for n, f in CATALOG.items() if "unloading" in (f.get("usage") or []) or n.startswith("Unload"))

    def mk(remaining):
        fuel = G.rng.choice(names)
        f = CATALOG[fuel]
        per_event = "/event" in str(f.get("unit"))
        good = ["events", "event"] if per_event else ["wells", "well"]
        grp = G.new_group()
        n0 = G.rng.randint(1, 60)
        for k in G.rng.sample([1, 2, 3, 5], 2):
            u = G.rng.choice(good)
            orc = oracle(0, f["ch4"] * n0 * k * 1e3, 0)
            if not per_event:
                orc["prorate_year"] = True
            G.add(fam, "default", {"process_type": "unloading", "fuel": fuel, "quantity": str(n0 * k), "unit": u},
                  "accept", orc, grp, k)
        u = G.rng.choice((["wells", "well"] if per_event else ["events", "event"]) +
                         ["devices", "components", "completions", "pcs", "each", "sources"])
        G.add(fam, "default", {"process_type": "unloading", "fuel": fuel, "quantity": str(G.rng.randint(1, 99)), "unit": u},
              "ambiguous", reason=f"{'per-event' if per_event else 'per-well-year'} factor with unit '{u}'")
    G.fill(fam, target, mk)


def t1_drilling(G, fam, target):
    names = [n for n, f in CATALOG.items() if (f.get("usage") or []) == ["drilling"]]

    def mk(remaining):
        fuel = G.rng.choice(names)
        f = CATALOG[fuel]
        grp = G.new_group()
        d0 = G.rng.uniform(1, 31)
        for unit in G.rng.sample(list(DAYS) + ["hours", "h"], 3):
            k = G.rng.choice([1, 0.5, 2, 0.25])
            if unit in ("hours", "h"):
                qty = d0 * k * 24
                G.add(fam, "default", {"process_type": "drilling", "fuel": fuel, "quantity": G.qty_str(qty), "unit": unit},
                      "either", oracle(0, f["ch4"] * d0 * k * 1e3, 0), grp, k,
                      note="drilling days given in hours: convert or refuse")
            else:
                G.add(fam, "default", {"process_type": "drilling", "fuel": fuel, "quantity": G.qty_str(d0 * k), "unit": unit},
                      "accept", oracle(0, f["ch4"] * d0 * k * 1e3, 0), grp, k)
    G.fill(fam, target, mk)


# ------------------------------------------------------------------------------------------
# Tier 2: custom factors (dimensional analysis done here, independently)
# ------------------------------------------------------------------------------------------
def cf_parse(unit):
    """(numerator kg, denominator dim, denominator base factor) for the fixture units."""
    if "/" not in unit:
        num, den = "kg", unit
    else:
        num, den = unit.split("/")
    num_kg = {"kg": 1.0, "tonne": 1e3, "lb": LB, "g": 1e-3}[num.strip()]
    den = den.strip()
    for dim in ("energy", "gas", "liq", "mass", "count"):
        if den in g(dim):
            return num_kg, dim, g(dim)[den]
    if den == "short_ton":
        return num_kg, "mass", 2000 * LB
    if den in ("device", "well", "event"):
        return num_kg, "count", 1.0
    raise KeyError(unit)


def t2_custom(G, fam, target):
    def mk(remaining):
        name, co2, ch4, n2o, unit, hhv, parent = G.rng.choice(CUSTOM_FACTORS)
        num_kg, ddim, dfac = cf_parse(unit)
        grp = G.new_group()
        base = G.rng.uniform(10, 1e5)            # activity in base units of the factor's dimension
        if ddim == "energy" and parent:
            pdim, pfac, mult = hhv_basis(CATALOG[parent])
            # energy-based factor with a parent fuel: physical units convert with the factor's HHV
            pool = unit_pool(["energy"]) + [(pdim, u) for u in g(pdim)]
        elif ddim == "gas":
            pool = unit_pool(["gas"])
        elif ddim == "liq":
            pool = unit_pool(["liq"])
        else:
            pool = unit_pool([ddim])
        for dim, u in G.rng.sample(pool, min(6, len(pool))):
            k = G.rng.choice([1, 2, 0.5, 3, 0.2])
            if ddim == "count":
                qty = float(G.rng.randint(1, 300))
                amt_den = qty
                k_use = None
            elif dim == ddim:
                qty = base * k / g(dim)[u]
                amt_den = base * k / dfac
                k_use = k
            else:   # physical unit of the parent fuel -> energy via the custom HHV
                pdim, pfac, mult = hhv_basis(CATALOG[parent])
                mj = base * k
                phys_base = mj / (hhv * mult * BTU / pfac)
                qty = phys_base / g(dim)[u]
                amt_den = mj / dfac
                k_use = k
            cells = {"process_type": "combustion", "fuel": name, "quantity": G.qty_str(qty), "unit": u}
            G.add(fam, "custom", cells, "accept",
                  oracle(co2 * num_kg * amt_den, ch4 * num_kg * amt_den, n2o * num_kg * amt_den),
                  grp if k_use else None, k_use)
        # one mismatched-dimension row per group: must be refused
        wrong = {"energy": "bbl", "gas": "tonne", "liq": "kg", "mass": "scf", "count": "kg"}[ddim]
        if ddim == "energy" and parent:
            wrong = {"gas": "bbl", "liq": "scf", "mass": "bbl"}[hhv_basis(CATALOG[parent])[0]]
        elif ddim == "energy":
            wrong = "kg"
        G.add(fam, "custom", {"process_type": "combustion", "fuel": name, "quantity": G.qty_str(G.rng.uniform(1, 1e4)),
                              "unit": wrong}, "reject", reason=f"custom factor per {unit} applied to {wrong}")
    G.fill(fam, target, mk)


def t2_engineering(G, target_each):
    # Completions (operational data): rate x duration in several rate units / GOR
    rate_units = {"Mcf/hr": 1e3 * FT3, "Mcf/day": 1e3 * FT3 / 24, "scf/hr": FT3, "m3/hr": 1.0,
                  "mcf/d": 1e3 * FT3 / 24, "MMscf/d": 1e6 * FT3 / 24}

    def compl(remaining):
        grp = G.new_group()
        rate_m3h = G.rng.uniform(1, 200)
        dur = G.rng.uniform(4, 240)
        ch4 = G.rng.uniform(60, 95)
        events = G.rng.randint(1, 6)
        for ru in G.rng.sample(list(rate_units), 4):
            cells = {"process_type": "completions", "quantity": str(events), "unit": "events", "calc_method": "rate_duration",
                     "comp_rate": G.qty_str(rate_m3h / rate_units[ru]), "comp_rate_unit": ru,
                     "comp_duration": G.qty_str(dur), "ch4_content": f"{ch4:.4f}", "co2_content": "2"}
            G.add("T2_COMPL", "custom", cells, "accept", None, grp, 1, note=f"rate unit {ru}")
        bbl = G.rng.uniform(100, 3000)
        gor = G.rng.uniform(50, 2000)
        grp2 = G.new_group()
        for k in (1, 2):
            G.add("T2_COMPL", "custom", {"process_type": "completions", "quantity": str(events), "unit": "events",
                                         "calc_method": "gor", "comp_liquid_bbl": G.qty_str(bbl * k), "comp_gor": G.qty_str(gor),
                                         "ch4_content": f"{ch4:.4f}"}, "accept", None, grp2, k)
    G.fill("T2_COMPL", target_each, compl)

    def unload(remaining):
        grp = G.new_group()
        ev = G.rng.randint(1, 60)
        typ = G.rng.choice(["plunger", "non_plunger"])
        reg = G.rng.choice(["Gulf Coast", "Appalachia", "Midcontinent", "Rocky Mountain", ""])
        ch4 = G.rng.uniform(70, 95)
        # Table 6-10 factors depend on the event-frequency band, so events do not scale linearly:
        # the group varies the spelling of the same count only
        for u in ("events", "event"):
            cells = {"process_type": "unloading", "quantity": str(ev), "unit": u,
                     "unloading_type": typ, "region": reg or None, "ch4_content": f"{ch4:.3f}"}
            G.add("T2_UNLOAD", "custom", cells, "accept", None, grp, 1)
    G.fill("T2_UNLOAD", target_each, unload)

    oil_units = {"bbl/day": BBL, "m3/day": 1.0, "bbl/d": BBL, "bpd": BBL, "gal/day": GAL}
    gor_units = {"scf/bbl": FT3 / BBL, "m3/m3": 1.0, "Sm3/Sm3": 1.0}

    def agv(remaining):
        grp = G.new_group()
        oil_m3d = G.rng.uniform(5, 500)
        gor_m3m3 = G.rng.uniform(10, 300)
        days = G.rng.randint(1, 28)
        for ou, gu in [(G.rng.choice(list(oil_units)), G.rng.choice(list(gor_units))) for _ in range(4)]:
            q = oil_m3d / oil_units[ou]
            cells = {"process_type": "associated_gas_venting", "quantity": G.qty_str(q), "unit": ou,
                     "oil_production": G.qty_str(q), "oil_unit": ou, "gor": G.qty_str(gor_m3m3 / gor_units[gu]),
                     "gor_unit": gu, "venting_duration": str(days), "ch4_content": "78.5", "co2_content": "2.5"}
            G.add("T2_AGV", "custom", cells, "accept", None, grp, 1, note=f"oil {ou}, gor {gu}")
    G.fill("T2_AGV", target_each, agv)

    def fug(remaining):
        grp = G.new_group()
        n = G.rng.randint(5, 2000)
        comp = G.rng.choice(["valve", "connector", "flange", "open_ended_line", "pump_seal", "other"])
        svc = G.rng.choice(["gas", "light_oil", "heavy_oil", "water_oil"])
        if comp == "pump_seal" and svc in ("heavy_oil", "gas"):
            svc = "light_oil"     # Table 7-12 has no pump-seal factor in gas / heavy-oil service
        hours = G.rng.choice([744, 720, 672])
        for k in G.rng.sample([1, 2, 3, 5], 2):
            cells = {"process_type": "fugitive", "quantity": str(n * k), "unit": "components", "fugitive_method": "component",
                     "component_type": comp, "service_type": svc, "operating_hours": str(hours),
                     "ch4_mole_pct": "81.6"}
            G.add("T2_FUG", "custom", cells, "accept", None, grp, k)
    G.fill("T2_FUG", target_each, fug)


# ------------------------------------------------------------------------------------------
# Tier 3: engineering methods - metamorphic groups over every unit the inputs accept
# ------------------------------------------------------------------------------------------
TEMP = {  # spelling -> function(K) giving the value in that unit
    "C": lambda k: k - 273.15, "F": lambda k: (k - 273.15) * 9 / 5 + 32, "K": lambda k: k, "R": lambda k: k * 9 / 5,
    "celsius": lambda k: k - 273.15, "fahrenheit": lambda k: (k - 273.15) * 9 / 5 + 32, "kelvin": lambda k: k,
    "degC": lambda k: k - 273.15, "degF": lambda k: (k - 273.15) * 9 / 5 + 32, "°C": lambda k: k - 273.15,
    "°F": lambda k: (k - 273.15) * 9 / 5 + 32, "rankine": lambda k: k * 9 / 5,
}
ATM_PSI = 14.696
PSI_PER = {"psia": 1.0, "psi": 1.0, "bar": 14.5037738, "bara": 14.5037738, "kPa": 0.145037738, "kpaa": 0.145037738,
           "MPa": 145.037738, "atm": 14.696, "mbar": 0.0145037738, "Pa": 0.000145037738}
PSI_GAUGE = {"psig": 1.0, "barg": 14.5037738, "kPag": 0.145037738, "MPag": 145.037738, "mbarg": 0.0145037738}
PRESS_UNKNOWN = ["kg/cm2", "inHg", "mmHg", "torr"]   # not in the platform's table


def press_in(unit, psia):
    if unit in PSI_PER:
        return psia / PSI_PER[unit]
    return (psia - ATM_PSI) / PSI_GAUGE[unit]


def composition(rng):
    c1 = rng.uniform(70, 95)
    rest = 100 - c1
    parts = [rng.random() for _ in range(6)]
    s = sum(parts)
    c2, c3, c4, c5, n2, co2 = [rest * p / s for p in parts]
    return {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "n2_mol": n2, "co2_mol": co2}


def comp_cells(comp, as_fraction):
    if as_fraction:
        return {k: f"{v / 100:.8f}" for k, v in comp.items()}
    return {k: f"{v:.6f}" for k, v in comp.items()}


def t3_combustion(G, target):
    gas_fuels = [n for n in comb_fuels("combustion") if hhv_basis(CATALOG[n])[0] == "gas"]

    def mk(remaining):
        fuel = G.rng.choice(gas_fuels)
        comp = composition(G.rng)
        hhv = G.rng.uniform(900, 1300)
        ce = G.rng.uniform(98, 99.99)
        grp = G.new_group()
        v_m3 = G.rng.uniform(100, 2e5)
        actual = G.rng.random() < 0.5
        if actual:
            T_K = G.rng.uniform(260, 340)
            P_psia = G.rng.uniform(15, 900)
        for i in range(6):
            k = G.rng.choice([1, 1, 2, 0.5])
            cells = {"process_type": G.process_label("combustion"), "fuel": fuel, "hhv": f"{hhv:.4f}",
                     "combustion_efficiency": f"{ce:.4f}" if G.rng.random() < 0.6 else f"{ce / 100:.6f}"}
            cells.update(comp_cells(comp, G.rng.random() < 0.3))
            if actual:
                u = G.rng.choice(["m3", "m³", "cf", "ft3"])
                cells["quantity"] = G.qty_str(v_m3 * k / (1.0 if u in ("m3", "m³") else FT3))
                cells["unit"] = u
                tu = G.rng.choice(list(TEMP))
                pu = G.rng.choice(list(PSI_PER) + list(PSI_GAUGE))
                cells.update({"operating_temperature": f"{TEMP[tu](T_K):.6f}", "temp_unit": tu,
                              "operating_pressure": f"{press_in(pu, P_psia):.8f}", "press_unit": pu, "z_factor": "1"})
            else:
                u = G.rng.choice(list(GAS_VOL))
                cells["quantity"] = G.qty_str(v_m3 * k / GAS_VOL[u])
                cells["unit"] = u
            G.add("T3_COMB", "specific", cells, "accept", None, grp, k)
        # HHV + catalog factor, no composition (the factor path of Tier 3)
        grp2 = G.new_group()
        f = CATALOG[fuel]
        for u in G.rng.sample(["scf", "Mscf", "MMscf", "Sm3", "Nm3"], 2):
            q = v_m3 / GAS_VOL[u]
            mmbtu = v_m3 / FT3 * hhv / 1e6
            G.add("T3_COMB", "specific", {"process_type": "combustion", "fuel": fuel, "quantity": G.qty_str(q), "unit": u,
                                          "hhv": f"{hhv:.4f}", "combustion_efficiency": f"{ce:.4f}"},
                  "accept", oracle(mmbtu * f["co2"], mmbtu * f["ch4"], mmbtu * f["n2o"]), grp2, 1,
                  note="Tier 3: site HHV x catalog factor, no gas analysis")
    G.fill("T3_COMB", target, mk)


def t3_flaring(G, target):
    names = [n for n, f in CATALOG.items() if (f.get("usage") or []) == ["flaring"]]

    def mk(remaining):
        comp = composition(G.rng)
        ce = G.rng.uniform(95, 99.9)
        ft = G.rng.choice(["elevated", "enclosed_ground", "offshore_boom", "air_assisted", "steam_assisted"])
        grp = G.new_group()
        v = G.rng.uniform(1e3, 5e6)
        fuel = G.rng.choice(names)
        for u in G.rng.sample(list(GAS_VOL), 5):
            k = G.rng.choice([1, 2, 0.5])
            cells = {"process_type": G.rng.choice(["flaring", "routine_flaring", "non_routine_flaring", "safety_flaring"]),
                     "fuel": fuel, "quantity": G.qty_str(v * k / GAS_VOL[u]), "unit": u, "flare_type": ft,
                     "control_efficiency": f"{ce:.4f}"}
            cells.update(comp_cells(comp, False))
            G.add("T3_FLARE", "specific", cells, "accept", None, grp, k)
    G.fill("T3_FLARE", target, mk)


def t3_completions(G, target):
    vol_units = ["scf", "Mscf", "mcf", "MMscf", "m3", "Sm3"]
    rate_units = {"Mcf/hr": 1e3 * FT3, "Mcf/day": 1e3 * FT3 / 24, "scf/hr": FT3, "m3/hr": 1.0}

    def mk(remaining):
        ch4 = G.rng.uniform(60, 95)
        co2 = G.rng.uniform(0, 5)
        eff = G.rng.choice([0, 50, 85, 90, 98])
        grp = G.new_group()
        v = G.rng.uniform(100, 1e5)
        for u in G.rng.sample(vol_units, 4):
            k = G.rng.choice([1, 2, 0.5])
            cells = {"process_type": "completions", "quantity": G.qty_str(v * k / GAS_VOL[u]), "unit": u,
                     "comp_method": "metered_volume", "ch4_content": f"{ch4:.4f}", "co2_content": f"{co2:.4f}",
                     "comp_flare_eff": str(eff)}
            G.add("T3_COMPL", "specific", cells, "accept", None, grp, k)
        grp2 = G.new_group()
        r = G.rng.uniform(1, 100)   # m3/h
        dur = G.rng.uniform(5, 200)
        for ru in G.rng.sample(list(rate_units), 3):
            cells = {"process_type": "completions", "comp_method": "rate_duration", "comp_rate": G.qty_str(r / rate_units[ru]),
                     "comp_rate_unit": ru, "comp_duration": G.qty_str(dur), "ch4_content": f"{ch4:.4f}",
                     "co2_content": f"{co2:.4f}", "comp_flare_eff": str(eff)}
            G.add("T3_COMPL", "specific", cells, "accept", None, grp2, 1)
    G.fill("T3_COMPL", target, mk)


def t3_unloading(G, target):
    def mk(remaining):
        grp = G.new_group()
        depth = G.rng.uniform(2000, 12000)
        diam = G.rng.choice([2.375, 2.875, 3.5, 4.5, 5.5])
        press = G.rng.uniform(100, 1500)
        ch4 = G.rng.uniform(70, 95)
        ev = G.rng.randint(1, 50)
        for k in G.rng.sample([1, 2, 3, 4, 5], 3):
            cells = {"process_type": "unloading", "quantity": str(ev * k), "unit": "events", "unload_depth": f"{depth:.2f}",
                     "unload_diam": str(diam), "unload_press": f"{press:.2f}", "unload_freq": str(ev * k),
                     "ch4_content": f"{ch4:.3f}", "co2_content": "1.5", "unload_flare_eff": "0"}
            G.add("T3_UNLOAD", "specific", cells, "accept", None, grp, k)
    G.fill("T3_UNLOAD", target, mk)


def t3_blowdown(G, target):
    vol_units = {"m3": 1.0, "scf": FT3, "Mscf": 1e3 * FT3, "Sm3": 1.0, "cf": FT3, "ft3": FT3, "bbl": BBL, "gal": GAL, "L": 1e-3}
    temp_units = ["F", "C", "K", "R", "degF", "degC"]
    press_units = ["psig", "psia", "barg", "bara", "kPa", "kPag", "MPa", "atm"]

    def mk(remaining):
        grp = G.new_group()
        vol = G.rng.uniform(1, 500)        # m3 physical
        T_K = G.rng.uniform(270, 340)
        P_psia = G.rng.uniform(50, 1500)
        ch4 = G.rng.uniform(70, 95)
        ev = G.rng.randint(1, 30)
        for i in range(5):
            vu = G.rng.choice(list(vol_units))
            tu = G.rng.choice(temp_units)
            pu = G.rng.choice(press_units)
            TT = {"degF": "F", "degC": "C"}.get(tu, tu)
            cells = {"process_type": G.rng.choice(["blowdown", "venting"]), "quantity": G.qty_str(vol / vol_units[vu]),
                     "unit": vu, "blowdown_pressure": f"{press_in(pu if pu in PSI_PER or pu in PSI_GAUGE else 'psig', P_psia):.8f}",
                     "blowdown_press_unit": pu, "blowdown_temp": f"{TEMP[TT](T_K):.6f}", "blowdown_temp_unit": tu,
                     "blowdown_events": str(ev), "ch4_content": f"{ch4:.4f}", "co2_content": "2", "z_factor": "0.95"}
            G.add("T3_BLOW", "specific", cells, "accept", None, grp, 1,
                  note=f"volume {vu}, T {tu}, P {pu}")
    G.fill("T3_BLOW", target, mk)


def t3_tank(G, target):
    units = {"bbl": BBL, "m3": 1.0, "m³": 1.0, "gal": GAL, "gallons": GAL, "l": 1e-3, "liters": 1e-3,
             "kbbl": 1e3 * BBL, "Mbbl": 1e3 * BBL, "L": 1e-3, "barrels": BBL}

    def mk(remaining):
        grp = G.new_group()
        v = G.rng.uniform(100, 5e4)      # bbl
        gor = G.rng.uniform(5, 200)
        ch4 = G.rng.uniform(20, 80)
        ce = G.rng.choice([0, 50, 90, 95, 98])
        for u in G.rng.sample(list(units), 5):
            k = G.rng.choice([1, 2, 0.5])
            q = v * k * BBL / units[u]
            cells = {"process_type": "tank_flashing", "quantity": G.qty_str(q), "unit": u, "tank_unit": u,
                     "tank_gor": f"{gor:.4f}", "tank_ch4_content": f"{ch4:.4f}", "tank_control_eff": str(ce)}
            G.add("T3_TANK", "specific", cells, "accept", None, grp, k, note=f"tank throughput unit {u}")
    G.fill("T3_TANK", target, mk)


def t3_pneumatic(G, target):
    units = {"scf": FT3, "m3": 1.0, "M3": 1.0, "m³": 1.0, "Sm3": 1.0, "scf/hr": FT3, "m3/hr": 1.0, "SCF": FT3}

    def mk(remaining):
        grp = G.new_group()
        rate_m3h = G.rng.uniform(0.01, 1.0)
        n = G.rng.randint(1, 200)
        hours = G.rng.choice([744, 720, 672, 500])
        ch4 = G.rng.uniform(70, 95)
        for u in G.rng.sample(list(units), 4):
            k = G.rng.choice([1, 2, 3])
            cells = {"process_type": "pneumatic", "quantity": str(n * k), "unit": "devices", "pneu_count": str(n * k),
                     "pneu_bleed_rate": G.qty_str(rate_m3h / units[u]), "pneu_bleed_unit": u, "pneu_hours": str(hours),
                     "pneu_ch4_content": f"{ch4:.3f}"}
            G.add("T3_PNEU", "specific", cells, "accept", None, grp, k, note=f"bleed unit {u}")
    G.fill("T3_PNEU", target, mk)


def t3_agr(G, target):
    units = {"mmscf": 1e6 * FT3, "MMscf": 1e6 * FT3, "m3": 1.0, "scf": FT3, "Mscf": 1e3 * FT3, "Sm3": 1.0, "Nm3": NM3}

    def mk(remaining):
        grp = G.new_group()
        v = G.rng.uniform(1e4, 5e6)    # m3
        cin = G.rng.uniform(2, 15)
        cout = G.rng.uniform(0, 1)
        for u in G.rng.sample(list(units), 4):
            k = G.rng.choice([1, 2, 0.5])
            q = v * k / units[u]
            cells = {"process_type": "agr", "quantity": G.qty_str(q), "unit": u, "agr_unit": u, "agr_co2_in": f"{cin:.4f}",
                     "agr_co2_out": f"{cout:.4f}", "agr_ch4_in": "85", "agr_ch4_slip": "0.001", "agr_control_eff": "0"}
            G.add("T3_AGR", "specific", cells, "accept", None, grp, k, note=f"throughput unit {u}")
    G.fill("T3_AGR", target, mk)


def t3_dehy(G, target):
    def mk(remaining):
        grp = G.new_group()
        v = G.rng.uniform(100, 1e5)
        ch4 = G.rng.uniform(60, 95)
        for u in G.rng.sample(["scf", "Mscf", "MMscf", "m3", "Sm3", "Nm3", "mcf"], 4):
            k = G.rng.choice([1, 2, 0.5])
            cells = {"process_type": "dehydrator", "quantity": G.qty_str(v * k / GAS_VOL[u]), "unit": u, "vent_method": "volume",
                     "ch4_content": f"{ch4:.4f}", "co2_content": "2"}
            G.add("T3_DEHY", "specific", cells, "accept", None, grp, k)
    G.fill("T3_DEHY", target, mk)


def t3_fugitive(G, target):
    rate_units = {"kg/hr": 1.0, "kg/h": 1.0, "g/hr": 1e-3, "lb/hr": LB, "g/s": 3.6, "kg/day": 1 / 24}
    vol_rate_units = {"scf/hr": FT3, "scfh": FT3, "m3/hr": 1.0, "m3/h": 1.0, "Mcf/day": 1e3 * FT3 / 24}

    def mk(remaining):
        grp = G.new_group()
        hours = G.rng.choice([744, 720, 672, 100])
        r = G.rng.choice(["meas_mass", "meas_vol", "screen", "ogi"])
        ch4 = G.rng.uniform(70, 95)
        if r == "meas_mass":
            kgph = G.rng.uniform(0.01, 5)
            for u in G.rng.sample(list(rate_units), 4):
                G.add("T3_FUG", "specific", {"process_type": "fugitive", "fugitive_method": "measurement",
                                              "measured_rate": G.qty_str(kgph / rate_units[u]), "rate_unit": u,
                                              "operating_hours": str(hours), "ch4_content": f"{ch4:.3f}", "co2_content": "1"},
                      "accept", None, grp, 1, note=f"leak rate unit {u}")
        elif r == "meas_vol":
            m3h = G.rng.uniform(0.01, 5)
            for u in G.rng.sample(list(vol_rate_units), 3):
                G.add("T3_FUG", "specific", {"process_type": "fugitive", "fugitive_method": "measurement",
                                              "measured_rate": G.qty_str(m3h / vol_rate_units[u]), "rate_unit": u,
                                              "operating_hours": str(hours), "ch4_content": f"{ch4:.3f}", "co2_content": "1"},
                      "accept", None, grp, 1, note=f"leak rate unit {u}")
        elif r == "screen":
            below = G.rng.randint(10, 2000)
            above = G.rng.randint(0, 50)
            comp = G.rng.choice(["valve", "connector", "flange", "open_ended_line", "pump_seal", "other"])
            for k in (1, 2):
                G.add("T3_FUG", "specific", {"process_type": "fugitive", "quantity": str((below + above) * k), "unit": "components",
                                              "fugitive_method": "screening", "component_type": comp, "service": "gas",
                                              "m21_below_count": str(below * k), "m21_above_count": str(above * k),
                                              "operating_hours": str(hours)}, "accept", None, grp, k)
        else:
            n = G.rng.randint(1, 30)
            comp = G.rng.choice(["valve", "connector", "flange", "open_ended_line", "pump_seal", "other"])
            for k in (1, 2, 3):
                G.add("T3_FUG", "specific", {"process_type": "fugitive", "fugitive_method": "ogi", "ogi_component": comp,
                                              "ogi_service": "gas", "leakers_count": str(n * k), "operating_hours": str(hours),
                                              "ch4_content": f"{ch4:.3f}"}, "accept", None, grp, k)
    G.fill("T3_FUG", target, mk)


def t3_stoich(G, target):
    def mk(remaining):
        grp = G.new_group()
        kg = G.rng.uniform(100, 1e6)
        cc = G.rng.uniform(0.5, 0.95)
        for u in G.rng.sample(list(MASS), 5):
            k = G.rng.choice([1, 2, 0.5])
            cells = {"process_type": "stoichiometry", "quantity": G.qty_str(kg * k / MASS[u]), "unit": u,
                     "carbon_content": f"{cc:.6f}"}
            G.add("T3_STOICH", "specific", cells, "accept", oracle(kg * k * cc * 44.0095 / 12.0107, 0, 0), grp, k,
                  note="CO2 = mass x carbon fraction x 44.01/12.011")
    G.fill("T3_STOICH", target, mk)


def t3_agv(G, target):
    vrates = {"scfh": FT3, "scf/hr": FT3, "m3/hr": 1.0, "Mcf/day": 1e3 * FT3 / 24, "m3/day": 1 / 24}

    def mk(remaining):
        ch4 = G.rng.uniform(50, 90)
        grp = G.new_group()
        v = G.rng.uniform(1e3, 1e6)
        for u in G.rng.sample(["scf", "Mscf", "MMscf", "m3", "Sm3", "Nm3", "mcf"], 3):
            q = v / GAS_VOL[u]
            G.add("T3_AGV", "specific", {"process_type": "associated_gas_venting", "quantity": G.qty_str(q), "unit": u,
                                          "vent_volume": G.qty_str(q), "vent_volume_unit": u, "ch4_content": f"{ch4:.4f}",
                                          "co2_content": "3"}, "accept", None, grp, 1, note=f"vent volume unit {u}")
        grp2 = G.new_group()
        r = G.rng.uniform(1, 500)
        h = G.rng.uniform(1, 744)
        for u in G.rng.sample(list(vrates), 3):
            G.add("T3_AGV", "specific", {"process_type": "associated_gas_venting", "vent_rate": G.qty_str(r / vrates[u]),
                                          "vent_rate_unit": u, "venting_duration": G.qty_str(h), "ch4_content": f"{ch4:.4f}",
                                          "co2_content": "3"}, "accept", None, grp2, 1, note=f"vent rate unit {u}")
    G.fill("T3_AGV", target, mk)


def t3_ventgas(G, target):
    procs = ["vented_gas", "well_testing", "workovers", "casing_gas", "compressor_venting", "non_routine_venting"]

    def mk(remaining):
        proc = G.rng.choice(procs)
        ch4 = G.rng.uniform(60, 95)
        co2 = G.rng.uniform(0, 5)
        grp = G.new_group()
        v = G.rng.uniform(100, 1e6)
        for u in G.rng.sample(["scf", "Mscf", "MMscf", "m3", "Sm3", "Nm3", "mcf"], 4):
            k = G.rng.choice([1, 2, 0.5])
            G.add("T3_VENTGAS", "specific", {"process_type": proc, "vent_method": "volume",
                                              "quantity": G.qty_str(v * k / GAS_VOL[u]), "unit": u,
                                              "ch4_content": f"{ch4:.4f}", "co2_content": f"{co2:.4f}"},
                  "accept", oracle(v * k * float(f"{co2:.4f}") / 100 * 44.01 / 23.685,
                                   v * k * float(f"{ch4:.4f}") / 100 * 16.04 / 23.685, 0), grp, k,
                  note="vented gas = V x mol fraction x MW / 23.685 m3/kmol")
    G.fill("T3_VENTGAS", target, mk)


# ------------------------------------------------------------------------------------------
# Negative / ambiguous rows
# ------------------------------------------------------------------------------------------
def negatives(G, target):
    gas_fuel = "Natural Gas"
    cases = []

    def neg(cells, reason, expect="reject", year=None, month=None, tier="default"):
        G.add("NEG", tier, cells, expect, reason=reason, year=year, month=month)

    def mk(remaining):
        r = G.rng.random()
        q = G.qty_str(G.rng.uniform(1, 1e4))
        base = {"process_type": "combustion", "fuel": gas_fuel, "quantity": q, "unit": "MMBtu"}
        c = dict(base)
        kind = G.rng.randrange(24)
        if kind == 0:
            c["quantity"] = "-" + q.lstrip("-")
            neg(c, "negative quantity")
        elif kind == 1:
            c["quantity"] = G.rng.choice(["abc", "N/A", "null", "#VALUE!", "1.2.3.4", "--5", "∞"])
            neg(c, "non-numeric quantity")
        elif kind == 2:
            c["unit"] = ""
            neg(c, "missing unit")
        elif kind == 3:
            c["unit"] = G.rng.choice(UNKNOWN) + f" {G.rng.randint(1, 999)}"
            neg(c, "unknown unit")
        elif kind == 4:
            c["unit"] = G.rng.choice(["ton", "tons"])
            c["fuel"] = "Bituminous Coal"
            neg(c, "bare ton is ambiguous")
        elif kind == 5:
            c["fuel"] = f"Unobtainium Gas {G.rng.randint(1, 99999)}"
            neg(c, "unknown catalog factor")
        elif kind == 6:
            c["process_type"] = G.rng.choice(["tank_flashing", "pneumatic", "nitric_acid_production"])
            neg(c, "factor does not apply to process")
        elif kind == 7:
            c["process_type"] = G.rng.choice(["purchased_electricity", "electricity", "steam", "cogen"])
            neg(c, "scope 2 process in scope 1 file")
        elif kind == 8:
            c["process_type"] = f"teleportation_{G.rng.randint(1, 9999)}"
            neg(c, "unknown process")
        elif kind == 9:
            c["factor_type"] = f"tier{G.rng.randint(4, 99)}"
            neg(c, "unknown factor type")
        elif kind == 10:
            G.add("NEG", "default", c, "reject", reason="invalid date (month 13)", year=2024, month=13)
        elif kind == 11:
            G.add("NEG", "default", c, "reject", reason="year out of range", year=G.rng.choice([1850, 2099, 3024]))
        elif kind == 12:
            c["quantity"] = None
            neg(c, "missing quantity (Tier 1)")
        elif kind == 13:
            c["fuel"] = f"CF Missing {G.rng.randint(1, 99999)}"
            neg(c, "custom factor does not exist", tier="custom")
        elif kind == 14:
            c["unit"] = G.rng.choice(["Mt", "MT", "mt"])
            c["fuel"] = "Bituminous Coal"
            neg(c, "ambiguous mass unit (Mt/MT)", expect="ambiguous")
        elif kind == 15:
            c["unit"] = G.rng.choice(["Mm3", "MMSCFD"])
            neg(c, "ambiguous / unsupported gas volume unit", expect="ambiguous")
        elif kind == 16:
            c["unit"] = G.rng.choice(["Dth", "Gcal", "toe"])
            neg(c, "unsupported energy unit", expect="ambiguous")
        elif kind == 17:
            c["fuel"] = "Diesel (No. 2 Fuel Oil)"
            c["unit"] = G.rng.choice(["litre", "litres"])
            # supported since the S1K fixes (a spelling, not an ambiguity): accepted or refused both pass
            neg(c, "British spelling of litre", expect="either")
        elif kind == 18:
            # quantity cell that carries its own (different) unit
            c["quantity"] = f"{G.rng.randint(10, 9999)} m3"
            c["unit"] = "scf"
            neg(c, "quantity cell carries a unit that contradicts the unit column", expect="ambiguous")
        elif kind == 19:
            # conflicting throughput units for a tank
            c = {"process_type": "tank_flashing", "quantity": q, "unit": "bbl", "tank_unit": G.rng.choice(["m3", "gal"]),
                 "tank_gor": "50", "tank_ch4_content": "50", "tank_control_eff": "0"}
            neg(c, "unit and tank_unit disagree", expect="ambiguous", tier="specific")
        elif kind == 20:
            c = {"process_type": "tank_flashing", "quantity": q, "unit": G.rng.choice(["tonne", "scf", "MMBtu", "kg"]),
                 "tank_gor": "50", "tank_ch4_content": "50", "tank_control_eff": "0"}
            c["tank_unit"] = c["unit"]
            neg(c, "non-volume tank throughput unit", tier="specific")
        elif kind == 21:
            c = {"process_type": "pneumatic", "quantity": "10", "unit": "devices", "pneu_count": "10",
                 "pneu_bleed_rate": "1.5", "pneu_bleed_unit": G.rng.choice(["lb/hr", "kg/hr", "furlongs"]),
                 "pneu_hours": "744", "pneu_ch4_content": "85"}
            neg(c, "non-volume bleed unit", tier="specific")
        elif kind == 22:
            c = {"process_type": "combustion", "fuel": gas_fuel, "quantity": q, "unit": "m3", "hhv": "1020",
                 "combustion_efficiency": "99.5", "c1": "90", "c2": "5", "operating_temperature": "25",
                 "temp_unit": G.rng.choice(["Celsius degrees", "deg", "centigrade"]),
                 "operating_pressure": "50", "press_unit": "psig"}
            neg(c, "unknown temperature unit", expect="either" if c["temp_unit"] == "centigrade" else "ambiguous",
                tier="specific")
        else:
            c = {"process_type": "combustion", "fuel": gas_fuel, "quantity": q, "unit": "m3", "hhv": "1020",
                 "combustion_efficiency": "99.5", "c1": "90", "c2": "5", "operating_temperature": "25",
                 "temp_unit": "C", "operating_pressure": "3", "press_unit": G.rng.choice(PRESS_UNKNOWN)}
            # mmHg / torr / inHg are absolute units supported since the S1K fixes; kg/cm2 (gauge or absolute?) is not
            neg(c, "unknown pressure unit", expect="ambiguous" if c["press_unit"] == "kg/cm2" else "either",
                tier="specific")
    G.fill("NEG", target, mk)


# ------------------------------------------------------------------------------------------
PLAN = [
    ("T1_COMB", 16000), ("T1_MOBILE", 2000), ("T1_FLARE", 4000), ("T1_VENT", 1500), ("T1_AGV", 2500),
    ("T1_COMPL", 1500), ("T1_UNLOAD", 2000), ("T1_CHEM", 3000), ("T1_DRILL", 1000), ("T1_COMPONENT", 4000),
    ("T1_ACTIVITY", 3500), ("T1_TANK", 1000),
    ("T2_CF", 16000), ("T2_ENG", 6000),
    ("T3_COMB", 6000), ("T3_FLARE", 3500), ("T3_COMPL", 2500), ("T3_UNLOAD", 2000), ("T3_BLOW", 3000), ("T3_TANK", 2500),
    ("T3_PNEU", 2000), ("T3_AGR", 2000), ("T3_DEHY", 1500), ("T3_FUG", 2000), ("T3_STOICH", 1500), ("T3_AGV", 1500),
    ("T3_VENTGAS", 1000),
    ("NEG", 5000),
]


def build(seed=20261001):
    G = Gen(seed)
    names = lambda pred: sorted(n for n, f in CATALOG.items() if pred(n, f))  # noqa: E731
    usage = lambda f: ([f.get("usage")] if isinstance(f.get("usage"), str) else (f.get("usage") or []))  # noqa: E731
    for fam, n in PLAN:
        if fam == "T1_COMB":
            t1_combustion(G, fam, "combustion", n, comb_fuels("combustion"))
        elif fam == "T1_MOBILE":
            t1_combustion(G, fam, "mobile", n, comb_fuels("mobile"))
        elif fam == "T1_FLARE":
            t1_simple(G, fam, "flaring", n, names(lambda k, f: usage(f) == ["flaring"]), ["gas"], per_m3)
        elif fam == "T1_VENT":
            t1_simple(G, fam, "venting", n, ["Natural Gas (Venting/Blowdown)"], ["gas"], per_m3)
        elif fam == "T1_AGV":
            t1_simple(G, fam, "associated_gas_venting", n,
                      names(lambda k, f: "associated_gas_venting" in usage(f)), ["liq"], per_bbl_kg)
        elif fam == "T1_COMPL":
            t1_simple(G, fam, "completions", n, names(lambda k, f: "completions" in usage(f)), ["count"], per_count_t)
        elif fam == "T1_UNLOAD":
            t1_unloading(G, fam, n)
        elif fam == "T1_CHEM":
            chem = names(lambda k, f: usage(f) == ["chemical_production"])
            nitric = names(lambda k, f: usage(f) == ["nitric_acid_production"])
            adip = names(lambda k, f: usage(f) == ["adipic_acid_production"])
            t1_simple(G, fam, "chemical_production", n // 2, chem, ["mass"], per_tonne_product({"co2": 1e3, "ch4": 1e3, "n2o": 1e3}))
            t1_simple(G, fam, "nitric_acid_production", n // 4, nitric, ["mass"], per_tonne_product({"co2": 1, "ch4": 1, "n2o": 1}))
            t1_simple(G, fam, "adipic_acid_production", n - n // 2 - n // 4, adip, ["mass"],
                      per_tonne_product({"co2": 1, "ch4": 1, "n2o": 1}))
        elif fam == "T1_DRILL":
            t1_drilling(G, fam, n)
        elif fam == "T1_COMPONENT":
            t1_component_hours(G, fam, n)
        elif fam == "T1_ACTIVITY":
            t1_activity(G, fam, n)
        elif fam == "T1_TANK":
            t1_simple(G, fam, "tank_flashing", n, names(lambda k, f: usage(f) == ["tank_flashing"]), ["liq"], per_bbl_kg)
        elif fam == "T2_CF":
            t2_custom(G, fam, n)
        elif fam == "T2_ENG":
            t2_engineering(G, n // 4)
            # top up any rounding
        elif fam == "T3_COMB":
            t3_combustion(G, n)
        elif fam == "T3_FLARE":
            t3_flaring(G, n)
        elif fam == "T3_COMPL":
            t3_completions(G, n)
        elif fam == "T3_UNLOAD":
            t3_unloading(G, n)
        elif fam == "T3_BLOW":
            t3_blowdown(G, n)
        elif fam == "T3_TANK":
            t3_tank(G, n)
        elif fam == "T3_PNEU":
            t3_pneumatic(G, n)
        elif fam == "T3_AGR":
            t3_agr(G, n)
        elif fam == "T3_DEHY":
            t3_dehy(G, n)
        elif fam == "T3_FUG":
            t3_fugitive(G, n)
        elif fam == "T3_STOICH":
            t3_stoich(G, n)
        elif fam == "T3_AGV":
            t3_agv(G, n)
        elif fam == "T3_VENTGAS":
            t3_ventgas(G, n)
        elif fam == "NEG":
            negatives(G, n)
    return G


def write(G, out):
    os.makedirs(out, exist_ok=True)
    order = ["source_ref", "date", "facility_name", "process_type", "fuel", "activity_key", "quantity", "unit",
             "factor_type", "equipment_id", "group"]
    extra = sorted({k for r in G.rows for k in r} - set(order))
    header = order + extra

    def dump(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, header, extrasaction="raise")
            w.writeheader()
            w.writerows(rows)

    dump(os.path.join(out, "scope1_audit_100k.csv"), G.rows)
    dump(os.path.join(out, "scope1_audit_part1.csv"), G.rows[:50000])
    dump(os.path.join(out, "scope1_audit_part2.csv"), G.rows[50000:])
    with open(os.path.join(out, "expected.jsonl"), "w") as f:
        for m in G.meta:
            f.write(json.dumps(m) + "\n")
    return header


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "data"))
    ap.add_argument("--seed", type=int, default=20261001)
    args = ap.parse_args()
    G = build(args.seed)
    assert len(G.rows) == 100000, len(G.rows)
    refs = [r["source_ref"] for r in G.rows]
    assert len(set(refs)) == len(refs)
    assert len(G.seen) >= len(G.rows)
    header = write(G, args.out)
    import collections

    fam = collections.Counter(m["family"] for m in G.meta)
    exp = collections.Counter(m["expect"] for m in G.meta)
    print("rows", len(G.rows), "columns", len(header), "families", dict(fam), "expect", dict(exp),
          "groups", G.group_n, "duplicate candidates discarded", G.dup_rejects)
