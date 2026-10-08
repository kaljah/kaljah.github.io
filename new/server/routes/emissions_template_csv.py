"""Scope 1 import template downloads (CSV), built from services.scope1_template.

Registered on the same ``emissions_bp`` blueprint, so URLs and endpoint names are the same.
"""
from flask import Response, request

from . import emissions_bp
from utils import get_allowed_facility_ids, get_current_user


def _template_args():
    """(tier, processes, optional columns, facility names the user can upload to) of a template request."""
    from services.scope1_template import normalize_tier, wanted_processes

    tier = normalize_tier(request.args.get("tier", "auto"))
    processes = wanted_processes(request.args.get("process", "all"))
    optional = str(request.args.get("optional", "")).lower() in ("1", "true", "yes")
    facilities = []
    user = get_current_user()
    if user:
        from models import Facility

        allowed = get_allowed_facility_ids(user)
        q = Facility.query if allowed is None else Facility.query.filter(Facility.id.in_(allowed))
        facilities = sorted({f.name for f in q.all() if f.name})
    return tier, processes, optional, facilities


@emissions_bp.route("/template/csv", methods=["GET"])
def get_csv_template():
    """Scope 1 CSV template built from services.scope1_template: column names are the import names,
    one short help row, example rows dated EXAMPLE (skipped on import). Only the columns of the chosen
    tier and processes are included (?tier=1|2|3|auto&process=a,b&optional=1)."""
    from services.scope1_template import build_csv, template_filename

    tier, processes, optional, facilities = _template_args()
    body = build_csv(tier, processes, optional, facilities[0] if facilities else "Your Facility")
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={template_filename(tier, processes, 'csv')}"},
    )
