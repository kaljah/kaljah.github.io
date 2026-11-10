vol_nm3 = 24359006.31
co2_reported = 70559.22

# Let's check: co2_reported / vol_nm3
factor = co2_reported / vol_nm3
print(f"Reported CO2 / Nm3 = {factor:.8f} tonne CO2 / Nm3 = {factor*1000:.6f} kg CO2 / Nm3")

# Let's test with the full gas composition in Table 6:
# C1: 0.684, C2: 0.172, C3: 0.101, C4: 0.023, C5: 0.005, C6: 0.002, C7: 0.001, C8: 0.001, CO2: 0.006
comp = {
    'c1': 0.684,
    'c2': 0.172,
    'c3': 0.101,
    'c4': 0.023,
    'c5': 0.005,
    'c6': 0.002,
    'c7': 0.001,
    'c8': 0.001,
    'co2': 0.006
}

# Total carbon atoms per mole of gas:
# C1 has 1, C2 has 2, C3 has 3, C4 has 4, C5 has 5, C6 has 6, C7 has 7, C8 has 8, CO2 has 1
mol_c = (comp['c1']*1 + comp['c2']*2 + comp['c3']*3 + comp['c4']*4 + 
         comp['c5']*5 + comp['c6']*6 + comp['c7']*7 + comp['c8']*8 + comp['co2']*1)
print(f"Moles of carbon per mole of gas = {mol_c:.6f}")

# At standard conditions:
# In SANGEA / API Compendium:
# If 1 kmol of gas is V_m Nm3:
# CO2 produced per Nm3 = mol_c * (44.01 kg CO2 / kmol) / V_m
for vm in [22.414, 22.4136, 22.4, 22.413996, 23.685 * (273.0/288.0), 23.685 * (273.15/288.15)]:
    co2_per_nm3 = mol_c * 44.01 / vm / 1000.0 # tonne CO2 / Nm3
    co2_tot = vol_nm3 * co2_per_nm3
    print(f"Vm {vm:.5f} -> CO2 per Nm3 = {co2_per_nm3*1000:.6f} kg/Nm3 -> Total CO2 = {co2_tot:.2f} (diff = {co2_tot - co2_reported:.2f})")
