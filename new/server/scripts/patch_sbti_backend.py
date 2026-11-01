path = 'new/server/routes/dashboard_sbti.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_loop = """    end_year = max(target_year, current_year)
    trajectory = []
    for yr in range(base_year, end_year + 1):
        d = yr - base_year
        s1 = round(scope1_actuals.get(yr, 0), 2)
        s2 = round(scope2_actuals.get(yr, 0), 2)
        s3 = round(scope3_actuals.get(yr, 0), 2)
        has = yr in actuals
        val = series(yr)
        trajectory.append({
            "year": str(yr),
            "sbti_target": line(rate, d),
            "sbti_15c": line(rate_15c, d),
            "sbti_wb2c": line(rate_wb2c, d),
            "bau_projection": round(baseline * (1.015 ** d), 2) if baseline else None,
            "actual": round(val, 2) if (val is not None and yr <= current_year) else None,
            "is_partial_year": yr == current_year,
            "scope1": s1 if has else 0,
            "scope2": s2 if has else 0,
            "scope3": s3 if has else 0,
            "scope12": round(s1 + s2, 2) if has else 0,
            "total_emissions": round(s1 + s2 + s3, 2) if has else 0,
        })"""

new_loop = """    end_year = max(target_year, current_year)
    max_month_res = db.session.query(func.max(Emission.month)).filter(
        Emission.year == current_year, Emission.status == "Verified", Emission.is_test == False
    ).scalar()
    months_reported = int(max_month_res or 1)

    trajectory = []
    for yr in range(base_year, end_year + 1):
        d = yr - base_year
        s1 = round(scope1_actuals.get(yr, 0), 2)
        s2 = round(scope2_actuals.get(yr, 0), 2)
        s3 = round(scope3_actuals.get(yr, 0), 2)
        has = yr in actuals
        val = series(yr)
        is_partial = (yr == current_year)
        actual_val = round(val, 2) if (val is not None and yr <= current_year) else None
        annualized = round(val * (12.0 / months_reported), 2) if (is_partial and val is not None and months_reported > 0) else None
        trajectory.append({
            "year": str(yr),
            "sbti_target": line(rate, d),
            "sbti_15c": line(rate_15c, d),
            "sbti_wb2c": line(rate_wb2c, d),
            "bau_projection": round(baseline * (1.015 ** d), 2) if baseline else None,
            "actual": actual_val,
            "actual_ytd": actual_val if is_partial else None,
            "actual_annualized": annualized,
            "is_partial_year": is_partial,
            "months_reported": months_reported if is_partial else 12,
            "scope1": s1 if has else 0,
            "scope2": s2 if has else 0,
            "scope3": s3 if has else 0,
            "scope12": round(s1 + s2, 2) if has else 0,
            "total_emissions": round(s1 + s2 + s3, 2) if has else 0,
        })"""

old_labels = """    labels = {"1.5C": "SBTi 1.5\\u00b0C Linear Target", "WB2C": "SBTi Well-Below 2\\u00b0C Linear Target",
              "custom": "Custom Linear Target"}"""

new_labels = """    labels = {"1.5C": "SBTi-aligned 1.5\\u00b0C Linear Target (Indicative)", "WB2C": "SBTi-aligned Well-Below 2\\u00b0C Linear Target (Indicative)",
              "custom": "Custom Linear Target (Indicative)"}"""

content_norm = content.replace('\r\n', '\n')
assert old_loop.replace('\r\n', '\n') in content_norm, "old_loop not found"
assert old_labels.replace('\r\n', '\n') in content_norm, "old_labels not found"

content_norm = content_norm.replace(old_loop.replace('\r\n', '\n'), new_loop.replace('\r\n', '\n'), 1)
content_norm = content_norm.replace(old_labels.replace('\r\n', '\n'), new_labels.replace('\r\n', '\n'), 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully patched dashboard_sbti.py")
