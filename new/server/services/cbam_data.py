"""CBAM declaration data shared by the XML and Excel exports (GET /api/reports/cbam-export & cbam-validate).

CbamContext, RecordFigures, and validation helpers compute consistent period bounds,
Scope 1/2 provenance, CCS deductions, Article 9 origin carbon prices, and ReportingMetadata assurance.
"""
import re
from datetime import datetime, timezone

from models import Emission, ProductionData, ReportingMetadata, Scope2Emission

_QUARTER_BOUNDS = {
    "Q1": ("01-01", "03-31"),
    "Q2": ("04-01", "06-30"),
    "Q3": ("07-01", "09-30"),
    "Q4": ("10-01", "12-31"),
}


def cbam_period_dates(year_filter, quarter, records=()):
    """Return (period_start_iso, period_end_iso) aligned with year_filter and quarter."""
    years = sorted({int(r.year) for r in records if getattr(r, "year", None)})
    if year_filter:
        y_start = y_end = str(year_filter)
    elif years:
        y_start, y_end = str(years[0]), str(years[-1])
    else:
        cur_y = str(datetime.now(timezone.utc).year)
        y_start, y_end = "2024", max(cur_y, "2026")

    q = (quarter or "Q1-Q4").upper()
    if q in _QUARTER_BOUNDS and y_start == y_end:
        md_s, md_e = _QUARTER_BOUNDS[q]
        return f"{y_start}-{md_s}", f"{y_end}-{md_e}"
    if q in _QUARTER_BOUNDS:
        md_s, md_e = _QUARTER_BOUNDS[q]
        return f"{y_start}-{md_s}", f"{y_end}-{md_e}"
    return f"{y_start}-01-01", f"{y_end}-12-31"


def _cbam_family(process_type):
    """combustion / process / flaring_venting family of a Scope 1 process type."""
    from calculations.uncertainty import PROCESS_CATEGORY

    pt = str(process_type or "").strip().lower()
    cat = PROCESS_CATEGORY.get(pt)
    if cat == "combustion":
        return "combustion"
    if cat in ("flaring", "vented", "fugitive") or "flar" in pt or "vent" in pt or "fugitive" in pt:
        return "flaring_venting"
    return "process"


def _get_facility_scope1_split(facility_id, year=None, statuses=("Verified",)):
    """
    Computes genuine combustion, process, and flaring/venting splits
    from the Emission table for the given facility and year (records of the report's statuses).
    Returns (comb_pct, proc_pct, flare_pct, has_real_data).
    """
    q = Emission.query.filter(Emission.facility_id == facility_id, Emission.status.in_(statuses),
                              Emission.is_test == False)  # noqa: E712  test rows excluded (BA-011)
    if year:
        q = q.filter_by(year=year)
    records = q.all()
    sums = {"combustion": 0.0, "process": 0.0, "flaring_venting": 0.0}
    for e in records:
        sums[_cbam_family(e.process_type)] += float(e.co2e_total or 0.0)
    total = sum(sums.values())
    if total <= 0:
        return (0.0, 1.0, 0.0, False)
    return (sums["combustion"] / total, sums["process"] / total, sums["flaring_venting"] / total, True)


_OIL_T_PER_BBL = 0.1364   # crude, ~33 API
_GAS_T_PER_MSCF = 0.0210  # natural gas, ~0.74 kg/Sm3


def _production_tonnes(amount, unit, kind, api_gravity=None):
    """Tonnes of one production amount in its own unit. None when the unit cannot be read."""
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
        oil_t_bbl = 0.158987294928 * (141.5 / max(0.1, float(api_gravity) + 131.5)) if api_gravity else _OIL_T_PER_BBL
        return m3 / 0.158987294928 * oil_t_bbl
    return m3 / 28.316846592 * _GAS_T_PER_MSCF


def _get_facility_production_tonnes(facility_id, year=None, declared_export_qty=0.0):
    """
    Fetches genuine annual facility production from ProductionData, each amount in its own unit.
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
    return (float(declared_export_qty or 0.0), False)


def _get_facility_scope2_metrics(facility_id, year=None, country="Not Specified", statuses=("Verified",)):
    """
    Queries Scope2Emission for actual electricity consumption and grid emission factor.
    Returns (total_mwh, grid_ef or None, supplier_label, has_real_data).
    """
    q = Scope2Emission.query.filter(Scope2Emission.facility_id == facility_id, Scope2Emission.status.in_(statuses))
    if year:
        q = q.filter_by(year=year)
    s2_records = q.all()
    country_label = country if (country and country != "Not Specified") else "National"
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
        supplier = grid_reg or f"{country_label} Grid / Utility"
        if elec_kwh > 0 and grid_ef and grid_ef > 0:
            return (elec_kwh / 1000.0, grid_ef, supplier, True)

    return (0.0, None, f"{country_label} Grid Operator", False)


def catalog_grid_factor(country):
    """(catalog name, t CO2e / MWh at the active GWP set, source) of a country's grid in electricity_factors."""
    if not country or country == "Not Specified":
        return None
    from electricity_factors import grid_entry, grid_factor_kg_co2e_per_kwh

    name, entry = grid_entry(country)
    if not entry:
        return None
    return name, grid_factor_kg_co2e_per_kwh(entry), entry.get("source") or ""


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


