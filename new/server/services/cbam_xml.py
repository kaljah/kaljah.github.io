"""EU CBAM transitional registry XML declaration (GET /api/reports/cbam-export?format=xml).

Split out of routes/reports_cbam.export_cbam_report on 2026-10-16; the XML is unchanged.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

from services.cbam_data import (RecordFigures, _clean_xml_text, fingerprint_row, get_cbam_aggregated_category,
                                get_cbam_production_route, quarter_of)


def _sub(parent, tag, text, attrs=None):
    el = ET.SubElement(parent, tag, attrs or {})
    el.text = text
    return el


def _header(root, ctx, quarter):
    header = ET.SubElement(root, "Header")
    _sub(header, "MessageId", f"CBAM-{ctx.op_iso}-{ctx.rep_year_str}-{ctx.now_utc.strftime('%Y%m%d%H%M%S')}")
    _sub(header, "CreationTimestamp", ctx.now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"))
    _sub(header, "LegalReference", "Regulation (EU) 2023/956 & Implementing Regulation (EU) 2023/1773")
    period = ET.SubElement(header, "ReportingPeriod")
    _sub(period, "Year", ctx.rep_year_str)
    _sub(period, "Quarter", quarter)
    _sub(period, "PeriodType", "Transitional Period Declaration")


def _declarant(root, ctx):
    declarant = ET.SubElement(root, "Declarant")
    _sub(declarant, "EORINumber", _clean_xml_text(ctx.op_id))
    _sub(declarant, "OperatorName", _clean_xml_text(ctx.company_name))
    _sub(declarant, "Role", "Operator of Non-EU Installation")
    _sub(declarant, "Country", _clean_xml_text(ctx.op_iso))
    _sub(declarant, "ContactEmail", _clean_xml_text(ctx.assessor_email))


def _installations(root, ctx):
    """The installations the records come from (every facility in scope when there are no records)."""
    installations = ET.SubElement(root, "Installations")
    reported = set(r.facility_id for r in ctx.records) if ctx.records else set(ctx.facilities.keys())
    for fid in sorted(reported):
        fac = ctx.facilities.get(fid)
        if not fac:
            continue
        inst = ET.SubElement(installations, "Installation")
        _sub(inst, "InstallationId", _clean_xml_text(fac.code or f"{ctx.op_iso}-FAC-{fac.id:03d}"))
        _sub(inst, "Name", _clean_xml_text(fac.name))
        _sub(inst, "Country", _clean_xml_text(fac.country or ctx.op_iso))
        _sub(inst, "EconomicActivity", _clean_xml_text(fac.activity or "Petrochemical & Refining"))
        coords = ET.SubElement(inst, "Coordinates")
        _sub(coords, "Latitude", f"{fac.latitude:.6f}" if fac.latitude is not None else "0.000000")
        _sub(coords, "Longitude", f"{fac.longitude:.6f}" if fac.longitude is not None else "0.000000")


def _ccs(good, r):
    """Carbon capture and storage (blue hydrogen / ammonia)."""
    if (r.captured_co2_tonnes or 0.0) > 0:
        ccs = ET.SubElement(good, "CarbonCaptureAndStorage")
        _sub(ccs, "CapturedCO2Tonnes", f"{float(r.captured_co2_tonnes):.2f}", {"unit": "tCO2"})
        _sub(ccs, "StorageCertificateId",
             _clean_xml_text(r.ccs_certificate_id or "Self-Declared / Pending Storage Certificate"))
        _sub(ccs, "PermanentStorageStandard", "Directive 2009/31/EC & ISO 27914 Geological Sequestration")


def _embedded(good, fig):
    em = ET.SubElement(good, "SpecificEmbeddedEmissions")
    _sub(em, "Direct", f"{fig.direct:.4f}", {"unit": "tCO2e/t"})
    _sub(em, "Indirect", f"{fig.indirect:.4f}", {"unit": "tCO2e/t"})
    if fig.precursor > 0:
        _sub(em, "PrecursorContribution", f"{fig.precursor:.4f}", {"unit": "tCO2e/t"})
    _sub(em, "Total", f"{fig.total_see:.4f}", {"unit": "tCO2e/t"})
    _sub(good, "TotalEmbeddedEmissions", f"{fig.total_emissions:.2f}", {"unit": "tCO2e"})


def _precursors(good, r, fig):
    """Article 7 complex goods."""
    _sub(good, "IsComplexGood", "true" if r.is_complex_good else "false")
    if r.is_complex_good and r.precursor_name:
        prec = ET.SubElement(ET.SubElement(good, "Precursors"), "Precursor")
        _sub(prec, "PrecursorName", _clean_xml_text(r.precursor_name))
        _sub(prec, "PrecursorCNCode", _clean_xml_text(r.precursor_cn_code))
        _sub(prec, "ConsumptionRatio", f"{float(r.precursor_ratio or 0.0):.4f}", {"unit": "t/t"})
        prec_em = ET.SubElement(prec, "PrecursorSpecificEmissions")
        _sub(prec_em, "Direct", f"{float(r.precursor_see_dir or 0.0):.4f}", {"unit": "tCO2e/t"})
        _sub(prec_em, "Indirect", f"{float(r.precursor_see_indir or 0.0):.4f}", {"unit": "tCO2e/t"})
        _sub(prec_em, "TotalPrecursorContribution", f"{fig.precursor:.4f}", {"unit": "tCO2e/t"})


def _carbon_price(good, r, fig, country):
    """Article 9 carbon price paid in the country of origin."""
    price = ET.SubElement(good, "CarbonPricePaidInCountryOfOrigin")
    _sub(price, "Currency", "EUR")
    _sub(price, "AmountPerTonne", f"{float(r.carbon_price_paid_eur or 0.0):.2f}", {"unit": "EUR/t"})
    _sub(price, "TotalAmountPaidEUR", f"{(float(r.carbon_price_paid_eur or 0.0) * fig.qty):.2f}")
    legal_ref = r.carbon_price_legal_ref or (
        f"{country} Environmental / Carbon Fiscality" if (r.carbon_price_paid_eur or 0) > 0 else "None")
    _sub(price, "LegalBasis", _clean_xml_text(legal_ref))
    _sub(price, "RebateOrCompensation", "None")


def _good(goods, ctx, r, fig):
    good = ET.SubElement(goods, "Good")
    _sub(good, "RecordId", str(r.id))
    _sub(good, "InstallationCode", _clean_xml_text(ctx.fac_code(r)))
    _sub(good, "InstallationName", _clean_xml_text(ctx.fac_name(r)))
    _sub(good, "CNCode", _clean_xml_text(r.cn_code))
    _sub(good, "CommercialDescription", _clean_xml_text(r.product_name))
    _sub(good, "AggregatedCategory", _clean_xml_text(get_cbam_aggregated_category(r.cn_code, r.product_name)))
    _sub(good, "ProductionRoute", _clean_xml_text(get_cbam_production_route(r.cn_code, r.product_name)))
    _sub(good, "Year", str(r.year))
    _sub(good, "Month", str(r.month))
    _sub(good, "Quarter", _clean_xml_text(quarter_of(r)))
    _sub(good, "QuantityTonnes", f"{fig.qty:.2f}")
    _sub(good, "ExportDestination", _clean_xml_text(r.export_destination or "EU"))
    _ccs(good, r)
    _embedded(good, fig)
    _precursors(good, r, fig)
    _carbon_price(good, r, fig, ctx.fac_country(r))


def build_xml(ctx, quarter):
    """(pretty-printed XML bytes, SHA-256 fingerprint of the declared values)."""
    root = ET.Element("CBAMDeclaration", {
        "xmlns": "urn:eu:taxud:cbam:v1",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "version": "1.0",
    })
    _header(root, ctx, quarter)
    _declarant(root, ctx)
    _installations(root, ctx)
    goods = ET.SubElement(root, "GoodsExported")
    fingerprint = []
    for r in ctx.records:
        fig = RecordFigures(r)
        _good(goods, ctx, r, fig)
        fingerprint.append(fingerprint_row(ctx, r, fig))
    data_hash = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode("utf-8")).hexdigest()
    assurance = ET.SubElement(root, "AuditAssurance")
    _sub(assurance, "VerificationStandard", "ISO 14064-3 / Implementing Regulation (EU) 2023/1773 Art. 18")
    _sub(assurance, "SHA256DataFingerprint", data_hash)
    _sub(assurance, "LeadAssessor", f"{ctx.assessor_name} ({ctx.user.role})")
    _sub(assurance, "AssuranceLevel", "Reasonable Assurance")
    pretty = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="  ", encoding="utf-8")
    return pretty, data_hash
