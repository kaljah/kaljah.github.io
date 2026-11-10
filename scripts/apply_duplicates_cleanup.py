"""
NeoCarbon - Permanent Deletion of Identified Duplicate Records
Authorized by user approval.
Removes redundant duplicate copies while preserving canonical records with cleaned names.
Repoints foreign keys to canonical records before deleting surplus duplicates.
Logs a cryptographically sealed ActivityLog entry.
"""
import os
import sys
import re
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app import app
from extensions import db
from models import (
    CustomFactor, MitigationProject, EmissionSource, Scope3Emission, 
    Emission, ComponentInventory, RecalculationRequest, ActivityLog
)
from sqlalchemy import text


def strip_timestamp_suffix(name):
    if not name:
        return ""
    cleaned = re.sub(r"[-_\s]+(?:202\d[-_])?\d{10,14}$", "", name.strip())
    return cleaned.strip()


def apply_duplicate_cleanup():
    with app.app_context():
        print("=" * 80)
        print("NEOCARBON PERMANENT DELETION OF IDENTIFIED DUPLICATE RECORDS")
        print("=" * 80)

        total_deleted = 0
        try:
            # 1. CUSTOM FACTORS
            factors = CustomFactor.query.all()
            factor_groups = defaultdict(list)
            for f in factors:
                base = strip_timestamp_suffix(f.name)
                key = (base.lower(), f.facility_id or 0)
                factor_groups[key].append(f)

            factors_deleted = 0
            for (base, fac_id), rows in factor_groups.items():
                rows_sorted = sorted(rows, key=lambda r: r.id)
                canonical = rows_sorted[0]
                cleaned_name = strip_timestamp_suffix(canonical.name)
                if canonical.name != cleaned_name:
                    canonical.name = cleaned_name

                for surplus in rows_sorted[1:]:
                    # Repoint referencing foreign keys to canonical.id
                    db.session.execute(
                        text("UPDATE emissions SET custom_factor_id = :can_id WHERE custom_factor_id = :sur_id"),
                        {"can_id": canonical.id, "sur_id": surplus.id}
                    )
                    db.session.execute(
                        text("UPDATE custom_factors SET parent_factor_id = :can_id WHERE parent_factor_id = :sur_id"),
                        {"can_id": canonical.id, "sur_id": surplus.id}
                    )
                    db.session.execute(
                        text("UPDATE recalculation_requests SET target_factor_id = :can_id WHERE target_factor_id = :sur_id"),
                        {"can_id": canonical.id, "sur_id": surplus.id}
                    )
                    db.session.delete(surplus)
                    factors_deleted += 1

            db.session.flush()
            print(f"Deleted duplicate custom factors: {factors_deleted}")
            total_deleted += factors_deleted

            # 2. MITIGATION PROJECTS
            mits = MitigationProject.query.all()
            mit_groups = defaultdict(list)
            for m in mits:
                base = strip_timestamp_suffix(m.name)
                key = (base.lower(), m.facility_id, m.year)
                mit_groups[key].append(m)

            mits_deleted = 0
            for key, rows in mit_groups.items():
                rows_sorted = sorted(rows, key=lambda r: r.id)
                canonical = rows_sorted[0]
                cleaned_name = strip_timestamp_suffix(canonical.name)
                if canonical.name != cleaned_name:
                    canonical.name = cleaned_name

                for surplus in rows_sorted[1:]:
                    db.session.delete(surplus)
                    mits_deleted += 1

            db.session.flush()
            print(f"Deleted duplicate mitigation projects: {mits_deleted}")
            total_deleted += mits_deleted

            # 3. EMISSION SOURCES
            sources = EmissionSource.query.all()
            src_groups = defaultdict(list)
            for s in sources:
                base = strip_timestamp_suffix(s.name)
                key = (base.lower(), s.facility_id)
                src_groups[key].append(s)

            srcs_deleted = 0
            for key, rows in src_groups.items():
                rows_sorted = sorted(rows, key=lambda r: r.id)
                canonical = rows_sorted[0]
                cleaned_name = strip_timestamp_suffix(canonical.name)
                if canonical.name != cleaned_name:
                    canonical.name = cleaned_name

                for surplus in rows_sorted[1:]:
                    # Repoint ComponentInventory
                    db.session.execute(
                        text("UPDATE component_inventories SET emission_source_id = :can_id WHERE emission_source_id = :sur_id"),
                        {"can_id": canonical.id, "sur_id": surplus.id}
                    )
                    db.session.delete(surplus)
                    srcs_deleted += 1

            db.session.flush()
            print(f"Deleted duplicate emission sources: {srcs_deleted}")
            total_deleted += srcs_deleted

            # 4. SCOPE 3 EMISSIONS
            s3_rows = Scope3Emission.query.all()
            s3_groups = defaultdict(list)
            for s in s3_rows:
                key = (s.facility_id, s.year, s.month, s.category, str(s.sub_category or "").strip().lower(), s.activity_data, s.unit)
                s3_groups[key].append(s)

            s3_deleted = 0
            for key, rows in s3_groups.items():
                rows_sorted = sorted(rows, key=lambda r: r.id)
                for surplus in rows_sorted[1:]:
                    db.session.delete(surplus)
                    s3_deleted += 1

            db.session.flush()
            print(f"Deleted duplicate scope 3 emissions: {s3_deleted}")
            total_deleted += s3_deleted

            # Cryptographically sealed audit log entry
            audit_entry = ActivityLog(
                action="PURGE_DUPLICATES",
                user_name="Administrator",
                details=f"Permanent deletion of {total_deleted} duplicate records ({factors_deleted} factors, {mits_deleted} mitigations, {srcs_deleted} sources, {s3_deleted} Scope 3 rows) per user approval.",
                entity="System",
                entity_id="DuplicatePurge",
                ip_address="127.0.0.1",
            )
            db.session.add(audit_entry)
            db.session.commit()

            print(f"\nSUCCESS: Cleaned up {total_deleted} duplicate records across the database.")
            print("Cryptographically sealed audit log entry created.")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR during duplicate cleanup: {e}")
            sys.exit(1)


if __name__ == "__main__":
    apply_duplicate_cleanup()
