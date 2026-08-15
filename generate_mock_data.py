import csv
import random

# Regions, Activities, Divisions etc for realistic data
regions = ["Hassi Messaoud", "Hassi R'Mel", "Rhourde Nouss", "In Salah", "Illizi", "Berkine", "Adrar"]
activities = ['Exploration & Production', 'Refining', 'Transportation', 'Marketing']
divisions = ['Production', 'Drilling', 'Logistics', 'Operations']
fields = ['Field A', 'Field B', 'Block 1', 'Block 2', 'Area X', 'Area Y']
months = list(range(1, 13))
years = [2022, 2023, 2024, 2025]

# 1. Production Data (10,000 rows)
print('Generating production_data.csv...')
with open('production_data.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Region', 'Activity', 'Division', 'Field', 'Year', 'Month', 'Oil Quantity', 'Oil Unit', 'Gas Quantity', 'Gas Unit'])
    for _ in range(10000):
        writer.writerow([
            random.choice(regions),
            random.choice(activities),
            random.choice(divisions),
            random.choice(fields),
            random.choice(years),
            random.choice(months),
            round(random.uniform(1000, 50000), 2),
            'bbl',
            round(random.uniform(5000, 200000), 2),
            'mscf'
        ])

# 2. Emission Sources (10,000 rows)
print('Generating emission_sources.csv...')
processes = ['combustion', 'flaring', 'venting', 'fugitive', 'drilling']
fuels = ['Natural Gas', 'Diesel', 'Fuel Gas', 'Propane', '']
with open('emission_sources.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Activity', 'Division', 'Region', 'Field', 'Equipment Name', 'Equipment ID', 'Process Type', 'Fuel Type', 'Quantity', 'Unit', 'Year', 'Month'])
    for i in range(10000):
        ptype = random.choice(processes)
        fuel = random.choice(fuels) if ptype in ['combustion', 'flaring'] else ''
        unit = 'scf' if fuel == 'Natural Gas' else ('gal' if fuel else '')
        writer.writerow([
            random.choice(activities),
            random.choice(divisions),
            random.choice(regions),
            random.choice(fields),
            f'Equipment-{i}',
            f'EQ-{i:05d}',
            ptype,
            fuel,
            round(random.uniform(10, 10000), 2),
            unit,
            random.choice(years),
            random.choice(months)
        ])

# 3. Mitigation Projects (10,000 rows)
print('Generating mitigation_projects.csv...')
proj_types = ['CCUS', 'REC', 'Energy Efficiency', 'Flare Reduction', 'Leak Detection']
statuses = ['Active', 'Planned', 'Completed', 'On Hold']
with open('mitigation_projects.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Region', 'Project Name', 'Type', 'Year', 'tCO2e Avoided', 'Status', 'Start Date', 'End Date', 'Investment', 'Description'])
    for i in range(10000):
        writer.writerow([
            random.choice(regions),
            f'Mitigation Project {i}',
            random.choice(proj_types),
            random.choice(years),
            round(random.uniform(100, 50000), 2),
            random.choice(statuses),
            f'{random.choice(years)}-01-01',
            f'{random.choice(years)+2}-12-31',
            round(random.uniform(10000, 5000000), 2),
            'Mock description of project'
        ])

# 4. Custom Factors (500 rows)
print('Generating custom_factors.csv...')
factor_units = ['scf', 'm3', 'gal', 'bbl', 'tonnes']
apply_tos = ['combustion', 'flaring', 'fugitive', 'venting']
with open('custom_factors.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Factor Name', 'Parent API Fuel', 'Unit', 'co2_factor', 'ch4_factor', 'n2o_factor', 'min_val', 'max_val', 'typical_val', 'default_efficiency', 'apply_to'])
    for i in range(500):
        writer.writerow([
            f'Custom Gas Factor {i}',
            random.choice(fuels),
            random.choice(factor_units),
            round(random.uniform(0.1, 150.0), 4),
            round(random.uniform(0.0001, 0.5), 6),
            round(random.uniform(0.00001, 0.05), 6),
            0,
            100,
            50,
            98,
            random.choice(apply_tos)
        ])

print('Done!')
