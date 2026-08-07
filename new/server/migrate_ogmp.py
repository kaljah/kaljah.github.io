import sys
import os
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from extensions import db
from models import MethaneSourceType, Facility, Emission, OgmpSurvey, LevelUpgradeLog

STANDARD_OGMP_SOURCES = [
    {
        "code": "PNEUMATIC_DEVICE",
        "name": "Pneumatic Controllers & Pumps",
        "category": "vented",
        "default_ef_reference": "API Compendium 2021 Table 5-15",
        "default_level": 3
    },
    {
        "code": "COMPRESSOR_SEAL",
        "name": "Centrifugal & Reciprocating Compressor Seals",
        "category": "vented",
        "default_ef_reference": "API Compendium 2021 Table 5-9",
        "default_level": 3
    },
    {
        "code": "TANK_VENTING",
        "name": "Atmospheric Storage Tank Venting & Flash Gas",
        "category": "vented",
        "default_ef_reference": "API Compendium 2021 Table 5-12",
        "default_level": 3
    },
    {
        "code": "WELL_VENTING",
        "name": "Well Workovers, Completions & Blowdowns",
        "category": "vented",
        "default_ef_reference": "API Compendium 2021 Table 5-4",
        "default_level": 3
    },
    {
        "code": "FLARE_UNCOMBUSTED",
        "name": "Flaring Incomplete Combustion (CH4 Slip)",
        "category": "flaring",
        "default_ef_reference": "API Compendium 2021 Table 4-1 (98% DRE)",
        "default_level": 3
    },
    {
        "code": "FUGITIVE_VALVE",
        "name": "Fugitive Valve & Flange Leaks",
        "category": "fugitive",
        "default_ef_reference": "API Compendium 2021 Table 6-1",
        "default_level": 3
    },
    {
        "code": "LDAR_LEAK",
        "name": "LDAR Detected Component Leaks (Method 21 / OGI)",
        "category": "fugitive",
        "default_ef_reference": "EPA Protocol for Equipment Leak Estimates",
        "default_level": 4
    },
    {
        "code": "COMBUSTION_SLIP",
        "name": "Internal Combustion Engine & Turbine CH4 Slip",
        "category": "combustion_slip",
        "default_ef_reference": "API Compendium 2021 Table 3-5",
        "default_level": 3
    }
]

def migrate_database():
    with app.app_context():
        # 1. Create any missing tables
        db.create_all()

        # 2. Add columns if missing in SQLite
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///ghg_app.db').replace('sqlite:///', '')
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Facility table columns
            cur.execute("PRAGMA table_info(facilities)")
            fac_cols = [c[1] for c in cur.fetchall()]
            if 'operator_status' not in fac_cols:
                cur.execute("ALTER TABLE facilities ADD COLUMN operator_status VARCHAR(20) DEFAULT 'operated'")
            if 'country' not in fac_cols:
                cur.execute("ALTER TABLE facilities ADD COLUMN country VARCHAR(100) DEFAULT 'Algeria'")
            if 'ogmp_membership_year' not in fac_cols:
                cur.execute("ALTER TABLE facilities ADD COLUMN ogmp_membership_year INTEGER DEFAULT 2023")
            if 'reconciliation_threshold' not in fac_cols:
                cur.execute("ALTER TABLE facilities ADD COLUMN reconciliation_threshold FLOAT DEFAULT 20.0")

            # Emission table columns
            cur.execute("PRAGMA table_info(emissions)")
            em_cols = [c[1] for c in cur.fetchall()]
            if 'ogmp_level' not in em_cols:
                cur.execute("ALTER TABLE emissions ADD COLUMN ogmp_level INTEGER DEFAULT 3")
            if 'source_type_code' not in em_cols:
                cur.execute("ALTER TABLE emissions ADD COLUMN source_type_code VARCHAR(50)")
            if 'data_source_ref' not in em_cols:
                cur.execute("ALTER TABLE emissions ADD COLUMN data_source_ref VARCHAR(120)")

            # OgmpSurvey table columns
            cur.execute("PRAGMA table_info(ogmp_surveys)")
            ogmp_cols = [c[1] for c in cur.fetchall()]
            if 'operating_hours_year' not in ogmp_cols:
                cur.execute("ALTER TABLE ogmp_surveys ADD COLUMN operating_hours_year FLOAT DEFAULT 8760.0")
            if 'detection_threshold' not in ogmp_cols:
                cur.execute("ALTER TABLE ogmp_surveys ADD COLUMN detection_threshold FLOAT")
            if 'instrument_vendor' not in ogmp_cols:
                cur.execute("ALTER TABLE ogmp_surveys ADD COLUMN instrument_vendor VARCHAR(100)")
            if 'raw_file_ref' not in ogmp_cols:
                cur.execute("ALTER TABLE ogmp_surveys ADD COLUMN raw_file_ref VARCHAR(255)")
            if 'bottom_up_tch4' not in ogmp_cols:
                cur.execute("ALTER TABLE ogmp_surveys ADD COLUMN bottom_up_tch4 FLOAT DEFAULT 0.0")
            if 'variance_pct' not in ogmp_cols:
                cur.execute("ALTER TABLE ogmp_surveys ADD COLUMN variance_pct FLOAT DEFAULT 0.0")
            if 'variance_flag' not in ogmp_cols:
                cur.execute("ALTER TABLE ogmp_surveys ADD COLUMN variance_flag BOOLEAN DEFAULT 0")
            if 'status' not in ogmp_cols:
                cur.execute("ALTER TABLE ogmp_surveys ADD COLUMN status VARCHAR(50) DEFAULT 'pending'")

            conn.commit()
            conn.close()
            print("SQLite schema columns successfully migrated.")

        # 3. Seed OGMP standard taxonomy
        for item in STANDARD_OGMP_SOURCES:
            existing = MethaneSourceType.query.filter_by(code=item['code']).first()
            if not existing:
                src = MethaneSourceType(
                    code=item['code'],
                    name=item['name'],
                    category=item['category'],
                    default_ef_reference=item['default_ef_reference'],
                    default_level=item['default_level']
                )
                db.session.add(src)
        db.session.commit()
        print(f"OGMP standard source taxonomy seeded ({len(STANDARD_OGMP_SOURCES)} categories).")

if __name__ == '__main__':
    migrate_database()
