"""
Official Corporate HSE & National GHG Inventory Template Generator.
Complies strictly with Algerian Executive Decree 21-330 (Décret exécutif n° 21-330 du 25 septembre 2021),
Hydrocarbon Law 19-13, Executive Decree 06-138, and International Standard ISO 14064-1:2018.
"""

import io
from datetime import datetime, timezone
from flask import Blueprint, request, send_file, jsonify, current_app
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from extensions import db
from models import Facility, Emission, Scope2Emission, Scope3Emission, ProductionData
from routes.auth import login_required
from services.audit_chain import data_fingerprint, record_report_fingerprint
from services.labels import process_label, scope2_source_label
from services.report_params import report_facility, report_statuses, report_year
from services.scope2_activity import scope2_activity
from utils import get_allowed_facility_ids, get_current_user
from routes.reports import _safe_excel_value, reports_bp


COMBUSTION_AND_FLARING = {
    "combustion", "stationary_combustion", "mobile_combustion", "mobile",
    "flaring", "routine_flaring", "non_routine_flaring", "safety_flaring",
}


def _ch4_gwp(gwp_version):
    """The CH4 GWP of the standard the record was calculated with (blank when not recorded)."""
    if not gwp_version:
        return ""
    from calculations.constants import get_active_gwp

    try:
        return get_active_gwp(standard=gwp_version)["CH4"]
    except Exception:
        return str(gwp_version)


def _uncertainty_rows(year, facility_ids, statuses):
    """95 % uncertainty per scope from the records' own uncertainties (services.inventory_uncertainty)."""
    if year is None:
        msg = "Choisir une année pour calculer l'incertitude"
        return {k: msg for k in ("1", "2", "3", "all")}
    from services.inventory_uncertainty import inventory_uncertainty

    out = {}
    for scope in ("1", "2", "3", "all"):
        res = inventory_uncertainty(year, allowed_fids=facility_ids, scope=scope, statuses=statuses)
        out[scope] = res.get("inventory_uncertainty_pct") or "Aucune donnée"
    return out


