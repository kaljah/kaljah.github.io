"""Carbon / methane intensity per facility (audit RC-9 / RC-12).

One computation feeds /intensity-stats (and batch-all) and /intensity-trend:

- Emissions and production are paired per (facility, year); an intensity only uses facility-years
  that have production, so the "all years" view never divides one period's emissions by another
  period's production (BUG-017). Unmatched emissions are reported separately.
- Activity / division / segment filters apply on the facility (BUG-004).
- BOE and gas units use the shared converters (BUG-044, BUG-033).
- GWP-20 uses the active standard's pairs (BUG-005); the methane split uses the canonical
  classifier (BUG-061).
- A facility with CH4 but no gas production has no loss rate ("Missing Production Data") instead
  of 0 % "Compliant" (BUG-088).
- Segment targets come from one classifier (BUG-086).
- The OGMP level comes from services.ogmp (BUG-080); top-down surveys are averaged per
  facility-year and reconciled against the same years' bottom-up CH4 (BUG-079).
"""
from collections import defaultdict
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import func, or_, and_

from extensions import db
from models import Emission, Facility, OgmpSurvey, ProductionData, Scope2Emission, Scope3Emission
from services.dashboard_filters import (apply_scope, gas_volume_m3, horizon_delta, production_boe,
                                        production_gas_m3, production_oil_bbl, source_category, statuses,
                                        SCF_PER_BOE)
from services.ogmp import compute_facility_ogmp_level, ogmp_level_for

from calculations.units import CONVERSIONS as _CONV

CH4_DENSITY_KG_M3 = _CONV["density_ch4"]  # 60 F, 14.696 psia (API Compendium molar volume)
WEC_CH4_DENSITY_T_PER_MSCF = 0.0192  # 40 CFR 99.20, density of methane for the waste emissions threshold
# CAA s.136 waste emissions charge. Public Law 119-21 (4 July 2025) moved its start from 2024 to methane
# emitted in 2034 (and EPA's implementing rule was disapproved under the Congressional Review Act in March
# 2025), so no charge applies to 2024-2033 emissions. The statutory rate from 2026 on is $1,500 per tonne.
WEC_FIRST_YEAR = 2034
WEC_RATE_USD_PER_T = 1500.0
# the charge applies to US facilities reporting under 40 CFR 98 subpart W only
_US_NAMES = {"united states", "united states of america", "usa", "us", "u.s.", "u.s.a."}


def wec_applies_to_country(country):
    return str(country or "").strip().lower() in _US_NAMES


def segment_category(segment):
    """upstream | midstream | downstream | None (unknown / not set)."""
    s = str(segment or "").strip().lower()
    if not s:
        return None
    if any(k in s for k in ("downstream", "refin", "raffin", "petrochem", "pétrochim", "distribution")):
        return "downstream"
    if any(k in s for k in ("midstream", "processing", "lng", "gnl", "gpl", "lsh", "transmission", "pipeline",
                            "gathering", "storage", "treatment")):
        return "midstream"
    if any(k in s for k in ("upstream", "production", "exploration", "e&p", "amont")):
        return "upstream"
    return None


def _blank():
    return {"s1": 0.0, "co2": 0.0, "ch4": 0.0, "n2o": 0.0, "s2": 0.0, "s2_20": 0.0, "s3": 0.0, "s3_cat11": 0.0,
            "flaring_t": 0.0, "flaring_m3": 0.0, "flaring_ledger_m3": 0.0, "flaring_reconciled_m3": 0.0,
            "ch4_split": defaultdict(float), "records": [], "s1_count": 0,
            "ogmp_ch4_weights": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0},
            "ogmp_co2e_weights": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0},
            "boe": 0.0, "gas_m3": 0.0, "oil_bbl": 0.0, "gas_mscf": 0.0, "has_prod": False,
            "prod_unknown_units": 0, "top_down": None}


