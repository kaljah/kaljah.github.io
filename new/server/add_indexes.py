import sqlite3
import time

def create_indexes():
    db_path = "ghg_app.db"
    
    queries = [
        "CREATE INDEX IF NOT EXISTS ix_emissions_activity ON emissions(activity);",
        "CREATE INDEX IF NOT EXISTS ix_emissions_division ON emissions(division);",
        "CREATE INDEX IF NOT EXISTS ix_production_data_activity ON production_data(activity);",
        "CREATE INDEX IF NOT EXISTS ix_production_data_division ON production_data(division);",
        "CREATE INDEX IF NOT EXISTS ix_production_data_facility_id ON production_data(facility_id);",
        "CREATE INDEX IF NOT EXISTS ix_production_data_year ON production_data(year);",
        "CREATE INDEX IF NOT EXISTS ix_scope2_emissions_activity ON scope2_emissions(activity);",
        "CREATE INDEX IF NOT EXISTS ix_scope2_emissions_division ON scope2_emissions(division);",
        "CREATE INDEX IF NOT EXISTS ix_scope2_emissions_status ON scope2_emissions(status);",
        "CREATE INDEX IF NOT EXISTS ix_scope3_emissions_facility_id ON scope3_emissions(facility_id);",
        "CREATE INDEX IF NOT EXISTS ix_scope3_emissions_status ON scope3_emissions(status);"
    ]
    
    print("Connecting to DB...")
    t0 = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for i, q in enumerate(queries):
        try:
            print(f"Executing: {q}")
            cursor.execute(q)
        except Exception as e:
            print(f"Error on {q}: {e}")
            
    conn.commit()
    conn.close()
    
    t1 = time.time()
    print(f"Successfully added indexes in {t1-t0:.2f}s")

if __name__ == '__main__':
    create_indexes()
