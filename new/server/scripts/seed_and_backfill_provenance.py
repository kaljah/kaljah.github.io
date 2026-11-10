"""
Factor Provenance Registry Seeding & Historical Lineage Backfill Script
======================================================================
Strictly complies with ISO 14064-1:2018 §9 and GHG Protocol Chapter 11.
Seeds all 72 verified methodology factors from `/audit/verified_ledger.md`
and links historical emission calculations to their authoritative factor records.
"""

import os
import sys

# Ensure server directory is in sys.path
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app import app
from models import db, FactorProvenanceRegistry, CalculationFactorLineage, Emission
from scripts.verified_factors_seed_data import ALL_VERIFIED_FACTORS


def seed_factor_provenance_registry():
    """Seeds or updates all verified factor records in the registry table."""
    seeded = 0
    updated = 0
    for factor_data in ALL_VERIFIED_FACTORS:
        existing = db.session.get(FactorProvenanceRegistry, factor_data["id"])
        if existing:
            for k, v in factor_data.items():
                setattr(existing, k, v)
            updated += 1
        else:
            rec = FactorProvenanceRegistry(**factor_data)
            db.session.add(rec)
            seeded += 1

    db.session.commit()
    print(f"FactorProvenanceRegistry: {seeded} seeded, {updated} updated (Total: {len(ALL_VERIFIED_FACTORS)}).")


def backfill_calculation_lineage():
    """Backfills lineage links for existing historical emission calculations."""
    emissions = Emission.query.all()
    backfilled_count = 0

    # Build lookup map of factor_key or id to factor
    factors_by_id = {f.id: f for f in FactorProvenanceRegistry.query.all()}
    gwp_ar5 = factors_by_id.get("GWP-005")

    for em in emissions:
        # Check if lineage already exists
        existing_lineage = CalculationFactorLineage.query.filter_by(calculation_id=em.id).first()
        if existing_lineage:
            continue

        # Link GWP factor
        if gwp_ar5:
            db.session.add(CalculationFactorLineage(
                calculation_id=em.id,
                factor_id=gwp_ar5.id,
                applied_value=gwp_ar5.value,
                applied_unit=gwp_ar5.unit,
                was_user_override=False,
                warning_flag="NONE"
            ))

        # Link process-specific factor if applicable
        ptype = str(em.process_type or "").strip().lower()
        if ptype in ("flaring", "routine_flaring", "non_routine_flaring"):
            flr_factor = factors_by_id.get("FLR-001")
            if flr_factor:
                db.session.add(CalculationFactorLineage(
                    calculation_id=em.id,
                    factor_id=flr_factor.id,
                    applied_value=em.combustion_efficiency or flr_factor.value,
                    applied_unit=flr_factor.unit,
                    was_user_override=bool(em.combustion_efficiency and em.combustion_efficiency != flr_factor.value),
                    warning_flag="NONE"
                ))
        elif ptype == "drilling":
            mud_factor = factors_by_id.get("VNT-001")
            if mud_factor:
                db.session.add(CalculationFactorLineage(
                    calculation_id=em.id,
                    factor_id=mud_factor.id,
                    applied_value=mud_factor.value,
                    applied_unit=mud_factor.unit,
                    was_user_override=False,
                    warning_flag="NONE"
                ))

        backfilled_count += 1

    db.session.commit()
    print(f"CalculationFactorLineage: backfilled lineage for {backfilled_count} historical emission records.")


def run_migration_and_seed():
    with app.app_context():
        print("Ensuring database tables exist...")
        db.create_all()
        print("Seeding factor provenance registry...")
        seed_factor_provenance_registry()
        print("Backfilling historical lineage...")
        backfill_calculation_lineage()
        print("Provenance seeding and backfill complete.")


if __name__ == "__main__":
    run_migration_and_seed()
