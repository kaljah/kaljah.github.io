# Test formulas against reported numbers in Table 8 for HBNS
# Heater 2:
# Activity: 24,359,006.31 Nm3
# Reported CO2: 70,559.22 tonne
# Reported CH4: 1.237 tonne
# Reported N2O: 0.346 tonne
# Reported CO2e: 70,693.33 tonne

# Properties from Table 6:
# Carbon content: 0.771 mass fraction
# MW: 23.01 kg/kg-mole
# HHV: 1362.97 Btu/scf

vol_nm3 = 24359006.31

# Standard molar volumes:
# At 0 C, 1 atm: 22.414 m3/kg-mole (or 22.4136)
# At 15 C (288.15 K), 1 atm: 23.644 m3/kg-mole (or 23.685 at 60F)
# Or let's test various molar volumes:
for vm in [22.414, 22.4136, 22.4, 23.685 * (273.15/288.15), 23.685 * (273.0/288.0)]:
    density = 23.01 / vm # kg/Nm3
    mass_tonne = vol_nm3 * density / 1000.0
    c_tonne = mass_tonne * 0.771
    co2_tonne = c_tonne * (44.01 / 12.011) # or 44/12
    co2_tonne_int = c_tonne * (44.0 / 12.0)
    print(f"Vm: {vm:.4f} -> density: {density:.5f} -> mass: {mass_tonne:.2f} -> CO2 (44.01/12.011): {co2_tonne:.2f}, CO2 (44/12): {co2_tonne_int:.2f}")

print("Target CO2:", 70559.22)
