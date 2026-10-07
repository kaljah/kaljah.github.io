"""Flaring summary and granular intensity routes.

Split out of routes/dashboard.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``dashboard_bp`` blueprint, so URLs and endpoint names are the same.
"""
from flask import jsonify, request
from models import Emission, ProductionData
from routes.auth import login_required
from utils import get_allowed_facility_ids, get_current_user
from routes.dashboard import dashboard_bp, is_it_role


@dashboard_bp.route("/flaring-summary", methods=["GET"])
@login_required
def get_flaring_summary():
    """Flaring by operational stream (Routine / Non-Routine / Safety / Unclassified) and the
    Decree 21-330 Art. 9 flaring intensity.

    RC-9 / RC-5: same facility-level filters, status, year and GWP horizon as the rest of the
    dashboard (BUG-026, BUG-072 addendum); exact unit conversion for flared and produced gas
    (BUG-033/035); no invented stream split or proxy factor (BUG-036).
    """
    from models import FlaringDetail
    from services.dashboard_filters import (apply_scope, gas_volume_m3, horizon_delta, production_gas_m3,
                                            source_category, statuses)

    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)
    year = request.args.get("year")
    all_years = not year or year == "all"
    try:
        yr = None if all_years else int(year)
    except ValueError:
        return jsonify({"error": "Invalid year"}), 400

    facility_id = request.args.get("facility_id") or request.args.get("facilityId")
    fac_filter = int(facility_id) if facility_id and facility_id != "all" else None
    if fac_filter and allowed_fids is not None and fac_filter not in allowed_fids:
        return jsonify({"error": "Unauthorized facility"}), 403
    scope = dict(allowed_fids=allowed_fids, facility_id=fac_filter, activity=request.args.get("activity"),
                 division=request.args.get("division"), segment=request.args.get("segment"))
    include_pending = request.args.get("includePending", "false").lower() == "true"
    horizon = request.args.get("gwp_horizon", "100")

    def streams_for(year_value):
        fd_q = apply_scope(FlaringDetail.query, FlaringDetail, **scope)
        if year_value is not None:
            fd_q = fd_q.filter(FlaringDetail.year == year_value)
        fd = fd_q.all()
        em_q = apply_scope(Emission.query, Emission, **scope).filter(Emission.status.in_(statuses(include_pending)))
        if year_value is not None:
            em_q = em_q.filter(Emission.year == year_value)
        out = {k: {"m3": 0.0, "tco2e": 0.0} for k in ("routine", "non_routine", "safety", "unclassified")}
        # operator-reported stream volumes take precedence for the facilities that report them (the
        # sum of the parts); the other facilities keep their emission-record volumes. Replacing
        # every facility's volume dropped the record-only facilities from the flared volume while
        # their gas production stayed in the intensity denominator.
        detail_fids = {r.facility_id for r in fd
                       if (r.routine_knm3 or 0) or (r.non_routine_knm3 or 0) or (r.safety_knm3 or 0)}
        unconverted = 0
        for e in em_q.all():
            if source_category(e.process_type) != "flaring":
                continue
            pt = (e.process_type or "").strip().lower()
            key = {"routine_flaring": "routine", "non_routine_flaring": "non_routine",
                   "safety_flaring": "safety"}.get(pt, "unclassified")
            if e.facility_id not in detail_fids:
                vol = gas_volume_m3(e.quantity, e.unit, e.year, e.month)
                if vol is None:
                    unconverted += 1
                else:
                    out[key]["m3"] += vol
            out[key]["tco2e"] += float(e.co2e_total or 0) + horizon_delta(e.ch4_emissions, e.n2o_emissions, horizon)
        detail_used = bool(detail_fids)
        for r in fd:
            if r.facility_id in detail_fids:
                out["routine"]["m3"] += float(r.routine_knm3 or 0) * 1000.0
                out["non_routine"]["m3"] += float(r.non_routine_knm3 or 0) * 1000.0
                out["safety"]["m3"] += float(r.safety_knm3 or 0) * 1000.0
        dres = [float(r.measured_dre_pct) for r in fd if r.measured_dre_pct is not None]
        return out, unconverted, detail_used, dres

    streams, unconverted, detail_used, dres = streams_for(yr)
    total_m3 = sum(v["m3"] for v in streams.values())
    total_tco2e = sum(v["tco2e"] for v in streams.values())

    # Gas produced over the same population and period
    prod_q = apply_scope(ProductionData.query, ProductionData, **scope)
    if yr is not None:
        prod_q = prod_q.filter(ProductionData.year == yr)
    gas_m3, prod_unconverted = 0.0, 0
    for prow in prod_q.all():
        g = production_gas_m3(prow)
        if g is None:
            prod_unconverted += 1
        else:
            gas_m3 += g

    if all_years:
        intensity, compliant, status_txt = None, None, "Select a single year to assess Decree 21-330 compliance"
    elif gas_m3 > 0:
        intensity = total_m3 / gas_m3 * 100.0
        compliant = intensity <= 1.00
        status_txt = "COMPLIANT (Under 1.00% Target)" if compliant else "EXCEEDS THRESHOLD (> 1.00%)"
    else:
        intensity, compliant, status_txt = None, None, "No gas production recorded for this period"

    yoy = None
    if not all_years:
        prev, _, _, _ = streams_for(yr - 1)
        prev_m3 = sum(v["m3"] for v in prev.values())
        if prev_m3 > 0:
            yoy = (total_m3 - prev_m3) / prev_m3 * 100.0

    def block(key):
        m3 = streams[key]["m3"]
        return {
            "volume_m3": round(m3, 2),
            "volume_knm3": round(m3 / 1000.0, 2),
            "percentage": round(m3 / total_m3 * 100.0, 1) if total_m3 > 0 else 0.0,
            # with operator stream volumes the emissions records may not be split by stream; not rounded to
            # 2 decimals here (the page rounds for display: 213.549 showed as 213.6 after two roundings)
            "tco2e": round(streams[key]["tco2e"], 6),
        }

    return jsonify({
        "year": yr if yr is not None else "all",
        "facility_id": fac_filter,
        "gwp_horizon": "20" if str(horizon) == "20" else "100",
        "includes_pending": include_pending,
        "routine_flaring": block("routine"),
        "non_routine_flaring": block("non_routine"),
        "safety_flaring": block("safety"),
        "unclassified_flaring": block("unclassified"),
        "total_flaring": {
            "volume_m3": round(total_m3, 2),
            "volume_knm3": round(total_m3 / 1000.0, 2),
            "tco2e": round(total_tco2e, 6),
        },
        "stream_volume_source": ("FlaringDetail (operator-reported)" if detail_used and not streams["unclassified"]["m3"]
                                 else "FlaringDetail and emission records" if detail_used else "Emission records"),
        "records_with_unknown_volume_unit": unconverted,
        "production_rows_with_unknown_gas_unit": prod_unconverted,
        "gas_production_m3": round(gas_m3, 2),
        "flaring_intensity_pct": round(intensity, 3) if intensity is not None else None,
        "regulatory_threshold_pct": 1.00,
        "statute": "Executive Decree 21-330 Article 9",
        "is_compliant": compliant,
        "compliance_status": status_txt,
        "yoy_change_pct": round(yoy, 2) if yoy is not None else None,
        "measured_dre_pct": round(sum(dres) / len(dres), 2) if dres else None,
        "dre_method": "Measured (FlaringDetail)" if dres else "Not measured (98% default in calculations)",
    })