def intensity_cells(years=None, facility_id=None, activity=None, division=None, allowed_fids=None, segment=None,
                    include_pending=False, scope2_method="location"):
    """{(facility_id, year): cell} for the requested years (None = all years)."""
    scope = dict(allowed_fids=allowed_fids, facility_id=facility_id, activity=activity, division=division,
                 segment=segment)
    st = statuses(include_pending)
    cells = defaultdict(_blank)

    def yfilter(q, model):
        q = q.filter(model.year.isnot(None))
        return q.filter(model.year.in_(years)) if years is not None else q

    # production (row-level so every row gets its own unit conversion; column projection avoids full ORM hydration)
    prod_rows = yfilter(apply_scope(ProductionData.query, ProductionData, **scope), ProductionData).with_entities(
        ProductionData.id,
        ProductionData.facility_id,
        ProductionData.year,
        ProductionData.month,
        ProductionData.total_production_mmboe,
        ProductionData.oil_amount,
        ProductionData.oil_unit,
        ProductionData.gas_amount,
        ProductionData.gas_unit,
        ProductionData.gross_gas_mmsm3,
    ).all()
    for p in prod_rows:
        c = cells[(p.facility_id, p.year)]
        boe = production_boe(p)
        gas = production_gas_m3(p)
        oil_b = production_oil_bbl(p)
        if boe is None and gas is None and oil_b is None:
            c["prod_unknown_units"] += 1
            continue
        if boe is None or gas is None or (oil_b is None and getattr(p, "oil_amount", None)):
            c["prod_unknown_units"] += 1

        if boe is not None:
            c["boe"] += boe
            if boe > 0:
                c["has_prod"] = True
        elif oil_b is not None and oil_b > 0:
            c["boe"] += oil_b
            c["has_prod"] = True
        elif gas is not None and gas > 0:
            c["boe"] += gas * 35.314666721 / SCF_PER_BOE
            c["has_prod"] = True

        if gas is not None:
            c["gas_m3"] += gas
            c["gas_mscf"] += gas * 35.314666721 / 1000.0
            if gas > 0:
                c["has_prod"] = True

        if oil_b is not None:
            c["oil_bbl"] += oil_b

    # scope 1 (row level: methane split, flaring volume, OGMP materiality via column projection)
    # Strictly exclude rejected records (both status column and [Rejected] qa_flags)
    s1_q = yfilter(apply_scope(Emission.query, Emission, **scope), Emission).filter(Emission.status.in_(st))
    if any("rejected" in str(s).lower() for s in st):
        s1_q = s1_q.filter(~Emission.status.ilike("%rejected%"))
    s1 = (
        s1_q.filter(
            or_(
                Emission.qa_flag.is_(None),
                and_(~Emission.qa_flag.ilike("[rejected]%"), ~Emission.qa_flag.ilike("rejected:%")),
            )
        )
        .with_entities(
            Emission.facility_id,
            Emission.year,
            Emission.month,
            Emission.process_type,
            Emission.quantity,
            Emission.unit,
            Emission.co2e_total,
            Emission.co2_emissions,
            Emission.ch4_emissions,
            Emission.n2o_emissions,
            Emission.ogmp_level,
            Emission.factor_source,
            Emission.calc_method,
        )
        .all()
    )
    cat_cache = {}
    ogmp_cache = {}
    _stub = SimpleNamespace(ogmp_level=None, factor_source=None, calc_method=None)
    _ch4_key = {"flaring": "ch4_flaring", "vented": "ch4_venting", "fugitive": "ch4_fugitive"}
    for fid, yr, mo, pt, qty, unit, co2e_tot, co2, ch4, n2o, olvl, fsrc, cmeth in s1:
        c = cells[(fid, yr)]
        ch4_v = float(ch4 or 0)
        co2e_v = float(co2e_tot or 0)
        c["s1"] += co2e_v
        c["co2"] += float(co2 or 0)
        c["ch4"] += ch4_v
        c["n2o"] += float(n2o or 0)
        c["s1_count"] += 1
        cat = cat_cache.get(pt)
        if cat is None:
            cat = source_category(pt)
            cat_cache[pt] = cat
        c["ch4_split"][_ch4_key.get(cat, "ch4_combustion")] += ch4_v
        if cat == "flaring":
            c["flaring_t"] += co2e_v
            vol = gas_volume_m3(qty, unit, yr, mo)
            if vol:
                c["flaring_ledger_m3"] += vol
                c["flaring_m3"] += vol
        okey = (olvl, fsrc, cmeth)
        ol = ogmp_cache.get(okey)
        if ol is None:
            _stub.ogmp_level = olvl
            _stub.factor_source = fsrc
            _stub.calc_method = cmeth
            ol = ogmp_level_for(_stub)
            ogmp_cache[okey] = ol
        c["ogmp_ch4_weights"][ol] += ch4_v
        c["ogmp_co2e_weights"][ol] += co2e_v

    # Scope 2 dual reporting (location-based vs market-based per GHG Protocol), per record at both GWP
    # horizons: the GWP-20 intensity added Scope 2 at GWP-100 (bug hunt 2026-10-15 #18)
    from services.dashboard_filters import gwp_pair
    from services.scope2_gases import record_totals_fields

    market = str(scope2_method).lower() == "market"
    c100, n100 = gwp_pair("100")
    c20, n20 = gwp_pair("20")
    gwp_diff = (c20 - c100, n20 - n100)
    s2_grid_cache = {}
    q2 = (
        yfilter(apply_scope(Scope2Emission.query, Scope2Emission, **scope), Scope2Emission)
        .filter(Scope2Emission.status.in_(st))
        .with_entities(
            Scope2Emission.facility_id,
            Scope2Emission.year,
            Scope2Emission.source_type,
            Scope2Emission.grid_region,
            Scope2Emission.electricity_kwh,
            Scope2Emission.co2e,
            Scope2Emission.co2e_market_based,
        )
    )
    for fid, yr, src_type, grid_region, kwh, co2e, co2e_mkt in q2.all():
        c = cells[(fid, yr)]
        co2e_f = float(co2e or 0)
        mkt_f = float(co2e_mkt if co2e_mkt is not None else co2e or 0)
        loc20, mkt20 = record_totals_fields(
            src_type, grid_region, kwh, co2e, co2e_mkt, "20",
            grid_cache=s2_grid_cache, gwp_diff=gwp_diff,
        )
        c["s2"] += mkt_f if market else co2e_f
        c["s2_20"] += mkt20 if market else loc20

    # Scope 3
    q3 = db.session.query(Scope3Emission.facility_id, Scope3Emission.year, Scope3Emission.category, func.sum(Scope3Emission.co2e))
    q3 = yfilter(apply_scope(q3, Scope3Emission, **scope), Scope3Emission).filter(Scope3Emission.status.in_(st))
    for fid, yr, cat, val in q3.group_by(Scope3Emission.facility_id, Scope3Emission.year, Scope3Emission.category).all():
        cells[(fid, yr)]["s3"] += float(val or 0)
        norm_cat = str(cat or "").strip().lower()
        if "11" in norm_cat or "use of sold" in norm_cat:
            cells[(fid, yr)]["s3_cat11"] += float(val or 0)

    # OGMP top-down: mean of the surveys of each facility-year (each is an annual estimate, D-02)
    q = db.session.query(OgmpSurvey.facility_id, OgmpSurvey.year, func.avg(OgmpSurvey.estimated_annual_tch4))
    q = yfilter(apply_scope(q, OgmpSurvey, **scope), OgmpSurvey)
    for fid, yr, avg in q.group_by(OgmpSurvey.facility_id, OgmpSurvey.year).all():
        if avg is not None:
            cells[(fid, yr)]["top_down"] = float(avg)
    from models import FlaringDetail
    q_fd = (
        yfilter(apply_scope(FlaringDetail.query, FlaringDetail, **scope), FlaringDetail)
        .filter(FlaringDetail.status.in_(st))
        .with_entities(
            FlaringDetail.facility_id,
            FlaringDetail.year,
            FlaringDetail.routine_knm3,
            FlaringDetail.non_routine_knm3,
            FlaringDetail.safety_knm3,
        )
    )
    for fid, yr, r_knm3, nr_knm3, s_knm3 in q_fd.all():
        stream_vol = (float(r_knm3 or 0.0) + float(nr_knm3 or 0.0) + float(s_knm3 or 0.0)) * 1000.0
        if stream_vol > 0:
            cells[(fid, yr)]["flaring_reconciled_m3"] += stream_vol

    for c in cells.values():
        if c["flaring_reconciled_m3"] > 0:
            c["flaring_m3"] = c["flaring_reconciled_m3"]

    return cells


