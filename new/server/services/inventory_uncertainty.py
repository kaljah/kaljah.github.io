"""Inventory uncertainty (audit RC-10) — IPCC 2006 Vol.1 Ch.3 Approach 1 with EF correlation.

Per record, emissions are split by gas in CO2e (BUG-018). Uncertainty has two parts:

- emission-factor part, FULLY CORRELATED between records that use the same factor (same
  ef_key, or the same process/fuel for legacy rows): sigma_EF,k = sum_records(u_EF,g x E_g) per
  gas, gases combined in quadrature (BUG-008 — splitting one inventory into N records no longer
  shrinks the EF uncertainty by sqrt(N));
- activity-data part, independent per record: sigma_AD^2 = sum (u_AD x E_record)^2.

Records that store only a combined 1-sigma value (legacy) are treated as EF-dominated, which is
the conservative choice. Stored values must be 1-sigma FRACTIONS in [0, 2]; anything else is
flagged and replaced by the tier default (BUG-043). Results are reported at 95 % (k = 2).
"""
import math
from collections import defaultdict

from sqlalchemy import func

from extensions import db
from models import Emission, Scope2Emission, Scope3Emission

K95 = 2.0
MAX_REL_1SIGMA = 2.0


def _valid(u):
    if u is None:
        return None, False
    try:
        x = float(u)
    except (TypeError, ValueError):
        return None, True
    if not math.isfinite(x) or x < 0 or x > MAX_REL_1SIGMA:
        return None, True
    return (x if x > 0 else None), False


def default_rel_1sigma(scope, process_type="", calc_method="", factor_source=""):
    """Normative 1-sigma defaults when nothing valid is stored (IPCC Vol.1 Table 3.1 / API 2021 s2.4)."""
    if scope == 2:
        return 0.05  # grid factor +/-10 % at 95 %
    if scope == 3:
        return 0.15  # value-chain average data +/-30 % at 95 %
    p = (process_type or "").lower()
    m = (calc_method or "").lower()
    src = (factor_source or "").lower()
    diffuse = any(x in p for x in ("fugitive", "vent", "pneumatic", "blowdown", "completion", "tank"))
    if src == "specific" or any(x in m for x in ("tier 3", "tier3", "measurement", "cems", "composition")):
        return 0.075 if diffuse else 0.025
    if src == "custom" or any(x in m for x in ("tier 2", "tier2", "custom")):
        return 0.125 if diffuse else 0.05
    return 0.20 if diffuse else 0.10


def _process_label(process_type):
    """Readable Scope 1 process name (the page showed raw keys such as "tank_flashing")."""
    from services.scope1_calc import PROCESS_LABELS

    p = (process_type or "").strip()
    if not p:
        return "Other Scope 1"
    return PROCESS_LABELS.get(p.lower()) or p.replace("_", " ").strip().capitalize()


def _band(u95):
    """Uncertainty band of a record at 95 % (the page legend: low <= 10 %, medium <= 30 %, high)."""
    return "low" if u95 <= 0.10 else ("medium" if u95 <= 0.30 else "high")


def _method_tier(factor_source):
    """Scope 1 calculation tier from the factor source: catalog / library factors are Tier 1, custom
    (regional / lab) factors Tier 2, site-specific engineering or measured inputs Tier 3. The page used
    to label the uncertainty bands as tiers (a 5 % catalog record showed as "Tier 3")."""
    src = (factor_source or "default").strip().lower()
    return {"custom": "Tier 2", "specific": "Tier 3"}.get(src, "Tier 1")


