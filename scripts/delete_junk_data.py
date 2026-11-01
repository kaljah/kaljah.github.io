"""
NeoCarbon - Permanent Deletion of Flagged Junk & Test Data
Authorized by user approval.
Permanently deletes all records previously flagged with is_test = 1.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app import app
from extensions import db
from models import Facility, Emission, ProductionData, EmissionSource, MitigationProject, CustomFactor, User, ActivityLog
from sqlalchemy import text
from utils import user_label

def delete_flagged_junk_data():
    with app.app_context():
        print("=" * 80)
        print("NEOCARBON PERMANENT DELETION OF FLAGGED JUNK & TEST DATA")
        print("=" * 80)

        try:
            # 1. Identify test facilities
            test_facs = Facility.query.filter_by(is_test=True).all()
            test_fac_ids = [f.id for f in test_facs]
            print(f"Flagged facilities to delete: {len(test_facs)} ({test_fac_ids})")

            if test_fac_ids:
                id_tuple_str = ",".join(str(i) for i in test_fac_ids)

                # Dependent emission/reporting tables under test facilities
                for tbl in ["cap_emissions", "scope2_emissions", "scope3_emissions", "ogmp_surveys", 
                            "flaring_details", "facility_equity_shares", "component_inventories", 
                            "fugitive_surveys", "cbam_product_exports"]:
                    try:
                        res = db.session.execute(text(f"DELETE FROM {tbl} WHERE facility_id IN ({id_tuple_str})"))
                        if res.rowcount > 0:
                            print(f"Deleted {res.rowcount} records from {tbl}")
                    except Exception as e:
                        pass

                # Note: activity_log does NOT have a foreign key to facilities (activity_log outlives deleted facilities),
                # so facility_id is retained to preserve cryptographic hash chain integrity.

            # 2. Scope 1 Emissions
            if test_fac_ids:
                em_query = Emission.query.filter(
                    (Emission.is_test == True) | (Emission.facility_id.in_(test_fac_ids))
                )
            else:
                em_query = Emission.query.filter_by(is_test=True)
            em_count = em_query.count()
            em_query.delete(synchronize_session=False)
            print(f"Deleted emissions records: {em_count}")

            # 3. Production Data
            if test_fac_ids:
                prod_query = ProductionData.query.filter(
                    (ProductionData.is_test == True) | (ProductionData.facility_id.in_(test_fac_ids))
                )
            else:
                prod_query = ProductionData.query.filter_by(is_test=True)
            prod_count = prod_query.count()
            prod_query.delete(synchronize_session=False)
            print(f"Deleted production_data records: {prod_count}")

            # 4. Emission Sources
            if test_fac_ids:
                src_query = EmissionSource.query.filter(
                    (EmissionSource.is_test == True) | (EmissionSource.facility_id.in_(test_fac_ids))
                )
            else:
                src_query = EmissionSource.query.filter_by(is_test=True)
            src_count = src_query.count()
            src_query.delete(synchronize_session=False)
            print(f"Deleted emission_sources records: {src_count}")

            # 5. Mitigation Projects
            if test_fac_ids:
                mit_query = MitigationProject.query.filter(
                    (MitigationProject.is_test == True) | (MitigationProject.facility_id.in_(test_fac_ids))
                )
            else:
                mit_query = MitigationProject.query.filter_by(is_test=True)
            mit_count = mit_query.count()
            mit_query.delete(synchronize_session=False)
            print(f"Deleted mitigation_projects records: {mit_count}")

            # 6. Custom Factors
            cf_query = CustomFactor.query.filter_by(is_test=True)
            cf_count = cf_query.count()
            cf_query.delete(synchronize_session=False)
            print(f"Deleted custom_factors records: {cf_count}")

            # 7. Test Users - clear FK references safely
            test_users = User.query.filter_by(is_test=True).all()
            user_count = len(test_users)
            for u in test_users:
                u_id = u.id
                label = user_label(u)
                db.session.execute(text("DELETE FROM notifications WHERE user_id = :uid"), {"uid": u_id})
                db.session.execute(text("DELETE FROM import_mappings WHERE user_id = :uid"), {"uid": u_id})
                for table in db.metadata.sorted_tables:
                    if table.name in ("users", "notifications", "import_mappings"):
                        continue
                    for col in table.columns:
                        if not any(fk.column.table.name == "users" for fk in col.foreign_keys):
                            continue
                        snapshot = f"{col.name}_name"
                        if snapshot in table.columns:
                            db.session.execute(
                                text(f'UPDATE "{table.name}" SET "{snapshot}" = :label '
                                     f'WHERE "{col.name}" = :uid AND ("{snapshot}" IS NULL OR "{snapshot}" = \'\')'),
                                {"uid": u_id, "label": label},
                            )
                        db.session.execute(
                            text(f'UPDATE "{table.name}" SET "{col.name}" = NULL WHERE "{col.name}" = :uid'), {"uid": u_id}
                        )
                db.session.delete(u)
            print(f"Deleted test user accounts: {user_count}")

            # 8. Facilities
            fac_count = len(test_facs)
            for f in test_facs:
                db.session.delete(f)
            print(f"Deleted facilities: {fac_count}")

            # 9. Audit trail logging (with cryptographic hash chain sealing)
            audit_entry = ActivityLog(
                action="PURGE_JUNK_DATA",
                user_name="Administrator",
                details=f"Permanent deletion of flagged test/junk records: {fac_count} facilities, {em_count} emissions, {prod_count} production rows, {src_count} sources, {mit_count} mitigation projects, {cf_count} factors, {user_count} users.",
                entity="System",
                entity_id="JunkDataPurge",
                ip_address="127.0.0.1",
            )
            db.session.add(audit_entry)
            db.session.commit()

            print("\nSUCCESS: All flagged test and junk data records have been permanently deleted.")
            print("Cryptographically sealed audit log entry created.")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR during deletion: {e}")
            sys.exit(1)

if __name__ == "__main__":
    delete_flagged_junk_data()
