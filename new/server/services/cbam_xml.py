"""EU CBAM transitional registry XML declaration (GET /api/reports/cbam-export?format=xml).

Generates enriched DG TAXUD compliant XML with explicit reporting period dates,
Scope 1/2 provenance splits, Gross/CCS/Net specific embedded breakdown,
Article 7 complex precursors (never <PrecursorContribution>), and ReportingMetadata assurance.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

from services.cbam_data import (  # noqa: E402
    country_iso,
    RecordFigures,
    _clean_xml_text,
    _get_facility_production_tonnes,
    _get_facility_scope1_split,
    _get_facility_scope2_metrics,
    catalog_grid_factor,
    fingerprint_row,
    get_cbam_aggregated_category,
    get_cbam_production_route,
    quarter_of,
)


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
    _sub(period, "PeriodStart", ctx.period_start)
    _sub(period, "PeriodEnd", ctx.period_end)
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
        # only recorded values: no invented id, activity or 0 / 0 coordinates (audit 2026-11 F-E2E-06)
        _sub(inst, "InstallationId", _clean_xml_text(fac.code or f"FAC-{fac.id:03d}"))
        _sub(inst, "Name", _clean_xml_text(fac.name))
        _sub(inst, "Country", _clean_xml_text(country_iso(fac.country) or "Not provided"))
        _sub(inst, "EconomicActivity", _clean_xml_text(fac.activity or "Not provided"))
        if fac.latitude is not None and fac.longitude is not None:
            coords = ET.SubElement(inst, "Coordinates")
            _sub(coords, "Latitude", f"{fac.latitude:.6f}")
            _sub(coords, "Longitude", f"{fac.longitude:.6f}")


def _ccs(good, r):
    """Carbon capture and storage (blue hydrogen / ammonia)."""
    if (r.captured_co2_tonnes or 0.0) > 0:
        ccs = ET.SubElement(good, "CarbonCaptureAndStorage")
        _sub(ccs, "CapturedCO2Tonnes", f"{float(r.captured_co2_tonnes):.2f}", {"unit": "tCO2"})
        _sub(ccs, "StorageCertificateId",
             _clean_xml_text(r.ccs_certificate_id or "Not provided"))
        _sub(ccs, "PermanentStorageStandard", "Directive 2009/31/EC & ISO 27914 Geological Sequestration")


def _provenance(good, ctx, r, fig):
    """Scope 1 split & Scope 2 electricity provenance per installation/year."""
    total_prod, from_prod = _get_facility_production_tonnes(r.facility_id, r.year, fig.qty)
    share_pct = round((fig.qty / total_prod * 100.0), 2) if total_prod > 0 else 100.0
    prod_el = ET.SubElement(good, "ProductionBoundary")
    _sub(prod_el, "TotalInstallationProductionTonnes", f"{total_prod:.2f}", {"unit": "t"})
    _sub(prod_el, "ExportSharePct", f"{share_pct:.2f}")
    _sub(prod_el, "ProductionDataSource", "Verified ProductionData" if from_prod else "Export Quantity Fallback")

    comb_pct, proc_pct, flare_pct, has_s1 = _get_facility_scope1_split(r.facility_id, r.year, ctx.statuses)
    s1_el = ET.SubElement(good, "DirectEmissionsBreakdown")
    _sub(s1_el, "CombustionSharePct", f"{comb_pct * 100.0:.2f}")
    _sub(s1_el, "ProcessSharePct", f"{proc_pct * 100.0:.2f}")
    _sub(s1_el, "FlaringVentingSharePct", f"{flare_pct * 100.0:.2f}")
    _sub(s1_el, "HasVerifiedScope1Data", "true" if has_s1 else "false")

    country = ctx.fac_country(r)
    mwh, grid_ef, supplier, has_s2 = _get_facility_scope2_metrics(r.facility_id, r.year, country, ctx.statuses)
    basis = "Verified Scope 2 Metering"
    if not has_s2:
        cat = catalog_grid_factor(country)
        if cat:
            grid_ef = cat[1]
            basis = f"Catalog Grid Factor ({cat[0]}: {cat[2]})"
        else:
            basis = "Direct Indirect SEE Declaration (No Scope 2 / Catalog Grid Factor)"
    s2_el = ET.SubElement(good, "IndirectElectricityMetrics")
    _sub(s2_el, "ConsumedElectricityMWh", f"{mwh:.2f}", {"unit": "MWh"})
    _sub(s2_el, "GridEmissionFactor", f"{grid_ef:.4f}" if grid_ef is not None else "N/A", {"unit": "tCO2e/MWh"})
    _sub(s2_el, "ElectricitySupplier", _clean_xml_text(supplier))
    _sub(s2_el, "AccountingBasis", _clean_xml_text(basis))
    _sub(s2_el, "HasVerifiedScope2Data", "true" if has_s2 else "false")


def _embedded(good, fig):
    em = ET.SubElement(good, "SpecificEmbeddedEmissions")
    _sub(em, "GrossDirect", f"{fig.gross_direct:.4f}", {"unit": "tCO2e/t"})
    _sub(em, "CapturedCO2Reduction", f"{fig.ccs_reduction_per_t:.4f}", {"unit": "tCO2e/t"})
    _sub(em, "Direct", f"{fig.direct:.4f}", {"unit": "tCO2e/t"})
    _sub(em, "Indirect", f"{fig.indirect:.4f}", {"unit": "tCO2e/t"})
    _sub(em, "Total", f"{fig.total_see:.4f}", {"unit": "tCO2e/t"})
    _sub(good, "TotalEmbeddedEmissions", f"{fig.total_emissions:.2f}", {"unit": "tCO2e"})


def _precursors(good, r, fig):
    """Article 7 complex goods (uses TotalPrecursorContribution — never <PrecursorContribution>)."""
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
    # the entered legal act only (a "<country> Environmental / Carbon Fiscality" basis was invented) and no claim
    # about rebates, which are not recorded (it printed "None"; audit 2026-11 F-GSTD-04)
    _sub(price, "LegalBasis", _clean_xml_text(r.carbon_price_legal_ref or "Not provided"))
    _sub(price, "RebateOrCompensation", "Not provided")


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
    _provenance(good, ctx, r, fig)
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
    user_role = getattr(ctx.user, "role", "Lead Assessor") if ctx.user else "Lead Assessor"
    _sub(assurance, "LeadAssessor", _clean_xml_text(f"{ctx.assessor_name} ({user_role})"))
    _sub(assurance, "AssuranceLevel", _clean_xml_text(ctx.assurance_level))
    if ctx.assurance_provider:
        _sub(assurance, "AssuranceProvider", _clean_xml_text(ctx.assurance_provider))
    pretty = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="  ", encoding="utf-8")
    return pretty, data_hash
