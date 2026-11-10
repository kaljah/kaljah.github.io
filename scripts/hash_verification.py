import hashlib
import os
import json

files_to_hash = [
    # Deliverables:
    "ROLE_AND_CSV_AUDIT_REPORT.md",
    "berkine_2022_all_68_sources.csv",
    "BROWSER_TEST_ALL_68_RESULTS.md",
    "DETAILED_EXECUTION_AUDIT_REPORT.md",
    "RESULTS_vs_REPORT.md",
    "comparison.csv",
    "report_anomalies.md",
    "extraction_checks.md",
    "sanity_check.csv",
    "spot_check.md",
    # Role and CSV test screenshots:
    "screenshots/role_tests/01_admin_csv_mapping.png",
    "screenshots/role_tests/02_admin_csv_success.png",
    "screenshots/role_tests/03_admin_emissions_history.png",
    "screenshots/role_tests/04_superuser_csv_mapping.png",
    "screenshots/role_tests/05_superuser_csv_success.png",
    "screenshots/role_tests/06_superuser_emissions_history.png",
    "screenshots/role_tests/07_user_csv_mapping.png",
    "screenshots/role_tests/08_user_csv_success.png",
    "screenshots/role_tests/09_user_emissions_history.png",
    "screenshots/role_tests/10_user_manual_form_entry.png",
    "screenshots/role_tests/11_user_manual_submitted.png",
    "screenshots/role_tests/12_user_all_68_history.png",
    "screenshots/role_tests/13_superuser_manual_form_entry.png",
    "screenshots/role_tests/14_superuser_manual_submitted.png",
    "screenshots/role_tests/15_superuser_all_68_history.png",
    "screenshots/role_tests/16_dashboard_corporate_2022.png",
    "screenshots/role_tests/17_reports_compliance_2022.png",
    # Browser test live screenshots:
    "screenshots/browser_test_68/dom_entry_heater4.png",
    "screenshots/browser_test_68/emissions_history.png",
    "screenshots/browser_test_68/manage_data_sources.png",
    "screenshots/browser_test_68/dashboard_2022.png",
    "screenshots/browser_test_68/reports_2022.png",
    # Spot-check images:
    "screenshots/spot_check/spot_01_hbns_heater4.png",
    "screenshots/spot_check/spot_02_hbns_turbine3.png",
    "screenshots/spot_check/spot_03_hbns_flare_purging.png",
    "screenshots/spot_check/spot_04_hbns_flare1_hp.png",
    "screenshots/spot_check/spot_05_hbns_venting_cpf.png",
    "screenshots/spot_check/spot_06_hbns_tank_liquid.png",
    "screenshots/spot_check/spot_07_elm_h01_ngl_heater.png",
    "screenshots/spot_check/spot_08_elm_flare_ap.png",
    "screenshots/spot_check/spot_09_elm_flare_ot1.png",
    "screenshots/spot_check/spot_10_elm_fire_suppressant.png",
    "screenshots/spot_check/page_26.png",
    "screenshots/spot_check/page_27.png",
    "screenshots/spot_check/page_28.png",
    "screenshots/spot_check/page_32.png",
    "screenshots/spot_check/page_33.png",
    "screenshots/spot_check/page_34.png",
    # Input source documents:
    r"C:\Users\samsung\.gemini\antigravity\brain\479daf75-25e8-4af0-af9b-4526d452b933\.user_uploaded\media_1794223915555_82a10d63.pdf"
]

manifest = {}
print("=== SHA-256 HASH VERIFICATION ===")
for p in files_to_hash:
    if os.path.exists(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        digest = h.hexdigest()
        manifest[p] = digest
        fname = os.path.basename(p)
        sz = os.path.getsize(p)
        print(f"{fname:38s} | {sz:8d} bytes | {digest}")
    else:
        print(f"NOT FOUND: {p}")

with open("audit_hash_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

print("\nSaved audit_hash_manifest.json")
