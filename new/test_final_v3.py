import os
import sys
import sqlite3
import csv
import types

# 1. Path setup
server_dir = os.path.join(os.path.dirname(__file__), 'server')
sys.path.insert(0, server_dir)

# 2. Mock DB to bypass flask completely
class MockSession:
    def bulk_save_objects(self, objects): pass
    def commit(self): pass

class MockDB:
    def __init__(self):
        self.session = MockSession()

mock_extensions = types.ModuleType('extensions')
mock_extensions.db = MockDB()
sys.modules['extensions'] = mock_extensions

from background_processor import _process_row
from calculations import compute_emissions
from emission_factors import API_FACTORS
from calculations.constants import get_active_gwp

# 3. Load facilities from real DB
db_path = os.path.join(server_dir, 'ghg_app.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT id, name FROM facilities")
all_facilities = cur.fetchall()

class DummyFacility:
    def __init__(self, fid, name):
        self.id = fid
        self.name = name

fac_name_map = {}
fac_id_map = {}
for fid, fname in all_facilities:
    f = DummyFacility(fid, fname)
    fac_name_map[fname.lower()] = f
    fac_id_map[str(fid)] = f
conn.close()

user_id = 1
cf_name_map = {}
gwp_dict = get_active_gwp()

CSV_FILE = r"C:\Users\samsung\Desktop\H2\1k_scope1_comprehensive_test.csv"
mapping = {
    "date": "date", "year": "year", "month": "month",
    "facility_name": "facility_name", "activity": "activity",
    "division": "division", "field": "field", "group": "group",
    "equipment": "equipment", "equipment_id": "equipment_id",
    "process": "process", "fuel": "fuel", "quantity": "quantity",
    "unit": "unit", "factor_type": "factor_type",
    "c1": "c1", "c2": "c2", "c3": "c3", "c4": "c4", "c5": "c5", "c6": "c6",
    "co2_mol": "co2_mol", "n2_mol": "n2_mol", "hhv": "hhv",
    "combustion_efficiency": "combustion_efficiency", "flare_type": "flare_type",
    "ch4_content": "ch4_content", "co2_content": "co2_content",
    "control_efficiency": "control_efficiency", "operating_temperature": "operating_temperature",
    "temp_unit": "temp_unit", "operating_pressure": "operating_pressure",
    "press_unit": "press_unit", "z_factor": "z_factor",
    "pneu_type": "pneu_type", "pneu_count": "pneu_count",
    "pneu_bleed_rate": "pneu_bleed_rate", "pneu_hours": "pneu_hours",
    "tank_gor": "tank_gor", "tank_ch4_content": "tank_ch4_content",
    "tank_control_eff": "tank_control_eff", "tank_api_gravity": "tank_api_gravity",
    "fugitive_method": "fugitive_method", "fugitive_ppm": "fugitive_ppm",
    "comp_count": "comp_count", "operating_hours": "operating_hours",
    "leak_count": "leak_count", "leak_duration": "leak_duration",
    "leak_rate": "leak_rate", "comp_method": "comp_method",
    "comp_rate": "comp_rate", "comp_duration": "comp_duration",
    "comp_flare_eff": "comp_flare_eff", "blowdown_pressure": "blowdown_pressure",
    "blowdown_events": "blowdown_events", "blowdown_temp": "blowdown_temp",
    "dehy_pump_rate": "dehy_pump_rate", "dehy_hours": "dehy_hours",
    "dehy_press": "dehy_press", "dehy_temp": "dehy_temp",
    "dehy_ch4_content": "dehy_ch4_content", "dehy_eff": "dehy_eff",
    "agr_co2_in": "agr_co2_in", "agr_co2_out": "agr_co2_out",
    "agr_ch4_in": "agr_ch4_in", "agr_ch4_slip": "agr_ch4_slip",
    "agr_control_eff": "agr_control_eff",
}

success_count = 0
skipped_count = 0
errors_by_type = {}

print("Validating 1000 CSV rows through backend _process_row() pipeline...")

with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        mapped_data = {}
        for sys_key, header_name in mapping.items():
            if header_name and header_name in row:
                mapped_data[sys_key] = row[header_name]
                
        # Send it to the exact row validator from background_processor
        emission_obj, row_errors = _process_row(
            row=mapped_data,
            user_id=user_id,
            fac_name_map=fac_name_map,
            fac_id_map=fac_id_map,
            cf_name_map=cf_name_map,
            compute_emissions_fn=compute_emissions,
            API_FACTORS_dict=API_FACTORS,
            global_factor_type="auto",
            gwp_dict=gwp_dict,
            gwp_std="AR5"
        )
        
        if row_errors:
            skipped_count += 1
            error_reason = "; ".join(row_errors)
            
            # Map specific strings back to categories for summary
            category = "Other"
            if "Missing valid date or year" in error_reason: category = "Missing Year"
            elif "Missing month" in error_reason: category = "Missing Month"
            elif "Region" in error_reason and "not found" in error_reason: category = "Invalid Region"
            elif "Invalid quantity" in error_reason: category = "Invalid Quantity"
            elif "Missing process type" in error_reason or "Invalid process type" in error_reason: category = "Missing Process"
            elif "factor" in error_reason.lower() or "fuel" in error_reason.lower() or "not found in api compendium" in error_reason.lower(): category = "Missing Fuel / Emission Factor"
            else: category = error_reason
            
            errors_by_type[category] = errors_by_type.get(category, 0) + 1
        elif emission_obj:
            success_count += 1

print("\n--- TEST RESULTS ---")
print(f"Total Rows Checked: {success_count + skipped_count}")
print(f"Successfully Validated (Ready to DB Insert): {success_count}")
print(f"Skipped Rows (Caught by Validation): {skipped_count}")
print("\nError Breakdown:")
for cat, count in errors_by_type.items():
    print(f"  - {cat}: {count}")
