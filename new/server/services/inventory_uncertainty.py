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
import logging
import math
from collections import defaultdict

from sqlalchemy import func

from extensions import db
from models import Emission, Scope2Emission, Scope3Emission

logger = logging.getLogger(__name__)

K95 = 2.0
MAX_REL_1SIGMA = 5.0  # an order-of-magnitude N2O default is 450 % at 1 sigma (IPCC 2006 Vol.2 Table 2.12)


def _valid(u):
    if u is None:
        return None, False
    try:
        x = float(u)
    except (TypeError, ValueError) as exc:
        logger.debug("Ignoring non-numeric uncertainty value %r: %s", u, exc)
        return None, True
    if not math.isfinite(x) or x < 0 or x > MAX_REL_1SIGMA:
        return None, True
    return (x if x > 0 else None), False


def default_rel_1sigma(scope, process_type="", calc_method="", factor_source=""):
    """Platform 1-sigma defaults (expert judgement) for a record with no valid stored uncertainty."""
    if scope == 2:
        return 0.05  # grid factor +/-10 % at 95 %
    if scope == 3:
        return 0.15  # value-chain average data +/-30 % at 95 %
    from calculations.uncertainty import resolve_tier

    p = (process_type or "").lower()
    m = (calc_method or "").lower()
    tier = resolve_tier(factor_source)  # also the aliases a form stores, e.g. drilling "tier2_plus"
    diffuse = any(x in p for x in ("fugitive", "vent", "pneumatic", "blowdown", "completion", "tank"))
    if tier == 3 or any(x in m for x in ("tier 3", "tier3", "measurement", "cems", "composition")):
        return 0.075 if diffuse else 0.025
    if tier == 2 or any(x in m for x in ("tier 2", "tier2", "custom")):
        return 0.125 if diffuse else 0.05
    return 0.20 if diffuse else 0.10


def _process_label(process_type):
    """Readable Scope 1 process name (the page showed raw keys such as "tank_flashing")."""
    from services.labels import process_label

    return process_label(process_type)


def _band(u95):
    """Uncertainty band of a record at 95 % (the page legend: low <= 10 %, medium <= 30 %, high)."""
    return "low" if u95 <= 0.10 else ("medium" if u95 <= 0.30 else "high")


def _method_tier(factor_source):
    """Scope 1 calculation tier from the factor source: catalog / library factors are Tier 1, custom
    (regional / lab) factors Tier 2, site-specific engineering or measured inputs Tier 3. The page used
    to label the uncertainty bands as tiers (a 5 % catalog record showed as "Tier 3")."""
    from calculations.uncertainty import resolve_tier

    return f"Tier {resolve_tier(factor_source)}"


def _published_1sigma(process_type, gas, factor_source, fallback):
    """1-sigma EF uncertainty of a record without a stored one: the published per-gas default of its category
    (calculations.uncertainty.DEFAULT_EF_UNCERTAINTY, 95 % half-widths: IPCC 2006 Table 2.12, Compendium Table 5-5),
    else the platform default. One 2.5-20 % value served every gas (audit 2026-11 F-AGG-11)."""
    from calculations.uncertainty import DEFAULT_EF_UNCERTAINTY, PROCESS_CATEGORY, resolve_tier

    cat = PROCESS_CATEGORY.get(str(process_type or "").strip().lower())
    row = (DEFAULT_EF_UNCERTAINTY.get(cat) or {}).get(gas)
    if not row:
        return fallback
    return row.get(f"T{resolve_tier(factor_source)}", row["T1"]) / K95


def _restrict(q, model, year, statuses, fids):
    """Year, status and the dashboard's scope: test records and test facilities out, the caller's facilities, or the
    tenant when unrestricted (only the record flag was checked and no tenant: audit 2026-11 F-AGG-02 / F-AGG-08)."""
    from services.dashboard_filters import apply_scope

    return apply_scope(q.filter(model.year == year, model.status.in_(statuses)), model, allowed_fids=fids)


def _gwp_variance(gwp_e, u_gwp):
    """({category: variance}, inventory variance) of the GWP uncertainty. One GWP serves every source, so it is fully
    correlated: sigma = u_GWP x sum(E_gas) (IPCC 2006 Vol 1 s3.2.3). It was added per factor key and the keys summed
    in quadrature, ~1/sqrt(n) of it (audit 2026-11 F-AGG-03)."""
    per_cat = {cat: sum((u_gwp.get(g, 0.0) * e) ** 2 for g, e in by_gas.items()) for cat, by_gas in gwp_e.items()}
    total = sum((u_gwp.get(g, 0.0) * sum(b.get(g, 0.0) for b in gwp_e.values())) ** 2 for g in ("co2", "ch4", "n2o"))
    return per_cat, total


