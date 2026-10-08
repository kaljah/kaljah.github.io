"""Scope 1 import template downloads (Excel), built from services.scope1_template.

Registered on the same ``emissions_bp`` blueprint, so URLs and endpoint names are the same.
"""
from flask import send_file

from . import emissions_bp
from .emissions_template_csv import _template_args


@emissions_bp.route("/template/excel", methods=["GET"])
def get_excel_template():
    """Scope 1 Excel template from the same column spec: Data Entry with dropdowns (the fuel and unit
    lists follow the row's process), Examples, Reference and a hidden Lists sheet."""
    from services.scope1_template import build_xlsx, template_filename

    tier, processes, optional, facilities = _template_args()
    return send_file(
        build_xlsx(tier, processes, optional, facilities),
        as_attachment=True,
        download_name=template_filename(tier, processes, "xlsx"),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