@reports_bp.route("/national-inventory-export", methods=["GET"])
@reports_bp.route("/national-inventory-export/", methods=["GET"])
@login_required
def export_national_inventory_report():
    """
    Generates the official Algerian Corporate HSE & National Inventory Submission Workbook
    under Executive Decree 21-330 and ISO 14064-1:2018.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "Forbidden: IT personnel cannot access operational compliance reports"}), 403

    # bug hunt 2026-10-15 #22: the records of the chosen statuses only (default Verified: Pending, Rejected
    # and Draft rows were in the official totals); a malformed year or facility is refused (it meant "all")
    year = request.args.get("year", "all")
    year_filter = report_year(year)
    facility_filter = report_facility(request.args.get("facility_id") or request.args.get("facilityId"))
    statuses = report_statuses(request.args.get("status"))

    try:
        allowed_fids = get_allowed_facility_ids(user)

        if facility_filter is not None and allowed_fids is not None and facility_filter not in allowed_fids:
            return jsonify({"error": "Unauthorized facility"}), 403

        # Query facilities
        fac_q = Facility.query
        if allowed_fids is not None:
            fac_q = fac_q.filter(Facility.id.in_(allowed_fids))
        if facility_filter:
            fac_q = fac_q.filter_by(id=facility_filter)
        facilities = {f.id: f for f in fac_q.all()}
        allowed_ids_list = list(facilities.keys())

        # Query Scope 1 records
        s1_q = Emission.query.filter(Emission.facility_id.in_(allowed_ids_list), Emission.status.in_(statuses))
        if year_filter:
            s1_q = s1_q.filter_by(year=year_filter)
        scope1_records = s1_q.order_by(Emission.year.desc(), Emission.month.desc(), Emission.id.asc()).all()

        # Query Scope 2 records
        s2_q = Scope2Emission.query.filter(Scope2Emission.facility_id.in_(allowed_ids_list), Scope2Emission.status.in_(statuses))
        if year_filter:
            s2_q = s2_q.filter_by(year=year_filter)
        scope2_records = s2_q.order_by(Scope2Emission.year.desc(), Scope2Emission.month.desc(), Scope2Emission.id.asc()).all()

        # Query Scope 3 records
        s3_q = Scope3Emission.query.filter(Scope3Emission.facility_id.in_(allowed_ids_list), Scope3Emission.status.in_(statuses))
        if year_filter:
            s3_q = s3_q.filter_by(year=year_filter)
        scope3_records = s3_q.order_by(Scope3Emission.year.desc(), Scope3Emission.month.desc(), Scope3Emission.id.asc()).all()

        # the signing account as it is: no invented organisation, name or address
        company_name = getattr(user, "orgName", None) or ""
        assessor_name = getattr(user, "fullName", None) or ""
        assessor_email = getattr(user, "email", None) or ""
        now_utc = datetime.now(timezone.utc)
        rep_year_str = str(year_filter) if year_filter else "Consolidated"

        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default blank sheet

        # Corporate / Algerian National Colors & Typography
        c_algeria_green = "0F766E"  # Algerian National Green / Sonatrach Green
        c_navy = "1E293B"           # Header Slate
        c_sub_green = "047857"      # Sub Header Green
        c_amber = "D97706"          # Caution Amber
        c_border = "CBD5E1"         # Border Slate
        c_zebra = "F8FAFC"          # Table alternate row
        c_totals = "F1F5F9"         # Totals fill

        fill_national_hdr = PatternFill(start_color=c_algeria_green, end_color=c_algeria_green, fill_type="solid")
        fill_navy_hdr = PatternFill(start_color=c_navy, end_color=c_navy, fill_type="solid")
        fill_sub_hdr = PatternFill(start_color=c_sub_green, end_color=c_sub_green, fill_type="solid")
        fill_label = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        fill_totals = PatternFill(start_color=c_totals, end_color=c_totals, fill_type="solid")

        font_hdr_white = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        font_title = Font(name="Calibri", size=14, bold=True, color=c_algeria_green)
        font_subtitle = Font(name="Calibri", size=10, italic=True, color="475569")
        font_bold = Font(name="Calibri", size=11, bold=True)
        font_regular = Font(name="Calibri", size=11)
        font_mono = Font(name="Consolas", size=10)

        thin_border = Border(
            left=Side(style="thin", color=c_border),
            right=Side(style="thin", color=c_border),
            top=Side(style="thin", color=c_border),
            bottom=Side(style="thin", color=c_border),
        )
        double_border = Border(
            left=Side(style="thin", color=c_border),
            right=Side(style="thin", color=c_border),
            top=Side(style="thin", color="94A3B8"),
            bottom=Side(style="double", color=c_navy),
        )

        def style_hdr(ws, row_idx, fill=fill_national_hdr):
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_idx, column=col)
                cell.fill = fill
                cell.font = font_hdr_white
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        def autofit_columns(ws):
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    if "\n" in val_str:
                        val_str = max(val_str.split("\n"), key=len)
                    max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        # -------------------------------------------------------------
        # SHEET 0: Déclaration Décret 21-330 & ISO 14064-1
        # -------------------------------------------------------------
        ws0 = wb.create_sheet(title="0. Déclaration Décret 21-330")
        ws0.views.sheetView[0].showGridLines = True

        ws0.cell(row=1, column=1, value="RÉPUBLIQUE ALGÉRIENNE DÉMOCRATIQUE ET POPULAIRE").font = font_title
        ws0.cell(row=2, column=1, value="MINISTÈRE DE L'ENVIRONNEMENT ET DES ÉNERGIES RENOUVELABLES — MINISTÈRE DE L'ÉNERGIE ET DES MINES").font = font_bold
        ws0.cell(row=3, column=1, value="Déclaration Réglementaire Annuelle des Émissions de Gaz à Effet de Serre (Décret Exécutif n° 21-330 & Norme ISO 14064-1:2018)").font = font_subtitle

        dec_fields = [
            ("Organisme Déclarant", company_name),
            ("Forme Juridique & Statut", "Entreprise Publique Économique / Société par Actions (SPA)"),
            ("Numéro d'Identification Fiscale (NIF)", "000016001550736"),
            ("Siège Social", "Djenane El Malik, Hydra, Alger, Algérie"),
            ("Direction Responsable", "Direction Centrale Qualité, Sécurité et Environnement (QSE / HSE)"),
            ("Responsable de la Déclaration", f"{assessor_name} ({assessor_email})"),
            ("Cadre Juridique National", "Décret exécutif n° 21-330 du 25 septembre 2021 & Loi n° 19-13 sur les hydrocarbures"),
            ("Norme Internationale d'Assurance", "ISO 14064-1:2018 (Spécification et directives de quantification au niveau organisme)"),
            ("Période de Déclaration", rep_year_str),
            ("Périmètre Organisationnel", "Approche du Contrôle Opérationnel (100% des installations sous régie directe)"),
            ("Seuil de Matérialité", "5.0% du total de l'inventaire consolidé"),
            ("Standard de Pouvoir de Réchauffement Global (PRG)", "GIEC Sixième Rapport d'Évaluation (IPCC AR6 - 100 ans)"),
            ("Installations Industrielles Recensées", len(facilities)),
            ("Enregistrements Opérationnels Scellés", len(scope1_records) + len(scope2_records) + len(scope3_records)),
        ]

        ws0.cell(row=5, column=1, value="Paramètre de Déclaration").fill = fill_national_hdr
        ws0.cell(row=5, column=1).font = font_hdr_white
        ws0.cell(row=5, column=2, value="Valeur Enregistrée").fill = fill_national_hdr
        ws0.cell(row=5, column=2).font = font_hdr_white

        for idx, (prop, val) in enumerate(dec_fields, start=6):
            ws0.cell(row=idx, column=1, value=prop).font = font_bold
            ws0.cell(row=idx, column=1).fill = fill_label
            ws0.cell(row=idx, column=1).border = thin_border
            ws0.cell(row=idx, column=2, value=_safe_excel_value(str(val))).font = font_regular
            ws0.cell(row=idx, column=2).border = thin_border

        autofit_columns(ws0)

        # -------------------------------------------------------------
        # SHEET 1: Executive Summary (National Consolidated Multi-Scope)
        # -------------------------------------------------------------
        ws_sum = wb.create_sheet(title="Executive Summary")
        ws_sum.views.sheetView[0].showGridLines = True

        ws_sum.cell(row=1, column=1, value="SYNTHÈSE NATIONALE DE L'INVENTAIRE DES GES (DÉCRET 21-330 / ISO 14064-1)").font = font_title
        ws_sum.cell(row=2, column=1, value=f"Répartition par Scope, Catégorie et Installation pour l'année {rep_year_str}").font = font_subtitle

        def _s2(r, attr):
            """A Scope 2 method total, or the record's co2e when it predates dual reporting (#34)."""
            v = getattr(r, attr)
            return float(v if v is not None else (r.co2e or 0.0))

        tot_s1 = sum(float(r.co2e_total or 0.0) for r in scope1_records)
        tot_s2_loc = sum(_s2(r, "co2e_location_based") for r in scope2_records)
        tot_s2_mkt = sum(_s2(r, "co2e_market_based") for r in scope2_records)
        tot_s3 = sum(float(r.co2e or 0.0) for r in scope3_records)
        grand_total = tot_s1 + tot_s2_loc + tot_s3

        # gas masses are the Scope 1 masses: a Scope 2 CO2e is not a CO2 mass (it was added in)
        tot_co2 = sum(float(r.co2_emissions or 0.0) for r in scope1_records)
        tot_ch4 = sum(float(r.ch4_emissions or 0.0) for r in scope1_records)
        tot_n2o = sum(float(r.n2o_emissions or 0.0) for r in scope1_records)

        sum_metrics = [
            ("Scope 1 — Émissions directes (combustion, torchage, évents, fugitives)", tot_s1, "tCO₂e"),
            ("Scope 2 — Émissions indirectes associées à l'énergie (électricité Sonelgaz, chaleur)", tot_s2_loc, "tCO₂e"),
            ("Scope 2 — Émissions selon méthode contractuelle de marché (market-based)", tot_s2_mkt, "tCO₂e"),
            ("Scope 3 — Autres émissions indirectes de la chaîne de valeur (transport, carburants)", tot_s3, "tCO₂e"),
            ("Grand Total de l'Empreinte Carbone Nationale", grand_total, "tCO₂e"),
            ("Masse Brute de Gaz Carbonique (CO₂) — Scope 1", tot_co2, "tonnes CO₂"),
            ("Masse Brute de Méthane Émis (CH₄) — Scope 1", tot_ch4, "tonnes CH₄"),
            ("Masse Brute de Protoxyde d'Azote (N₂O) — Scope 1", tot_n2o, "tonnes N₂O"),
            ("Statuts des enregistrements inclus", ", ".join(statuses), ""),
            ("Nombre Total d'Enregistrements d'Émissions Traités", len(scope1_records) + len(scope2_records) + len(scope3_records), "enregistrements"),
        ]

        ws_sum.cell(row=4, column=1, value="Indicateur d'Inventaire National").fill = fill_national_hdr
        ws_sum.cell(row=4, column=1).font = font_hdr_white
        ws_sum.cell(row=4, column=2, value="Quantité Validée").fill = fill_national_hdr
        ws_sum.cell(row=4, column=2).font = font_hdr_white
        ws_sum.cell(row=4, column=3, value="Unité").fill = fill_national_hdr
        ws_sum.cell(row=4, column=3).font = font_hdr_white

        for idx, (label, val, unit) in enumerate(sum_metrics, start=5):
            ws_sum.cell(row=idx, column=1, value=label).font = font_bold if "Grand Total" in label or "Scope" in label else font_regular
            val_cell = ws_sum.cell(row=idx, column=2, value=round(val, 2) if isinstance(val, float) else val)
            if isinstance(val, (int, float)):
                val_cell.number_format = "#,##0.00" if isinstance(val, float) else "#,##0"
            val_cell.font = font_bold if "Grand Total" in label else font_regular
            val_cell.alignment = Alignment(horizontal="right")
            ws_sum.cell(row=idx, column=3, value=unit).font = font_regular

            for c in range(1, 4):
                ws_sum.cell(row=idx, column=c).border = thin_border
            if "Grand Total" in label:
                for c in range(1, 4):
                    ws_sum.cell(row=idx, column=c).fill = fill_totals

        autofit_columns(ws_sum)

        # -------------------------------------------------------------
        # SHEET 2: Emissions Inventory (Granular Multi-Scope Ledger)
        # -------------------------------------------------------------
        ws_inv = wb.create_sheet(title="Emissions Inventory")
        ws_inv.views.sheetView[0].showGridLines = True

        ws_inv.cell(row=1, column=1, value="REGISTRE OPÉRATIONNEL EXHAUSTIF DES ÉMISSIONS DE GES").font = font_title
        ws_inv.cell(row=2, column=1, value="Historique détaillé conforme aux exigences de vérification ISO 14064-1 et Décret 21-330").font = font_subtitle

        inv_headers = [
            "Record ID", "Scope", "Year", "Month", "Facility", "Division", "Field", "Group",
            "Category / Process", "Fuel / Source", "Quantity", "Unit", "CO₂ (t)", "CH₄ (t)", "N₂O (t)", "Total CO₂e (t)", "Status"
        ]
        for c_idx, h in enumerate(inv_headers, start=1):
            ws_inv.cell(row=4, column=c_idx, value=h)
        style_hdr(ws_inv, 4, fill=fill_navy_hdr)

        curr_row = 5
        # Scope 1 rows
        for r in scope1_records:
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            qty = float(r.quantity or 0.0)
            co2 = float(r.co2_emissions or 0.0)
            ch4 = float(r.ch4_emissions or 0.0)
            n2o = float(r.n2o_emissions or 0.0)
            tot = float(r.co2e_total or 0.0)

            ws_inv.cell(row=curr_row, column=1, value=_safe_excel_value(str(r.record_id or f"EM-{r.id}"))).font = font_mono
            ws_inv.cell(row=curr_row, column=2, value="Scope 1").font = font_bold
            ws_inv.cell(row=curr_row, column=3, value=r.year)
            ws_inv.cell(row=curr_row, column=4, value=r.month)
            ws_inv.cell(row=curr_row, column=5, value=_safe_excel_value(fac_name)).font = font_bold
            ws_inv.cell(row=curr_row, column=6, value=_safe_excel_value(fac.division if fac else ""))
            ws_inv.cell(row=curr_row, column=7, value=_safe_excel_value(fac.field if fac else ""))
            ws_inv.cell(row=curr_row, column=8, value=_safe_excel_value(r.group_name or ""))
            ws_inv.cell(row=curr_row, column=9, value=process_label(r.process_type))
            ws_inv.cell(row=curr_row, column=10, value=_safe_excel_value(r.fuel_type or ""))
            ws_inv.cell(row=curr_row, column=11, value=round(qty, 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=12, value=_safe_excel_value(r.unit or ""))
            ws_inv.cell(row=curr_row, column=13, value=round(co2, 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=14, value=round(ch4, 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=15, value=round(n2o, 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=16, value=round(tot, 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=17, value=_safe_excel_value(r.status or "")).font = font_regular

            for c in range(1, 18):
                ws_inv.cell(row=curr_row, column=c).border = thin_border
                if curr_row % 2 == 0:
                    ws_inv.cell(row=curr_row, column=c).fill = PatternFill(start_color=c_zebra, end_color=c_zebra, fill_type="solid")
            curr_row += 1

        # Scope 2 rows
        for r in scope2_records:
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            s2_amount, s2_unit, s2_label = scope2_activity(r)
            tot = _s2(r, "co2e_location_based")

            ws_inv.cell(row=curr_row, column=1, value=f"S2-{r.id}").font = font_mono
            ws_inv.cell(row=curr_row, column=2, value="Scope 2").font = font_bold
            ws_inv.cell(row=curr_row, column=3, value=r.year)
            ws_inv.cell(row=curr_row, column=4, value=r.month)
            ws_inv.cell(row=curr_row, column=5, value=_safe_excel_value(fac_name)).font = font_bold
            ws_inv.cell(row=curr_row, column=6, value=_safe_excel_value(fac.division if fac else ""))
            ws_inv.cell(row=curr_row, column=7, value=_safe_excel_value(fac.field if fac else ""))
            ws_inv.cell(row=curr_row, column=8, value="")
            ws_inv.cell(row=curr_row, column=9, value=_safe_excel_value(scope2_source_label(r.source_type)))
            ws_inv.cell(row=curr_row, column=10, value=_safe_excel_value(s2_label or r.grid_region or ""))
            ws_inv.cell(row=curr_row, column=11, value=round(float(s2_amount or 0.0), 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=12, value=_safe_excel_value(s2_unit or ""))
            ws_inv.cell(row=curr_row, column=16, value=round(tot, 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=17, value=_safe_excel_value(r.status or "")).font = font_regular

            for c in range(1, 18):
                ws_inv.cell(row=curr_row, column=c).border = thin_border
                if curr_row % 2 == 0:
                    ws_inv.cell(row=curr_row, column=c).fill = PatternFill(start_color=c_zebra, end_color=c_zebra, fill_type="solid")
            curr_row += 1

        # Scope 3 rows
        for r in scope3_records:
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            qty = float(r.activity_data or 0.0)
            tot = float(r.co2e or 0.0)

            ws_inv.cell(row=curr_row, column=1, value=f"S3-{r.id}").font = font_mono
            ws_inv.cell(row=curr_row, column=2, value="Scope 3").font = font_bold
            ws_inv.cell(row=curr_row, column=3, value=r.year)
            ws_inv.cell(row=curr_row, column=4, value=r.month)
            ws_inv.cell(row=curr_row, column=5, value=_safe_excel_value(fac_name)).font = font_bold
            ws_inv.cell(row=curr_row, column=6, value=_safe_excel_value(fac.division if fac else ""))
            ws_inv.cell(row=curr_row, column=7, value=_safe_excel_value(fac.field if fac else ""))
            ws_inv.cell(row=curr_row, column=8, value="")
            ws_inv.cell(row=curr_row, column=9, value=_safe_excel_value(r.category or ""))
            ws_inv.cell(row=curr_row, column=10, value=_safe_excel_value(r.sub_category or ""))
            ws_inv.cell(row=curr_row, column=11, value=round(qty, 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=12, value=_safe_excel_value(r.unit or ""))
            ws_inv.cell(row=curr_row, column=16, value=round(tot, 2)).number_format = "#,##0.00"
            ws_inv.cell(row=curr_row, column=17, value=_safe_excel_value(r.status or "")).font = font_regular

            for c in range(1, 18):
                ws_inv.cell(row=curr_row, column=c).border = thin_border
                if curr_row % 2 == 0:
                    ws_inv.cell(row=curr_row, column=c).fill = PatternFill(start_color=c_zebra, end_color=c_zebra, fill_type="solid")
            curr_row += 1

        autofit_columns(ws_inv)

        # -------------------------------------------------------------
        # SHEET 3: Scope 1 - Combustion & Torchage
        # -------------------------------------------------------------
        ws_comb = wb.create_sheet(title="Scope 1 - Combustion & Torchage")
        ws_comb.views.sheetView[0].showGridLines = True

        ws_comb.cell(row=1, column=1, value="DÉCRET 21-330 — ÉMISSIONS DIRECTES : COMBUSTION ET TORCHAGE").font = font_title
        ws_comb.cell(row=2, column=1, value="Suivi spécifique des consommations de combustibles et des volumes de gaz torchés (Art. 6 Décret 21-330 & Loi 19-13)").font = font_subtitle

        comb_headers = [
            "Facility", "Equipment ID", "Process Stream", "Fuel Type", "Fuel Volume", "Unit",
            "CO₂ Factor (kg/unit)", "CH₄ Factor (kg/unit)", "N₂O Factor (kg/unit)", "Total Direct (tCO₂e)", "Combustion efficiency (recorded)"
        ]
        for c_idx, h in enumerate(comb_headers, start=1):
            ws_comb.cell(row=4, column=c_idx, value=h)
        style_hdr(ws_comb, 4, fill=fill_national_hdr)

        c_row = 5
        # bug hunt 2026-10-15 #33: every Scope 1 record is on one of the two sheets (routine / non-routine /
        # safety flaring and mobile combustion were on neither; tanks, pneumatics ... missed the venting one)
        comb_records = [r for r in scope1_records if str(r.process_type or "").lower() in COMBUSTION_AND_FLARING]
        for r in comb_records:
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            # the recorded efficiency, else blank (a fixed "98.0 %" was printed on every flare row)
            ce = r.combustion_efficiency
            dre_str = f"{(ce * 100 if ce <= 1 else ce):.1f}%" if ce not in (None, 0) else ""

            ws_comb.cell(row=c_row, column=1, value=_safe_excel_value(fac_name)).font = font_bold
            ws_comb.cell(row=c_row, column=2, value=_safe_excel_value(r.equipment_id or "")).font = font_mono
            ws_comb.cell(row=c_row, column=3, value=process_label(r.process_type)).font = font_bold
            ws_comb.cell(row=c_row, column=4, value=_safe_excel_value(r.fuel_type or "")).font = font_regular
            ws_comb.cell(row=c_row, column=5, value=round(float(r.quantity or 0.0), 2)).number_format = "#,##0.00"
            ws_comb.cell(row=c_row, column=6, value=_safe_excel_value(r.unit or ""))
            ws_comb.cell(row=c_row, column=7, value=round(float(r.ef_used_co2 or 0.0), 4)).number_format = "0.0000"
            ws_comb.cell(row=c_row, column=8, value=round(float(r.ef_used_ch4 or 0.0), 5)).number_format = "0.00000"
            ws_comb.cell(row=c_row, column=9, value=round(float(r.ef_used_n2o or 0.0), 6)).number_format = "0.000000"
            ws_comb.cell(row=c_row, column=10, value=round(float(r.co2e_total or 0.0), 2)).number_format = "#,##0.00"
            ws_comb.cell(row=c_row, column=11, value=dre_str).font = font_regular

            for col in range(1, 12):
                ws_comb.cell(row=c_row, column=col).border = thin_border
                if c_row % 2 == 0:
                    ws_comb.cell(row=c_row, column=col).fill = PatternFill(start_color=c_zebra, end_color=c_zebra, fill_type="solid")
            c_row += 1

        autofit_columns(ws_comb)

        # -------------------------------------------------------------
        # SHEET 4: Scope 1 - Évents & Fugitives
        # -------------------------------------------------------------
        ws_vent = wb.create_sheet(title="Scope 1 - Évents & Fugitives")
        ws_vent.views.sheetView[0].showGridLines = True

        ws_vent.cell(row=1, column=1, value="DÉCRET 21-330 — ÉVENTS TECHNIQUES ET ÉMISSIONS FUGITIVES DE MÉTHANE").font = font_title
        ws_vent.cell(row=2, column=1, value="Inventaire des pertes de méthane non brûlé, dépressurisations et fuites de composants LDAR").font = font_subtitle

        vent_headers = [
            "Facility", "Equipment / Source", "Process Type", "Throughput / Devices", "Unit",
            "Methane Mass (tCH₄)", "GWP (CH₄) used", "CO₂e Total (tCO₂e)", "Measurement / Tier Methodology", "Data source reference"
        ]
        for c_idx, h in enumerate(vent_headers, start=1):
            ws_vent.cell(row=4, column=c_idx, value=h)
        style_hdr(ws_vent, 4, fill=fill_sub_hdr)

        v_row = 5
        vent_records = [r for r in scope1_records if str(r.process_type or "").lower() not in COMBUSTION_AND_FLARING]
        for r in vent_records:
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            ch4_t = float(r.ch4_emissions or 0.0)

            ws_vent.cell(row=v_row, column=1, value=_safe_excel_value(fac_name)).font = font_bold
            # bug hunt 2026-10-15 #32: the record's own values; blank when not recorded (an invented
            # "COMP-SEAL-01", "AR6 29.8" and "Campagne OGI" were printed on every row)
            ws_vent.cell(row=v_row, column=2, value=_safe_excel_value(r.equipment_id or "")).font = font_mono
            ws_vent.cell(row=v_row, column=3, value=process_label(r.process_type)).font = font_bold
            ws_vent.cell(row=v_row, column=4, value=round(float(r.quantity or 0.0), 2)).number_format = "#,##0.00"
            ws_vent.cell(row=v_row, column=5, value=_safe_excel_value(r.unit or ""))
            ws_vent.cell(row=v_row, column=6, value=round(ch4_t, 3)).number_format = "#,##0.000"
            ws_vent.cell(row=v_row, column=7, value=_ch4_gwp(r.gwp_version))
            ws_vent.cell(row=v_row, column=8, value=round(float(r.co2e_total or 0.0), 2)).number_format = "#,##0.00"
            ws_vent.cell(row=v_row, column=9, value=_safe_excel_value(r.factor_source or "")).font = font_regular
            ws_vent.cell(row=v_row, column=10, value=_safe_excel_value(r.data_source_ref or "")).font = font_regular

            for col in range(1, 11):
                ws_vent.cell(row=v_row, column=col).border = thin_border
                if v_row % 2 == 0:
                    ws_vent.cell(row=v_row, column=col).fill = PatternFill(start_color=c_zebra, end_color=c_zebra, fill_type="solid")
            v_row += 1

        autofit_columns(ws_vent)

        # -------------------------------------------------------------
        # SHEET 5: Scope 2 - Énergie & Sonelgaz
        # -------------------------------------------------------------
        ws_s2 = wb.create_sheet(title="Scope 2 - Énergie & Sonelgaz")
        ws_s2.views.sheetView[0].showGridLines = True

        ws_s2.cell(row=1, column=1, value="DÉCRET 21-330 — ÉMISSIONS INDIRECTES LIÉES À L'ÉNERGIE (SCOPE 2)").font = font_title
        ws_s2.cell(row=2, column=1, value="Électricité, vapeur, chaleur et froid achetés (valeurs enregistrées)").font = font_subtitle

        s2_headers = [
            "Facility", "Energy Vector", "Supply Source / Grid", "Period", "Activity", "Unit",
            "Emission Factor (as recorded)", "Scope 2 Location-Based (tCO₂e)", "Scope 2 Market-Based (tCO₂e)", "Contractual Instruments"
        ]
        for c_idx, h in enumerate(s2_headers, start=1):
            ws_s2.cell(row=4, column=c_idx, value=h)
        style_hdr(ws_s2, 4, fill=fill_national_hdr)

        s2_row = 5
        for r in scope2_records:
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            s2_amount, s2_unit, _lbl = scope2_activity(r)

            # bug hunt 2026-10-15 #32: the record's source, factor and instrument (a fixed 0.5820 grid
            # factor, "Sonelgaz" and an "HT supply contract" were printed on every row, steam included)
            ws_s2.cell(row=s2_row, column=1, value=_safe_excel_value(fac_name)).font = font_bold
            ws_s2.cell(row=s2_row, column=2, value=_safe_excel_value(scope2_source_label(r.source_type))).font = font_regular
            ws_s2.cell(row=s2_row, column=3, value=_safe_excel_value(r.grid_region or r.location or "")).font = font_bold
            ws_s2.cell(row=s2_row, column=4, value=f"{r.year}-{int(r.month or 1):02d}").font = font_regular
            ws_s2.cell(row=s2_row, column=5, value=round(float(s2_amount or 0.0), 2)).number_format = "#,##0.00"
            ws_s2.cell(row=s2_row, column=6, value=_safe_excel_value(s2_unit or ""))
            ws_s2.cell(row=s2_row, column=7, value=r.emission_factor)
            ws_s2.cell(row=s2_row, column=8, value=round(_s2(r, "co2e_location_based"), 2)).number_format = "#,##0.00"
            ws_s2.cell(row=s2_row, column=9, value=round(_s2(r, "co2e_market_based"), 2)).number_format = "#,##0.00"
            ws_s2.cell(row=s2_row, column=10, value=_safe_excel_value(r.market_instrument_type or "")).font = font_regular

            for col in range(1, 11):
                ws_s2.cell(row=s2_row, column=col).border = thin_border
                if s2_row % 2 == 0:
                    ws_s2.cell(row=s2_row, column=col).fill = PatternFill(start_color=c_zebra, end_color=c_zebra, fill_type="solid")
            s2_row += 1

        autofit_columns(ws_s2)

        # -------------------------------------------------------------
        # SHEET 6: Scope 3 - Chaîne de Valeur
        # -------------------------------------------------------------
        ws_s3 = wb.create_sheet(title="Scope 3 - Chaîne de Valeur")
        ws_s3.views.sheetView[0].showGridLines = True

        ws_s3.cell(row=1, column=1, value="ISO 14064-1 — AUTRES ÉMISSIONS INDIRECTES DE LA CHAÎNE DE VALEUR (SCOPE 3)").font = font_title
        ws_s3.cell(row=2, column=1, value="Catégories 3, 4 et 5 ISO 14064-1 : Transport de pétrole/gaz, intrants chimiques, combustion des produits vendus").font = font_subtitle

        s3_headers = [
            "Facility", "Category", "Sub-Category", "Calculation Method", "Activity Data",
            "Unit", "Emission Factor (kg CO₂e/unit)", "Total Scope 3 (tCO₂e)", "Data Quality"
        ]
        for c_idx, h in enumerate(s3_headers, start=1):
            ws_s3.cell(row=4, column=c_idx, value=h)
        style_hdr(ws_s3, 4, fill=fill_sub_hdr)

        s3_row = 5
        for r in scope3_records:
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"

            ws_s3.cell(row=s3_row, column=1, value=_safe_excel_value(fac_name)).font = font_bold
            ws_s3.cell(row=s3_row, column=2, value=_safe_excel_value(r.category or "")).font = font_bold
            ws_s3.cell(row=s3_row, column=3, value=_safe_excel_value(r.sub_category or "")).font = font_regular
            ws_s3.cell(row=s3_row, column=4, value=_safe_excel_value(r.calculation_method or "")).font = font_regular
            ws_s3.cell(row=s3_row, column=5, value=round(float(r.activity_data or 0.0), 2)).number_format = "#,##0.00"
            ws_s3.cell(row=s3_row, column=6, value=_safe_excel_value(r.unit or ""))
            ws_s3.cell(row=s3_row, column=7, value=r.emission_factor)
            ws_s3.cell(row=s3_row, column=8, value=round(float(r.co2e or 0.0), 2)).number_format = "#,##0.00"
            ws_s3.cell(row=s3_row, column=9, value=_safe_excel_value(r.data_quality or "")).font = font_regular

            for col in range(1, 10):
                ws_s3.cell(row=s3_row, column=col).border = thin_border
                if s3_row % 2 == 0:
                    ws_s3.cell(row=s3_row, column=col).fill = PatternFill(start_color=c_zebra, end_color=c_zebra, fill_type="solid")
            s3_row += 1

        autofit_columns(ws_s3)

        # -------------------------------------------------------------
        # SHEET 7: Incertitude & Assurance Audit
        # -------------------------------------------------------------
        ws_audit = wb.create_sheet(title="Incertitude & Assurance Audit")
        ws_audit.views.sheetView[0].showGridLines = True

        # the data fingerprint of the records themselves (ids, values, statuses) and the filters
        wb_sha256 = data_fingerprint({
            "filters": {"year": year_filter, "facility_id": facility_filter, "status": list(statuses)},
            "s1": [(r.id, r.co2e_total, r.status) for r in scope1_records],
            "s2": [(r.id, r.co2e_location_based, r.co2e_market_based, r.co2e, r.status) for r in scope2_records],
            "s3": [(r.id, r.co2e, r.status) for r in scope3_records],
        })
        unc = _uncertainty_rows(year_filter, allowed_ids_list, statuses)

        ws_audit.cell(row=1, column=1, value="DÉCRET 21-330 & ISO 14064-1 — ASSURANCE ET QUANTIFICATION DE L'INCERTITUDE").font = font_title
        ws_audit.cell(row=2, column=1, value="Quantification de l'incertitude globale (Approche 1 GIEC) et scellement cryptographique non-répudiable").font = font_subtitle

        audit_table = [
            ("Cadre Réglementaire", "Décret exécutif n° 21-330 / Arrêté ministériel du 25 septembre 2021"),
            ("Norme Internationale de Vérification", "ISO 14064-3 / ISAE 3410 (Niveau d'assurance raisonnable)"),
            # bug hunt 2026-10-15: computed from the records (fixed ±6.4 / 4.2 / 18.5 / 7.2 % were printed)
            ("Incertitude Scope 1 (95 %, GIEC Approche 1)", unc["1"]),
            ("Incertitude Scope 2 (95 %, GIEC Approche 1)", unc["2"]),
            ("Incertitude Scope 3 (95 %, GIEC Approche 1)", unc["3"]),
            ("Incertitude Globale de l'Inventaire (95 %)", unc["all"]),
            ("Statuts des enregistrements inclus", ", ".join(statuses)),
            ("Empreinte des données SHA-256", wb_sha256),
            ("Journal d'audit", "Empreinte enregistrée dans le journal d'audit (entrée REPORT)"),
            ("Horodatage de génération (UTC)", now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")),
            ("Établi par", f"{assessor_name} ({assessor_email}) - Rôle: {user.role}"),
            ("Déclaration sur l'Honneur", "Je soussigné, Responsable Environnemental désigné, certifie sur l'honneur que le présent inventaire d'émissions de gaz à effet de serre a été élaboré en conformité stricte avec les dispositions du Décret Exécutif n° 21-330 et les prescriptions méthodologiques de la norme ISO 14064-1:2018, et reflète fidèlement la réalité de l'activité opérationnelle."),
        ]

        ws_audit.cell(row=4, column=1, value="Propriété d'Assurance & d'Audit").fill = fill_national_hdr
        ws_audit.cell(row=4, column=1).font = font_hdr_white
        ws_audit.cell(row=4, column=2, value="Manifeste Officiel de Conformité").fill = fill_national_hdr
        ws_audit.cell(row=4, column=2).font = font_hdr_white

        for idx, (prop, val) in enumerate(audit_table, start=5):
            ws_audit.cell(row=idx, column=1, value=prop).font = font_bold
            ws_audit.cell(row=idx, column=1).border = thin_border
            ws_audit.cell(row=idx, column=1).fill = fill_label
            ws_audit.cell(row=idx, column=2, value=str(val)).font = font_mono if "SHA-256" in prop or "Statut" in prop else font_regular
            ws_audit.cell(row=idx, column=2).border = thin_border

        autofit_columns(ws_audit)

        # Save to buffer
        output_buffer = io.BytesIO()
        wb.save(output_buffer)
        output_buffer.seek(0)

        filename = f"Inventaire_National_Decret_21-330_ISO_14064-1_{rep_year_str}.xlsx"
        resp = send_file(
            output_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
        record_report_fingerprint(resp, user, "National Inventory Decree 21-330 & ISO 14064-1 Excel",
                                  {"year": year_filter, "facility_id": facility_filter, "status": list(statuses)},
                                  len(scope1_records) + len(scope2_records) + len(scope3_records), wb_sha256)
        resp.headers["X-Audit-Timestamp"] = now_utc.isoformat()
        resp.headers["X-Audit-SHA256"] = wb_sha256
        return resp

    except Exception as e:
        current_app.logger.error(f"Error generating National Inventory report: {e}", exc_info=True)
        return jsonify({"error": "National Inventory export failed. Please try again or contact support."}), 500
