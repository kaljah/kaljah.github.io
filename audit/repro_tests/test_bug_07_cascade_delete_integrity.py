"""
Reproduction Test: BUG-07 / BACK-07
Foreign keys in new/server/models.py lack ON DELETE CASCADE / SET NULL.
With PRAGMA foreign_keys = ON enabled in app.py, deleting a facility with related emissions
raises a fatal sqlite3.IntegrityError: FOREIGN KEY constraint failed.
"""

import sys
import pytest
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, "new/server")

def test_facility_delete_foreign_key_violation():
    from app import app, db
    from models import Facility, Emission

    with app.app_context():
        # Create a test facility and emission
        fac = Facility(
            name="Cascade Test Facility",
            segment="Upstream",
            country="Algeria",
            region="Hassi Messaoud",
            is_test=True
        )
        db.session.add(fac)
        db.session.flush()

        em = Emission(
            facility_id=fac.id,
            year=2025,
            month=1,
            process_type="combustion",
            quantity=100.0,
            unit="m3",
            co2_emissions=10.0,
            co2e_total=10.0,
            status="Draft",
            is_test=True
        )
        db.session.add(em)
        db.session.commit()

        fac_id = fac.id

        # Attempt to delete the parent facility via SQL execution without manually deleting child records
        try:
            from sqlalchemy import text
            db.session.execute(text(f"DELETE FROM facilities WHERE id = {fac_id}"))
            db.session.commit()
            pytest.fail("Expected IntegrityError: FOREIGN KEY constraint failed, but deletion succeeded")
        except IntegrityError as exc:
            db.session.rollback()
            print("Confirmed: Foreign key violation raised on deleting parent facility via SQL:", exc)
            assert "FOREIGN KEY constraint failed" in str(exc)
        finally:
            # Cleanup test records
            try:
                Emission.query.filter_by(facility_id=fac_id).delete()
                Facility.query.filter_by(id=fac_id).delete()
                db.session.commit()
            except Exception:
                db.session.rollback()