class CbamContext:
    """The declaring account, reporting period, assurance metadata, facilities, and export records."""

    def __init__(self, user, year_filter, statuses, facilities, records, safe, quarter="Q1-Q4"):
        self.user = user
        self.year_filter = year_filter
        self.statuses = statuses
        self.facilities = facilities
        self.records = records
        self.safe = safe
        self.quarter = quarter or "Q1-Q4"
        self.company_name = getattr(user, "orgName", None) or ""
        self.assessor_name = getattr(user, "fullName", None) or ""
        self.assessor_email = getattr(user, "email", None) or ""
        self.now_utc = datetime.now(timezone.utc)
        self.rep_year_str = str(year_filter) if year_filter else "2024-2026"
        self.period_start, self.period_end = cbam_period_dates(year_filter, self.quarter, records)

        first_fac = next(iter(facilities.values()), None) if facilities else None
        raw_user_loc = getattr(user, "location", None) or ""
        if str(raw_user_loc).strip().lower() in ("global", "all"):
            raw_user_loc = ""
        self.op_country = getattr(first_fac, "country", None) or raw_user_loc or "Not Specified"
        oc = self.op_country
        if "algeria" in oc.lower():
            self.op_iso = "DZ"
        elif oc != "Not Specified" and len(oc) >= 2:
            self.op_iso = oc[:2].upper()
        else:
            self.op_iso = "XX"

        clean_org = re.sub(r"[^A-Za-z0-9]", "", self.company_name).upper()[:10] or "OPERATOR"
        self.op_id = f"{self.op_iso}-{clean_org}-001"

        meta = ReportingMetadata.query.filter_by(year=year_filter).first() if year_filter else None
        if meta is None:
            meta = ReportingMetadata.query.order_by(ReportingMetadata.year.desc()).first()
        self.assurance_level = (meta.assurance_level.strip() if meta and meta.assurance_level else "") or "Self-Declared / Unverified"
        self.assurance_provider = (meta.assurance_provider.strip() if meta and meta.assurance_provider else "")

    def facility(self, r):
        return self.facilities.get(r.facility_id)

    def fac_name(self, r):
        fac = self.facility(r)
        return fac.name if fac else f"Facility {r.facility_id}"

    def fac_code(self, r):
        fac = self.facility(r)
        return fac.code if fac and fac.code else f"{self.op_iso}-FAC-{r.facility_id:03d}"

    def fac_country(self, r):
        return getattr(self.facility(r), "country", None) or self.op_country


class RecordFigures:
    """Quantity and specific embedded emissions (tCO2e/t) of one export record."""

    def __init__(self, r):
        self.qty = float(getattr(r, "quantity_tonnes", 0.0) or 0.0)
        self.direct = float(getattr(r, "specific_embedded_direct", 0.0) or 0.0)
        self.indirect = float(getattr(r, "specific_embedded_indirect", 0.0) or 0.0)
        self.captured_co2 = float(getattr(r, "captured_co2_tonnes", 0.0) or 0.0)
        self.ccs_reduction_per_t = (self.captured_co2 / self.qty) if (self.qty > 0 and self.captured_co2 > 0) else 0.0
        self.gross_direct = self.direct + self.ccs_reduction_per_t
        is_complex = bool(getattr(r, "is_complex_good", False))
        self.precursor_direct = (float(getattr(r, "precursor_ratio", 0.0) or 0.0) * float(getattr(r, "precursor_see_dir", 0.0) or 0.0)) if is_complex else 0.0
        self.precursor_indirect = (float(getattr(r, "precursor_ratio", 0.0) or 0.0) * float(getattr(r, "precursor_see_indir", 0.0) or 0.0)) if is_complex else 0.0
        self.precursor = self.precursor_direct + self.precursor_indirect
        self.total_see = self.direct + self.indirect + self.precursor
        self.total_emissions = self.qty * self.total_see


