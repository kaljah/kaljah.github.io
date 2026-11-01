with open('new/server/routes/emissions.py', 'rb') as f:
    content = f.read()

target = b'''        if status_arg and status_arg != "all" and hasattr(model, "status"):
            q = q.filter(model.status.in_([x.strip() for x in status_arg.split(",") if x.strip()]))'''

replacement = b'''        # Exclude test data from production ledger unless explicitly requested
        include_test = request.args.get("include_test") in ("1", "true", "True")
        if not include_test:
            if hasattr(model, "is_test"):
                q = q.filter(model.is_test == False)
            if hasattr(Facility, "is_test") and hasattr(model, "facility_id"):
                test_fids = Facility.query.with_entities(Facility.id).filter(Facility.is_test == True)
                q = q.filter(~model.facility_id.in_(test_fids))

        if status_arg and status_arg.strip().lower() != "all" and hasattr(model, "status"):
            statuses = [x.strip().lower() for x in status_arg.split(",") if x.strip()]
            q = q.filter(db.func.lower(db.func.trim(model.status)).in_(statuses))'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open('new/server/routes/emissions.py', 'wb') as f:
        f.write(content)
    print('Successfully patched emissions.py (LF)')
elif target.replace(b'\n', b'\r\n') in content:
    content = content.replace(target.replace(b'\n', b'\r\n'), replacement.replace(b'\n', b'\r\n'), 1)
    with open('new/server/routes/emissions.py', 'wb') as f:
        f.write(content)
    print('Successfully patched emissions.py (CRLF)')
else:
    print('Target not found in emissions.py')
