"""CBAM attributed emissions of an installation (Implementing Regulation (EU) 2023/1773 Annex III; Regulation (EU)
2023/956 Annex I). Audit 2026-11 F-RPT-26 / F-RPT-27: the direct specific embedded emissions were the facility's
whole Scope 1 CO2e (CH4 included) over each good's activity level, so two goods carried the installation twice, and
the indirect ones added steam / heat and accepted market-based Scope 2.
"""
from sqlalchemy import func

from extensions import db

_N2O_GOODS = ("2808", "2814", "31")  # nitric acid, ammonia, fertilisers: N2O is a CBAM gas for these (Annex I)


def _digits(cn_code):
    return "".join(ch for ch in str(cn_code or "") if ch.isdigit())


def installation_cbam_ghg_t(facility_id, year, cn_code):
    """t CO2e of the CBAM greenhouse gases the installation emitted in the year (Verified, test rows out)."""
    from calculations.constants import get_active_gwp
    from models import Emission
    from services.dashboard_filters import exclude_test_rows

    q = exclude_test_rows(db.session.query(func.coalesce(func.sum(Emission.co2_emissions), 0.0),
                                           func.coalesce(func.sum(Emission.n2o_emissions), 0.0))
                          .filter(Emission.facility_id == facility_id, Emission.year == year,
                                  Emission.status == "Verified"), Emission)
    co2, n2o = q.one()
    total = float(co2 or 0.0)
    if _digits(cn_code).startswith(_N2O_GOODS):
        total += float(n2o or 0.0) * float(get_active_gwp()["N2O"])
    return total


def installation_electricity_t(facility_id, year):
    """t CO2e of the electricity the installation consumed, location-based (grid factor)."""
    from models import Scope2Emission
    from services.dashboard_filters import exclude_test_rows

    q = exclude_test_rows(db.session.query(func.coalesce(func.sum(
        func.coalesce(Scope2Emission.co2e_location_based, Scope2Emission.co2e)), 0.0))
        .filter(Scope2Emission.facility_id == facility_id, Scope2Emission.year == year,
                Scope2Emission.status == "Verified", func.lower(Scope2Emission.source_type).like("%electric%")),
        Scope2Emission)
    return float(q.scalar() or 0.0)


def attributed_exceeds_installation(facility_id, year, cn_code, this_good_t, installation_t, record_id=None):
    """True when the goods' direct attributed emissions (specific x activity level, one value per good) would exceed
    what the installation emitted."""
    from models import CbamProductExport

    by_good = {}
    q = CbamProductExport.query.filter_by(facility_id=facility_id, year=year)
    if record_id:
        q = q.filter(CbamProductExport.id != int(record_id))
    for r in q.order_by(CbamProductExport.id).all():
        if _digits(r.cn_code) == _digits(cn_code):
            continue
        by_good[_digits(r.cn_code)] = float(r.specific_embedded_direct or 0.0) * float(r.activity_level_tonnes or 0.0)
    return sum(by_good.values()) + float(this_good_t) > float(installation_t) * (1 + 1e-6) + 1e-9