def _materiality_from_weights(ch4_weights, co2e_weights, s1_count, threshold=0.5):
    if s1_count <= 0:
        return None
    total = sum(ch4_weights.values())
    weights = ch4_weights
    if total <= 0:
        weights = co2e_weights
        total = sum(weights.values())
    if total <= 0:
        return 2
    for level in (4, 3, 2):
        if sum(v for k, v in weights.items() if k >= level) / total >= threshold:
            return level
    return 1


def facility_row(fid, cell_list, fac, year_value, gwp_horizon="100", surveys=None):
    """Aggregate one facility's cells into the API row (field names kept for the client)."""
    from routes.auth import _app_settings

    total = _blank()
    matched = _blank()  # facility-years with production: the only population used for intensities
    years_used, top_down_years = [], []
    for yr, c in cell_list:
        for tgt in ([total, matched] if c["has_prod"] else [total]):
            for k in ("s1", "co2", "ch4", "n2o", "s2", "s2_20", "s3", "s3_cat11", "flaring_t", "flaring_m3", "flaring_ledger_m3", "flaring_reconciled_m3", "boe", "gas_m3",
                      "oil_bbl", "gas_mscf"):
                tgt[k] += c[k]
            for k, v in c["ch4_split"].items():
                tgt["ch4_split"][k] += v
            tgt["prod_unknown_units"] += c["prod_unknown_units"]
        if c.get("records"):
            total["records"].extend(c["records"])
        total["s1_count"] += c.get("s1_count", 0)
        for lvl, w in c.get("ogmp_ch4_weights", {}).items():
            total["ogmp_ch4_weights"][lvl] = total["ogmp_ch4_weights"].get(lvl, 0.0) + w
        for lvl, w in c.get("ogmp_co2e_weights", {}).items():
            total["ogmp_co2e_weights"][lvl] = total["ogmp_co2e_weights"].get(lvl, 0.0) + w
        if c["has_prod"]:
            years_used.append(yr)
        if c["top_down"] is not None:
            top_down_years.append((yr, c["top_down"], c["ch4"]))

    s1_20 = total["s1"] + horizon_delta(total["ch4"], total["n2o"], "20")
    m_s1_20 = matched["s1"] + horizon_delta(matched["ch4"], matched["n2o"], "20")
    boe = matched["boe"]

    def per_boe(t):
        return (t * 1000.0) / boe if boe > 0 else None

    gas_m3 = matched["gas_m3"]
    ch4_vol = matched["ch4"] * 1000.0 / CH4_DENSITY_KG_M3
    seg_cat = segment_category(fac.segment if fac else None)
    up_t = float(_app_settings.get("ogmp_upstream_target_pct", 0.20))
    mid_t = float(_app_settings.get("ogmp_midstream_target_pct", 0.05))
    target = up_t if seg_cat == "upstream" else (mid_t if seg_cat in ("midstream", "downstream") else None)
    if gas_m3 > 0:
        loss = ch4_vol / gas_m3 * 100.0
        if target is None:
            loss_status = "Segment not set"
        elif loss <= target:
            loss_status = "Compliant"
        elif loss <= target * 1.25:
            loss_status = "Warning"
        else:
            loss_status = "Non-Compliant"
    else:
        loss = None
        loss_status = "Missing Production Data" if total["ch4"] > 0 else "No Activity"

    # OGMP reconciliation over the facility-years that have a top-down survey (BUG-079)
    threshold = (fac.reconciliation_threshold if fac and fac.reconciliation_threshold else
                 float(_app_settings.get("reconciliation_threshold", 20.0)))
    td = sum(t for _, t, _ in top_down_years)
    bu_td_years = sum(b for _, _, b in top_down_years)
    if td > 0 and bu_td_years > 0:
        variance = (td - bu_td_years) / bu_td_years * 100.0
        variance_flag = abs(variance) > threshold
        rec_status = "Discrepancy Flagged" if variance_flag else "Reconciled"
        ratio = round(td / bu_td_years, 2)
    elif td > 0:
        variance, variance_flag, rec_status, ratio = None, True, "Discrepancy Flagged", None
    elif total["ch4"] > 0:
        variance, variance_flag, rec_status, ratio = None, False, "Bottom-Up Only", None
    else:
        variance, variance_flag, rec_status, ratio = None, False, "No Activity", None

    # Check if actual surveys have recorded discrepancies
    surveys_have_discrepancy = False
    if fac:
        try:
            if surveys is None:
                from models import OgmpSurvey
                sq = OgmpSurvey.query.filter_by(facility_id=fac.id)
                if year_value and year_value != "all" and str(year_value).isdigit():
                    sq = sq.filter_by(year=int(year_value))
                actual_surveys = sq.all()
            else:
                actual_surveys = surveys
            if actual_surveys:
                surveys_have_discrepancy = any(
                    (s.reconciliation_status or "").lower() == "discrepancy detected"
                    or s.variance_flag is True
                    or (s.variance_pct is not None and abs(s.variance_pct) > threshold)
                    or (float(s.bottom_up_tch4 or 0.0) == 0.0 and float(s.estimated_annual_tch4 or 0.0) > 0.0)
                    for s in actual_surveys
                )
        except Exception:
            pass

    if surveys_have_discrepancy:
        variance_flag = True
        rec_status = "Discrepancy Detected"

    if total["records"]:
        bu_level = _bottom_up_level(total["records"])
        l_weights = defaultdict(float)
        for r in total["records"]:
            l_weights[ogmp_level_for(r)] += float(r.co2e_total or 0)
    else:
        bu_level = _materiality_from_weights(
            total["ogmp_ch4_weights"], total["ogmp_co2e_weights"], total["s1_count"]
        )
        l_weights = total["ogmp_co2e_weights"]

    level = compute_facility_ogmp_level(
        fac, year=year_value, top_down_tch4=td or None, bottom_up_tch4=bu_td_years or (total["ch4"] or None),
        reconciled_survey=(not surveys_have_discrepancy) if (td > 0 and bu_td_years > 0) else None,
        bottom_up_level=bu_level,
    ) if fac else 1

    s1_sum = sum(l_weights.values())
    l4_pct = round(sum(v for k, v in l_weights.items() if k >= 4) / s1_sum * 100.0, 1) if s1_sum > 0 else 0.0
    l3_pct = round(l_weights.get(3, 0.0) / s1_sum * 100.0, 1) if s1_sum > 0 else 0.0

    op_status = (fac.operator_status if fac else None) or "operated"
    base_year = (fac.ogmp_membership_year if fac else None) or _app_settings.get("ogmp_default_base_year", 2023)
    deadline = 3 if op_status == "operated" else 5
    gold_year = base_year + deadline
    cal_year = int(year_value) if year_value not in (None, "all") and str(year_value).isdigit() else datetime.now(timezone.utc).year
    if level == 5 and not surveys_have_discrepancy:
        pathway = "Gold Standard Achieved (Level 5)"
    elif surveys_have_discrepancy or (level == 4 and variance_flag):
        pathway = "Level 4 (Discrepancy Detected - Remediation Required)"
    elif level == 4 and loss is not None and target is not None and loss <= target:
        pathway = "Level 4 Pathway (Target Met)"
    elif cal_year <= gold_year:
        left = gold_year - cal_year
        pathway = f'On Track ({left} yr{"s" if left != 1 else ""} remaining)'
    else:
        pathway = "Overdue / Action Plan Required"

    def r4(v):
        return round(v, 4) if v is not None else None

    # EPA Waste Emissions Charge (40 CFR Part 99 / IRA s.136), per calendar year
    wec_up = float(_app_settings.get("wec_upstream_threshold", 0.0020))
    wec_mid = float(_app_settings.get("wec_midstream_threshold", 0.0005))
    wec_threshold = wec_mid if seg_cat == "midstream" else wec_up
    if gas_m3 > 0:
        # 40 CFR 99.20 Eq B-1 / B-2: threshold x gas sent to sale (Mscf) x 0.0192 mt CH4/Mscf (the rule's own
        # methane density, not the Compendium 0.6772 kg/m3)
        allowed_ch4 = gas_m3 * 35.3146667 / 1000.0 * wec_threshold * WEC_CH4_DENSITY_T_PER_MSCF
    elif matched["oil_bbl"] > 0 and seg_cat == "upstream":
        allowed_ch4 = matched["oil_bbl"] / 1_000_000.0 * 10.0  # 40 CFR 99.20(a)(2)
    else:
        allowed_ch4 = 0.0
    wec_year = cal_year
    fee_map = _app_settings.get("wec_fee_rates", {})
    first_year = int(_app_settings.get("wec_first_year", WEC_FIRST_YEAR))
    country = (fac.country if fac else None) or "Algeria"
    if year_value in (None, "all"):
        wec_rate, excess, fee, wec_status = None, None, None, "Select a single year"
    elif not wec_applies_to_country(country):
        # a liability was shown for every facility, whatever its country
        wec_rate, excess, fee, wec_status = None, None, None, "Not Applicable (US subpart W facilities only)"
    elif wec_year < first_year:
        # 2024-2033 emissions carried $900 / $1,200 / $1,500 per tonne before P.L. 119-21
        wec_rate, excess, fee, wec_status = None, None, None, f"Not Applicable (charge starts with {first_year} emissions)"
    elif seg_cat == "downstream":
        wec_rate, excess, fee, wec_status = 0.0, 0.0, 0.0, "Exempt (Downstream)"
    else:
        wec_rate = float(fee_map.get(str(wec_year), WEC_RATE_USD_PER_T))
        excess = max(0.0, (total["ch4"] if total["ch4"] > 0 else matched["ch4"]) - allowed_ch4)
        fee = round(excess * wec_rate, 2)
        wec_status = "Compliant" if excess <= 0 else "Taxable Liability"

    return {
        "facility_id": fid,
        "facility_name": fac.name if fac else "Unknown",
        "activity": fac.activity if fac else None,
        "division": fac.division if fac else None,
        "region": (fac.region or fac.name) if fac else None,
        "segment": fac.segment if fac else None,
        "segment_category": seg_cat,
        "operator_status": op_status,
        "country": (fac.country if fac else None) or "Algeria",
        "ogmp_membership_year": base_year,
        "target_gold_year": gold_year,
        "deadline_years": deadline,
        "current_ogmp_level": level,
        "gold_pathway_status": pathway,
        "reconciliation_threshold": threshold,
        "variance_pct": round(variance, 2) if variance is not None else None,
        "variance_flag": variance_flag,
        "reconciliation_status": rec_status,
        "reconciliation_years": [y for y, _, _ in top_down_years],
        # intensities (kg per BOE) over facility-years with production only
        "intensity_years": sorted(years_used),
        "co2_intensity": per_boe(matched["s1"] + matched["s2"]),
        "co2_intensity_gwp20": per_boe(m_s1_20 + matched["s2_20"]),
        "scope1_intensity": per_boe(matched["s1"]),
        "scope1_intensity_gwp20": per_boe(m_s1_20),
        "scope2_intensity": per_boe(matched["s2"]),
        "scope3_intensity": per_boe(matched["s3"]),
        "ch4_intensity": per_boe(matched["ch4"]),
        "api_flaring_intensity": per_boe(matched["flaring_t"]),
        "methane_loss_rate_pct": r4(loss),
        "flaring_rate_pct": r4(matched["flaring_m3"] / gas_m3 * 100.0) if gas_m3 > 0 else None,
        "ogmp_gold_standard_target": target,
        "ogmp_target_status": loss_status,
        "wec_status": wec_status,
        "excess_ch4_tonnes": excess,
        "wec_fee_usd": fee,
        "wec_rate_usd_per_t": wec_rate,
        "ogmp_l3_pct": l3_pct,
        "ogmp_l4_pct": l4_pct,
        "top_down_tch4": td,
        "reconciliation_ratio": ratio,
        "ch4_venting": total["ch4_split"]["ch4_venting"],
        "ch4_fugitive": total["ch4_split"]["ch4_fugitive"],
        "ch4_flaring": total["ch4_split"]["ch4_flaring"],
        "ch4_combustion": total["ch4_split"]["ch4_combustion"],
        # production over the matched years
        "total_boe": boe,
        "total_oil": matched["oil_bbl"],
        "total_gas": matched["gas_mscf"],
        "total_gas_m3": gas_m3,
        "production_rows_with_unknown_units": total["prod_unknown_units"],
        "flaring_volume": total["flaring_m3"],
        "flaring_m3": total["flaring_m3"],
        "flaring_ledger_volume": total["flaring_ledger_m3"],
        "flaring_ledger_m3": total["flaring_ledger_m3"],
        "flaring_reconciled_volume": total["flaring_reconciled_m3"],
        "flaring_reconciled_m3": total["flaring_reconciled_m3"],
        "flaring_emissions": total["flaring_t"],
        # totals over every requested year (display); intensities use the matched subset
        "total_co2e": total["s1"] + total["s2"],
        "total_co2e_gwp20": s1_20 + total["s2_20"],
        "total_scope1": total["s1"],
        "total_scope1_gwp20": s1_20,
        "total_scope2": total["s2"],
        "total_scope3": total["s3"],
        "total_scope3_cat11": total["s3_cat11"],
        "scope3_cat11_missing": bool(matched["boe"] > 0 and matched["s3_cat11"] == 0.0),
        "total_co2": total["co2"],
        "total_ch4": total["ch4"],
        "total_n2o": total["n2o"],
        "total_co2e_s3": total["s3"],
        "total_co2e_all": total["s1"] + total["s2"] + total["s3"],
        "unmatched_co2e": (total["s1"] + total["s2"]) - (matched["s1"] + matched["s2"]),
        "gwp_horizon": "20" if str(gwp_horizon) == "20" else "100",
    }