@dashboard_bp.route("/granular-intensities", methods=["GET"])
@login_required
def get_granular_intensities():
    """Multi-metric intensities for the Master Report (BUG-044).

    Numerator and denominator cover the same facility-years (those with production); BOE is
    computed per production row with the platform's single BOE definition; values that are not
    recorded (saleable production, gas throughput) are returned as null instead of invented
    constants. Same filters and role rules as the rest of the dashboard.
    """
    from services.dashboard_filters import SCF_PER_BOE
    from services.intensity import intensity_cells

    user = get_current_user()
    if is_it_role(user):
        return jsonify({"error": "Forbidden: IT Administrators cannot access operational dashboard data"}), 403
    allowed_fids = get_allowed_facility_ids(user)

    year = request.args.get("year")
    try:
        years = None if (not year or year == "all") else [int(year)]
    except ValueError:
        return jsonify({"error": "Invalid year"}), 400
    facility_id = request.args.get("facility_id") or request.args.get("facilityId")
    fac_filter = int(facility_id) if facility_id and facility_id != "all" else None
    if fac_filter and allowed_fids is not None and fac_filter not in allowed_fids:
        return jsonify({"error": "Unauthorized facility"}), 403

    cells = intensity_cells(years=years, facility_id=fac_filter, allowed_fids=allowed_fids,
                            activity=request.args.get("activity"), division=request.args.get("division"),
                            segment=request.args.get("segment"))
    matched = [(k, c) for k, c in cells.items() if c["has_prod"]]
    ghg = sum(c["s1"] + c["s2"] for _, c in matched)
    ch4 = sum(c["ch4"] for _, c in matched)
    boe = sum(c["boe"] for _, c in matched)
    gas_m3 = sum(c["gas_m3"] for _, c in matched)
    unmatched_ghg = sum(c["s1"] + c["s2"] for _, c in cells.items() if not c["has_prod"])

    # saleable production only where it is actually recorded (no assumed 85 % fraction)
    # the same facility filters as the emissions (activity / division / segment were not applied,
    # so a filtered view divided its emissions by every facility's saleable production)
    from services.dashboard_filters import apply_scope
    prod_q = apply_scope(ProductionData.query, ProductionData, allowed_fids=allowed_fids, facility_id=fac_filter,
                         activity=request.args.get("activity"), division=request.args.get("division"),
                         segment=request.args.get("segment"))
    if years:
        prod_q = prod_q.filter(ProductionData.year.in_(years))
    saleable_rows = [p for p in prod_q.all() if p.saleable_production_mmboe]
    saleable_boe = sum(float(p.saleable_production_mmboe) * 1e6 for p in saleable_rows) or None
    saleable_ghg = sum(cells[(p.facility_id, p.year)]["s1"] + cells[(p.facility_id, p.year)]["s2"]
                       for p in {(r.facility_id, r.year): r for r in saleable_rows}.values()
                       if (p.facility_id, p.year) in cells) if saleable_boe else None

    ci_total = ghg * 1000.0 / boe if boe > 0 else None
    ci_saleable = saleable_ghg * 1000.0 / saleable_boe if saleable_boe else None
    # NGSI methane intensity (wt %): CH4 mass / natural gas mass, pipeline gas ~0.80 kg/Sm3
    ngsi = ch4 / (gas_m3 * 0.00080) * 100.0 if gas_m3 > 0 else None

    OGCI_TARGET = 17.0
    basis = ci_saleable if ci_saleable is not None else ci_total
    ratio = basis / OGCI_TARGET if basis is not None else None
    return jsonify({
        "year": years[0] if years else "all",
        "facility_id": fac_filter,
        "total_ghg_tco2e": round(ghg, 2),
        "unmatched_ghg_tco2e": round(unmatched_ghg, 2),
        "total_ch4_tonnes": round(ch4, 2),
        "total_production_boe": round(boe, 2),
        "boe_definition_scf_per_boe": round(SCF_PER_BOE, 1),
        "saleable_production_boe": round(saleable_boe, 2) if saleable_boe else None,
        "gross_gas_sm3": round(gas_m3, 2),
        "ci_by_total_production_kg_boe": round(ci_total, 2) if ci_total is not None else None,
        "ci_by_saleable_production_kg_boe": round(ci_saleable, 2) if ci_saleable is not None else None,
        "methane_intensity_ngsi_wt_pct": round(ngsi, 3) if ngsi is not None else None,
        "ogci_target_kg_boe": OGCI_TARGET,
        "ogci_comparison_basis": "saleable" if ci_saleable is not None else ("total" if ci_total is not None else None),
        "ratio_to_ogci_target": round(ratio, 2) if ratio is not None else None,
        "ogci_status": None if ratio is None else ("WITHIN TARGET" if basis <= OGCI_TARGET else f"{round(ratio, 1)}x ABOVE TARGET"),
    })
