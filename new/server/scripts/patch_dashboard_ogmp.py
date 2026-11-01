path = 'new/server/routes/dashboard_ogmp.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        if top_down > 0 and bottom_up > 0:
            variance_pct = round(((top_down - bottom_up) / bottom_up * 100.0), 2)
            variance_flag = abs(variance_pct) > threshold
            rec_status = "Discrepancy Flagged" if variance_flag else "Reconciled"
        elif top_down > 0 and bottom_up == 0:
            # Invariant Zero (Decision D-02): Zero Bottom-Up Edge Case
            variance_pct = None
            variance_flag = True
            rec_status = "Discrepancy Flagged"
        elif top_down == 0 and bottom_up > 0:
            variance_pct = None
            variance_flag = False
            rec_status = "Bottom-Up Only"
        else:
            variance_pct = None
            variance_flag = False
            rec_status = "No Activity\""""

new_block = """        # Check empirical survey records for recorded discrepancies
        survey_has_discrepancy = False
        try:
            from models import OgmpSurvey
            sq = OgmpSurvey.query.filter_by(facility_id=f.id)
            if single_year:
                sq = sq.filter_by(year=int(year))
            for s in sq.all():
                if (s.reconciliation_status or "").lower() == "discrepancy detected" or s.variance_flag is True or (float(s.bottom_up_tch4 or 0.0) == 0.0 and float(s.estimated_annual_tch4 or 0.0) > 0.0) or (s.variance_pct is not None and abs(s.variance_pct) > threshold):
                    survey_has_discrepancy = True
                    break
        except Exception:
            pass

        if top_down > 0 and bottom_up > 0:
            variance_pct = round(((top_down - bottom_up) / bottom_up * 100.0), 2)
            variance_flag = abs(variance_pct) > threshold or survey_has_discrepancy
            rec_status = "Discrepancy Detected" if variance_flag else "Reconciled"
        elif top_down > 0 and bottom_up == 0:
            # Invariant Zero (Decision D-02): Zero Bottom-Up Edge Case
            variance_pct = None
            variance_flag = True
            rec_status = "Discrepancy Detected"
        elif top_down == 0 and bottom_up > 0:
            variance_pct = None
            variance_flag = False
            rec_status = "Bottom-Up Only"
        else:
            variance_pct = None
            variance_flag = False
            rec_status = "No Activity"

        if survey_has_discrepancy:
            variance_flag = True
            rec_status = "Discrepancy Detected"
            highest_level = min(4, highest_level)"""

content_norm = content.replace('\r\n', '\n')
assert old_block.replace('\r\n', '\n') in content_norm, "old_block not found in dashboard_ogmp.py"
content_norm = content_norm.replace(old_block.replace('\r\n', '\n'), new_block.replace('\r\n', '\n'), 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully patched dashboard_ogmp.py")