def _bottom_up_level(records):
    from services.ogmp import materiality_level

    return materiality_level(records) if records else None


def intensity_rows(year=None, include_pending=False, gwp_horizon="100", scope2_method="location", **scope):
    """Per-facility rows for one year or all years (year None / 'all')."""
    years = None if year in (None, "", "all") else [int(year)]
    cells = intensity_cells(years=years, include_pending=include_pending, scope2_method=scope2_method, **scope)
    by_fac = defaultdict(list)
    for (fid, yr), c in cells.items():
        by_fac[fid].append((yr, c))
    fids = list(by_fac) or [-1]
    facs = {f.id: f for f in Facility.query.filter(Facility.id.in_(fids)).all()}
    sq = OgmpSurvey.query.filter(OgmpSurvey.facility_id.in_(fids))
    if years is not None:
        sq = sq.filter(OgmpSurvey.year.in_(years))
    surveys_by_fid = defaultdict(list)
    for s in sq.all():
        surveys_by_fid[s.facility_id].append(s)
    return [
        facility_row(fid, lst, facs.get(fid), year, gwp_horizon, surveys=surveys_by_fid.get(fid, []))
        for fid, lst in by_fac.items()
    ]


def intensity_trend(years, include_pending=False, gwp_horizon="100", scope2_method="location", **scope):
    """[{year, data: [facility rows]}] computed from one bulk read."""
    yr_list = list(years)
    cells = intensity_cells(years=yr_list, include_pending=include_pending, scope2_method=scope2_method, **scope)
    fids = list({fid for fid, _ in cells}) or [-1]
    facs = {f.id: f for f in Facility.query.filter(Facility.id.in_(fids)).all()}
    surveys_by_fy = defaultdict(list)
    if yr_list:
        for s in OgmpSurvey.query.filter(OgmpSurvey.facility_id.in_(fids), OgmpSurvey.year.in_(yr_list)).all():
            surveys_by_fy[(s.facility_id, s.year)].append(s)
    out = []
    for y in years:
        rows = [
            facility_row(fid, [(yr, c)], facs.get(fid), y, gwp_horizon, surveys=surveys_by_fy.get((fid, yr), []))
            for (fid, yr), c in cells.items()
            if yr == y
        ]
        out.append({"year": str(y), "data": rows})  # string year: the established API contract
    return out
