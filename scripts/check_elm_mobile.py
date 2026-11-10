# Check emissions of El Merk on-road fuels:
# Heavy Duty Diesel: 158,779.00 L
# Light Duty Diesel: 137,066.00 L
# Light Duty Gasoline: 98,340.00 L

# For HBNS (Table 8):
# Heavy Duty Diesel: 19,658.28 L -> CO2 = 52.723, CH4 = 0.003, N2O = 0.002, CO2e = 53.27
# Light Duty Diesel: 113,235.33 L -> CO2 = 303.693, CH4 = 0.008, N2O = 0.024, CO2e = 310.93
# Light Duty Gasoline: 110,665.36 L -> CO2 = 261.061, CH4 = 0.025, N2O = 0.053, CO2e = 277.38

# Notice the HBNS EFs:
ef_hd_diesel_co2 = 52.723 / 19658.28 # ~ 0.002682 t/L = 2.682 kg/L
ef_ld_diesel_co2 = 303.693 / 113235.33 # ~ 0.002682 t/L = 2.682 kg/L
ef_ld_gasoline_co2 = 261.061 / 110665.36 # ~ 0.002359 t/L = 2.359 kg/L

print(f"HBNS EFs: HD Diesel = {ef_hd_diesel_co2:.6f}, LD Diesel = {ef_ld_diesel_co2:.6f}, LD Gasoline = {ef_ld_gasoline_co2:.6f}")

# Now apply to El Merk:
elm_hd_diesel_co2 = 158779.00 * ef_hd_diesel_co2
elm_ld_diesel_co2 = 137066.00 * ef_ld_diesel_co2
elm_ld_gasoline_co2 = 98340.00 * ef_ld_gasoline_co2
elm_total_onroad_co2 = elm_hd_diesel_co2 + elm_ld_diesel_co2 + elm_ld_gasoline_co2

print(f"El Merk On-road CO2 calculated: HD={elm_hd_diesel_co2:.2f}, LD_D={elm_ld_diesel_co2:.2f}, LD_G={elm_ld_gasoline_co2:.2f} -> Total Onroad CO2 = {elm_total_onroad_co2:.2f}")

# Aviation CO2: 1233.79
elm_total_mobile_co2 = elm_total_onroad_co2 + 1233.79
print(f"El Merk Total Mobile CO2 = {elm_total_mobile_co2:.2f}")
print("Table 16 Mobile CO2 = 2259.22")
print(f"Difference = {elm_total_mobile_co2 - 2259.22:.2f}")

# What was the 425.84 in Table 15?
print(f"Ratio of 425.84 to hd_diesel: {425.84 / elm_hd_diesel_co2:.4f}")
print(f"Ratio of 425.84 to (hd+ld diesel): {425.84 / (elm_hd_diesel_co2 + elm_ld_diesel_co2):.4f}")
print(f"Difference between 1025.43 and 425.84: {elm_total_onroad_co2 - 425.84:.2f}")
