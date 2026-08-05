import csv
import random
from datetime import datetime, timedelta

def generate_csv(filepath, num_rows=10000):
    headers = [
        'Date', 'Activity', 'Region', 'Division', 'Field', 
        'Emission Source', 'Equipment ID', 'Process', 'Activity/Fuel', 
        'Factor Type', 'Quantity', 'Unit', 
        'ch4_content', 'co2_content', 'control_efficiency', 'flare_type', 'pneumatic_count'
    ]
    
    activities = ['Upstream', 'Midstream', 'Downstream', 'Production', 'Processing']
    regions = ['ADR', 'REB', 'HBK', 'GTL', 'OHT', 'STAH', 'TFT', 'HMD', 'RNS', 'HRM']
    divisions = ['Div A', 'Div B', 'Div C', 'Exploration', 'Refining', 'Distribution']
    fields = ['Field Alpha', 'Field Beta', 'Field Gamma', 'Eagle Ford', 'Ghawar', 'Troll']
    
    # Process configurations mapping to fuel, unit, and potential tier-3 fields
    processes = [
        {'process': 'Combustion', 'fuels': ['Natural Gas', 'Diesel (No. 2 Fuel Oil)', 'Propane (Gas)'], 'units': ['scf', 'm3', 'gal']},
        {'process': 'Flaring', 'fuels': ['Refinery Fuel Gas', 'Natural Gas'], 'units': ['scf', 'm3', 'mmscf']},
        {'process': 'Venting', 'fuels': ['Natural Gas'], 'units': ['scf', 'm3']},
        {'process': 'Tanks', 'fuels': ['Crude Oil', 'Crude Oil'], 'units': ['bbl', 'gal', 'm3']},
        {'process': 'Fugitive', 'fuels': ['Natural Gas'], 'units': ['kg', 'tonne', 'scf']},
        {'process': 'Pneumatic Devices', 'fuels': ['Natural Gas'], 'units': ['scf']},
        {'process': 'Dehydrators', 'fuels': ['Natural Gas'], 'units': ['scf', 'mmscf']},
        {'process': 'Well Completions', 'fuels': ['Natural Gas'], 'units': ['scf', 'bbl']},
        {'process': 'Liquids Unloading', 'fuels': ['Natural Gas'], 'units': ['scf', 'bbl']},
        {'process': 'Blowdowns', 'fuels': ['Natural Gas'], 'units': ['scf', 'm3']}
    ]

    start_date = datetime(2023, 1, 1)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i in range(num_rows):
            dt = start_date + timedelta(days=random.randint(0, 700))
            date_str = dt.strftime('%Y-%m-%d')
            
            proc = random.choice(processes)
            process_name = proc['process']
            fuel = random.choice(proc['fuels'])
            unit = random.choice(proc['units'])
            
            quantity = round(random.uniform(10.0, 500000.0), 2)
            
            # Uncertainty and engineering parameters
            ch4_c = round(random.uniform(70.0, 95.0), 2) if random.random() > 0.2 else ''
            co2_c = round(random.uniform(0.5, 5.0), 2) if random.random() > 0.2 else ''
            
            ctrl_eff = ''
            f_type = ''
            p_count = ''
            
            if process_name == 'Flaring':
                ctrl_eff = round(random.uniform(95.0, 99.5), 1)
                f_type = random.choice(['Steam-Assisted', 'Air-Assisted', 'Non-Assisted'])
            elif process_name == 'Pneumatic Devices':
                p_count = random.randint(1, 150)
                
            row = [
                date_str,
                random.choice(activities),
                random.choice(regions),
                random.choice(divisions),
                random.choice(fields),
                f"Source Group {random.randint(1,50)}",
                f"EQP-{random.randint(1000,9999)}",
                process_name,
                fuel,
                'default' if random.random() > 0.1 else 'custom',
                quantity,
                unit,
                ch4_c,
                co2_c,
                ctrl_eff,
                f_type,
                p_count
            ]
            writer.writerow(row)
            
    print(f"Generated {num_rows} rows at {filepath}")

if __name__ == '__main__':
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    generate_csv('C:\\Users\\samsung\\Desktop\\h\\10k_exhaust_test.csv', count)
