"""Script to insert period lock checks across emissions, scope2, scope3, and data routes."""
import re

def patch_emissions():
    path = "new/server/routes/emissions.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. In add_emission
    old_code = 'data["month"] = parse_month(data["month"], required=True)\n'
    new_code = (
        'data["month"] = parse_month(data["month"], required=True)\n'
        '        from services.period_lock_service import check_period_lock_for_record\n'
        '        lock_err = check_period_lock_for_record(data.get("year"), data.get("month"), is_prior_period_adjustment=bool(data.get("is_prior_period_adjustment")))\n'
        '        if lock_err:\n'
        '            return jsonify(lock_err[0]), lock_err[1]\n'
    )
    if old_code in content and "check_period_lock_for_record(data.get" not in content:
        content = content.replace(old_code, new_code, 1)

    # 2. In update_emission
    old_update = 'if not record:\n        return jsonify({"error": "Emission record not found"}), 404\n'
    new_update = (
        'if not record:\n        return jsonify({"error": "Emission record not found"}), 404\n\n'
        '    from services.period_lock_service import check_period_lock_for_record\n'
        '    is_ppa = bool(data.get("is_prior_period_adjustment", getattr(record, "is_prior_period_adjustment", False)))\n'
        '    lock_err = check_period_lock_for_record(record.year, record.month, is_prior_period_adjustment=is_ppa)\n'
        '    if lock_err:\n'
        '        return jsonify(lock_err[0]), lock_err[1]\n'
    )
    if old_update in content and "lock_err = check_period_lock_for_record(record.year" not in content:
        content = content.replace(old_update, new_update, 1)

    # 3. In delete_emission
    old_del = 'if not record:\n        return jsonify({"error": "Emission record not found"}), 404\n'
    # There are two occurrences of this pattern (update and delete).
    if "check_period_lock_for_record(record.year, record.month)" not in content:
        # Match inside delete_emission
        del_target = 'or db.session.get(Emission, int(clean_id) if clean_id.isdigit() else -1)\n    )\n    if not record:\n        return jsonify({"error": "Emission record not found"}), 404\n'
        del_replace = (
            'or db.session.get(Emission, int(clean_id) if clean_id.isdigit() else -1)\n    )\n'
            '    if not record:\n        return jsonify({"error": "Emission record not found"}), 404\n\n'
            '    from services.period_lock_service import check_period_lock_for_record\n'
            '    lock_err = check_period_lock_for_record(record.year, record.month)\n'
            '    if lock_err:\n'
            '        return jsonify(lock_err[0]), lock_err[1]\n'
        )
        if del_target in content:
            content = content.replace(del_target, del_replace, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched emissions.py")


def patch_scope2():
    path = "new/server/routes/scope2.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # In add_scope2_emission
    create_target = 'year = parse_year(data.get("year"))\n        month = parse_month(data.get("month"), required=False)\n'
    create_replace = (
        'year = parse_year(data.get("year"))\n        month = parse_month(data.get("month"), required=False)\n'
        '        from services.period_lock_service import check_period_lock_for_record\n'
        '        lock_err = check_period_lock_for_record(year, month, is_prior_period_adjustment=bool(data.get("is_prior_period_adjustment")))\n'
        '        if lock_err:\n'
        '            return jsonify(lock_err[0]), lock_err[1]\n'
    )
    if create_target in content and "check_period_lock_for_record(year, month" not in content:
        content = content.replace(create_target, create_replace, 1)

    # In delete_scope2_emission
    del_target = 'record = db.session.get(Scope2Emission, id)\n    if not record:\n        return jsonify({"error": "Scope 2 emission record not found"}), 404\n'
    del_replace = (
        'record = db.session.get(Scope2Emission, id)\n    if not record:\n        return jsonify({"error": "Scope 2 emission record not found"}), 404\n\n'
        '    from services.period_lock_service import check_period_lock_for_record\n'
        '    lock_err = check_period_lock_for_record(record.year, record.month)\n'
        '    if lock_err:\n'
        '        return jsonify(lock_err[0]), lock_err[1]\n'
    )
    if del_target in content and "check_period_lock_for_record(record.year" not in content:
        content = content.replace(del_target, del_replace, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched scope2.py")


def patch_scope3():
    path = "new/server/routes/scope3.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # In add_scope3_emission
    create_target = 'year = parse_year(data.get("year"))\n        month = parse_month(data.get("month"), required=False)\n'
    create_replace = (
        'year = parse_year(data.get("year"))\n        month = parse_month(data.get("month"), required=False)\n'
        '        from services.period_lock_service import check_period_lock_for_record\n'
        '        lock_err = check_period_lock_for_record(year, month, is_prior_period_adjustment=bool(data.get("is_prior_period_adjustment")))\n'
        '        if lock_err:\n'
        '            return jsonify(lock_err[0]), lock_err[1]\n'
    )
    if create_target in content and "check_period_lock_for_record(year, month" not in content:
        content = content.replace(create_target, create_replace, 1)

    # In delete_scope3_emission
    del_target = 'record = db.session.get(Scope3Emission, id)\n    if not record:\n        return jsonify({"error": "Scope 3 record not found"}), 404\n'
    del_replace = (
        'record = db.session.get(Scope3Emission, id)\n    if not record:\n        return jsonify({"error": "Scope 3 record not found"}), 404\n\n'
        '    from services.period_lock_service import check_period_lock_for_record\n'
        '    lock_err = check_period_lock_for_record(record.year, record.month)\n'
        '    if lock_err:\n'
        '        return jsonify(lock_err[0]), lock_err[1]\n'
    )
    if del_target in content and "check_period_lock_for_record(record.year" not in content:
        content = content.replace(del_target, del_replace, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched scope3.py")


if __name__ == "__main__":
    patch_emissions()
    patch_scope2()
    patch_scope3()
