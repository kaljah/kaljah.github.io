"""CBAM declaration data shared by the XML and Excel exports (GET /api/reports/cbam-export).

The helpers were moved unchanged from routes/reports_cbam.py on 2026-10-16 (which re-exports them);
CbamContext and record_figures hold what the two formats used to compute separately.
"""
import re
from datetime import datetime, timezone

from models import Emission, ProductionData, Scope2Emission


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
    Returns (total_mwh, grid_ef or None, supplier_label, has_real_data).
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

    # no verified Scope 2 electricity: no grid factor either (a fixed national table, Algeria 0.5820, was used
    # in its place; review 2026-10-16, as for the national report in the 2026-10-15 bug hunt)
    return (0.0, None, f"{country} National Grid Operator", False)




def catalog_grid_factor(country):
    """(catalog name, t CO2e / MWh at the active GWP set, source) of a country's grid in the Scope 2 factor
    catalog (electricity_factors), or None when the catalog has no factor for it."""
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
    """The declaring account, the reporting period and the facilities and export records in scope."""

    def __init__(self, user, year_filter, statuses, facilities, records, safe):
        self.user = user
        self.statuses = statuses
        self.facilities = facilities  # {id: Facility}
        self.records = records
        self.safe = safe  # routes.reports._safe_excel_value
        # the declaring account as it is: no invented organisation, name or address
        self.company_name = getattr(user, "orgName", None) or ""
        self.assessor_name = getattr(user, "fullName", None) or ""
        self.assessor_email = getattr(user, "email", None) or ""
        self.now_utc = datetime.now(timezone.utc)
        self.rep_year_str = str(year_filter) if year_filter else "2024-2026"
        first_fac = next(iter(facilities.values()), None) if facilities else None
        self.op_country = getattr(first_fac, "country", None) or getattr(user, "location", None) or "Algeria"
        oc = self.op_country
        self.op_iso = "DZ" if "algeria" in oc.lower() else (oc[:2].upper() if len(oc) >= 2 else "DZ")
        clean_org = re.sub(r"[^A-Za-z0-9]", "", self.company_name).upper()[:10] or "OPERATOR"
        self.op_id = f"{self.op_iso}-{clean_org}-001"

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
        self.qty = float(r.quantity_tonnes or 0.0)
        self.direct = float(r.specific_embedded_direct or 0.0)
        self.indirect = float(r.specific_embedded_indirect or 0.0)
        self.precursor = ((float(r.precursor_ratio or 0.0)
                           * (float(r.precursor_see_dir or 0.0) + float(r.precursor_see_indir or 0.0)))
                          if r.is_complex_good else 0.0)
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
        "captured_co2": float(r.captured_co2_tonnes or 0.0),
        "precursor_contrib": fig.precursor,
        "carbon_price_paid": float(r.carbon_price_paid_eur or 0.0),
        "total_emissions": fig.total_emissions,
    }


def quarter_of(r):
    return r.quarter or f"Q{(r.month - 1) // 3 + 1 if r.month else 1}"
