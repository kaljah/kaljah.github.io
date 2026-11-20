"""Regression tests for the clean-room calculation audit of November 2026, reports / OGMP / Scope 2 vintage batch.

Finding IDs refer to CALC_AUDIT_2026-11/REPORT.md. Expected values come from the cited documents (EPA eGRID2022 Table
1, ISO 3166-1, OGMP 2.0 Framework s4.5 and Reconciliation & L5 Guidance s3.3, Student t table), never from the engine.
"""
from types import SimpleNamespace

import pytest

from app import app
from input_validation import ValidationError


@pytest.fixture
def ctx():
    with app.app_context():
        yield


# ---------------------------------------------------------------- F-S23-09 / F-GREST-04 grid vintage by year
def test_f_s23_09_egrid2022_from_2022(ctx):
    from electricity_factors import grid_entry_for_year

    lb = 0.45359237 / 1000.0
    # eGRID2022 Table 1, CAMX: 497.4 lb CO2 / MWh
    assert grid_entry_for_year("US-CAMX (WECC California)", 2024)[1]["co2"] == pytest.approx(497.4 * lb)
    # before 2022 the Compendium Table 8-2 (eGRID2019) row stays: 0.206 kg/kWh
    assert grid_entry_for_year("US-CAMX (WECC California)", 2020)[1]["co2"] == pytest.approx(0.206)
    # U.S. average 823.1 lb/MWh; a non-U.S. grid is unchanged
    assert grid_entry_for_year("US Average", 2023)[1]["co2"] == pytest.approx(823.1 * lb)
    assert grid_entry_for_year("Germany (grid average)", 2024)[1]["co2"] == pytest.approx(0.3387)


# ---------------------------------------------------------------- F-RPT-29 ISO country codes
@pytest.mark.parametrize("name,code", [("Germany", "DE"), ("Georgia", "GE"), ("Algeria", "DZ"), ("United Kingdom", "GB"),
                                       ("de", "DE"), ("Atlantis", None)])
def test_f_rpt_29_iso_codes(name, code):
    from services.cbam_data import country_iso

    assert country_iso(name) == code


# ---------------------------------------------------------------- F-RPT-01 portfolio materiality
def _ent(i, fid, op, wi, excluded=False):
    return SimpleNamespace(id=i, facility_id=fid, entity_name=f"E{i}", asset_name="", segment="Upstream", country="",
                           operator_status=op, operating_company="", working_interest_pct=wi,
                           is_nojv_material_excluded=excluded, is_member_reported_nojv=False, exclusion_reason="")


def test_f_rpt_01_small_equity_nojv_is_immaterial_whatever_its_emissions():
    from services.ogmp_reconciliation import compute_portfolio_materiality

    # Framework s4.5: a NOJV below 5 % equity is immaterial (1,000 t at 3 % equity)
    res = compute_portfolio_materiality([_ent(1, 1, "operated", 100), _ent(2, 2, "non_operated", 3, excluded=True)],
                                        {1: 99.0, 2: 1000.0})
    row = [e for e in res["entities"] if e["id"] == 2][0]
    assert row["immaterial_nojv_below_5pct_equity"] and row["exclusion_valid"]
    assert res["meets_95pct_threshold"] is True


def test_f_rpt_01_material_assets_ranked_by_absolute_emissions():
    from services.ogmp_reconciliation import compute_portfolio_materiality

    # absolute CH4 94 t (operated) and 5 t (40 % NOJV): cumulative before the NOJV is 94.95 % < 95 % -> material
    res = compute_portfolio_materiality([_ent(1, 1, "operated", 100), _ent(2, 2, "non_operated", 40, excluded=True)],
                                        {1: 94.0, 2: 5.0})
    row = [e for e in res["entities"] if e["id"] == 2][0]
    assert row["material"] is True and row["exclusion_valid"] is False


# ---------------------------------------------------------------- F-GOGMP-08 Student t
def test_f_gogmp_08_student_t_for_two_campaigns():
    from services.ogmp_reconciliation import compute_top_down_rss

    ms = [SimpleNamespace(measurement_mode="Annualized", option_mode="Option 2", annualized_tch4=v, uncertainty_pct=30.0)
          for v in (35.04, 70.08)]
    res = compute_top_down_rss(ms, option_mode="Option 2")
    mean = (35.04 + 70.08) / 2
    s2 = ((35.04 - mean) ** 2 + (70.08 - mean) ** 2) / 1
    inter = 12.706 * (s2 / 2) ** 0.5
    rss = ((35.04 * 0.3) ** 2 + (70.08 * 0.3) ** 2) ** 0.5 / 2
    assert res["half_width_tch4"] == pytest.approx((inter ** 2 + rss ** 2) ** 0.5, rel=1e-3)


# ---------------------------------------------------------------- F-GOGMP-03 instantaneous snapshots
def test_f_gogmp_03_snapshots_give_no_annual_agreement():
    from services.ogmp_reconciliation import reconcile_l4_l5

    srcs = [SimpleNamespace(ogmp_level=4, status_flag="Quantified", ch4_tonnes=50.0, uncertainty_pct=10.0)]
    ms = [SimpleNamespace(measurement_mode="Instantaneous", option_mode="Option 1", annualized_tch4=v,
                          uncertainty_pct=30.0) for v in (35.04, 70.08)]
    res = reconcile_l4_l5(srcs, ms)
    assert res["pathway_code"] == "3" and res["reporting_level"] != 5


# ---------------------------------------------------------------- F-GOGMP-07 future target years
def test_f_gogmp_07_future_target_year():
    import datetime

    from input_validation import parse_future_year

    y = datetime.date.today().year + 5
    assert parse_future_year(y) == y
    with pytest.raises(ValidationError):
        parse_future_year(datetime.date.today().year + 100)


# ---------------------------------------------------------------- F-GUI2-07 profile matching
def test_f_gui2_07_no_substring_profile_match(ctx):
    from services.regional_profiles import REGIONAL_PROFILES, get_regional_profile

    # a "midstream" facility no longer takes a demo profile (its operator, 25 % JV equity, geology) by substring
    prof = get_regional_profile("G2-MID midstream site")
    assert prof["key"] not in REGIONAL_PROFILES


# ---------------------------------------------------------------- F-UPL-10 readable messages
def test_f_upl_10_raw_float_error_is_reworded():
    from services.import_feedback import readable_error

    msg = readable_error("Row 4: could not convert string to float: '2,5'")
    assert "is not a number" in msg and "decimal mark" in msg and "could not convert" not in msg


# ---------------------------------------------------------------- F-RPT-21 CRF categories
def test_f_rpt_21_crf_categories():
    from routes.reports_national import _crf_category

    assert _crf_category("flaring").startswith("1.B.2")
    assert _crf_category("combustion").startswith("1.A")
    assert _crf_category("hydrogen_production").startswith("2")