def fingerprint_row(ctx, r, fig):
    """The values of a record that the declaration's SHA-256 fingerprint covers."""
    return {
        "id": r.id,
        "fac": ctx.fac_code(r),
        "cn": r.cn_code,
        "qty": fig.qty,
        "direct_see": fig.direct,
        "indirect_see": fig.indirect,
        "captured_co2": fig.captured_co2,
        "precursor_contrib": fig.precursor,
        "carbon_price_paid": float(r.carbon_price_paid_eur or 0.0),
        "total_emissions": fig.total_emissions,
    }


def quarter_of(r):
    return r.quarter or f"Q{(r.month - 1) // 3 + 1 if r.month else 1}"


def _record_field_errors(ctx, r, fig, country) -> list:
    """Declaration fields of one record that DG TAXUD requires (CN code, quantity, destination, CCS, Art. 9, Art. 7)."""
    errors = []
    cn_digits = re.sub(r"\s+", "", str(r.cn_code or ""))
    if not re.match(r"^\d{6,8}$", cn_digits):
        errors.append({
            "record_id": r.id,
            "field": "cn_code",
            "message": f"Record #{r.id} ({r.product_name}): CN code '{r.cn_code}' must contain 6 or 8 digits.",
        })

    if fig.qty <= 0:
        errors.append({
            "record_id": r.id,
            "field": "quantity_tonnes",
            "message": f"Record #{r.id} ({r.product_name}): export quantity must be greater than zero.",
        })

    if not (r.export_destination or "").strip():
        errors.append({
            "record_id": r.id,
            "field": "export_destination",
            "message": f"Record #{r.id} ({r.product_name}): export destination is missing.",
        })

    if fig.captured_co2 > 0 and not (r.ccs_certificate_id or "").strip():
        errors.append({
            "record_id": r.id,
            "field": "ccs_certificate_id",
            "message": f"Record #{r.id} ({r.product_name}): CCS geological storage certificate ID is required when captured CO2 > 0.",
        })

    if (r.carbon_price_paid_eur or 0.0) > 0 and not (r.carbon_price_legal_ref or "").strip():
        errors.append({
            "record_id": r.id,
            "field": "carbon_price_legal_ref",
            "message": f"Record #{r.id} ({r.product_name}): Article 9 origin legal basis reference is required when carbon price paid > 0.",
        })

    if r.is_complex_good:
        if not (r.precursor_name or "").strip() or not (r.precursor_cn_code or "").strip() or float(r.precursor_ratio or 0.0) <= 0:
            errors.append({
                "record_id": r.id,
                "field": "precursor",
                "message": f"Record #{r.id} ({r.product_name}): complex goods require precursor name, CN code, and positive consumption ratio.",
            })

    if not country or country == "Not Specified":
        errors.append({
            "record_id": r.id,
            "field": "country",
            "message": f"Record #{r.id} ({ctx.fac_name(r)}): facility country of origin is not set.",
        })
    return errors


def _record_provenance_warnings(ctx, r, country):
    """(warnings, has Scope 1 data, has Scope 2 data or a catalog grid factor) of one record."""
    warnings = []
    _c, _p, _f, has_s1 = _get_facility_scope1_split(r.facility_id, r.year, ctx.statuses)
    if not has_s1:
        warnings.append({
            "record_id": r.id,
            "field": "scope1_provenance",
            "message": f"Record #{r.id} ({ctx.fac_name(r)} {r.year}): no verified Scope 1 emissions found; split defaults to process-only.",
        })

    _mwh, _ef, _sup, has_s2 = _get_facility_scope2_metrics(r.facility_id, r.year, country, ctx.statuses)
    if not has_s2 and catalog_grid_factor(country) is None:
        warnings.append({
            "record_id": r.id,
            "field": "scope2_provenance",
            "message": f"Record #{r.id} ({ctx.fac_name(r)} {r.year}): no verified Scope 2 data and no grid factor in catalog for {country}.",
        })
    return warnings, has_s1, has_s2


def _validated_record_row(ctx, r, fig, has_s1, has_s2) -> dict:
    """The per-record figures returned with the validation."""
    return {
        "id": r.id,
        "facility_id": r.facility_id,
        "facility_name": ctx.fac_name(r),
        "product_name": r.product_name,
        "cn_code": r.cn_code,
        "year": r.year,
        "quarter": quarter_of(r),
        "quantity_tonnes": round(fig.qty, 2),
        "gross_direct_see": round(fig.gross_direct, 4),
        "ccs_reduction_see": round(fig.ccs_reduction_per_t, 4),
        "net_direct_see": round(fig.direct, 4),
        "indirect_see": round(fig.indirect, 4),
        "precursor_see": round(fig.precursor, 4),
        "total_see": round(fig.total_see, 4),
        "total_embedded_tco2e": round(fig.total_emissions, 2),
        "has_scope1_data": has_s1,
        "has_scope2_data": has_s2,
    }


