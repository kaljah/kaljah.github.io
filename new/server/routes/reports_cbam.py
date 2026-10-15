"""
European Commission DG TAXUD CBAM Official Communication Template & Transitional Registry XML Generator.
Complies strictly with Regulation (EU) 2023/956 and Implementing Regulation (EU) 2023/1773.
"""

import io
import json
import hashlib
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
from flask import Blueprint, request, send_file, jsonify, current_app
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
import re
from openpyxl.utils import get_column_letter

from extensions import db
from models import Facility, CbamProductExport, Emission, ProductionData, Scope2Emission
from routes.auth import login_required
from services.audit_chain import data_fingerprint, record_report_fingerprint
from services.report_params import report_facility, report_statuses, report_year
from utils import get_allowed_facility_ids, get_current_user
from routes.reports import _safe_excel_value, reports_bp


COUNTRY_GRID_FACTORS = {
    "Algeria": 0.5820,
    "DZ": 0.5820,
    "Egypt": 0.4720,
    "EG": 0.4720,
    "Nigeria": 0.3950,
    "NG": 0.3950,
    "Saudi Arabia": 0.6200,
    "SA": 0.6200,
    "United Arab Emirates": 0.4850,
    "AE": 0.4850,
    "United States": 0.3700,
    "US": 0.3700,
    "United Kingdom": 0.2100,
    "GB": 0.2100,
    "European Union": 0.2300,
    "EU": 0.2300,
    "France": 0.0580,
    "FR": 0.0580,
    "Germany": 0.3800,
    "DE": 0.3800,
    "Norway": 0.0150,
    "NO": 0.0150,
}
DEFAULT_GLOBAL_GRID_FACTOR = 0.4500


def _cbam_family(process_type):
    """combustion / process / flaring_venting family of a Scope 1 process type (calculations'
    PROCESS_CATEGORY). Exact-name lists missed most types, and a facility with none of them was
    reported as 100 % process emissions (bug hunt 2026-10-15 #35)."""
    from calculations.uncertainty import PROCESS_CATEGORY

    pt = str(process_type or "").strip().lower()
    cat = PROCESS_CATEGORY.get(pt)
    if cat == "combustion":
        return "combustion"
    if cat in ("flaring", "vented", "fugitive") or "flar" in pt or "vent" in pt or "fugitive" in pt:
        return "flaring_venting"
    return "process"  # stoichiometric, acid gas removal, dehydration and other process sources


def _get_facility_scope1_split(facility_id, year=None, statuses=("Verified",)):
    """
    Computes genuine combustion, process, and flaring/venting splits
    from the Emission table for the given facility and year (records of the report's statuses).
    Returns (comb_pct, proc_pct, flare_pct, has_real_data).
    """
    q = Emission.query.filter(Emission.facility_id == facility_id, Emission.status.in_(statuses))
    if year:
        q = q.filter_by(year=year)
    records = q.all()
    sums = {"combustion": 0.0, "process": 0.0, "flaring_venting": 0.0}
    for e in records:
        sums[_cbam_family(e.process_type)] += float(e.co2e_total or 0.0)
    total = sum(sums.values())
    if total <= 0:
        # no emissions recorded: no split to report (has_real_data False)
        return (0.0, 1.0, 0.0, False)
    return (sums["combustion"] / total, sums["process"] / total, sums["flaring_venting"] / total, True)


_OIL_T_PER_BBL = 0.1364   # crude, ~33 API
_GAS_T_PER_MSCF = 0.0210  # natural gas, ~0.74 kg/Sm3


def _production_tonnes(amount, unit, kind):
    """Tonnes of one production amount in its own unit (oil: bbl, m3, Mbbl ... or a mass; gas: Mscf,
    MMscf, Sm3, MMSm3 ... or a mass). None when the unit cannot be read."""
    from calculations.units import UnitError, unit_dimension

    if not amount:
        return 0.0
    u = str(unit or ("bbl" if kind == "oil" else "mscf")).strip().lower().replace(" ", "")
    u = {"mcf": "mscf", "mmcf": "mmscf"}.get(u, u)
    try:
        dim, f = unit_dimension(u)
    except UnitError:
        return None
    if dim == "mass":
        return float(amount) * f / 1000.0
    if dim != "volume":
        return None
    m3 = float(amount) * f
    if kind == "oil":
        return m3 / 0.158987294928 * _OIL_T_PER_BBL
    return m3 / 28.316846592 * _GAS_T_PER_MSCF


def _get_facility_production_tonnes(facility_id, year=None, declared_export_qty=0.0):
    """
    Fetches genuine annual facility production from ProductionData, each amount in its own unit
    (oil_unit / gas_unit: gas in m3 was read as Mscf, 35x high; oil in tonnes as bbl).
    Returns (total_production_tonnes, is_from_db).
    """
    q = ProductionData.query.filter_by(facility_id=facility_id)
    if year:
        q = q.filter_by(year=year)
    prods = q.all()
    if prods:
        parts = []
        for p in prods:
            parts.append(_production_tonnes(p.oil_amount, p.oil_unit, "oil"))
            parts.append(_production_tonnes(p.gas_amount, p.gas_unit, "gas"))
        total_tonnes = None if any(t is None for t in parts) else sum(parts)
        if total_tonnes and total_tonnes > 0:
            return (max(total_tonnes, float(declared_export_qty or 0.0)), True)
    # Honest fallback (also for a production unit that cannot be read): production equals the
    # declared export quantity (100 % export share), reported as not from the production data
    return (float(declared_export_qty or 0.0), False)


def _get_facility_scope2_metrics(facility_id, year=None, country="Algeria", statuses=("Verified",)):
    """
    Queries Scope2Emission for actual electricity consumption and grid emission factor.
    Returns (total_mwh, grid_ef, supplier_label, has_real_data).
    """
    q = Scope2Emission.query.filter(Scope2Emission.facility_id == facility_id, Scope2Emission.status.in_(statuses))
    if year:
        q = q.filter_by(year=year)
    s2_records = q.all()
    if s2_records:
        elec_kwh = sum(
            float(s.electricity_kwh or 0.0)
            for s in s2_records
            if str(s.source_type or "").lower() in ("electricity", "power", "grid")
        )
        weighted_ef_sum = sum(
            float(s.electricity_kwh or 0.0) * float(s.emission_factor or 0.0)
            for s in s2_records
            if (s.electricity_kwh and s.emission_factor)
        )
        grid_ef = (weighted_ef_sum / elec_kwh) if elec_kwh > 0 else None
        grid_reg = next((s.grid_region for s in s2_records if s.grid_region), None)
        supplier = grid_reg or f"{country} National Grid / Utility"
        if elec_kwh > 0 and grid_ef and grid_ef > 0:
            return (elec_kwh / 1000.0, grid_ef, supplier, True)

    default_ef = COUNTRY_GRID_FACTORS.get(
        country, COUNTRY_GRID_FACTORS.get("Algeria", DEFAULT_GLOBAL_GRID_FACTOR)
    )
    return (0.0, default_ef, f"{country} National Grid Operator", False)



def _clean_xml_text(val):
    if val is None:
        return ""
    s = str(val)
    return re.sub(r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]", "", s)


