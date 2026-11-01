"""Patch emissions_export.py to include traceability metadata (Item 2.4)."""

def patch_export():
    path = "new/server/routes/emissions_export.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Scope 1 export dict
    old_s1 = '"data_source_ref": r.data_source_ref or "",\n                }'
    new_s1 = (
        '"data_source_ref": r.data_source_ref or "",\n'
        '                    "factor_version": r.factor_version or "API-2021.1",\n'
        '                    "factor_source": r.factor_source or "API Compendium 2021",\n'
        '                    "gwp_version": r.gwp_version or "AR5",\n'
        '                    "approved_by": r.approved_by_name or (f"User #{r.approved_by}" if r.approved_by else ""),\n'
        '                    "approved_at": r.approved_at.isoformat() if r.approved_at else "",\n'
        '                    "is_prior_period_adjustment": bool(getattr(r, "is_prior_period_adjustment", False)),\n'
        '                }'
    )
    if old_s1 in content:
        content = content.replace(old_s1, new_s1, 1)

    # Scope 2 export dict
    old_s2 = '"co2e_market_based": float(r.co2e_market_based if r.co2e_market_based is not None else (r.co2e or 0)),\n                    "status": r.status or "Verified",\n                    "data_source_ref": getattr(r, "data_source_ref", "") or "",\n                }'
    new_s2 = (
        '"co2e_market_based": float(r.co2e_market_based if r.co2e_market_based is not None else (r.co2e or 0)),\n'
        '                    "status": r.status or "Verified",\n'
        '                    "data_source_ref": getattr(r, "data_source_ref", "") or "",\n'
        '                    "factor_version": getattr(r, "factor_version", None) or "2023.1",\n'
        '                    "factor_source": getattr(r, "factor_source", None) or f"Grid ({r.grid_region or \'National\'})",\n'
        '                    "gwp_version": getattr(r, "gwp_version", None) or "AR5",\n'
        '                    "approved_by": r.approved_by_name or (f"User #{r.approved_by}" if r.approved_by else ""),\n'
        '                    "approved_at": r.approved_at.isoformat() if r.approved_at else "",\n'
        '                    "is_prior_period_adjustment": bool(getattr(r, "is_prior_period_adjustment", False)),\n'
        '                }'
    )
    if old_s2 in content:
        content = content.replace(old_s2, new_s2, 1)

    # Scope 3 export dict
    old_s3 = '"status": r.status or "Verified",\n                    "data_source_ref": getattr(r, "data_source_ref", "") or "",\n                }'
    new_s3 = (
        '"status": r.status or "Verified",\n'
        '                    "data_source_ref": getattr(r, "data_source_ref", "") or "",\n'
        '                    "factor_version": getattr(r, "factor_version", None) or "2023.1",\n'
        '                    "factor_source": getattr(r, "factor_source", None) or (r.calculation_method or "GHG Protocol Cat 11"),\n'
        '                    "gwp_version": getattr(r, "gwp_version", None) or "AR5",\n'
        '                    "approved_by": r.approved_by_name or (f"User #{r.approved_by}" if r.approved_by else ""),\n'
        '                    "approved_at": r.approved_at.isoformat() if r.approved_at else "",\n'
        '                    "is_prior_period_adjustment": bool(getattr(r, "is_prior_period_adjustment", False)),\n'
        '                }'
    )
    if old_s3 in content:
        content = content.replace(old_s3, new_s3, 1)

    # Excel headers
    old_headers = '"Source Reference",\n        ]'
    new_headers = (
        '"Source Reference",\n'
        '            "Factor Version",\n'
        '            "GWP Standard",\n'
        '            "Approved By",\n'
        '            "Approved At",\n'
        '            "Prior Period Adjustment",\n'
        '        ]'
    )
    if old_headers in content:
        content = content.replace(old_headers, new_headers, 1)

    # Excel cell writes
    old_cells = 'ws1.cell(row=row_num, column=18, value=_safe_excel_value(item["data_source_ref"]))\n'
    new_cells = (
        'ws1.cell(row=row_num, column=18, value=_safe_excel_value(item["data_source_ref"]))\n'
        '            ws1.cell(row=row_num, column=19, value=_safe_excel_value(item.get("factor_version", "")))\n'
        '            ws1.cell(row=row_num, column=20, value=_safe_excel_value(item.get("gwp_version", "")))\n'
        '            ws1.cell(row=row_num, column=21, value=_safe_excel_value(item.get("approved_by", "")))\n'
        '            ws1.cell(row=row_num, column=22, value=_safe_excel_value(item.get("approved_at", "")))\n'
        '            ws1.cell(row=row_num, column=23, value="Yes" if item.get("is_prior_period_adjustment") else "No")\n'
    )
    if old_cells in content:
        content = content.replace(old_cells, new_cells, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched emissions_export.py successfully")

if __name__ == "__main__":
    patch_export()
