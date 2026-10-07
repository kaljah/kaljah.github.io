import sys
import sqlite3
import datetime
import argparse

def get_connection():
    return sqlite3.connect('new/server/ghg_app.db')

def seed1():
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Clean previous test record if exists
    c.execute("DELETE FROM emissions WHERE record_id = 'E2E-MC-S1-001'")
    c.execute('''
        INSERT INTO emissions (
            record_id, year, month, facility_id, process_type, fuel_type,
            quantity, unit, co2e_total, status, created_by, timestamp, ef_used_co2
        ) VALUES ('E2E-MC-S1-001', 2025, 6, 1, 'Stationary Combustion', 'Diesel Fuel Oil', 12500.0, 'liters', 33.5, 'Pending', 2, ?, 2.68)
    ''', (now,))
    conn.commit()
    conn.close()
    print("SEED1_OK")

def seed2():
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c.execute("DELETE FROM scope2_emissions WHERE electricity_kwh = 95000.0")
    c.execute('''
        INSERT INTO scope2_emissions (
            facility_id, year, month, source_type, electricity_kwh,
            emission_factor, co2e, qa_flag, created_by, status, created_at
        ) VALUES (2, 2025, 7, 'Purchased Electricity', 95000.0, 0.54, 51.3, 'Missing Utility Invoice', 2, 'Pending', ?)
    ''', (now,))
    conn.commit()
    conn.close()
    print("SEED2_OK")

def seed_wizard():
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c.execute("DELETE FROM emissions WHERE record_id = 'E2E-WIZARD-001'")
    c.execute("DELETE FROM scope2_emissions WHERE electricity_kwh = 12000.0")
    c.execute('''
        INSERT INTO emissions (
            record_id, year, month, facility_id, process_type, fuel_type,
            quantity, unit, co2e_total, status, created_by, timestamp
        ) VALUES ('E2E-WIZARD-001', 2025, 8, 3, 'Flaring Operations', 'Associated Gas Flared', 5000.0, 'm3', 13.9, 'Pending', 2, ?)
    ''', (now,))
    c.execute('''
        INSERT INTO scope2_emissions (
            facility_id, year, month, source_type, electricity_kwh,
            emission_factor, co2e, created_by, status, created_at
        ) VALUES (1, 2025, 8, 'Imported Heat', 12000.0, 0.45, 5.4, 2, 'Pending', ?)
    ''', (now,))
    conn.commit()
    conn.close()
    print("SEED_WIZARD_OK")

def check_s1():
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT status, approved_by FROM emissions WHERE record_id = 'E2E-MC-S1-001'").fetchone()
    conn.close()
    if row:
        print(f"{row[0]}:{row[1]}")
    else:
        print("NOT_FOUND")

def check_s2():
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT status FROM scope2_emissions WHERE electricity_kwh = 95000.0").fetchone()
    conn.close()
    if row:
        print(f"{row[0]}")
    else:
        print("NOT_FOUND")

def clean():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM emissions WHERE record_id IN ('E2E-MC-S1-001', 'E2E-WIZARD-001')")
    c.execute("DELETE FROM scope2_emissions WHERE electricity_kwh IN (95000.0, 12000.0)")
    conn.commit()
    conn.close()
    print("CLEAN_OK")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=["seed1", "seed2", "seed_wizard", "check_s1", "check_s2", "clean"])
    args = parser.parse_args()

    actions = {
        "seed1": seed1,
        "seed2": seed2,
        "seed_wizard": seed_wizard,
        "check_s1": check_s1,
        "check_s2": check_s2,
        "clean": clean
    }
    actions[args.action]()
