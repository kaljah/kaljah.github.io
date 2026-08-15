import os
import sys
import pandas as pd
from app import app
from extensions import db
from models import Scope2Emission, Scope3Emission, Facility, User
from background_processor import _process_row_scope2, _process_row_scope3
from electricity_factors import GRID_FACTORS

def test_upload(scope, filename, processor_func):
    print(f"\n======================================")
    print(f"Testing Scope {scope} Upload using {filename}")
    print(f"======================================")
    
    with app.app_context():
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User.query.first()
            
        facilities = Facility.query.all()
        fac_name_map = {f.name.lower(): f for f in facilities}
        fac_id_map = {str(f.id): f for f in facilities}

        df = pd.read_csv(filename)
        # Create a mock mapping (we just use identical keys for our test CSV)
        mapping = {col: col for col in df.columns}
        
        success_count = 0
        error_count = 0
        
        for idx, row in df.iterrows():
            mapped_row = {}
            for target_field, csv_col in mapping.items():
                if pd.notna(row.get(csv_col)):
                    mapped_row[target_field] = row[csv_col]
                    
            if scope == "2":
                emission, errors = processor_func(mapped_row, admin.id, fac_name_map, fac_id_map, GRID_FACTORS)
            else:
                emission, errors = processor_func(mapped_row, admin.id, fac_name_map, fac_id_map)
            
            if errors:
                print(f"Row {idx+1} [ERROR]: {', '.join(errors)}")
                error_count += 1
            else:
                if scope == "2":
                    print(f"Row {idx+1} [SUCCESS]: FacilityID {emission.facility_id} | {emission.source_type} | kWh: {emission.electricity_kwh} | MMBtu: {emission.heat_mmbtu} | CO2e: {emission.co2e}")
                else:
                    print(f"Row {idx+1} [SUCCESS]: FacilityID {emission.facility_id} | Cat: {emission.category} | CO2e: {emission.co2e}")
                success_count += 1
                db.session.add(emission)
                
        print(f"\nResults for Scope {scope}:")
        print(f"Success: {success_count}")
        print(f"Errors: {error_count}")
        
        # Rollback so we don't actually dirty the database with test data
        db.session.rollback()

if __name__ == "__main__":
    test_upload("2", "test_scope2.csv", _process_row_scope2)
    test_upload("3", "test_scope3.csv", _process_row_scope3)
