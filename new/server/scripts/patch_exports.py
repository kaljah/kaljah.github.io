# Patch reports.py, reports_export.py, emissions_export.py

# 1. reports.py
with open('new/server/routes/reports.py', 'rb') as f:
    c_reports = f.read()

target1 = b'''        # 1. SCOPE 1
        if scope in ["all", "1"]:
            q = Emission.query
            if year:
                q = q.filter_by(year=year)
            if month:
                q = q.filter_by(month=month)
            if facility_id:
                q = q.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q = q.filter(Emission.facility_id.in_(allowed_fids))
            if process_type:
                q = q.filter_by(process_type=process_type)
            q = q.filter(Emission.status == "Verified")'''

replacement1 = b'''        status_filter = str(filters.get("status") or "Verified").strip()
        statuses = [x.strip().lower() for x in status_filter.split(",") if x.strip()] if status_filter.lower() != "all" else None
        test_fids = Facility.query.with_entities(Facility.id).filter(Facility.is_test == True)

        # 1. SCOPE 1
        if scope in ["all", "1"]:
            q = Emission.query
            if year:
                q = q.filter_by(year=year)
            if month:
                q = q.filter_by(month=month)
            if facility_id:
                q = q.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q = q.filter(Emission.facility_id.in_(allowed_fids))
            if process_type:
                q = q.filter_by(process_type=process_type)
            q = q.filter(~Emission.facility_id.in_(test_fids))
            if hasattr(Emission, "is_test"):
                q = q.filter(Emission.is_test == False)
            if statuses:
                q = q.filter(db.func.lower(db.func.trim(Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target1.replace(b'\n', nl)
    r = replacement1.replace(b'\n', nl)
    if t in c_reports:
        c_reports = c_reports.replace(t, r, 1)
        print('Patched reports.py Scope 1')
        break

target1_s2 = b'''            q2 = Scope2Emission.query
            if year:
                q2 = q2.filter_by(year=year)
            if month:
                q2 = q2.filter_by(month=month)
            if facility_id:
                q2 = q2.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q2 = q2.filter(Scope2Emission.facility_id.in_(allowed_fids))
            q2 = q2.filter(Scope2Emission.status == "Verified")'''

replacement1_s2 = b'''            q2 = Scope2Emission.query
            if year:
                q2 = q2.filter_by(year=year)
            if month:
                q2 = q2.filter_by(month=month)
            if facility_id:
                q2 = q2.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q2 = q2.filter(Scope2Emission.facility_id.in_(allowed_fids))
            q2 = q2.filter(~Scope2Emission.facility_id.in_(test_fids))
            if hasattr(Scope2Emission, "is_test"):
                q2 = q2.filter(Scope2Emission.is_test == False)
            if statuses:
                q2 = q2.filter(db.func.lower(db.func.trim(Scope2Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target1_s2.replace(b'\n', nl)
    r = replacement1_s2.replace(b'\n', nl)
    if t in c_reports:
        c_reports = c_reports.replace(t, r, 1)
        print('Patched reports.py Scope 2')
        break

target1_s3 = b'''            q3 = Scope3Emission.query
            if year:
                q3 = q3.filter_by(year=year)
            if month:
                q3 = q3.filter_by(month=month)
            if facility_id:
                q3 = q3.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q3 = q3.filter(Scope3Emission.facility_id.in_(allowed_fids))
            q3 = q3.filter(Scope3Emission.status == "Verified")'''

replacement1_s3 = b'''            q3 = Scope3Emission.query
            if year:
                q3 = q3.filter_by(year=year)
            if month:
                q3 = q3.filter_by(month=month)
            if facility_id:
                q3 = q3.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q3 = q3.filter(Scope3Emission.facility_id.in_(allowed_fids))
            q3 = q3.filter(~Scope3Emission.facility_id.in_(test_fids))
            if hasattr(Scope3Emission, "is_test"):
                q3 = q3.filter(Scope3Emission.is_test == False)
            if statuses:
                q3 = q3.filter(db.func.lower(db.func.trim(Scope3Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target1_s3.replace(b'\n', nl)
    r = replacement1_s3.replace(b'\n', nl)
    if t in c_reports:
        c_reports = c_reports.replace(t, r, 1)
        print('Patched reports.py Scope 3')
        break

with open('new/server/routes/reports.py', 'wb') as f:
    f.write(c_reports)

# 2. reports_export.py
with open('new/server/routes/reports_export.py', 'rb') as f:
    c_repexp = f.read()

target2_s1 = b'''            q1 = q1.filter(Emission.status == "Verified")'''
replacement2_s1 = b'''            status_filter = str(filters.get("status") or request.args.get("status") or "Verified").strip()
            statuses = [x.strip().lower() for x in status_filter.split(",") if x.strip()] if status_filter.lower() != "all" else None
            test_fids = Facility.query.with_entities(Facility.id).filter(Facility.is_test == True)
            q1 = q1.filter(~Emission.facility_id.in_(test_fids))
            if hasattr(Emission, "is_test"):
                q1 = q1.filter(Emission.is_test == False)
            if statuses:
                q1 = q1.filter(db.func.lower(db.func.trim(Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target2_s1.replace(b'\n', nl)
    r = replacement2_s1.replace(b'\n', nl)
    if t in c_repexp:
        c_repexp = c_repexp.replace(t, r, 1)
        print('Patched reports_export.py Scope 1')
        break

target2_s2 = b'''            q2 = q2.filter(Scope2Emission.status == "Verified")'''
replacement2_s2 = b'''            q2 = q2.filter(~Scope2Emission.facility_id.in_(test_fids))
            if hasattr(Scope2Emission, "is_test"):
                q2 = q2.filter(Scope2Emission.is_test == False)
            if statuses:
                q2 = q2.filter(db.func.lower(db.func.trim(Scope2Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target2_s2.replace(b'\n', nl)
    r = replacement2_s2.replace(b'\n', nl)
    if t in c_repexp:
        c_repexp = c_repexp.replace(t, r, 1)
        print('Patched reports_export.py Scope 2')
        break

target2_s3 = b'''            q3 = q3.filter(Scope3Emission.status == "Verified")'''
replacement2_s3 = b'''            q3 = q3.filter(~Scope3Emission.facility_id.in_(test_fids))
            if hasattr(Scope3Emission, "is_test"):
                q3 = q3.filter(Scope3Emission.is_test == False)
            if statuses:
                q3 = q3.filter(db.func.lower(db.func.trim(Scope3Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target2_s3.replace(b'\n', nl)
    r = replacement2_s3.replace(b'\n', nl)
    if t in c_repexp:
        c_repexp = c_repexp.replace(t, r, 1)
        print('Patched reports_export.py Scope 3')
        break

with open('new/server/routes/reports_export.py', 'wb') as f:
    f.write(c_repexp)

# 3. emissions_export.py
with open('new/server/routes/emissions_export.py', 'rb') as f:
    c_emexp = f.read()

target3_s1 = b'''        q1 = Emission.query.filter(Emission.status == "Verified")'''
replacement3_s1 = b'''        status_arg = str(request.args.get("status") or "Verified").strip()
        statuses = [x.strip().lower() for x in status_arg.split(",") if x.strip()] if status_arg.lower() != "all" else None
        test_fids = Facility.query.with_entities(Facility.id).filter(Facility.is_test == True)
        q1 = Emission.query.filter(~Emission.facility_id.in_(test_fids))
        if hasattr(Emission, "is_test"):
            q1 = q1.filter(Emission.is_test == False)
        if statuses:
            q1 = q1.filter(db.func.lower(db.func.trim(Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target3_s1.replace(b'\n', nl)
    r = replacement3_s1.replace(b'\n', nl)
    if t in c_emexp:
        c_emexp = c_emexp.replace(t, r, 1)
        print('Patched emissions_export.py Scope 1')
        break

target3_s2 = b'''        q2 = Scope2Emission.query.filter(Scope2Emission.status == "Verified")'''
replacement3_s2 = b'''        q2 = Scope2Emission.query.filter(~Scope2Emission.facility_id.in_(test_fids))
        if hasattr(Scope2Emission, "is_test"):
            q2 = q2.filter(Scope2Emission.is_test == False)
        if statuses:
            q2 = q2.filter(db.func.lower(db.func.trim(Scope2Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target3_s2.replace(b'\n', nl)
    r = replacement3_s2.replace(b'\n', nl)
    if t in c_emexp:
        c_emexp = c_emexp.replace(t, r, 1)
        print('Patched emissions_export.py Scope 2')
        break

target3_s3 = b'''        q3 = Scope3Emission.query.filter(Scope3Emission.status == "Verified")'''
replacement3_s3 = b'''        q3 = Scope3Emission.query.filter(~Scope3Emission.facility_id.in_(test_fids))
        if hasattr(Scope3Emission, "is_test"):
            q3 = q3.filter(Scope3Emission.is_test == False)
        if statuses:
            q3 = q3.filter(db.func.lower(db.func.trim(Scope3Emission.status)).in_(statuses))'''

for nl in [b'\r\n', b'\n']:
    t = target3_s3.replace(b'\n', nl)
    r = replacement3_s3.replace(b'\n', nl)
    if t in c_emexp:
        c_emexp = c_emexp.replace(t, r, 1)
        print('Patched emissions_export.py Scope 3')
        break

with open('new/server/routes/emissions_export.py', 'wb') as f:
    f.write(c_emexp)

print('All patches completed.')