def inventory_uncertainty(year, allowed_fids=None, facility_id=None, scope="all", statuses=("Verified",), include_gwp_uncertainty=False, scope2_method="location", include_monte_carlo=True):
    """Computes IPCC Approach 1 (correlated EF) and Approach 2 Monte Carlo inventory uncertainty."""
    from calculations.constants import get_active_gwp
    from calculations.uncertainty import gwp_uncertainty_1sigma
    from services.dashboard_filters import _parse_facility_ids

    g = get_active_gwp(horizon="100")
    GWP_UNCERTAINTY_1SIGMA = gwp_uncertainty_1sigma(g)  # of the active report (audit 2026-11 F-AGG-09)
    gwp = {"co2": 1.0, "ch4": float(g["CH4"]), "n2o": float(g["N2O"])}
    parsed = _parse_facility_ids(facility_id)
    if parsed is not None:
        if allowed_fids is not None:
            allowed_set = set(allowed_fids)
            fids = [fid for fid in parsed if fid in allowed_set] or [-1]
        else:
            fids = parsed
    else:
        fids = allowed_fids

    # group key -> accumulators
    ef_lin = defaultdict(lambda: defaultdict(float))  # key -> gas -> sum(u_ef * E_gas)
    ad_sq = defaultdict(float)                         # key -> sum((u_ad * E)^2)
    tot = defaultdict(float)
    cat_of = {}
    names = defaultdict(lambda: defaultdict(float))
    flagged = 0
    band_e = defaultdict(float)
    tier_s1 = defaultdict(float)
    gwp_e = defaultdict(lambda: defaultdict(float))  # category -> gas -> CO2e (one GWP for all: _gwp_variance)

    def restrict(q, model):
        return _restrict(q, model, year, statuses, fids)

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
                u_ef = u_ef if u_ef is not None else _published_1sigma(r.process_type, gas, r.factor_source, dflt)
                # IPCC AR5 Chapter 8 GWP uncertainty propagation
                gwp_u = GWP_UNCERTAINTY_1SIGMA.get(gas, 0.0) if include_gwp_uncertainty else 0.0
                effective_u_ef = math.sqrt(u_ef ** 2 + gwp_u ** 2) if gwp_u > 0 else u_ef
                ef_lin[key][gas] += u_ef * e_gas[gas]
                gwp_e[_process_label(r.process_type)][gas] += e_gas[gas] if gwp_u > 0 else 0.0
                rec_u95 = max(rec_u95, effective_u_ef * K95)
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
        co2e_col = (
            func.coalesce(Scope2Emission.co2e_market_based, Scope2Emission.co2e)
            if sc == "2" and str(scope2_method).lower() == "market"
            else model.co2e
        )
        rows = restrict(model.query, model).with_entities(label_col, co2e_col, model.uncertainty,
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
        """Combines correlated emission-factor and independent activity-data variance in quadrature."""
        return math.sqrt(sum(v ** 2 for v in ef_lin[key].values()) + ad_sq[key])

    cats = defaultdict(lambda: {"e": 0.0, "var": 0.0, "names": defaultdict(float)})
    for key in tot:
        c = cats[cat_of[key]]
        c["e"] += tot[key]
        c["var"] += sigma(key) ** 2
        for n, v in names[key].items():
            c["names"][n] += v
    gwp_cat_var, gwp_var = _gwp_variance(gwp_e, GWP_UNCERTAINTY_1SIGMA)
    for cat, v in gwp_cat_var.items():
        cats[cat]["var"] += v
    total = sum(tot.values())
    var_total = sum(sigma(k) ** 2 for k in tot) + gwp_var
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

    # Approach 2: Monte Carlo simulation & distribution histogram
    mc_result = None
    if results and include_monte_carlo:
        try:
            from calculations.uncertainty import monte_carlo_simulation
            mc_sources = [
                {"value": float(r["total_emissions"]), "relative_uncertainty": float(r.get("uncertainty_1sigma") or 0.05)}
                for r in results if r.get("total_emissions", 0) > 0
            ]
            if mc_sources:
                mc_result = monte_carlo_simulation(mc_sources, iterations=2500, seed=42)
        except Exception as exc:
            logger.warning("Monte Carlo uncertainty simulation failed for year %s: %s", year, exc, exc_info=True)
            mc_result = None

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
        "monte_carlo": mc_result,
        "confidence_level_pct": 95,
        "coverage_factor": K95,
        "method": "IPCC Approach 1, EF fully correlated within a factor, AD independent",
        "records_with_invalid_uncertainty": flagged,
        "has_data": total > 0,
        "scope": scope,
        "facility_id": facility_id,
        "gwp_uncertainty_included": include_gwp_uncertainty,
    }