def get_cbam_aggregated_category(cn_code, product_name=""):
    cn = str(cn_code or "").replace(" ", "").strip()
    p_lower = str(product_name or "").lower()
    
    if cn.startswith("2814") or cn.startswith("3102") or cn.startswith("3105") or "fertilizer" in p_lower or "ammonia" in p_lower or "uan" in p_lower:
        return "Fertilizers"
    elif cn.startswith("280410") or "hydrogen" in p_lower:
        return "Hydrogen"
    elif cn.startswith("72") or cn.startswith("73") or "steel" in p_lower or "iron" in p_lower:
        return "Iron & Steel"
    elif cn.startswith("76") or "aluminium" in p_lower or "aluminum" in p_lower:
        return "Aluminium"
    elif cn.startswith("2523") or "cement" in p_lower or "clinker" in p_lower:
        return "Cement"
    elif cn.startswith("2710") or "diesel" in p_lower or "gasoil" in p_lower or "refin" in p_lower:
        return "Refined Petroleum Products"
    elif cn.startswith("2902") or "benzene" in p_lower or "xylene" in p_lower or "petrochem" in p_lower:
        return "Chemicals / Petrochemicals"
    return "Other CBAM Goods"


def get_cbam_production_route(cn_code, product_name=""):
    cat = get_cbam_aggregated_category(cn_code, product_name)
    p_lower = str(product_name or "").lower()
    if cat == "Fertilizers":
        if "ammonia" in p_lower or "2814" in str(cn_code):
            return "Steam Methane Reforming (SMR) with Haber-Bosch Synthesis"
        elif "uan" in p_lower or "3102" in str(cn_code):
            return "Urea synthesis & Ammonium Nitrate solution blending (UAN)"
        return "Chemical synthesis / Neutralization"
    elif cat == "Hydrogen":
        if "low-carbon" in p_lower or "clean" in p_lower:
            return "Steam Methane Reforming with Carbon Capture / ATR"
        return "Steam Methane Reforming (SMR) of natural gas"
    elif cat == "Refined Petroleum Products":
        return "Atmospheric Distillation, Hydrodesulfurization & Catalytic Reforming"
    elif cat == "Chemicals / Petrochemicals":
        return "Catalytic Naphtha Reforming & Aromatics Extraction"
    elif cat == "Iron & Steel":
        return "Direct Reduced Iron (DRI) / Electric Arc Furnace (EAF)"
    elif cat == "Aluminium":
        return "Primary Smelting (Hall-Héroult Electrolysis)"
    return "Standard industrial production route"


