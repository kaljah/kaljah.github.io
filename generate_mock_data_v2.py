import csv
import random

regions_file = 'regions_upload.csv'

combinations = []
fields_set = set()

with open(regions_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        region = row.get('Region Name', '').strip()
        activity = row.get('Activity', '').strip()
        division = row.get('Division', '').strip()
        field = row.get('Field / Block', '').strip()
        
        if region and activity and division:
            combinations.append({
                'region': region,
                'activity': activity,
                'division': division,
                'field': field if field else 'Block A'
            })
            if field:
                fields_set.add(field)

if not fields_set:
    fields_set = {'Field A', 'Field B'}

months = list(range(1, 13))
years = [2022, 2023, 2024, 2025]

# 1. Production Data (10,000 rows)
print('Generating production_data_v2.csv...')
with open('production_data_v2.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Region', 'Activity', 'Division', 'Field', 'Year', 'Month', 'Oil Quantity', 'Oil Unit', 'Gas Quantity', 'Gas Unit'])
    
    # Need 10,000 unique combinations of (Region, Year, Month)
    # Loop over combinations, years, and months systematically
    count = 0
    start_year = 1900
    while count < 10000:
        for combo in combinations:
            for y in range(start_year, start_year + 50):
                for m in range(1, 13):
                    if count >= 10000:
                        break
                    writer.writerow([
                        combo['region'],
                        combo['activity'],
                        combo['division'],
                        combo['field'],
                        y,
                        m,
                        round(random.uniform(1000, 50000), 2),
                        'bbl',
                        round(random.uniform(5000, 200000), 2),
                        'mscf'
                    ])
                    count += 1
                if count >= 10000:
                    break
            if count >= 10000:
                break
        start_year += 50

# 2. Emission Sources (10,000 rows)
print('Generating emission_sources_v2.csv...')
processes = ['combustion', 'flaring', 'venting', 'fugitive', 'drilling']
fuels = ['Natural Gas', 'Diesel', 'Fuel Gas', 'Propane', '']
with open('emission_sources_v2.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Activity', 'Division', 'Region', 'Field', 'Equipment Name', 'Equipment ID', 'Process Type', 'Fuel Type', 'Quantity', 'Unit', 'Year', 'Month'])
    for i in range(10000):
        combo = random.choice(combinations)
        ptype = random.choice(processes)
        fuel = random.choice(fuels) if ptype in ['combustion', 'flaring'] else ''
        unit = 'scf' if fuel == 'Natural Gas' else ('gal' if fuel else '')
        writer.writerow([
            combo['activity'],
            combo['division'],
            combo['region'],
            combo['field'],
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
print('Generating mitigation_projects_v2.csv...')
proj_types = ['CCUS', 'REC', 'Energy Efficiency', 'Flare Reduction', 'Leak Detection']
statuses = ['Active', 'Planned', 'Completed', 'On Hold']
with open('mitigation_projects_v2.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Region', 'Project Name', 'Type', 'Year', 'tCO2e Avoided', 'Status', 'Start Date', 'End Date', 'Investment', 'Description'])
    for i in range(10000):
        combo = random.choice(combinations)
        writer.writerow([
            combo['region'],
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

print('Done!')
