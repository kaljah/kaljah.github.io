import re

path = 'new/server/services/intensity.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Ogmp check and level call
old_chunk = """    else:
        variance, variance_flag, rec_status, ratio = None, False, "No Activity", None

    level = compute_facility_ogmp_level(
        fac, year=year_value, top_down_tch4=td or None, bottom_up_tch4=bu_td_years or (total["ch4"] or None),
        bottom_up_level=_bottom_up_level(total["records"]),
    ) if fac else 1"""

new_chunk = """    else:
        variance, variance_flag, rec_status, ratio = None, False, "No Activity", None

    # Check if actual surveys have recorded discrepancies
    surveys_have_discrepancy = False
    if fac:
        try:
            from models import OgmpSurvey
            sq = OgmpSurvey.query.filter_by(facility_id=fac.id)
            if year_value and year_value != "all" and str(year_value).isdigit():
                sq = sq.filter_by(year=int(year_value))
            actual_surveys = sq.all()
            if actual_surveys:
                surveys_have_discrepancy = any(
                    (s.reconciliation_status or "").lower() == "discrepancy detected"
                    or s.variance_flag is True
                    or (s.variance_pct is not None and abs(s.variance_pct) > threshold)
                    or (float(s.bottom_up_tch4 or 0.0) == 0.0 and float(s.estimated_annual_tch4 or 0.0) > 0.0)
                    for s in actual_surveys
                )
        except Exception:
            pass

    if surveys_have_discrepancy:
        variance_flag = True
        rec_status = "Discrepancy Detected"

    level = compute_facility_ogmp_level(
        fac, year=year_value, top_down_tch4=td or None, bottom_up_tch4=bu_td_years or (total["ch4"] or None),
        reconciled_survey=(not surveys_have_discrepancy) if (td > 0 and bu_td_years > 0) else None,
        bottom_up_level=_bottom_up_level(total["records"]),
    ) if fac else 1"""

old_chunk_norm = old_chunk.replace('\r\n', '\n')
content_norm = content.replace('\r\n', '\n')

assert old_chunk_norm in content_norm, "old_chunk not found in content"
content_norm = content_norm.replace(old_chunk_norm, new_chunk.replace('\r\n', '\n'), 1)

# 2. Update pathway
old_pathway = """    if level == 5:
        pathway = "Gold Standard Achieved (Level 5)"
    elif level == 4 and loss is not None and target is not None and loss <= target:
        pathway = "Level 4 Pathway (Target Met)"
    elif cal_year <= gold_year:
        left = gold_year - cal_year
        pathway = f'On Track ({left} yr{"s" if left != 1 else ""} remaining)'
    else:
        pathway = "Overdue / Action Plan Required\""""

new_pathway = """    if level == 5 and not surveys_have_discrepancy:
        pathway = "Gold Standard Achieved (Level 5)"
    elif surveys_have_discrepancy or (level == 4 and variance_flag):
        pathway = "Level 4 (Discrepancy Detected - Remediation Required)"
    elif level == 4 and loss is not None and target is not None and loss <= target:
        pathway = "Level 4 Pathway (Target Met)"
    elif cal_year <= gold_year:
        left = gold_year - cal_year
        pathway = f'On Track ({left} yr{"s" if left != 1 else ""} remaining)'
    else:
        pathway = "Overdue / Action Plan Required\""""

assert old_pathway.replace('\r\n', '\n') in content_norm, "old_pathway not found"
content_norm = content_norm.replace(old_pathway.replace('\r\n', '\n'), new_pathway.replace('\r\n', '\n'), 1)

# 3. Update return dict keys for flaring
old_ret = """"production_rows_with_unknown_units": total["prod_unknown_units"],
        "flaring_volume": total["flaring_m3"],
        "flaring_emissions": total["flaring_t"],"""

new_ret = """"production_rows_with_unknown_units": total["prod_unknown_units"],
        "flaring_volume": total["flaring_m3"],
        "flaring_m3": total["flaring_m3"],
        "flaring_ledger_volume": total["flaring_ledger_m3"],
        "flaring_ledger_m3": total["flaring_ledger_m3"],
        "flaring_reconciled_volume": total["flaring_reconciled_m3"],
        "flaring_reconciled_m3": total["flaring_reconciled_m3"],
        "flaring_emissions": total["flaring_t"],"""

assert old_ret.replace('\r\n', '\n') in content_norm, "old_ret not found"
content_norm = content_norm.replace(old_ret.replace('\r\n', '\n'), new_ret.replace('\r\n', '\n'), 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully patched intensity.py")
