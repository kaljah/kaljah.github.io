path = 'new/client/src/pages/CarbonIntensity.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update interface
old_def = """    totalBoe: number;
    totalFlaringVolume: number;
    // the intensity numerators:"""

new_def = """    totalBoe: number;
    totalFlaringVolume: number;
    totalFlaringLedgerVolume: number;
    // the intensity numerators:"""

content = content.replace(old_def, new_def, 1)

# Update initial state
old_init = """    totalBoe: 0,
    totalFlaringVolume: 0,
    usedCo2e: 0,"""

new_init = """    totalBoe: 0,
    totalFlaringVolume: 0,
    totalFlaringLedgerVolume: 0,
    usedCo2e: 0,"""

content = content.replace(old_init, new_init, 1)

# Update loop
old_loop = """        tFlaringVol += d.flaring_volume || 0;
        tFlaringEm += d.flaring_emissions || 0;"""

new_loop = """        tFlaringVol += d.flaring_volume || 0;
        tFlaringLedgerVol += d.flaring_ledger_volume || d.flaring_ledger_m3 || 0;
        tFlaringEm += d.flaring_emissions || 0;"""

old_vars = """      let tFlaringVol = 0;
      let tFlaringEm = 0;"""

new_vars = """      let tFlaringVol = 0;
      let tFlaringLedgerVol = 0;
      let tFlaringEm = 0;"""

content = content.replace(old_vars, new_vars, 1)
content = content.replace(old_loop, new_loop, 1)

old_set = """        totalBoe: tBoe,
        totalFlaringVolume: tFlaringVol,"""

new_set = """        totalBoe: tBoe,
        totalFlaringVolume: tFlaringVol,
        totalFlaringLedgerVolume: tFlaringLedgerVol,"""

content = content.replace(old_set, new_set, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched CarbonIntensity.tsx")