def _cbam_readiness_checks(ctx, errors, total_ccs, total_tax, complex_count) -> list:
    """Pass / fail / warning summary of the declaration, from the errors found."""
    cn_ok = not any(e["field"] == "cn_code" for e in errors)
    ccs_ok = not any(e["field"] in ("ccs_certificate_id", "carbon_price_legal_ref") for e in errors)
    prec_ok = not any(e["field"] == "precursor" for e in errors)
    return [
        {
            "id": "records_present",
            "label": "Quarter & Facility Export Coverage",
            "status": "pass" if ctx.records else "fail",
            "detail": f"{len(ctx.records)} export record(s) in {ctx.quarter} ({ctx.period_start} to {ctx.period_end})",
        },
        {
            "id": "cn_and_qty",
            "label": "CN Codes (6-8 digit) & Export Quantities",
            "status": "pass" if (ctx.records and cn_ok and not any(e["field"] == "quantity_tonnes" for e in errors)) else ("fail" if ctx.records else "warning"),
            "detail": "All product CN codes and quantities valid" if cn_ok else "One or more records have invalid CN codes or zero quantity",
        },
        {
            "id": "ccs_and_art9",
            "label": "CCS Certificates & Article 9 Carbon Price Proofs",
            "status": "pass" if ccs_ok else "fail",
            "detail": f"{round(total_ccs, 1)} tCO2 captured; EUR {round(total_tax, 2):,.2f} origin carbon price documented" if ccs_ok else "Missing required CCS certificate ID or Article 9 legal reference",
        },
        {
            "id": "complex_precursors",
            "label": "Article 7 Complex Goods Precursors",
            "status": "pass" if prec_ok else "fail",
            "detail": f"{complex_count} complex product declaration(s) validated" if prec_ok else "Incomplete upstream precursor ratio or CN code",
        },
        {
            "id": "assurance_meta",
            "label": "Reporting Assurance Metadata",
            "status": "pass" if ctx.assurance_level != "Self-Declared / Unverified" else "warning",
            "detail": f"{ctx.assurance_level}" + (f" ({ctx.assurance_provider})" if ctx.assurance_provider else ""),
        },
    ]


def validate_cbam_context(ctx) -> dict:
    """
    Pre-export completeness & DG TAXUD schema readiness validation for CBAM records.
    Returns {ready, quarter, period_start, period_end, year, assurance_level,
             record_count, errors, warnings, checks, summary, records}.
    """
    errors = []
    warnings = []
    checks = []

    if not ctx.records:
        errors.append({
            "record_id": None,
            "field": "records",
            "message": "No CBAM export records match the selected year/quarter/facility filters.",
        })

    if ctx.assurance_level == "Self-Declared / Unverified":
        warnings.append({
            "record_id": None,
            "field": "assurance_level",
            "message": "No ReportingMetadata assurance level configured; declaration defaults to 'Self-Declared / Unverified'.",
        })

    total_qty = 0.0
    total_emb = 0.0
    total_ccs = 0.0
    total_tax = 0.0
    complex_count = 0
    validated_records = []

    for r in ctx.records:
        fig = RecordFigures(r)
        total_qty += fig.qty
        total_emb += fig.total_emissions
        total_ccs += fig.captured_co2
        total_tax += float(r.carbon_price_paid_eur or 0.0) * fig.qty
        if r.is_complex_good:
            complex_count += 1

        country = ctx.fac_country(r)
        errors.extend(_record_field_errors(ctx, r, fig, country))
        rec_warnings, has_s1, has_s2 = _record_provenance_warnings(ctx, r, country)
        warnings.extend(rec_warnings)
        validated_records.append(_validated_record_row(ctx, r, fig, has_s1, has_s2))

    checks.extend(_cbam_readiness_checks(ctx, errors, total_ccs, total_tax, complex_count))

    return {
        "ready": len(errors) == 0,
        "quarter": ctx.quarter,
        "period_start": ctx.period_start,
        "period_end": ctx.period_end,
        "year": ctx.rep_year_str,
        "assurance_level": ctx.assurance_level,
        "assurance_provider": ctx.assurance_provider,
        "record_count": len(ctx.records),
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "summary": {
            "total_quantity_tonnes": round(total_qty, 2),
            "total_embedded_emissions_tco2e": round(total_emb, 2),
            "total_captured_co2_tonnes": round(total_ccs, 2),
            "total_carbon_price_paid_eur": round(total_tax, 2),
            "complex_goods_count": complex_count,
        },
        "records": validated_records,
    }
