from flask import Blueprint, jsonify, request, Response
from sqlalchemy import func
from extensions import db
from models import Emission, Scope2Emission, Scope3Emission, ActivityLog
from routes.auth import superuser_required
import csv
import io

qaqc_bp = Blueprint("qaqc_bp", __name__)

@qaqc_bp.route("/dashboard", methods=["GET"])
@superuser_required
def get_qaqc_dashboard():
    """
    Returns aggregated uncertainty (Tier 1) and lists of flagged anomalies.
    """
    try:
        # Fetch flagged anomalies
        anomalies_scope1 = Emission.query.filter(Emission.qa_flag.isnot(None)).all()
        anomalies_scope2 = Scope2Emission.query.filter(Scope2Emission.qa_flag.isnot(None)).all()
        anomalies_scope3 = Scope3Emission.query.filter(Scope3Emission.qa_flag.isnot(None)).all()

        flagged_records = []
        for r in anomalies_scope1:
            flagged_records.append({
                "id": r.id,
                "scope": 1,
                "facility_id": r.facility_id,
                "qa_flag": r.qa_flag,
                "status": r.status,
                "co2e": r.co2e_total
            })
        for r in anomalies_scope2:
            flagged_records.append({
                "id": r.id,
                "scope": 2,
                "facility_id": r.facility_id,
                "qa_flag": r.qa_flag,
                "status": r.status,
                "co2e": r.co2e
            })
        for r in anomalies_scope3:
            flagged_records.append({
                "id": r.id,
                "scope": 3,
                "facility_id": r.facility_id,
                "qa_flag": r.qa_flag,
                "status": r.status,
                "co2e": r.co2e
            })

        # Calculate Tier 1 Uncertainty (Error Propagation: sqrt(sum( (unc * emissions)^2 )) / total_emissions )
        
        # Scope 1
        s1_emissions = Emission.query.all()
        s1_total = sum((e.co2e_total or 0) for e in s1_emissions)
        s1_unc_var = sum( (( (e.uncertainty_pct or e.uncertainty or 0.05) * (e.co2e_total or 0) ) ** 2) for e in s1_emissions)

        # Scope 2
        s2_emissions = Scope2Emission.query.all()
        s2_total = sum((e.co2e or 0) for e in s2_emissions)
        s2_unc_var = sum( (( (e.uncertainty_pct or e.uncertainty or 0.05) * (e.co2e or 0) ) ** 2) for e in s2_emissions)

        # Scope 3
        s3_emissions = Scope3Emission.query.all()
        s3_total = sum((e.co2e or 0) for e in s3_emissions)
        s3_unc_var = sum( (( (e.uncertainty_pct or e.uncertainty or 0.10) * (e.co2e or 0) ) ** 2) for e in s3_emissions)

        total_inventory = s1_total + s2_total + s3_total
        total_unc_var = s1_unc_var + s2_unc_var + s3_unc_var
        
        overall_uncertainty = 0
        if total_inventory > 0:
            overall_uncertainty = (total_unc_var ** 0.5) / total_inventory

        return jsonify({
            "status": "success",
            "tier1_uncertainty": {
                "overall": overall_uncertainty,
                "scope1": (s1_unc_var ** 0.5) / s1_total if s1_total > 0 else 0,
                "scope2": (s2_unc_var ** 0.5) / s2_total if s2_total > 0 else 0,
                "scope3": (s3_unc_var ** 0.5) / s3_total if s3_total > 0 else 0,
            },
            "flagged_records": flagged_records
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@qaqc_bp.route("/export", methods=["GET"])
@superuser_required
def export_qaqc_report():
    """
    Exports the QA/QC dashboard data (anomalies) as a CSV file.
    """
    try:
        anomalies_scope1 = Emission.query.filter(Emission.qa_flag.isnot(None)).all()
        anomalies_scope2 = Scope2Emission.query.filter(Scope2Emission.qa_flag.isnot(None)).all()
        anomalies_scope3 = Scope3Emission.query.filter(Scope3Emission.qa_flag.isnot(None)).all()

        si = io.StringIO()
        cw = csv.writer(si)
        
        # Write headers
        cw.writerow(['Record ID', 'Scope', 'Facility ID', 'Issue (QA Flag)', 'Emissions (tCO2e)', 'Status'])

        for r in anomalies_scope1:
            cw.writerow([r.id, 1, r.facility_id, r.qa_flag, r.co2e_total, r.status])
        for r in anomalies_scope2:
            cw.writerow([r.id, 2, r.facility_id, r.qa_flag, r.co2e, r.status])
        for r in anomalies_scope3:
            cw.writerow([r.id, 3, r.facility_id, r.qa_flag, r.co2e, r.status])

        output = si.getvalue()
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=qa_qc_report.csv"}
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
