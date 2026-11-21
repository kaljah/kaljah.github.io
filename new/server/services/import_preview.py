"""The file-check (dry run) summary of a bulk import, moved out of background_processor.py."""


def preview_summary(pv, rows, skipped_in_sample, headers, mapping, fac_name_map, fac_id_map, scope=None):
    from services.scope1_calc import SCOPE2_PROCESS_TYPES, normalize_process_type

    def scope2(name):
        n = name.strip().lower()
        return bool(n) and (n in SCOPE2_PROCESS_TYPES or normalize_process_type(n) in SCOPE2_PROCESS_TYPES)

    checked = pv["checked"]
    ok = max(0, checked - skipped_in_sample)
    ratio = (ok / checked) if checked else 0.0
    dates = sorted(pv["dates"])

    def known_fac(name):
        k = name.strip().lower()
        return bool(k) and (k in fac_name_map or k in fac_id_map)

    facilities = [{"name": n or "(blank)", "rows": c, "known": known_fac(n)}
                  for n, c in sorted(pv["facilities"].items(), key=lambda x: -x[1])]
    processes = [{"name": n or "(blank)", "rows": c, "scope2": scope2(n),
                  "known": bool(n) and bool(normalize_process_type(n)) and not scope2(n)}
                 for n, c in sorted(pv["processes"].items(), key=lambda x: -x[1])]
    matched = [h for h in headers if h and h in set(mapping.values())]
    # period / facility / process counts describe emission rows: a facilities, factors or production file reported
    # "unknown process" for every row (GB RY2022 GB-030)
    emission_scope = scope is None or str(scope) in ("1", "2", "3")
    if not emission_scope:
        processes = []
        if str(scope) in ("facilities", "custom_factors"):
            facilities = []
    return {
        "rows": rows,
        "checked": checked,
        "checked_ok": ok,
        "checked_skipped": skipped_in_sample,
        "estimated_ok": int(round(rows * ratio)) if checked < rows else ok,
        "estimated_skipped": rows - (int(round(rows * ratio)) if checked < rows else ok),
        "is_estimate": checked < rows,
        "period": {"from": dates[0] if dates else None, "to": dates[-1] if dates else None,
                   "months": len(dates), "unreadable_rows": pv["bad_dates"]},
        "facilities": facilities[:50],
        "unknown_facility_rows": sum(f["rows"] for f in facilities if not f["known"]),
        "processes": processes[:50],
        "unknown_process_rows": sum(p["rows"] for p in processes if not p["known"] and not p["scope2"]),
        "scope2_rows": sum(p["rows"] for p in processes if p["scope2"]),
        "example_rows": pv.get("examples", 0),
        "columns": {"total": len([h for h in headers if h]), "headers": [h for h in headers if h], "matched": matched,
                    "by_name": [h for h in headers if h and h not in matched]},
    }
