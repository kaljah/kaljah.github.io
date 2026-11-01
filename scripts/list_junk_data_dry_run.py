"""
NeoCarbon - Junk & Test Data Dry-Run Report
Lists all test/junk records flagged with is_test=1 that are candidate for deletion or exclusion.
ZERO DELETIONS ARE PERFORMED by this script.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "new", "server", "ghg_app.db")

def run_dry_run_report():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("=" * 80)
    print("NEOCARBON JUNK & TEST DATA DRY-RUN AUDIT REPORT")
    print(f"Database: {DB_PATH}")
    print("Mode: READ-ONLY DRY-RUN (Zero records deleted)")
    print("=" * 80)

    # 1. Facilities
    c.execute("SELECT id, name, region, location, activity, division FROM facilities WHERE is_test = 1")
    facs = c.fetchall()
    print(f"\n[1] TEST FACILITIES ({len(facs)} found):")
    for f in facs:
        print(f"  - Facility #{f[0]}: Name='{f[1]}', Region='{f[2]}', Location='{f[3]}', Activity='{f[4]}', Division='{f[5]}'")

    # 2. Emissions under test facilities / regions
    c.execute("SELECT count(*), coalesce(sum(co2e_total), 0) FROM emissions WHERE is_test = 1")
    em_count, em_co2e = c.fetchone()
    print(f"\n[2] TEST EMISSIONS RECORDS ({em_count} found):")
    print(f"  - Total Impact: {em_co2e:,.2f} tCO2e flagged as test data and excluded from production")

    # 3. Production Data under test facilities / regions
    c.execute("SELECT count(*), coalesce(sum(total_production_mmboe), 0) FROM production_data WHERE is_test = 1")
    prod_count, prod_mmboe = c.fetchone()
    print(f"\n[3] TEST PRODUCTION DATA RECORDS ({prod_count} found):")
    print(f"  - Total Impact: {prod_mmboe:,.2f} MMBOE flagged as test data and excluded from production")

    # 4. Emission Sources
    c.execute("SELECT id, facility_id, name, type, equipment_id FROM emission_sources WHERE is_test = 1")
    srcs = c.fetchall()
    print(f"\n[4] TEST EMISSION SOURCES ({len(srcs)} found):")
    for s in srcs:
        print(f"  - Source #{s[0]}: Name='{s[2]}', Type='{s[3]}', EquipmentID='{s[4]}', FacilityID={s[1]}")

    # 5. Mitigation Projects
    c.execute("SELECT id, facility_id, name, project_type, year, quantity_tco2e FROM mitigation_projects WHERE is_test = 1")
    mits = c.fetchall()
    print(f"\n[5] TEST MITIGATION PROJECTS ({len(mits)} found):")
    for m in mits:
        print(f"  - Project #{m[0]}: Name='{m[2]}', Type='{m[3]}', Year={m[4]}, tCO2e={m[5]}, FacilityID={m[1]}")

    # 6. Custom Factors
    c.execute("SELECT id, name, co2_factor, ch4_factor, n2o_factor, unit FROM custom_factors WHERE is_test = 1")
    cfs = c.fetchall()
    print(f"\n[6] TEST CUSTOM FACTORS ({len(cfs)} found):")
    for cf in cfs:
        print(f"  - Factor #{cf[0]}: Name='{cf[1]}', CO2={cf[2]}, CH4={cf[3]}, N2O={cf[4]}, Unit='{cf[5]}'")

    # 7. Test Users
    c.execute("SELECT id, email, fullName, role FROM users WHERE is_test = 1")
    us = c.fetchall()
    print(f"\n[7] TEST USERS ({len(us)} found):")
    for u in us:
        print(f"  - User #{u[0]}: Email='{u[1]}', FullName='{u[2]}', Role='{u[3]}'")

    total_candidates = len(facs) + em_count + prod_count + len(srcs) + len(mits) + len(cfs) + len(us)
    print("\n" + "=" * 80)
    print(f"TOTAL TEST / JUNK CANDIDATE RECORDS: {total_candidates}")
    print("Action Taken: FLAGGED with is_test=1 and excluded from production reports/dashboards.")
    print("Permanent Deletion: PENDING USER APPROVAL.")
    print("=" * 80)

if __name__ == "__main__":
    run_dry_run_report()
