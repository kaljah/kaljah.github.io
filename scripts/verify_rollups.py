import sys, os
sys.path.insert(0, os.path.abspath('scripts'))

from populate_sources_hbns import hbns_sources
from populate_sources_elm import elm_sources

print("=== HBNS Module Rollup Check ===")
hbns_by_mod = {}
for s in hbns_sources:
    mod = s['module']
    if mod not in hbns_by_mod:
        hbns_by_mod[mod] = {'co2': 0.0, 'ch4': 0.0, 'n2o': 0.0, 'co2e': 0.0}
    hbns_by_mod[mod]['co2'] += s['rep_co2']
    hbns_by_mod[mod]['ch4'] += s['rep_ch4']
    hbns_by_mod[mod]['n2o'] += s['rep_n2o']
    hbns_by_mod[mod]['co2e'] += s['rep_co2e']

for mod, vals in hbns_by_mod.items():
    print(f"{mod:30s} | CO2={vals['co2']:10.2f} | CH4={vals['ch4']:8.2f} | N2O={vals['n2o']:6.2f} | CO2e={vals['co2e']:10.2f}")

print("\n=== El Merk Module Rollup Check ===")
elm_by_mod = {}
for s in elm_sources:
    mod = s['module']
    if mod not in elm_by_mod:
        elm_by_mod[mod] = {'co2': 0.0, 'ch4': 0.0, 'n2o': 0.0, 'co2e': 0.0}
    elm_by_mod[mod]['co2'] += s['rep_co2']
    elm_by_mod[mod]['ch4'] += s['rep_ch4']
    elm_by_mod[mod]['n2o'] += s['rep_n2o']
    elm_by_mod[mod]['co2e'] += s['rep_co2e']

for mod, vals in elm_by_mod.items():
    print(f"{mod:30s} | CO2={vals['co2']:10.2f} | CH4={vals['ch4']:8.2f} | N2O={vals['n2o']:6.2f} | CO2e={vals['co2e']:10.2f}")
