path = 'new/server/services/ogmp.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """    if td > 0 and bu > 0:
        variance_pct = abs((td - bu) / bu * 100.0)
        # Check if reconciled within threshold
        is_reconciled = reconciled_survey is True or (reconciled_survey is None and variance_pct <= threshold)"""

new_block = """    if reconciled_survey is None and facility is not None:
        try:
            from flask import has_app_context
            if has_app_context():
                from models import OgmpSurvey
                sq = OgmpSurvey.query.filter_by(facility_id=facility.id)
                if year and year != "all" and str(year).isdigit():
                    sq = sq.filter_by(year=int(year))
                surveys = sq.all()
                if surveys:
                    has_discrepancy = any(
                        (s.reconciliation_status or "").lower() == "discrepancy detected"
                        or s.variance_flag is True
                        or (s.variance_pct is not None and abs(s.variance_pct) > threshold)
                        or (float(s.bottom_up_tch4 or 0.0) == 0.0 and float(s.estimated_annual_tch4 or 0.0) > 0.0)
                        for s in surveys
                    )
                    has_reconciled = any(
                        (s.reconciliation_status or "").lower() == "reconciled" and not s.variance_flag
                        for s in surveys
                    )
                    if has_discrepancy or not has_reconciled:
                        reconciled_survey = False
                    else:
                        reconciled_survey = True
        except Exception:
            pass

    if td > 0 and bu > 0:
        variance_pct = abs((td - bu) / bu * 100.0)
        # Check if reconciled within threshold
        is_reconciled = reconciled_survey is True or (reconciled_survey is None and variance_pct <= threshold)"""

content_norm = content.replace('\r\n', '\n')
assert old_block.replace('\r\n', '\n') in content_norm, "old_block not found in ogmp.py"
content_norm = content_norm.replace(old_block.replace('\r\n', '\n'), new_block.replace('\r\n', '\n'), 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully patched ogmp.py")
