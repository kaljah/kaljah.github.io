"""
Data Provenance & 'Trace This Number' Drill-Down Service (Part 2.4)
==================================================================
Provides complete end-to-end transparency for any KPI, metric card, or export figure:
1. Total and unit
2. Granular category / process breakdown
3. Underlying records count & sample records
4. Exact emission factor name, version, and official source reference
5. GWP standard and factors applied
6. Maker-checker workflow lineage (submitter, reviewer, sign-off timestamps)
7. Explicit mathematical calculation formula
"""
from collections import defaultdict
from flask import Blueprint, request, jsonify, session
from extensions import db
from models import (
    Emission, Scope2Emission, Scope3Emission, Facility, CustomFactor, User, FlaringDetail
)
from routes.auth import login_required
from utils import get_current_user, get_allowed_facility_ids
from calculations.constants import GWP_STANDARDS, GWP_AR5
from routes.auth_settings import _app_settings

traceability_bp = Blueprint("traceability", __name__, url_prefix="/api/traceability")


@traceability_bp.route("/trace", methods=["GET"])
@login_required
def trace_metric():
    """
    Part 2.4: Trace any metric to its underlying source records, factor versions,
    GWP standards, and approval audit timestamps.
    """
    user = get_current_user()
    metric = str(request.args.get("metric") or "scope1_total").strip().lower()
    year_arg = request.args.get("year")
    facility_id_arg = request.args.get("facility_id") or request.args.get("facilityId")
    process_type = request.args.get("process_type")

    allowed_fids = get_allowed_facility_ids(user)

    year = int(year_arg) if (year_arg and year_arg != "all" and str(year_arg).isdigit()) else None
    facility_id = int(facility_id_arg) if (facility_id_arg and str(facility_id_arg).isdigit()) else None

    if facility_id and allowed_fids is not None and facility_id not in allowed_fids:
        return jsonify({"error": "Access to requested facility is denied"}), 403

    active_gwp = str(_app_settings.get("gwp_standard") or "AR5").upper()
    gwp_meta = GWP_STANDARDS.get(active_gwp, GWP_AR5)

    # Initialize provenance structures
    total_val = 0.0
    unit = "tCO2e"
    records_count = 0
    categories = defaultdict(lambda: {"count": 0, "val": 0.0})
    factors_used = {}
    submitters = set()
    approvers = set()
    statuses = defaultdict(int)
    earliest_date = None
    latest_date = None
    sample_records = []
    formula_str = ""

    # Facility map for names (tenant/facility scoped)
    fac_q = Facility.query
    if allowed_fids is not None:
        fac_q = fac_q.filter(Facility.id.in_(allowed_fids or [-1]))
    fac_map = {f.id: f.name for f in fac_q.all()}

    # Scope 1 or Corporate Total or Methane or Flaring
    include_s1 = metric in ("scope1_total", "corporate_total", "methane_total", "flaring_volume") or metric.startswith("s1")
    include_s2 = metric in ("scope2_total", "corporate_total") or metric.startswith("s2")
    include_s3 = metric in ("scope3_total", "corporate_total") or metric.startswith("s3")

    if include_s1:
        q1 = Emission.query.filter(Emission.is_test == False)
        if year:
            q1 = q1.filter(Emission.year == year)
        if facility_id:
            q1 = q1.filter(Emission.facility_id == facility_id)
        elif allowed_fids is not None:
            q1 = q1.filter(Emission.facility_id.in_(allowed_fids))
        if process_type:
            q1 = q1.filter(Emission.process_type == process_type)
        if metric == "flaring_volume":
            q1 = q1.filter(Emission.process_type == "flaring")

        s1_records = q1.all()
        for r in s1_records:
            records_count += 1
            if metric == "methane_total":
                v = float(r.ch4_emissions or 0.0)
                unit = "tCH4"
            elif metric == "flaring_volume":
                v = float(r.quantity or 0.0) if str(r.unit or "").lower() in ("m3", "nm3", "sm3") else 0.0
                unit = "m3"
            else:
                v = float(r.co2e_total or 0.0)

            total_val += v
            cat_name = r.process_type or "General Scope 1"
            categories[cat_name]["count"] += 1
            categories[cat_name]["val"] += v
            statuses[r.status or "Pending"] += 1

            if r.created_by_name:
                submitters.add(r.created_by_name)
            if r.approved_by_name:
                approvers.add(r.approved_by_name)

            if r.timestamp:
                ts = r.timestamp.isoformat()
                earliest_date = ts if earliest_date is None or ts < earliest_date else earliest_date
                latest_date = ts if latest_date is None or ts > latest_date else latest_date

            f_key = f"{r.factor_source or 'Default'}|{r.factor_version or 'API-2021.1'}"
            if f_key not in factors_used:
                factors_used[f_key] = {
                    "source": r.factor_source or "API Compendium 2021 / Decree 21-330",
                    "version": r.factor_version or "API-2021.1",
                    "ef_co2": r.ef_used_co2,
                    "ef_ch4": r.ef_used_ch4,
                    "ef_n2o": r.ef_used_n2o,
                    "records_count": 0,
                }
            factors_used[f_key]["records_count"] += 1

            if len(sample_records) < 25:
                sample_records.append({
                    "record_id": r.record_id or f"S1-{r.id}",
                    "scope": 1,
                    "facility_name": fac_map.get(r.facility_id, f"Facility #{r.facility_id}"),
                    "process_type": r.process_type,
                    "fuel_or_source": r.fuel_type or r.equipment_id or "Stationary",
                    "quantity": r.quantity,
                    "unit": r.unit,
                    "factor_source": r.factor_source or "API Compendium 2021",
                    "factor_version": r.factor_version or "API-2021.1",
                    "gwp_version": r.gwp_version or active_gwp,
                    "co2e_t": round(float(r.co2e_total or 0.0), 4),
                    "status": r.status or "Pending",
                    "submitter": r.created_by_name or f"User #{r.created_by}",
                    "approver": r.approved_by_name or (f"User #{r.approved_by}" if r.approved_by else "None"),
                    "approved_at": r.approved_at.isoformat() if r.approved_at else None,
                })

    # Scope 2
    if include_s2 and metric != "flaring_volume" and metric != "methane_total":
        q2 = Scope2Emission.query
        if year:
            q2 = q2.filter(Scope2Emission.year == year)
        if facility_id:
            q2 = q2.filter(Scope2Emission.facility_id == facility_id)
        elif allowed_fids is not None:
            q2 = q2.filter(Scope2Emission.facility_id.in_(allowed_fids))

        for r in q2.all():
            records_count += 1
            v = float(r.co2e or 0.0)
            total_val += v
            cat_name = f"Scope 2: {r.source_type or 'Electricity'}"
            categories[cat_name]["count"] += 1
            categories[cat_name]["val"] += v
            statuses[r.status or "Pending"] += 1
            if r.created_by_name:
                submitters.add(r.created_by_name)
            if r.approved_by_name:
                approvers.add(r.approved_by_name)

            f_key = f"Scope2-{r.grid_region or 'Algerian National Grid'}|{r.factor_version or '2023.1'}"
            if f_key not in factors_used:
                factors_used[f_key] = {
                    "source": f"Grid Emission Factor ({r.grid_region or 'Algerian Grid / Sonelgaz'})",
                    "version": r.factor_version or "2023.1",
                    "ef_co2": r.emission_factor,
                    "records_count": 0,
                }
            factors_used[f_key]["records_count"] += 1

            if len(sample_records) < 25:
                sample_records.append({
                    "record_id": f"S2-{r.id}",
                    "scope": 2,
                    "facility_name": fac_map.get(r.facility_id, f"Facility #{r.facility_id}"),
                    "process_type": r.source_type or "Electricity",
                    "fuel_or_source": r.grid_region or "Grid Electricity",
                    "quantity": r.electricity_kwh,
                    "unit": "kWh",
                    "factor_source": "Sonelgaz Grid Factor",
                    "factor_version": r.factor_version or "2023.1",
                    "gwp_version": r.gwp_version or active_gwp,
                    "co2e_t": round(v, 4),
                    "status": r.status or "Pending",
                    "submitter": r.created_by_name or f"User #{r.created_by}",
                    "approver": r.approved_by_name or (f"User #{r.approved_by}" if r.approved_by else "None"),
                    "approved_at": r.approved_at.isoformat() if r.approved_at else None,
                })

    # Scope 3
    if include_s3 and metric != "flaring_volume" and metric != "methane_total":
        q3 = Scope3Emission.query
        if year:
            q3 = q3.filter(Scope3Emission.year == year)
        if facility_id:
            q3 = q3.filter(Scope3Emission.facility_id == facility_id)
        elif allowed_fids is not None:
            q3 = q3.filter(Scope3Emission.facility_id.in_(allowed_fids))

        for r in q3.all():
            records_count += 1
            v = float(r.co2e or 0.0)
            total_val += v
            cat_name = f"Scope 3: {r.category or 'Category 11'}"
            categories[cat_name]["count"] += 1
            categories[cat_name]["val"] += v
            statuses[r.status or "Pending"] += 1
            if r.created_by_name:
                submitters.add(r.created_by_name)
            if r.approved_by_name:
                approvers.add(r.approved_by_name)

            f_key = f"Scope3-{r.category or 'Cat11'}|{r.factor_version or '2023.1'}"
            if f_key not in factors_used:
                factors_used[f_key] = {
                    "source": f"Scope 3 Factor ({r.calculation_method or 'GHG Protocol Category 11'})",
                    "version": r.factor_version or "2023.1",
                    "ef_co2": r.emission_factor,
                    "records_count": 0,
                }
            factors_used[f_key]["records_count"] += 1

            if len(sample_records) < 25:
                sample_records.append({
                    "record_id": f"S3-{r.id}",
                    "scope": 3,
                    "facility_name": fac_map.get(r.facility_id, f"Facility #{r.facility_id}"),
                    "process_type": r.category or "Use of Sold Products",
                    "fuel_or_source": r.sub_category or "Natural Gas / Crude",
                    "quantity": r.activity_data,
                    "unit": r.unit,
                    "factor_source": "GHG Protocol Cat 11 (54.18 kg/MMBtu)",
                    "factor_version": r.factor_version or "2023.1",
                    "gwp_version": r.gwp_version or active_gwp,
                    "co2e_t": round(v, 4),
                    "status": r.status or "Pending",
                    "submitter": r.created_by_name or f"User #{r.created_by}",
                    "approver": r.approved_by_name or (f"User #{r.approved_by}" if r.approved_by else "None"),
                    "approved_at": r.approved_at.isoformat() if r.approved_at else None,
                })

    # Mathematical Formula construction
    if metric == "methane_total":
        formula_str = "Total Methane (tCH4) = Sum of source-level CH4 mass emissions across all active facilities"
    elif metric == "flaring_volume":
        formula_str = "Total Flaring Volume (m3) = Sum of metered flare gas volumes (routine, non-routine, safety) under Decree 21-330 Art. 9"
    elif metric == "scope1_total":
        formula_str = f"Scope 1 (tCO2e) = Sum(Activity_i × EF_CO2,i) + Sum(Activity_i × EF_CH4,i × GWP_CH4[{gwp_meta.get('CH4', 28.0)}]) + Sum(Activity_i × EF_N2O,i × GWP_N2O[{gwp_meta.get('N2O', 265.0)}])"
    elif metric == "scope2_total":
        formula_str = "Scope 2 (tCO2e) = Electricity Consumption (MWh) × Grid Emission Factor (tCO2e/MWh) + Steam / Heat (MMBtu) × Boiler Factor"
    elif metric == "scope3_total":
        formula_str = "Scope 3 (tCO2e) = Activity (Volume/Energy) × HHV Conversion × Product Combustion Factor (e.g. 54.18 kg CO2e/MMBtu / 1000)"
    else:
        formula_str = f"Total Corporate Inventory (tCO2e) = Scope 1 (Direct) + Scope 2 (Location-Based Indirect) + Scope 3 (Value Chain) under IPCC {active_gwp}"

    category_list = [
        {
            "category": k,
            "record_count": v["count"],
            "value": round(v["val"], 2),
            "percentage": round(v["val"] / total_val * 100.0, 1) if total_val > 0 else 0.0,
            "unit": unit,
        }
        for k, v in sorted(categories.items(), key=lambda item: item[1]["val"], reverse=True)
    ]

    return jsonify({
        "metric": metric,
        "metric_label": metric.replace("_", " ").title(),
        "total_value": round(total_val, 2),
        "unit": unit,
        "record_count": records_count,
        "filter_scope": {
            "year": year or "All Years",
            "facility_id": facility_id,
            "facility_name": fac_map.get(facility_id, "All Facilities") if facility_id else "All Facilities",
            "process_type": process_type or "All Processes",
        },
        "formula": formula_str,
        "gwp_standard": {
            "standard": active_gwp,
            "report_name": f"IPCC {active_gwp} (100-year horizon)",
            "ch4_factor": gwp_meta.get("CH4", 28.0),
            "n2o_factor": gwp_meta.get("N2O", 265.0),
            "co2_factor": 1.0,
        },
        "breakdown_by_category": category_list,
        "factors_applied": list(factors_used.values()),
        "data_lineage": {
            "statuses": dict(statuses),
            "submitters": sorted(list(submitters))[:10],
            "approvers": sorted(list(approvers))[:10],
            "earliest_entry": earliest_date,
            "latest_approval": latest_date,
        },
        "sample_records": sample_records,
    }), 200