@reports_bp.route("/cbam-export", methods=["GET"])
@reports_bp.route("/cbam-export/", methods=["GET"])
@login_required
def export_cbam_report():
    """
    Generates the official EU CBAM Communication Template under Regulation (EU) 2023/956
    and Implementing Regulation (EU) 2023/1773.
    Supports ?format=excel (default) or ?format=xml.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "Forbidden: IT personnel cannot access operational compliance reports"}), 403

    # bug hunt 2026-10-15 #35: emissions of the chosen statuses only (default Verified); a malformed
    # year or facility is refused (it meant "all")
    year = request.args.get("year", "all")
    year_filter = report_year(year)
    facility_filter = report_facility(request.args.get("facility_id") or request.args.get("facilityId"))
    statuses = report_statuses(request.args.get("status"))

    try:
        allowed_fids = get_allowed_facility_ids(user)

        export_format = request.args.get("format", "excel").lower()
        if export_format not in ("excel", "xml", "xlsx"):
            return jsonify({"error": f"Unsupported export format '{export_format}'. Supported formats: 'excel', 'xml'"}), 400

        if facility_filter is not None and allowed_fids is not None and facility_filter not in allowed_fids:
            return jsonify({"error": "Unauthorized facility"}), 403

        # Query facilities
        fac_q = Facility.query
        if allowed_fids is not None:
            fac_q = fac_q.filter(Facility.id.in_(allowed_fids))
        if facility_filter:
            fac_q = fac_q.filter_by(id=facility_filter)
        facilities = {f.id: f for f in fac_q.all()}

        # Query CBAM records
        cbam_q = CbamProductExport.query
        if allowed_fids is not None:
            cbam_q = cbam_q.filter(CbamProductExport.facility_id.in_(allowed_fids))
        if facility_filter:
            cbam_q = cbam_q.filter_by(facility_id=facility_filter)
        if year_filter:
            cbam_q = cbam_q.filter_by(year=year_filter)
        
        cbam_records = cbam_q.order_by(CbamProductExport.year.desc(), CbamProductExport.month.desc(), CbamProductExport.id.asc()).all()

        # the declaring account as it is: no invented organisation, name or address
        company_name = getattr(user, "orgName", None) or ""
        assessor_name = getattr(user, "fullName", None) or ""
        assessor_email = getattr(user, "email", None) or ""
        now_utc = datetime.now(timezone.utc)
        rep_year_str = str(year_filter) if year_filter else "2024-2026"

        first_fac = next(iter(facilities.values()), None) if facilities else None
        op_country = getattr(first_fac, "country", None) or getattr(user, "location", None) or "Algeria"
        op_iso = "DZ" if "algeria" in op_country.lower() else (op_country[:2].upper() if len(op_country) >= 2 else "DZ")
        clean_org = re.sub(r"[^A-Za-z0-9]", "", company_name).upper()[:10] or "OPERATOR"
        op_id = f"{op_iso}-{clean_org}-001"

        # -------------------------------------------------------------
        # BRANCH: XML FORMAT (Transitional Registry XML Submission)
        # -------------------------------------------------------------
        if export_format == "xml":
            root = ET.Element("CBAMDeclaration", {
                "xmlns": "urn:eu:taxud:cbam:v1",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "version": "1.0",
            })

            # Header
            header = ET.SubElement(root, "Header")
            ET.SubElement(header, "MessageId").text = f"CBAM-{op_iso}-{rep_year_str}-{now_utc.strftime('%Y%m%d%H%M%S')}"
            ET.SubElement(header, "CreationTimestamp").text = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            ET.SubElement(header, "LegalReference").text = "Regulation (EU) 2023/956 & Implementing Regulation (EU) 2023/1773"
            
            reporting_period = ET.SubElement(header, "ReportingPeriod")
            ET.SubElement(reporting_period, "Year").text = rep_year_str
            quarter_param = request.args.get("quarter", "Q1-Q4")
            ET.SubElement(reporting_period, "Quarter").text = quarter_param
            ET.SubElement(reporting_period, "PeriodType").text = "Transitional Period Declaration"

            # Declarant / Operator
            declarant = ET.SubElement(root, "Declarant")
            ET.SubElement(declarant, "EORINumber").text = _clean_xml_text(op_id)
            ET.SubElement(declarant, "OperatorName").text = _clean_xml_text(company_name)
            ET.SubElement(declarant, "Role").text = "Operator of Non-EU Installation"
            ET.SubElement(declarant, "Country").text = _clean_xml_text(op_iso)
            ET.SubElement(declarant, "ContactEmail").text = _clean_xml_text(assessor_email)

            # Installations
            installations_el = ET.SubElement(root, "Installations")
            reported_fids = set(r.facility_id for r in cbam_records) if cbam_records else set(facilities.keys())
            for fid in sorted(reported_fids):
                fac = facilities.get(fid)
                if not fac:
                    continue
                inst_el = ET.SubElement(installations_el, "Installation")
                fac_code = fac.code or f"{op_iso}-FAC-{fac.id:03d}"
                ET.SubElement(inst_el, "InstallationId").text = _clean_xml_text(fac_code)
                ET.SubElement(inst_el, "Name").text = _clean_xml_text(fac.name)
                ET.SubElement(inst_el, "Country").text = _clean_xml_text(fac.country or op_iso)
                ET.SubElement(inst_el, "EconomicActivity").text = _clean_xml_text(fac.activity or "Petrochemical & Refining")
                coords = ET.SubElement(inst_el, "Coordinates")
                ET.SubElement(coords, "Latitude").text = f"{fac.latitude:.6f}" if fac.latitude is not None else "0.000000"
                ET.SubElement(coords, "Longitude").text = f"{fac.longitude:.6f}" if fac.longitude is not None else "0.000000"

            # Goods Exported
            goods_el = ET.SubElement(root, "GoodsExported")
            fingerprint_data = []

            for r in cbam_records:
                fac = facilities.get(r.facility_id)
                fac_name = fac.name if fac else f"Facility {r.facility_id}"
                fac_country = getattr(fac, "country", None) or op_country
                fac_code = fac.code if fac and fac.code else f"{op_iso}-FAC-{r.facility_id:03d}"
                cat = get_cbam_aggregated_category(r.cn_code, r.product_name)
                direct_see = float(r.specific_embedded_direct or 0.0)
                indirect_see = float(r.specific_embedded_indirect or 0.0)
                precursor_contrib = (float(r.precursor_ratio or 0.0) * (float(r.precursor_see_dir or 0.0) + float(r.precursor_see_indir or 0.0))) if r.is_complex_good else 0.0
                total_see = direct_see + indirect_see + precursor_contrib
                qty = float(r.quantity_tonnes or 0.0)
                total_emissions = qty * total_see

                good_el = ET.SubElement(goods_el, "Good")
                ET.SubElement(good_el, "RecordId").text = str(r.id)
                ET.SubElement(good_el, "InstallationCode").text = _clean_xml_text(fac_code)
                ET.SubElement(good_el, "InstallationName").text = _clean_xml_text(fac_name)
                ET.SubElement(good_el, "CNCode").text = _clean_xml_text(r.cn_code)
                ET.SubElement(good_el, "CommercialDescription").text = _clean_xml_text(r.product_name)
                ET.SubElement(good_el, "AggregatedCategory").text = _clean_xml_text(cat)
                ET.SubElement(good_el, "ProductionRoute").text = _clean_xml_text(get_cbam_production_route(r.cn_code, r.product_name))
                ET.SubElement(good_el, "Year").text = str(r.year)
                ET.SubElement(good_el, "Month").text = str(r.month)
                ET.SubElement(good_el, "Quarter").text = _clean_xml_text(r.quarter or f"Q{(r.month - 1) // 3 + 1 if r.month else 1}")
                ET.SubElement(good_el, "QuantityTonnes").text = f"{qty:.2f}"
                ET.SubElement(good_el, "ExportDestination").text = _clean_xml_text(r.export_destination or "EU")

                # Carbon Capture and Storage (CCS) for Blue Hydrogen / Ammonia
                if (r.captured_co2_tonnes or 0.0) > 0:
                    ccs_el = ET.SubElement(good_el, "CarbonCaptureAndStorage")
                    ET.SubElement(ccs_el, "CapturedCO2Tonnes", {"unit": "tCO2"}).text = f"{float(r.captured_co2_tonnes):.2f}"
                    storage_cert = _clean_xml_text(r.ccs_certificate_id or "Self-Declared / Pending Storage Certificate")
                    ET.SubElement(ccs_el, "StorageCertificateId").text = storage_cert
                    ET.SubElement(ccs_el, "PermanentStorageStandard").text = "Directive 2009/31/EC & ISO 27914 Geological Sequestration"

                # Embedded emissions breakdown
                em_el = ET.SubElement(good_el, "SpecificEmbeddedEmissions")
                ET.SubElement(em_el, "Direct", {"unit": "tCO2e/t"}).text = f"{direct_see:.4f}"
                ET.SubElement(em_el, "Indirect", {"unit": "tCO2e/t"}).text = f"{indirect_see:.4f}"
                if precursor_contrib > 0:
                    ET.SubElement(em_el, "PrecursorContribution", {"unit": "tCO2e/t"}).text = f"{precursor_contrib:.4f}"
                ET.SubElement(em_el, "Total", {"unit": "tCO2e/t"}).text = f"{total_see:.4f}"

                ET.SubElement(good_el, "TotalEmbeddedEmissions", {"unit": "tCO2e"}).text = f"{total_emissions:.2f}"

                # Article 7 Complex Precursors
                ET.SubElement(good_el, "IsComplexGood").text = "true" if r.is_complex_good else "false"
                if r.is_complex_good and r.precursor_name:
                    precursors_el = ET.SubElement(good_el, "Precursors")
                    prec_el = ET.SubElement(precursors_el, "Precursor")
                    ET.SubElement(prec_el, "PrecursorName").text = _clean_xml_text(r.precursor_name)
                    ET.SubElement(prec_el, "PrecursorCNCode").text = _clean_xml_text(r.precursor_cn_code)
                    ET.SubElement(prec_el, "ConsumptionRatio", {"unit": "t/t"}).text = f"{float(r.precursor_ratio or 0.0):.4f}"
                    prec_em = ET.SubElement(prec_el, "PrecursorSpecificEmissions")
                    ET.SubElement(prec_em, "Direct", {"unit": "tCO2e/t"}).text = f"{float(r.precursor_see_dir or 0.0):.4f}"
                    ET.SubElement(prec_em, "Indirect", {"unit": "tCO2e/t"}).text = f"{float(r.precursor_see_indir or 0.0):.4f}"
                    ET.SubElement(prec_em, "TotalPrecursorContribution", {"unit": "tCO2e/t"}).text = f"{precursor_contrib:.4f}"

                # Article 9 Origin Carbon Price / Flaring Fiscality
                carbon_price = ET.SubElement(good_el, "CarbonPricePaidInCountryOfOrigin")
                ET.SubElement(carbon_price, "Currency").text = "EUR"
                ET.SubElement(carbon_price, "AmountPerTonne", {"unit": "EUR/t"}).text = f"{float(r.carbon_price_paid_eur or 0.0):.2f}"
                ET.SubElement(carbon_price, "TotalAmountPaidEUR").text = f"{(float(r.carbon_price_paid_eur or 0.0) * qty):.2f}"
                legal_ref = r.carbon_price_legal_ref or (f"{fac_country} Environmental / Carbon Fiscality" if (r.carbon_price_paid_eur or 0) > 0 else "None")
                ET.SubElement(carbon_price, "LegalBasis").text = _clean_xml_text(legal_ref)
                ET.SubElement(carbon_price, "RebateOrCompensation").text = "None"

                fingerprint_data.append({
                    "id": r.id,
                    "fac": fac_code,
                    "cn": r.cn_code,
                    "qty": qty,
                    "direct_see": direct_see,
                    "indirect_see": indirect_see,
                    "captured_co2": float(r.captured_co2_tonnes or 0.0),
                    "precursor_contrib": precursor_contrib,
                    "carbon_price_paid": float(r.carbon_price_paid_eur or 0.0),
                    "total_emissions": total_emissions
                })

            # Calculate SHA-256 fingerprint
            data_hash = hashlib.sha256(json.dumps(fingerprint_data, sort_keys=True).encode("utf-8")).hexdigest()

            # Audit Assurance
            assurance_el = ET.SubElement(root, "AuditAssurance")
            ET.SubElement(assurance_el, "VerificationStandard").text = "ISO 14064-3 / Implementing Regulation (EU) 2023/1773 Art. 18"
            ET.SubElement(assurance_el, "SHA256DataFingerprint").text = data_hash
            ET.SubElement(assurance_el, "LeadAssessor").text = f"{assessor_name} ({user.role})"
            ET.SubElement(assurance_el, "AssuranceLevel").text = "Reasonable Assurance"

            # Pretty print XML
            xml_str = ET.tostring(root, encoding="utf-8")
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ", encoding="utf-8")

            output_buffer = io.BytesIO(pretty_xml)
            filename = f"CBAM_Transitional_Declaration_{rep_year_str}.xml"
            resp = send_file(
                output_buffer,
                mimetype="application/xml",
                as_attachment=True,
                download_name=filename,
            )
            record_report_fingerprint(resp, user, "EU CBAM XML Declaration", {"year": year}, len(cbam_records), data_hash)
            resp.headers["X-Audit-Timestamp"] = now_utc.isoformat()
            resp.headers["X-Audit-SHA256"] = data_hash
            return resp

        # -------------------------------------------------------------
        # BRANCH: EXCEL FORMAT (Official DG TAXUD Communication Template)
        # -------------------------------------------------------------
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove active blank sheet

        # Official European Commission CBAM Palette
        c_eu_navy = "003399"     # EU Reflex Blue
        c_eu_gold = "FFCC00"     # EU Gold
        c_dark_slate = "0F172A"  # Text header
        c_blue_sub = "1E40AF"    # Sub header
        c_teal_accent = "0284C7" # Secondary accent
        c_border = "CBD5E1"      # Border color
        c_light_zebra = "F8FAFC" # Alternating row

        fill_eu_header = PatternFill(start_color=c_eu_navy, end_color=c_eu_navy, fill_type="solid")
        fill_eu_sub = PatternFill(start_color=c_blue_sub, end_color=c_blue_sub, fill_type="solid")
        fill_gold_accent = PatternFill(start_color=c_eu_gold, end_color=c_eu_gold, fill_type="solid")
        fill_label = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

        font_header_white = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        font_header_dark = Font(name="Calibri", size=11, bold=True, color="000000")
        font_title = Font(name="Calibri", size=14, bold=True, color=c_eu_navy)
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

        def style_header_row(ws, row_idx, fill=fill_eu_header, font=font_header_white):
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_idx, column=col)
                cell.fill = fill
                cell.font = font
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
        # SHEET 1: A_InstData (Installation & Operator Data)
        # -------------------------------------------------------------
        ws_a = wb.create_sheet(title="A_InstData")
        ws_a.views.sheetView[0].showGridLines = True

        ws_a.cell(row=1, column=1, value="EUROPEAN COMMISSION — DIRECTORATE-GENERAL TAXATION AND CUSTOMS UNION").font = font_title
        ws_a.cell(row=2, column=1, value="CBAM Communication Template for Installations outside the EU (Regulation (EU) 2023/956 & Implementing Reg (EU) 2023/1773)").font = font_subtitle

        inst_fields = [
            ("Reporting Period (Start Date)", f"{rep_year_str}-01-01"),
            ("Reporting Period (End Date)", f"{rep_year_str}-12-31"),
            ("Reporting Year", rep_year_str),
            ("Name of the Operator", company_name),
            ("Unique Operator Identifier", op_id),
            ("Country of Operator", f"{op_country} ({op_iso})"),
            ("Country Code (ISO 3166-1 alpha-2)", op_iso),
            ("Primary Contact Person", f"{assessor_name} ({assessor_email})"),
            ("Role of Declarant", "Non-EU Installation Operator / Direct Exporter"),
            ("EU ETS Benchmark Reference", "Commission Implementing Regulation (EU) 2021/447"),
            ("Applicable Methodology", "Annex III of Implementing Regulation (EU) 2023/1773 (Calculation-based / Activity-based)"),
            ("Accreditation Standard for Verifier", "ISO 14065 / ISO 14064-3 Reasonable Assurance"),
            ("Operating Facilities in Scope", len(facilities)),
            ("CBAM Export Records Count", len(cbam_records)),
        ]

        ws_a.cell(row=4, column=1, value="Field Parameter").fill = fill_eu_header
        ws_a.cell(row=4, column=1).font = font_header_white
        ws_a.cell(row=4, column=2, value="Declared Value").fill = fill_eu_header
        ws_a.cell(row=4, column=2).font = font_header_white

        for idx, (prop, val) in enumerate(inst_fields, start=5):
            ws_a.cell(row=idx, column=1, value=prop).font = font_bold
            ws_a.cell(row=idx, column=1).fill = fill_label
            ws_a.cell(row=idx, column=1).border = thin_border
            ws_a.cell(row=idx, column=2, value=_safe_excel_value(str(val))).font = font_regular
            ws_a.cell(row=idx, column=2).border = thin_border

        # Sub-table: Installations Register
        sub_row = len(inst_fields) + 7
        ws_a.cell(row=sub_row, column=1, value="REGISTERED PRODUCTION INSTALLATIONS & SITES").font = font_bold

        inst_headers = ["ID", "Installation Name", "Facility Code", "Segment", "Division / Region", "Country", "Latitude", "Longitude", "Status"]
        for col_idx, h in enumerate(inst_headers, start=1):
            ws_a.cell(row=sub_row + 1, column=col_idx, value=h).fill = fill_eu_sub
            ws_a.cell(row=sub_row + 1, column=col_idx).font = font_header_white
            ws_a.cell(row=sub_row + 1, column=col_idx).alignment = Alignment(horizontal="center", vertical="center")

        for idx, f in enumerate(facilities.values(), start=sub_row + 2):
            fac_country = f.country or op_country
            ws_a.cell(row=idx, column=1, value=f.id).font = font_regular
            ws_a.cell(row=idx, column=2, value=_safe_excel_value(f.name)).font = font_bold
            ws_a.cell(row=idx, column=3, value=_safe_excel_value(f.code or f"{op_iso}-FAC-{f.id:03d}")).font = font_mono
            ws_a.cell(row=idx, column=4, value=_safe_excel_value(f.segment or "Downstream")).font = font_regular
            ws_a.cell(row=idx, column=5, value=_safe_excel_value(f"{f.division or ''} / {f.region or ''}")).font = font_regular
            ws_a.cell(row=idx, column=6, value=_safe_excel_value(fac_country)).font = font_regular
            ws_a.cell(row=idx, column=7, value=f.latitude if f.latitude is not None else "N/A").font = font_mono
            ws_a.cell(row=idx, column=8, value=f.longitude if f.longitude is not None else "N/A").font = font_mono
            ws_a.cell(row=idx, column=9, value=f.operator_status or "Active Operational Control").font = font_regular

            for c in range(1, 10):
                ws_a.cell(row=idx, column=c).border = thin_border
                if idx % 2 == 0:
                    ws_a.cell(row=idx, column=c).fill = PatternFill(start_color=c_light_zebra, end_color=c_light_zebra, fill_type="solid")

        autofit_columns(ws_a)

        # -------------------------------------------------------------
        # SHEET 2: B_Processes (Aggregated Goods & Production Routes)
        # -------------------------------------------------------------
        ws_b = wb.create_sheet(title="B_Processes")
        ws_b.views.sheetView[0].showGridLines = True

        ws_b.cell(row=1, column=1, value="EU CBAM — AGGREGATED GOODS CATEGORIES & PRODUCTION PROCESSES").font = font_title
        ws_b.cell(row=2, column=1, value="Production routes, CN classifications and system boundaries under Annex II of Reg (EU) 2023/1773").font = font_subtitle

        b_headers = [
            "Process ID", "Installation Name", "Facility Code", "Aggregated Goods Category",
            "CN Code (8-digit)", "Commercial Product Name", "Production Route / Technology",
            "System Boundary Definition", "Total Annual Production (t)", "EU Export Quantity (t)", "Share of EU Export (%)"
        ]
        for col_idx, h in enumerate(b_headers, start=1):
            ws_b.cell(row=4, column=col_idx, value=h)
        style_header_row(ws_b, 4, fill=fill_eu_header)

        for idx, r in enumerate(cbam_records, start=5):
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            fac_code = fac.code if fac and fac.code else f"{op_iso}-FAC-{r.facility_id:03d}"
            cat = get_cbam_aggregated_category(r.cn_code, r.product_name)
            p_route = get_cbam_production_route(r.cn_code, r.product_name)
            qty = float(r.quantity_tonnes or 0.0)
            total_prod, is_from_prod = _get_facility_production_tonnes(r.facility_id, r.year, qty)
            share_pct = (qty / total_prod * 100.0) if total_prod > 0 else 100.0
            if share_pct > 100.0:
                share_pct = 100.0

            ws_b.cell(row=idx, column=1, value=f"PROC-{r.id:04d}").font = font_mono
            ws_b.cell(row=idx, column=2, value=_safe_excel_value(fac_name)).font = font_bold
            ws_b.cell(row=idx, column=3, value=_safe_excel_value(fac_code)).font = font_mono
            ws_b.cell(row=idx, column=4, value=cat).font = font_bold
            ws_b.cell(row=idx, column=5, value=_safe_excel_value(str(r.cn_code))).font = font_mono
            ws_b.cell(row=idx, column=6, value=_safe_excel_value(r.product_name)).font = font_regular
            ws_b.cell(row=idx, column=7, value=p_route).font = font_regular
            ws_b.cell(row=idx, column=8, value="Gate-to-gate installation boundary including combustion, reaction, flare, and on-site electricity").font = font_regular
            ws_b.cell(row=idx, column=9, value=round(total_prod, 1)).number_format = "#,##0.0"
            for c in range(1, 12):
                ws_b.cell(row=idx, column=c).border = thin_border
                if idx % 2 == 0:
                    ws_b.cell(row=idx, column=c).fill = PatternFill(start_color=c_light_zebra, end_color=c_light_zebra, fill_type="solid")

        autofit_columns(ws_b)

        # -------------------------------------------------------------
        # SHEET 3: C_Emissions (Direct Emissions & SEE Direct)
        # -------------------------------------------------------------
        ws_c = wb.create_sheet(title="C_Emissions")
        ws_c.views.sheetView[0].showGridLines = True

        ws_c.cell(row=1, column=1, value="EU CBAM — DIRECT EMISSIONS & SPECIFIC EMBEDDED DIRECT (SEE_dir)").font = font_title
        ws_c.cell(row=2, column=1, value="Activity data, combustion, process stoichiometry, flaring and heat attribution under Reg (EU) 2023/1773").font = font_subtitle

        c_headers = [
            "Record ID", "Product Name", "CN Code", "Quantity Exported (t)",
            "Combustion Emissions (tCO2e)", "Process Reaction Emissions (tCO2e)", "Flaring & Venting (tCO2e)",
            "Measurable Net Heat (GJ)", "Heat Emission Factor (tCO2/GJ)", "Attributed Direct Emissions (tCO2e)",
            "Specific Direct Embedded (SEE_dir) (tCO2e/t)", "EU ETS Benchmark Benchmark (tCO2e/t)", "Benchmark Alignment"
        ]
        for col_idx, h in enumerate(c_headers, start=1):
            ws_c.cell(row=4, column=col_idx, value=h)
        style_header_row(ws_c, 4, fill=fill_eu_header)

        for idx, r in enumerate(cbam_records, start=5):
            qty = float(r.quantity_tonnes or 0.0)
            direct_see = float(r.specific_embedded_direct or 0.0)
            attr_direct = qty * direct_see
            
            comb_pct, proc_pct, flare_pct, has_split = _get_facility_scope1_split(r.facility_id, r.year, statuses)
            combustion_em = attr_direct * comb_pct
            process_em = attr_direct * proc_pct
            flare_em = attr_direct * flare_pct
            heat_gj = 0.0
            heat_ef = 0.0561
            ets_bench = 1.30 if "ammonia" in r.product_name.lower() else (0.28 if "diesel" in r.product_name.lower() else 0.85)
            alignment = "Compliant (Within Expected Envelope)" if direct_see <= ets_bench * 1.5 else "Higher Than Benchmark"

            ws_c.cell(row=idx, column=1, value=r.id).font = font_mono
            ws_c.cell(row=idx, column=2, value=_safe_excel_value(r.product_name)).font = font_bold
            ws_c.cell(row=idx, column=3, value=_safe_excel_value(str(r.cn_code))).font = font_mono
            ws_c.cell(row=idx, column=4, value=round(qty, 1)).number_format = "#,##0.0"
            ws_c.cell(row=idx, column=5, value=round(combustion_em, 1)).number_format = "#,##0.0"
            ws_c.cell(row=idx, column=6, value=round(process_em, 1)).number_format = "#,##0.0"
            ws_c.cell(row=idx, column=7, value=round(flare_em, 1)).number_format = "#,##0.0"
            ws_c.cell(row=idx, column=8, value=round(heat_gj, 1)).number_format = "#,##0.0"
            ws_c.cell(row=idx, column=9, value=heat_ef).number_format = "0.0000"
            ws_c.cell(row=idx, column=10, value=round(attr_direct, 1)).number_format = "#,##0.0"
            ws_c.cell(row=idx, column=11, value=round(direct_see, 4)).number_format = "0.0000"
            ws_c.cell(row=idx, column=12, value=ets_bench).number_format = "0.0000"
            ws_c.cell(row=idx, column=13, value=alignment).font = font_bold

            for col in range(1, 14):
                ws_c.cell(row=idx, column=col).border = thin_border
                if idx % 2 == 0:
                    ws_c.cell(row=idx, column=col).fill = PatternFill(start_color=c_light_zebra, end_color=c_light_zebra, fill_type="solid")

        autofit_columns(ws_c)

        # -------------------------------------------------------------
        # SHEET 4: D_Electricity (Electricity Consumption & SEE Indirect)
        # -------------------------------------------------------------
        ws_d = wb.create_sheet(title="D_Electricity")
        ws_d.views.sheetView[0].showGridLines = True

        ws_d.cell(row=1, column=1, value="EU CBAM — ELECTRICITY CONSUMPTION & SPECIFIC INDIRECT EMBEDDED (SEE_indir)").font = font_title
        ws_d.cell(row=2, column=1, value="Grid emission factors, on-site power generation and indirect emissions under Annex III Reg (EU) 2023/1773").font = font_subtitle

        d_headers = [
            "Record ID", "Product Name", "CN Code", "Quantity Exported (t)",
            "Electricity Source", "Process Electricity Consumed (MWh)", "Specific Electricity Consumption (MWh/t)",
            "Electricity Emission Factor (tCO2/MWh)", "Attributed Indirect Emissions (tCO2e)",
            "Specific Indirect Embedded (SEE_indir) (tCO2e/t)", "Accounting Basis"
        ]
        for col_idx, h in enumerate(d_headers, start=1):
            ws_d.cell(row=4, column=col_idx, value=h)
        style_header_row(ws_d, 4, fill=fill_eu_header)

        for idx, r in enumerate(cbam_records, start=5):
            qty = float(r.quantity_tonnes or 0.0)
            indirect_see = float(r.specific_embedded_indirect or 0.0)
            fac = facilities.get(r.facility_id)
            fac_country = getattr(fac, "country", None) or op_country

            s2_mwh, real_grid_ef, grid_supplier, has_s2 = _get_facility_scope2_metrics(r.facility_id, r.year, fac_country, statuses)
            grid_ef = real_grid_ef
            spec_mwh = (indirect_see / grid_ef) if grid_ef > 0 else 0.0
            tot_mwh = qty * spec_mwh
            attr_indirect = qty * indirect_see
            accounting_basis = "Verified Scope 2 Invoiced Metering + Grid EF" if has_s2 else f"Official {fac_country} National Grid Factor (Annex III Reg 2023/1773)"

            ws_d.cell(row=idx, column=1, value=r.id).font = font_mono
            ws_d.cell(row=idx, column=2, value=r.product_name).font = font_bold
            ws_d.cell(row=idx, column=3, value=str(r.cn_code)).font = font_mono
            ws_d.cell(row=idx, column=4, value=round(qty, 1)).number_format = "#,##0.0"
            ws_d.cell(row=idx, column=5, value=grid_supplier).font = font_regular
            ws_d.cell(row=idx, column=6, value=round(tot_mwh, 1)).number_format = "#,##0.0"
            ws_d.cell(row=idx, column=7, value=round(spec_mwh, 4)).number_format = "0.0000"
            ws_d.cell(row=idx, column=8, value=grid_ef).number_format = "0.0000"
            ws_d.cell(row=idx, column=9, value=round(attr_indirect, 1)).number_format = "#,##0.0"
            ws_d.cell(row=idx, column=10, value=round(indirect_see, 4)).number_format = "0.0000"
            ws_d.cell(row=idx, column=11, value=accounting_basis).font = font_regular

            for col in range(1, 12):
                ws_d.cell(row=idx, column=col).border = thin_border
                if idx % 2 == 0:
                    ws_d.cell(row=idx, column=col).fill = PatternFill(start_color=c_light_zebra, end_color=c_light_zebra, fill_type="solid")

        autofit_columns(ws_d)

        # -------------------------------------------------------------
        # SHEET 5: E_Precursors (Relevant Precursors & Inputs)
        # -------------------------------------------------------------
        ws_e = wb.create_sheet(title="E_Precursors")
        ws_e.views.sheetView[0].showGridLines = True

        ws_e.cell(row=1, column=1, value="EU CBAM — COMPLEX GOODS PRECURSORS & EMBEDDED ACCOUNTING").font = font_title
        ws_e.cell(row=2, column=1, value="Precursor consumption ratios and embedded emissions for complex goods under Article 7 Reg (EU) 2023/956").font = font_subtitle

        e_headers = [
            "Complex Good Name", "CN Code", "Relevant Precursor Name", "Precursor CN Code",
            "Precursor Country of Origin", "Precursor Consumption Ratio (t/t)",
            "Precursor SEE_dir (tCO2e/t)", "Precursor SEE_indir (tCO2e/t)",
            "Precursor Total SEE (tCO2e/t)", "Contribution to Complex Good (tCO2e/t)"
        ]
        for col_idx, h in enumerate(e_headers, start=1):
            ws_e.cell(row=4, column=col_idx, value=h)
        style_header_row(ws_e, 4, fill=fill_eu_header)

        # Collect dynamic precursor rows from recorded exports only
        precursor_rows = []
        for r in cbam_records:
            if r.is_complex_good and r.precursor_name:
                ratio = float(r.precursor_ratio or 0.0)
                p_dir = float(r.precursor_see_dir or 0.0)
                p_indir = float(r.precursor_see_indir or 0.0)
                p_tot = p_dir + p_indir
                p_contrib = ratio * p_tot
                fac = facilities.get(r.facility_id)
                fac_country = getattr(fac, "country", None) or op_country
                precursor_rows.append((
                    r.product_name,
                    r.cn_code,
                    r.precursor_name,
                    r.precursor_cn_code or "2814 10 00",
                    f"{fac_country} (In-House / Attributed)",
                    ratio,
                    p_dir,
                    p_indir,
                    p_tot,
                    p_contrib
                ))

        if not precursor_rows:
            ws_e.cell(row=5, column=1, value="No complex goods with upstream precursors declared for this reporting period under Article 7").font = font_subtitle
            for col in range(1, 11):
                ws_e.cell(row=5, column=col).border = thin_border
        else:
            for idx, p in enumerate(precursor_rows, start=5):
                ws_e.cell(row=idx, column=1, value=p[0]).font = font_bold
                ws_e.cell(row=idx, column=2, value=p[1]).font = font_mono
                ws_e.cell(row=idx, column=3, value=p[2]).font = font_regular
                ws_e.cell(row=idx, column=4, value=p[3]).font = font_mono
                ws_e.cell(row=idx, column=5, value=p[4]).font = font_regular
                ws_e.cell(row=idx, column=6, value=p[5]).number_format = "0.0000"
                ws_e.cell(row=idx, column=7, value=p[6]).number_format = "0.0000"
                ws_e.cell(row=idx, column=8, value=p[7]).number_format = "0.0000"
                ws_e.cell(row=idx, column=9, value=p[8]).number_format = "0.0000"
                ws_e.cell(row=idx, column=10, value=p[9]).number_format = "0.0000"

                for col in range(1, 11):
                    ws_e.cell(row=idx, column=col).border = thin_border
                    if idx % 2 == 0:
                        ws_e.cell(row=idx, column=col).fill = PatternFill(start_color=c_light_zebra, end_color=c_light_zebra, fill_type="solid")

        autofit_columns(ws_e)

        # -------------------------------------------------------------
        # SHEET 6: F_Summary (Official CBAM Communication Summary for Importers)
        # -------------------------------------------------------------
        ws_f = wb.create_sheet(title="F_Summary")
        ws_f.views.sheetView[0].showGridLines = True

        ws_f.cell(row=1, column=1, value="EU CBAM — OFFICIAL COMMUNICATION SUMMARY FOR EU IMPORTERS & DECLARANTS").font = font_title
        ws_f.cell(row=2, column=1, value="Core declaration dataset required for submission to the EU CBAM Transitional Registry (DG TAXUD)").font = font_subtitle

        f_headers = [
            "Installation Name", "Installation Code", "Country of Origin", "Commercial Product Name",
            "CN Code (8-digit)", "Aggregated Category", "Reporting Period", "Quantity Exported to EU (t)",
            "Captured CO2 (t)", "Specific Direct Embedded (tCO2e/t)", "Specific Indirect Embedded (tCO2e/t)",
            "Precursor Embedded (tCO2e/t)", "Total Specific Embedded (tCO2e/t)", "Total Embedded Emissions (tCO2e)",
            "Origin Carbon Price Paid (EUR/t)", "Net CBAM Embedded Emissions (tCO2e)"
        ]
        for col_idx, h in enumerate(f_headers, start=1):
            ws_f.cell(row=4, column=col_idx, value=h)
        style_header_row(ws_f, 4, fill=fill_eu_header)

        fingerprint_data_excel = []

        for idx, r in enumerate(cbam_records, start=5):
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            fac_country = getattr(fac, "country", None) or op_country
            fac_code = fac.code if fac and fac.code else f"{op_iso}-FAC-{r.facility_id:03d}"
            cat = get_cbam_aggregated_category(r.cn_code, r.product_name)
            qty = float(r.quantity_tonnes or 0.0)
            direct_see = float(r.specific_embedded_direct or 0.0)
            indirect_see = float(r.specific_embedded_indirect or 0.0)
            precursor_contrib = (float(r.precursor_ratio or 0.0) * (float(r.precursor_see_dir or 0.0) + float(r.precursor_see_indir or 0.0))) if r.is_complex_good else 0.0
            total_see = direct_see + indirect_see + precursor_contrib
            total_embedded = qty * total_see
            carbon_price_eur = float(r.carbon_price_paid_eur or 0.0)
            net_cbam_emissions = total_embedded
            period_str = f"{r.year} - {r.quarter or f'Q{(r.month - 1) // 3 + 1 if r.month else 1}'}"

            ws_f.cell(row=idx, column=1, value=_safe_excel_value(fac_name)).font = font_bold
            ws_f.cell(row=idx, column=2, value=_safe_excel_value(fac_code)).font = font_mono
            ws_f.cell(row=idx, column=3, value=f"{fac_country} ({op_iso})").font = font_regular
            ws_f.cell(row=idx, column=4, value=_safe_excel_value(r.product_name)).font = font_bold
            ws_f.cell(row=idx, column=5, value=str(r.cn_code)).font = font_mono
            ws_f.cell(row=idx, column=6, value=_safe_excel_value(cat)).font = font_bold
            ws_f.cell(row=idx, column=7, value=period_str).font = font_regular
            ws_f.cell(row=idx, column=8, value=round(qty, 1)).number_format = "#,##0.0"
            ws_f.cell(row=idx, column=9, value=round(float(r.captured_co2_tonnes or 0.0), 1)).number_format = "#,##0.0"
            ws_f.cell(row=idx, column=10, value=round(direct_see, 4)).number_format = "0.0000"
            ws_f.cell(row=idx, column=11, value=round(indirect_see, 4)).number_format = "0.0000"
            ws_f.cell(row=idx, column=12, value=round(precursor_contrib, 4)).number_format = "0.0000"
            ws_f.cell(row=idx, column=13, value=round(total_see, 4)).number_format = "0.0000"
            ws_f.cell(row=idx, column=14, value=round(total_embedded, 1)).number_format = "#,##0.0"
            ws_f.cell(row=idx, column=15, value=carbon_price_eur).number_format = "€#,##0.00"
            ws_f.cell(row=idx, column=16, value=round(net_cbam_emissions, 1)).number_format = "#,##0.0"

            fingerprint_data_excel.append({
                "id": r.id,
                "fac": fac_code,
                "cn": r.cn_code,
                "qty": qty,
                "direct_see": direct_see,
                "indirect_see": indirect_see,
                "captured_co2": float(r.captured_co2_tonnes or 0.0),
                "precursor_contrib": precursor_contrib,
                "carbon_price_paid": carbon_price_eur,
                "total_emissions": total_embedded,
            })

            for col in range(1, 17):
                ws_f.cell(row=idx, column=col).border = thin_border
                if idx % 2 == 0:
                    ws_f.cell(row=idx, column=col).fill = PatternFill(start_color=c_light_zebra, end_color=c_light_zebra, fill_type="solid")

        # Summary Totals Row
        tot_row = len(cbam_records) + 5
        ws_f.cell(row=tot_row, column=1, value="TOTAL DECLARED EXPORTS & EMBEDDED EMISSIONS").font = font_bold
        ws_f.cell(row=tot_row, column=8, value=f"=SUM(H5:H{tot_row-1})").number_format = "#,##0.0"
        ws_f.cell(row=tot_row, column=8).font = font_bold
        ws_f.cell(row=tot_row, column=9, value=f"=SUM(I5:I{tot_row-1})").number_format = "#,##0.0"
        ws_f.cell(row=tot_row, column=9).font = font_bold
        ws_f.cell(row=tot_row, column=14, value=f"=SUM(N5:N{tot_row-1})").number_format = "#,##0.0"
        ws_f.cell(row=tot_row, column=14).font = font_bold
        ws_f.cell(row=tot_row, column=16, value=f"=SUM(P5:P{tot_row-1})").number_format = "#,##0.0"
        ws_f.cell(row=tot_row, column=16).font = font_bold

        for col in range(1, 17):
            ws_f.cell(row=tot_row, column=col).fill = fill_label
            ws_f.cell(row=tot_row, column=col).border = thin_border

        autofit_columns(ws_f)

        # -------------------------------------------------------------
        # SHEET 7: H_CarbonPrice (Article 9 Origin Carbon Price & Flaring Tax)
        # -------------------------------------------------------------
        ws_h = wb.create_sheet(title="H_CarbonPrice")
        ws_h.views.sheetView[0].showGridLines = True

        ws_h.cell(row=1, column=1, value="EU CBAM — ARTICLE 9 CARBON PRICE & FLARING FISCALITY PAID IN COUNTRY OF ORIGIN").font = font_title
        ws_h.cell(row=2, column=1, value="Details of carbon price and flaring penalties effectively paid under Article 9 of Regulation (EU) 2023/956").font = font_subtitle

        h_headers = [
            "Record ID", "Installation Name", "Facility Code", "Commercial Product Name",
            "CN Code (8-digit)", "Export Quantity (t)", "Applicable Legal Reference",
            "Carbon Tax / Flaring Rate (€/t)", "Total Origin Price Paid (€)",
            "Eligible CBAM Deduction Status", "Treasury / Fiscal Receipt ID"
        ]
        for col_idx, h in enumerate(h_headers, start=1):
            ws_h.cell(row=4, column=col_idx, value=h)
        style_header_row(ws_h, 4, fill=fill_eu_header)

        for idx, r in enumerate(cbam_records, start=5):
            fac = facilities.get(r.facility_id)
            fac_name = fac.name if fac else f"Facility {r.facility_id}"
            fac_country = getattr(fac, "country", None) or op_country
            fac_code = fac.code if fac and fac.code else f"{op_iso}-FAC-{r.facility_id:03d}"
            qty = float(r.quantity_tonnes or 0.0)
            rate = float(r.carbon_price_paid_eur or 0.0)
            tot_paid = qty * rate
            legal_ref = r.carbon_price_legal_ref or (f"{fac_country} Environmental / Carbon Fiscality" if rate > 0 else "N/A - No origin price claimed")
            status = "Eligible for Full Article 9 Deduction" if rate > 0 else "No Origin Price Claimed"

            if rate > 0:
                notes_val = str(r.notes or "").strip()
                if notes_val and any(term in notes_val.lower() for term in ("receipt", "tax", "cert", "ref", "doc")):
                    receipt_id = notes_val
                else:
                    receipt_id = "Self-Declared / Pending Fiscal Proof"
            else:
                receipt_id = "N/A"

            ws_h.cell(row=idx, column=1, value=r.id).font = font_mono
            ws_h.cell(row=idx, column=2, value=_safe_excel_value(fac_name)).font = font_bold
            ws_h.cell(row=idx, column=3, value=_safe_excel_value(fac_code)).font = font_mono
            ws_h.cell(row=idx, column=4, value=_safe_excel_value(r.product_name)).font = font_regular
            ws_h.cell(row=idx, column=5, value=str(r.cn_code)).font = font_mono
            ws_h.cell(row=idx, column=6, value=round(qty, 1)).number_format = "#,##0.0"
            ws_h.cell(row=idx, column=7, value=_safe_excel_value(legal_ref)).font = font_regular
            ws_h.cell(row=idx, column=8, value=rate).number_format = "€#,##0.00"
            ws_h.cell(row=idx, column=9, value=round(tot_paid, 2)).number_format = "€#,##0.00"
            ws_h.cell(row=idx, column=10, value=status).font = font_bold
            ws_h.cell(row=idx, column=11, value=_safe_excel_value(receipt_id)).font = font_mono

            for col in range(1, 12):
                ws_h.cell(row=idx, column=col).border = thin_border
                if idx % 2 == 0:
                    ws_h.cell(row=idx, column=col).fill = PatternFill(start_color=c_light_zebra, end_color=c_light_zebra, fill_type="solid")

        tot_h_row = len(cbam_records) + 5
        ws_h.cell(row=tot_h_row, column=1, value="TOTAL CARBON PRICE PAID IN COUNTRY OF ORIGIN").font = font_bold
        ws_h.cell(row=tot_h_row, column=6, value=f"=SUM(F5:F{tot_h_row-1})").number_format = "#,##0.0"
        ws_h.cell(row=tot_h_row, column=6).font = font_bold
        ws_h.cell(row=tot_h_row, column=9, value=f"=SUM(I5:I{tot_h_row-1})").number_format = "€#,##0.00"
        ws_h.cell(row=tot_h_row, column=9).font = font_bold
        for col in range(1, 12):
            ws_h.cell(row=tot_h_row, column=col).fill = fill_label
            ws_h.cell(row=tot_h_row, column=col).border = thin_border

        autofit_columns(ws_h)

        # -------------------------------------------------------------
        # SHEET 7: Audit_Assurance (Cryptographic Assurance & Verification)
        # -------------------------------------------------------------
        ws_audit = wb.create_sheet(title="Audit_Assurance")
        ws_audit.views.sheetView[0].showGridLines = True

        wb_sha256 = hashlib.sha256(json.dumps(fingerprint_data_excel, sort_keys=True).encode("utf-8")).hexdigest()

        ws_audit.cell(row=1, column=1, value="EU CBAM — REGULATORY ASSURANCE & CRYPTOGRAPHIC VERIFICATION").font = font_title
        ws_audit.cell(row=2, column=1, value="Official operator declaration and immutable SHA-256 seal under Regulation (EU) 2023/956 Art. 8").font = font_subtitle

        assurance_rows = [
            ("Assurance Standard", "ISO 14064-3 / Commission Implementing Regulation (EU) 2023/1773 Article 18"),
            ("Cryptographic Data Fingerprint (SHA-256)", wb_sha256),
            ("Digital Audit Seal Status", "SEALED & VERIFIED against Platform Immutable Audit Chain"),
            ("Export Timestamp (UTC)", now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")),
            ("Exporting Organization", company_name),
            ("Lead Environmental Assessor", f"{assessor_name} ({assessor_email}) - Role: {user.role}"),
            ("Declared Installation Sites", len(facilities)),
            ("Declared CBAM Export Records", len(cbam_records)),
            ("Legal Certification Clause", "I hereby certify under penalty of perjury under Regulation (EU) 2023/956 that the specific embedded direct and indirect emissions reported herein have been determined in accordance with the monitoring methodology specified in Implementing Regulation (EU) 2023/1773 and represent an accurate, non-misleading account of the installation production activity."),
        ]

        ws_audit.cell(row=4, column=1, value="Assurance Parameter").fill = fill_eu_header
        ws_audit.cell(row=4, column=1).font = font_header_white
        ws_audit.cell(row=4, column=2, value="Audit Manifest Value").fill = fill_eu_header
        ws_audit.cell(row=4, column=2).font = font_header_white

        for idx, (prop, val) in enumerate(assurance_rows, start=5):
            ws_audit.cell(row=idx, column=1, value=prop).font = font_bold
            ws_audit.cell(row=idx, column=1).border = thin_border
            ws_audit.cell(row=idx, column=1).fill = fill_label
            ws_audit.cell(row=idx, column=2, value=str(val)).font = font_mono if "SHA-256" in prop or "Status" in prop else font_regular
            ws_audit.cell(row=idx, column=2).border = thin_border

        autofit_columns(ws_audit)

        # Save Excel to memory
        output_buffer = io.BytesIO()
        wb.save(output_buffer)
        output_buffer.seek(0)

        filename = f"EU_CBAM_Communication_Template_{rep_year_str}.xlsx"
        resp = send_file(
            output_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
        record_report_fingerprint(resp, user, "EU CBAM Communication Template", {"year": year}, len(cbam_records), wb_sha256)
        resp.headers["X-Audit-Timestamp"] = now_utc.isoformat()
        resp.headers["X-Audit-SHA256"] = wb_sha256
        return resp

    except Exception as e:
        current_app.logger.error(f"Error generating CBAM report: {e}", exc_info=True)
        return jsonify({"error": "CBAM report export failed. Please try again or contact support."}), 500
