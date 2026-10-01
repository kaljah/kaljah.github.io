"""Test harness for the Scope 1 bulk-import audit.

Points the Flask app at an isolated SQLite file, seeds the fixtures the CSV refers to
(admin user, facilities, custom factors) and can run a CSV through the real import
thread (background_processor._process_file_thread) synchronously.

Usage (library):  from harness import boot; app = boot("/path/db.sqlite")
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.abspath(os.path.join(HERE, "..", "..", "new", "server"))

ADMIN_EMAIL = "audit.admin@ghg.test"
ADMIN_PASSWORD = "Audit-Passw0rd!2026"

# Facilities referenced by the CSV (names exercise apostrophes, accents, spaces, digits)
FACILITIES = [
    ("Hassi Messaoud Gas Plant", "HMD-GP", "Ouargla", "Production", "Upstream"),
    ("Hassi R'Mel Hub", "HRM-HUB", "Laghouat", "Production", "Upstream"),
    ("In Amenas CPF", "IAM-CPF", "Illizi", "Production", "Upstream"),
    ("Arzew GNL-1Z", "ARZ-GNL1Z", "Oran", "LNG", "Midstream"),
    ("Skikda Raffinerie", "SKK-RA1K", "Skikda", "Refining", "Downstream"),
    ("Béjaïa Terminal", "BJA-TERM", "Béjaïa", "Transport", "Midstream"),
    ("Rhourde Nouss Complex", "RNS-CPX", "Illizi", "Production", "Upstream"),
    ("Tin Fouyé Tabankort", "TFT-01", "Illizi", "Production", "Upstream"),
    ("Gassi Touil Field", "GTL-FLD", "Ouargla", "Production", "Upstream"),
    ("Ohanet Gas Plant 2", "OHN-GP2", "Illizi", "Production", "Upstream"),
    ("Krechba CO2 Site", "KRB-CCS", "In Salah", "CCUS", "Upstream"),
    ("Alrar Compression Station", "ALR-CS", "Illizi", "Transport", "Midstream"),
]

# Custom (Tier 2) factors: every factor-unit shape the parser accepts.
# (name, co2, ch4, n2o, unit, hhv, parent_fuel)
CUSTOM_FACTORS = [
    ("CF Gas kg/MMBtu", 52.9, 0.0012, 0.00011, "kg/MMBtu", 1035, "Natural Gas"),
    ("CF Diesel kg/MMBtu", 74.1, 0.0031, 0.00062, "kg/MMBtu", 137500, "Diesel (No. 2 Fuel Oil)"),
    ("CF Coal kg/MMBtu", 95.0, 0.0105, 0.0015, "kg/MMBtu", 24000, "Bituminous Coal"),
    ("CF Gas kg/GJ", 50.3, 0.0011, 0.0001, "kg/GJ", None, None),
    ("CF Power kg/kWh", 0.181, 0.000003, 0.0000003, "kg/kWh", None, None),
    ("CF Heat kg/MJ", 0.0561, 0.000001, 0.0000001, "kg/MJ", None, None),
    ("CF Therm kg/therm", 5.31, 0.0001, 0.00001, "kg/therm", None, None),
    ("CF Gas kg/scf", 0.05444, 0.0000010, 0.0000001, "kg/scf", None, None),
    ("CF Gas kg/m3", 1.9225, 0.000036, 0.0000036, "kg/m3", None, None),
    ("CF Gas tonne/MMscf", 54.44, 0.00104, 0.000103, "tonne/MMscf", None, None),
    ("CF Gas kg/Mscf", 54.44, 0.00104, 0.000103, "kg/Mscf", None, None),
    ("CF Liquid kg/gal", 10.21, 0.00041, 0.000083, "kg/gal", None, None),
    ("CF Liquid kg/bbl", 428.9, 0.0174, 0.0035, "kg/bbl", None, None),
    ("CF Liquid kg/L", 2.697, 0.00011, 0.000022, "kg/L", None, None),
    ("CF Solid kg/tonne", 2420.0, 0.25, 0.037, "kg/tonne", None, None),
    ("CF Solid kg/kg", 2.42, 0.00025, 0.000037, "kg/kg", None, None),
    ("CF Solid lb/short_ton", 4840.0, 0.5, 0.074, "lb/short_ton", None, None),
    ("CF Solid kg/lb", 1.0977, 0.000113, 0.0000168, "kg/lb", None, None),
    ("CF Vent tonne CH4/event", 0.0, 0.215, 0.0, "tonne/event", None, None),
    ("CF Well tonne/well", 0.01, 1.32, 0.0, "tonne/well", None, None),
    ("CF Device kg/device", 0.0, 41.7, 0.0, "kg/device", None, None),
    ("CF Bare unit scf", 0.0549, 0.0000011, 0.0000001, "scf", None, None),  # Manage Data "kg per scf" convention
    ("CF Bare unit tonne", 2400.0, 0.2, 0.03, "tonne", None, None),
    ("CF g/MJ", 56.1, 0.001, 0.0001, "g/MJ", None, None),
]


def boot(db_path, fresh=True):
    """Configure env, import the app and seed fixtures. Returns the Flask app."""
    if db_path.startswith(("postgresql", "postgres://")):
        # PostgreSQL: DB_TYPE=postgres + DATABASE_URL; a fresh run starts from an empty public schema
        if fresh:
            import sqlalchemy as sa
            eng = sa.create_engine(db_path)
            with eng.begin() as c:
                c.execute(sa.text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
            eng.dispose()
        os.environ["DB_TYPE"] = "postgres"
        os.environ["DATABASE_URL"] = db_path
    else:
        if fresh and os.path.exists(db_path):
            for suffix in ("", "-wal", "-shm"):
                try:
                    os.remove(db_path + suffix)
                except OSError:
                    pass
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path
    os.environ.setdefault("SECRET_KEY", "audit-secret-key-not-for-production")
    os.environ["SEED_ADMIN"] = "false"
    os.environ.setdefault("FLASK_ENV", "development")
    if SERVER not in sys.path:
        sys.path.insert(0, SERVER)
    os.chdir(SERVER)
    import logging

    logging.disable(logging.WARNING)
    from app import app

    seed(app)
    return app


def seed(app):
    from werkzeug.security import generate_password_hash

    from extensions import db
    from models import CustomFactor, Facility, User

    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(email=ADMIN_EMAIL).first()
        if not admin:
            admin = User(fullName="Audit Admin", orgName="Audit", sector="Oil & Gas", email=ADMIN_EMAIL,
                         role="admin", status="active", password_hash=generate_password_hash(ADMIN_PASSWORD))
            db.session.add(admin)
            db.session.flush()
        for name, code, region, division, segment in FACILITIES:
            if not Facility.query.filter_by(code=code).first():
                db.session.add(Facility(name=name, code=code, region=region, division=division, segment=segment,
                                        activity="Exploration & Production", field=name.split()[0],
                                        location=region, created_by=admin.id))
        for name, co2, ch4, n2o, unit, hhv, parent in CUSTOM_FACTORS:
            if not CustomFactor.query.filter_by(name=name).first():
                db.session.add(CustomFactor(name=name, co2_factor=co2, ch4_factor=ch4, n2o_factor=n2o, unit=unit,
                                            hhv_factor=hhv, parent_fuel=parent, source="Audit fixture",
                                            usage="combustion", created_by=admin.id, uncertainty=5.0))
        db.session.commit()
        return admin.id


def run_csv(app, csv_path, global_factor_type="auto", mapping=None):
    """Run one file through the real import thread, synchronously. Returns the job status dict
    plus the skipped rows ({row, reason, ...}) and the error CSV path."""
    import time
    import uuid

    import background_processor as bp
    from models import User

    with app.app_context():
        uid = User.query.filter_by(email=ADMIN_EMAIL).first().id
    job_id = str(uuid.uuid4())
    with bp.upload_jobs_lock:
        bp.upload_jobs[job_id] = {"status": "processing", "progress": 0, "processed": 0, "total": 0, "errors": [],
                                  "skipped": [], "error_csv_path": None, "anomalies": [],
                                  "created_at": time.time(), "owner_id": uid}
    import shutil
    import tempfile

    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(csv_path)[1] or ".csv")
    os.close(fd)
    shutil.copy(csv_path, tmp)
    t0 = time.time()
    bp._process_file_thread(app, job_id, tmp, os.path.basename(csv_path), uid, global_factor_type, mapping, "1", False)
    with bp.upload_jobs_lock:
        job = dict(bp.upload_jobs[job_id])
    job["elapsed_s"] = time.time() - t0
    return job