def inventory_uncertainty(year, allowed_fids=None, facility_id=None, scope="all", statuses=("Verified",)):
    from calculations.constants import get_active_gwp

    g = get_active_gwp(horizon="100")
    gwp = {"co2": 1.0, "ch4": float(g["CH4"]), "n2o": float(g["N2O"])}
    fids = [facility_id] if facility_id else allowed_fids

    # group key -> accumulators
    ef_lin = defaultdict(lambda: defaultdict(float))  # key -> gas -> sum(u_ef * E_gas)
    ad_sq = defaultdict(float)                         # key -> sum((u_ad * E)^2)
    tot = defaultdict(float)
    cat_of = {}
    names = defaultdict(lambda: defaultdict(float))
    flagged = 0
    band_e = defaultdict(float)
    tier_s1 = defaultdict(float)

    def restrict(q, model):
        q = q.filter(model.year == year, model.status.in_(statuses))
        if fids is not None:
            q = q.filter(model.facility_id.in_(fids or [-1]))
        return q

    if scope in ("all", "1"):
        rows = restrict(Emission.query, Emission).with_entities(
            Emission.process_type, Emission.fuel_type, Emission.calc_method, Emission.factor_source,
            Emission.ef_key, Emission.co2_emissions, Emission.ch4_emissions, Emission.n2o_emissions,
            Emission.co2e_total, Emission.uncertainty, Emission.uncertainty_ch4, Emission.uncertainty_n2o,
            Emission.uncertainty_ad, Emission.uncertainty_ef_co2, Emission.uncertainty_ef_ch4,
            Emission.uncertainty_ef_n2o,
        ).all()
        for r in rows:
            e_gas = {"co2": float(r.co2_emissions or 0), "ch4": float(r.ch4_emissions or 0) * gwp["ch4"],
                     "n2o": float(r.n2o_emissions or 0) * gwp["n2o"]}
            e_tot = float(r.co2e_total or 0) or sum(e_gas.values())
            if e_tot <= 0:
                continue
            if sum(e_gas.values()) <= 0:
                e_gas = {"co2": e_tot, "ch4": 0.0, "n2o": 0.0}  # legacy rows without the gas split
            key = ("S1", r.ef_key or f"{r.process_type}|{r.fuel_type}")
            cat_of[key] = _process_label(r.process_type)
            dflt = default_rel_1sigma(1, r.process_type, r.calc_method, r.factor_source)
            u_ad, bad_ad = _valid(r.uncertainty_ad)
            has_components = u_ad is not None
            rec_u95 = 0.0
            for gas, comb, efc in (("co2", r.uncertainty, r.uncertainty_ef_co2),
                                   ("ch4", r.uncertainty_ch4, r.uncertainty_ef_ch4),
                                   ("n2o", r.uncertainty_n2o, r.uncertainty_ef_n2o)):
                if e_gas[gas] <= 0:
                    continue
                u_ef, bad1 = _valid(efc if has_components else comb)
                flagged += int(bad1)
                u_ef = u_ef if u_ef is not None else dflt
                ef_lin[key][gas] += u_ef * e_gas[gas]
                rec_u95 = max(rec_u95, u_ef * K95)
            flagged += int(bad_ad)
            if has_components:
                ad_sq[key] += (u_ad * e_tot) ** 2
            tot[key] += e_tot
            names[key][r.fuel_type or _process_label(r.process_type)] += e_tot
            band_e[_band(rec_u95)] += e_tot
            tier_s1[_method_tier(r.factor_source)] += e_tot

    for sc, model, label_col, cat_label in (
        ("2", Scope2Emission, Scope2Emission.grid_region, "Scope 2 (Indirect)"),
        ("3", Scope3Emission, Scope3Emission.category, "Scope 3 (Value Chain)"),
    ):
        if scope not in ("all", sc):
            continue
        rows = restrict(model.query, model).with_entities(label_col, model.co2e, model.uncertainty,
                                                          model.emission_factor).all()
        for lbl, co2e, u, ef in rows:
            e = float(co2e or 0)
            if e <= 0:
                continue
            key = (f"S{sc}", f"{lbl}|{ef}")  # same grid / same category factor -> correlated
            cat_of[key] = cat_label
            uu, bad = _valid(u)
            flagged += int(bad)
            uu = uu if uu is not None else default_rel_1sigma(int(sc))
            ef_lin[key]["co2e"] += uu * e
            tot[key] += e
            names[key][str(lbl or cat_label)] += e
            band_e[_band(uu * K95)] += e

    def sigma(key):
        return math.sqrt(sum(v ** 2 for v in ef_lin[key].values()) + ad_sq[key])

    cats = defaultdict(lambda: {"e": 0.0, "var": 0.0, "names": defaultdict(float)})
    for key in tot:
        c = cats[cat_of[key]]
        c["e"] += tot[key]
        c["var"] += sigma(key) ** 2
        for n, v in names[key].items():
            c["names"][n] += v
    total = sum(tot.values())
    var_total = sum(sigma(k) ** 2 for k in tot)
    u_inv_1s = math.sqrt(var_total) / total if total > 0 else None

    results = []
    for cat, c in cats.items():
        if c["e"] <= 0:
            continue
        u1 = math.sqrt(c["var"]) / c["e"]
        u95 = u1 * K95
        results.append({
            "category": cat,
            "total_emissions": c["e"],
            "uncertainty_decimal": u95,
            "uncertainty_1sigma": u1,
            "uncertainty_pct": f"±{round(u95 * 100, 1)}%",
            "level": "low" if u95 <= 0.10 else ("medium" if u95 <= 0.30 else "high"),
            "top_contributors": [
                {"name": n, "contribution": round(v / c["e"] * 100, 1)}
                for n, v in sorted(c["names"].items(), key=lambda kv: kv[1], reverse=True)[:3]
            ],
        })
    results.sort(key=lambda r: r["total_emissions"], reverse=True)
    u95_inv = u_inv_1s * K95 if u_inv_1s is not None else None
    s1_total = sum(tier_s1.values())
    return {
        "year": year,
        "inventory_uncertainty_pct": f"±{round(u95_inv * 100, 2)}%" if u95_inv is not None else None,
        "inventory_uncertainty_decimal": u95_inv,
        "inventory_uncertainty_1sigma": u_inv_1s,
        "total_inventory_emissions": total,
        # share of Scope 1 emissions by calculation tier (factor source)
        "tier_breakdown": {t: round(tier_s1.get(t, 0) / s1_total * 100, 1) if s1_total > 0 else 0
                           for t in ("Tier 1", "Tier 2", "Tier 3")},
        # share of the whole inventory by uncertainty band at 95 %
        "uncertainty_bands": {b: round(band_e.get(b, 0) / total * 100, 1) if total > 0 else 0
                              for b in ("low", "medium", "high")},
        "categories": results,
        "confidence_level_pct": 95,
        "coverage_factor": K95,
        "method": "IPCC Approach 1, EF fully correlated within a factor, AD independent",
        "records_with_invalid_uncertainty": flagged,
        "has_data": total > 0,
        "scope": scope,
        "facility_id": facility_id,
    }
